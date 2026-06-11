"""Module 3 – Airtable Monitor.

Connects to an Airtable content-planning base, checks for anomalies,
and sends alerts to Microsoft Teams.
"""
import logging
from datetime import date, timedelta
from typing import Any

import httpx

from app.config import settings
from app.utils.teams import send_teams_message

logger = logging.getLogger(__name__)
AIRTABLE_API = "https://api.airtable.com/v0"


class AirtableClient:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.airtable_token}",
            "Content-Type": "application/json",
        }
        self.base_id = settings.airtable_base_id
        self.table = settings.airtable_table_name

    async def list_records(self, filter_formula: str | None = None) -> list[dict[str, Any]]:
        url = f"{AIRTABLE_API}/{self.base_id}/{self.table}"
        params: dict[str, Any] = {"pageSize": 100}
        if filter_formula:
            params["filterByFormula"] = filter_formula

        records: list[dict] = []
        offset = None
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                if offset:
                    params["offset"] = offset
                r = await client.get(url, headers=self.headers, params=params)
                r.raise_for_status()
                data = r.json()
                records.extend(data.get("records", []))
                offset = data.get("offset")
                if not offset:
                    break
        return records


airtable = AirtableClient()

# ── Anomaly detection ─────────────────────────────────────────────────────────

_EXPECTED_POSTS_PER_WEEK = 5  # configurable baseline


def _check_records(records: list[dict]) -> list[str]:
    issues: list[str] = []
    today = date.today()
    week_ago = today - timedelta(days=7)

    missing_link: list[str] = []
    unposted: list[str] = []
    recent_posted = 0

    for rec in records:
        fields = rec.get("fields", {})
        name = fields.get("Name") or fields.get("Title") or rec.get("id")
        post_date_str = fields.get("Post Date") or fields.get("Scheduled Date") or ""
        status = (fields.get("Status") or "").lower()
        post_link = fields.get("Post Link") or fields.get("Link") or ""

        # Count posts in the last 7 days
        try:
            post_date = date.fromisoformat(post_date_str[:10])
        except (ValueError, TypeError):
            post_date = None

        if post_date and week_ago <= post_date <= today:
            if status in ("published", "posted", "done", "completed"):
                recent_posted += 1
            if status in ("published", "posted", "done", "completed") and not post_link:
                missing_link.append(str(name))

        # Flag scheduled but not posted content past its date
        if post_date and post_date < today and status not in ("published", "posted", "done", "completed", "cancelled"):
            unposted.append(f"{name} (ngày {post_date})")

    if missing_link:
        issues.append(f"⚠️ **{len(missing_link)} bài thiếu link đăng**: {', '.join(missing_link[:10])}")

    if unposted:
        issues.append(f"🔴 **{len(unposted)} bài chưa đăng dù đã quá ngày**: {', '.join(unposted[:10])}")

    if recent_posted < _EXPECTED_POSTS_PER_WEEK:
        issues.append(
            f"📉 **Số bài đăng tuần này thấp hơn kỳ vọng**: {recent_posted}/{_EXPECTED_POSTS_PER_WEEK} bài"
        )

    return issues


async def run_daily_check() -> list[str]:
    """Run anomaly check and send Teams alert if issues found. Returns list of issues."""
    logger.info("Running daily Airtable check")
    try:
        records = await airtable.list_records()
        issues = _check_records(records)
        if issues:
            title = "🚨 Airtable Monitor – Phát hiện bất thường"
            body = "\n\n".join(issues)
            await send_teams_message(title, body)
            logger.warning("Airtable issues found: %d", len(issues))
        else:
            logger.info("Airtable check passed – no issues found")
        return issues
    except Exception as e:
        logger.error("Airtable check failed: %s", e)
        await send_teams_message("❌ Airtable Monitor – Lỗi", f"Không thể kiểm tra Airtable: {e}")
        return [str(e)]


async def get_records_summary() -> dict[str, Any]:
    """Return a quick summary of current Airtable content plan."""
    records = await airtable.list_records()
    statuses: dict[str, int] = {}
    for rec in records:
        status = rec.get("fields", {}).get("Status") or "Unknown"
        statuses[status] = statuses.get(status, 0) + 1
    return {"total": len(records), "by_status": statuses}
