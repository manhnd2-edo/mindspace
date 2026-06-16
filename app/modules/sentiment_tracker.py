"""Module 4 – Sentiment Tracker.

Fetches sentiment data from Google Sheets (primary source) with Sprout Social
as fallback, uses the LLM to generate a summary, and sends it to Teams.
"""
import logging
from collections import Counter
from datetime import date, timedelta

from app.modules.sheets_client import (
    fetch_sheet, rows_to_text,
    SHEET_SENTIMENT_ANALYSIS,
)
from app.modules.sprout_client import sprout
from app.utils.llm import chat
from app.utils.teams import send_teams_message

logger = logging.getLogger(__name__)


def _last_week() -> tuple[date, date]:
    today = date.today()
    end = today - timedelta(days=today.weekday() + 1)
    start = end - timedelta(days=6)
    return start, end


def _aggregate_sentiment(messages: list[dict]) -> dict:
    counter: Counter = Counter()
    samples: dict[str, list[str]] = {"POSITIVE": [], "NEGATIVE": [], "NEUTRAL": []}
    for msg in messages:
        sentiment = (msg.get("sentiment") or "NEUTRAL").upper()
        counter[sentiment] += 1
        text = msg.get("text", "")
        if text and len(samples[sentiment]) < 3:
            samples[sentiment].append(text[:200])
    return {"counts": dict(counter), "samples": samples, "total": sum(counter.values())}


def _aggregate_sheets_sentiment(rows: list[dict]) -> dict:
    """Aggregate sentiment rows from Google Sheets.

    Expected columns: Sentiment (POSITIVE/NEGATIVE/NEUTRAL), Comment/Text, Date.
    Falls back gracefully when columns differ.
    """
    counter: Counter = Counter()
    samples: dict[str, list[str]] = {"POSITIVE": [], "NEGATIVE": [], "NEUTRAL": []}
    for row in rows:
        sentiment = (
            row.get("Sentiment") or row.get("sentiment") or "NEUTRAL"
        ).upper().strip()
        if sentiment not in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
            sentiment = "NEUTRAL"
        counter[sentiment] += 1
        text = row.get("Comment") or row.get("Text") or row.get("text") or ""
        if text and len(samples[sentiment]) < 3:
            samples[sentiment].append(str(text)[:200])
    return {"counts": dict(counter), "samples": samples, "total": sum(counter.values())}


async def generate_sentiment_report(
    start: date | None = None,
    end: date | None = None,
    product: str = "PUBG Mobile VN",
    send_to_teams: bool = True,
) -> str:
    if not start or not end:
        start, end = _last_week()

    logger.info("Generating sentiment report [%s → %s]", start, end)

    # ── Primary: Google Sheets Sentiment Analysis tab ─────────────────────────
    sheet_rows = await fetch_sheet(SHEET_SENTIMENT_ANALYSIS)
    # Filter by date if a Date column exists
    filtered_rows = []
    for row in sheet_rows:
        raw_date = row.get("Date", "")
        try:
            row_date = date.fromisoformat(str(raw_date)[:10])
            if start <= row_date <= end:
                filtered_rows.append(row)
        except (ValueError, TypeError):
            filtered_rows.append(row)

    sheets_table = rows_to_text(filtered_rows, max_rows=100)

    if filtered_rows:
        agg = _aggregate_sheets_sentiment(filtered_rows)
        data_source = "Google Sheets"
    else:
        # ── Fallback: Sprout Social ───────────────────────────────────────────
        logger.info("No Sheets data — falling back to Sprout Social")
        try:
            raw = await sprout.get_inbox_messages(start, end)
            messages = raw.get("data", {}).get("messages", []) or raw.get("data", []) or []
        except Exception as e:
            logger.warning("Sprout Social also unavailable: %s", e)
            messages = []

        if not messages:
            report = f"Không có dữ liệu sentiment cho kỳ {start} → {end}."
            if send_to_teams:
                await send_teams_message(f"📬 Sentiment Report – {product}", report)
            return report

        agg = _aggregate_sentiment(messages)
        data_source = "Sprout Social"
        sheets_table = "(no Google Sheets data)"

    prompt = f"""Bạn là chuyên gia phân tích cộng đồng cho game {product} (VNGGames Vietnam).
Dưới đây là dữ liệu cảm xúc (sentiment) từ {data_source}, tuần {start} đến {end}.

## Bảng dữ liệu chi tiết ({data_source})
{sheets_table}

## Thống kê tổng hợp
- Tổng bình luận: {agg['total']}
- Tích cực (POSITIVE): {agg['counts'].get('POSITIVE', 0)}
- Tiêu cực (NEGATIVE): {agg['counts'].get('NEGATIVE', 0)}
- Trung lập (NEUTRAL): {agg['counts'].get('NEUTRAL', 0)}

## Mẫu bình luận tích cực
{chr(10).join('- ' + s for s in agg['samples']['POSITIVE']) or 'Không có.'}

## Mẫu bình luận tiêu cực
{chr(10).join('- ' + s for s in agg['samples']['NEGATIVE']) or 'Không có.'}

## Yêu cầu báo cáo:
1. Tổng quan cảm xúc cộng đồng tuần này
2. Các chủ đề nổi bật (từ bình luận mẫu)
3. Điểm đáng chú ý / rủi ro truyền thông
4. Đề xuất phản hồi cộng đồng

Viết ngắn gọn, súc tích bằng tiếng Việt."""

    report_text = chat([{"role": "user", "content": prompt}], max_tokens=1500)

    if send_to_teams:
        title = f"💬 Weekly Sentiment Report – {product} ({start} → {end})"
        await send_teams_message(title, report_text)

    return report_text


async def run_weekly_sentiment():
    """Scheduled job: generate and send weekly sentiment report."""
    try:
        await generate_sentiment_report(send_to_teams=True)
    except Exception as e:
        logger.error("Weekly sentiment job failed: %s", e)
        await send_teams_message("❌ Sentiment Tracker – Lỗi", f"Không thể tạo báo cáo sentiment: {e}")
