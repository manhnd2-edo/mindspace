"""Module 4 – Sentiment Tracker.

Pulls inbox/mention messages from Sprout Social, uses Claude to generate
a sentiment summary, and sends it to Teams on a weekly schedule.
"""
import logging
from collections import Counter
from datetime import date, timedelta

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


async def generate_sentiment_report(
    start: date | None = None,
    end: date | None = None,
    product: str = "PUBG Mobile VN",
    send_to_teams: bool = True,
) -> str:
    if not start or not end:
        start, end = _last_week()

    logger.info("Generating sentiment report [%s → %s]", start, end)
    raw = await sprout.get_inbox_messages(start, end)
    messages = raw.get("data", {}).get("messages", []) or raw.get("data", []) or []

    if not messages:
        report = f"Không có dữ liệu inbox/mention cho kỳ {start} → {end}."
        if send_to_teams:
            await send_teams_message(f"📬 Sentiment Report – {product}", report)
        return report

    agg = _aggregate_sentiment(messages)

    prompt = f"""Bạn là chuyên gia phân tích cộng đồng cho game {product} (VNGGames Vietnam).
Dưới đây là dữ liệu cảm xúc (sentiment) từ inbox/mention trên mạng xã hội tuần {start} đến {end}.

## Thống kê tổng hợp
- Tổng tin nhắn: {agg['total']}
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
