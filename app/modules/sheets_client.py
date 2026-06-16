"""Google Sheets public CSV client.

Fetches data from a publicly shared Google Spreadsheet using the gviz CSV
export endpoint — no API key or OAuth required.
"""
import csv
import io
import logging
import os

import httpx

logger = logging.getLogger(__name__)

_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "1J_ah9NDH5NYbXAYo0AMbzTrw8OmTva1o")
_BASE_URL = "https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet}"

SHEET_DAILY_PERFORMANCE = "Daily%20Performance"
SHEET_WEEKLY_SUMMARY = "Weekly%20Summary"
SHEET_SENTIMENT_ANALYSIS = "Sentiment%20Analysis"


async def fetch_sheet(sheet_name: str, sheet_id: str | None = None) -> list[dict]:
    """Fetch a sheet tab as a list of row dicts (header row → keys).

    Returns an empty list on error so callers degrade gracefully.
    """
    sid = sheet_id or _SHEET_ID
    url = _BASE_URL.format(sheet_id=sid, sheet=sheet_name)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, follow_redirects=True)
            r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        rows = [row for row in reader]
        logger.info("Fetched %d rows from sheet '%s'", len(rows), sheet_name)
        return rows
    except Exception as e:
        logger.error("Failed to fetch sheet '%s': %s", sheet_name, e)
        return []


def rows_to_text(rows: list[dict], max_rows: int = 50) -> str:
    """Convert sheet rows to a compact markdown table string for LLM context."""
    if not rows:
        return "(no data)"
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows[:max_rows]:
        lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
    if len(rows) > max_rows:
        lines.append(f"_(showing {max_rows} of {len(rows)} rows)_")
    return "\n".join(lines)
