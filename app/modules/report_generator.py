"""Module 1 – Report Generator.

Fetches channel performance data from Google Sheets (primary source) with
Sprout Social as fallback, asks the LLM to summarise, and sends the result
to Microsoft Teams.
"""
import logging
from datetime import date, timedelta
from typing import Literal

from app.modules.sheets_client import (
    fetch_sheet, rows_to_text,
    SHEET_DAILY_PERFORMANCE, SHEET_WEEKLY_SUMMARY,
)
from app.modules.sprout_client import sprout
from app.utils.llm import chat
from app.utils.teams import send_teams_message

logger = logging.getLogger(__name__)

ReportPeriod = Literal["weekly", "monthly", "quarterly", "yearly", "campaign"]

_SYSTEM_PROMPT = (
    "Bạn là chuyên gia phân tích social media cho VNGGames Vietnam. "
    "Viết báo cáo ngắn gọn, rõ ràng bằng tiếng Việt. "
    "Chỉ dùng số liệu từ dữ liệu được cung cấp."
)

_MAX_TABLE_ROWS = 20   # cap rows fed to LLM to keep prompt short
_MAX_TOKENS = 4096     # allow Qwen thinking mode to complete reasoning before generating
_MAX_RETRIES = 2


def _date_range(period: ReportPeriod, start: date | None, end: date | None) -> tuple[date, date]:
    today = date.today()
    if start and end:
        return start, end
    if period == "weekly":
        end = today - timedelta(days=today.weekday() + 1)  # last Sunday
        start = end - timedelta(days=6)
    elif period == "monthly":
        first_of_month = today.replace(day=1)
        end = first_of_month - timedelta(days=1)
        start = end.replace(day=1)
    elif period == "quarterly":
        q = (today.month - 1) // 3
        start = date(today.year, q * 3 + 1, 1) if q > 0 else date(today.year - 1, 10, 1)
        end = today.replace(day=1) - timedelta(days=1)
    elif period == "yearly":
        start = date(today.year - 1, 1, 1)
        end = date(today.year - 1, 12, 31)
    else:
        raise ValueError("For campaign reports, provide explicit start and end dates.")
    return start, end


def _filter_rows_by_date(rows: list[dict], start: date, end: date) -> list[dict]:
    """Return rows whose 'Date' column falls within [start, end] (inclusive)."""
    filtered = []
    for row in rows:
        raw = row.get("Date", "")
        try:
            row_date = date.fromisoformat(raw[:10])
            if start <= row_date <= end:
                filtered.append(row)
        except (ValueError, TypeError):
            filtered.append(row)
    return filtered


def _build_prompt(
    period: str,
    product: str,
    start_dt: date,
    end_dt: date,
    sheets_data: str,
) -> str:
    return (
        f"Tạo báo cáo {period} cho {product} ({start_dt} → {end_dt}).\n\n"
        f"Dữ liệu:\n{sheets_data}\n\n"
        "Viết 4 phần ngắn:\n"
        "1. Tổng quan kênh\n"
        "2. Hiệu suất nội dung\n"
        "3. Xu hướng nổi bật\n"
        "4. Khuyến nghị"
    )


async def generate_report(
    period: ReportPeriod,
    product: str = "PUBG Mobile VN",
    start: date | None = None,
    end: date | None = None,
    send_to_teams: bool = True,
) -> str:
    start_dt, end_dt = _date_range(period, start, end)
    logger.info("Generating %s report [%s → %s] for %s", period, start_dt, end_dt, product)

    # ── Primary: Google Sheets (capped to avoid oversized prompts) ────────────
    sheet_name = SHEET_WEEKLY_SUMMARY if period == "weekly" else SHEET_DAILY_PERFORMANCE
    rows = await fetch_sheet(sheet_name)
    rows = _filter_rows_by_date(rows, start_dt, end_dt)
    sheets_data = rows_to_text(rows, max_rows=_MAX_TABLE_ROWS)

    # If Sheets returned nothing, try Sprout Social summary as fallback text
    if not rows:
        try:
            profile_data = await sprout.get_profile_analytics(start_dt, end_dt)
            sheets_data = str(profile_data)[:800]
        except Exception as e:
            logger.warning("Sprout Social also unavailable: %s", e)
            sheets_data = "Không có dữ liệu."

    prompt = _build_prompt(period, product, start_dt, end_dt, sheets_data)

    # ── LLM call with retry on empty content ─────────────────────────────────
    report_text = ""
    for attempt in range(1, _MAX_RETRIES + 2):  # 1, 2, 3
        report_text = chat(
            [{"role": "user", "content": prompt}],
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
        )
        if report_text:
            break
        logger.warning("LLM returned empty content (attempt %d/%d)", attempt, _MAX_RETRIES + 1)

    if not report_text:
        report_text = f"Không thể tạo báo cáo {period} sau {_MAX_RETRIES + 1} lần thử."
        logger.error("All LLM attempts returned empty for period=%s product=%s", period, product)

    if send_to_teams:
        title = f"📊 {period.capitalize()} Report – {product} ({start_dt} → {end_dt})"
        await send_teams_message(title, report_text)

    return report_text
