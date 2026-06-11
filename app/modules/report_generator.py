"""Module 1 – Report Generator.

Pulls channel performance from Sprout Social, asks the LLM to summarise,
and sends the result to Microsoft Teams.
"""
import logging
from datetime import date, timedelta
from typing import Literal

from app.modules.sprout_client import sprout
from app.utils.llm import chat
from app.utils.teams import send_teams_message

logger = logging.getLogger(__name__)

ReportPeriod = Literal["weekly", "monthly", "quarterly", "yearly", "campaign"]


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


async def generate_report(
    period: ReportPeriod,
    product: str = "PUBG Mobile VN",
    start: date | None = None,
    end: date | None = None,
    send_to_teams: bool = True,
) -> str:
    start_dt, end_dt = _date_range(period, start, end)
    logger.info("Generating %s report [%s → %s] for %s", period, start_dt, end_dt, product)

    profile_data = await sprout.get_profile_analytics(start_dt, end_dt)
    post_data = await sprout.get_post_analytics(start_dt, end_dt)

    prompt = f"""You are a social media analyst for {product} (VNGGames Vietnam).
Analyse the following Sprout Social data and produce a concise {period} performance report in Vietnamese.

## Profile Metrics
{profile_data}

## Post Metrics (top posts)
{post_data}

Report structure:
1. Tổng quan kênh (followers, tăng trưởng)
2. Hiệu suất nội dung (reach, engagement rate, top posts)
3. Nhận xét xu hướng
4. Khuyến nghị tuần/kỳ tiếp theo

Be specific with numbers. Format clearly with markdown headings."""

    report_text = chat([{"role": "user", "content": prompt}], max_tokens=2048)

    if send_to_teams:
        title = f"📊 {period.capitalize()} Report – {product} ({start_dt} → {end_dt})"
        await send_teams_message(title, report_text)

    return report_text
