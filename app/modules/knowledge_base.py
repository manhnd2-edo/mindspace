"""Module 2 – Knowledge Base + Social Plan Generator.

Stores product knowledge as JSON files in data/knowledge/.
LLM uses retrieved entries to generate social content plans.
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.utils.llm import chat

logger = logging.getLogger(__name__)
KB_DIR = Path("data/knowledge")
KB_DIR.mkdir(parents=True, exist_ok=True)


# ── Storage helpers ───────────────────────────────────────────────────────────

def _all_entries() -> list[dict[str, Any]]:
    entries = []
    for f in KB_DIR.glob("*.json"):
        try:
            entries.append(json.loads(f.read_text()))
        except Exception:
            pass
    return sorted(entries, key=lambda e: e.get("created_at", ""), reverse=True)


def add_entry(title: str, content: str, tags: list[str] | None = None) -> dict:
    entry = {
        "id": str(uuid.uuid4()),
        "title": title,
        "content": content,
        "tags": tags or [],
        "created_at": datetime.utcnow().isoformat(),
    }
    (KB_DIR / f"{entry['id']}.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2))
    logger.info("KB entry added: %s", title)
    return entry


def search_entries(query: str, limit: int = 10) -> list[dict]:
    q = query.lower()
    results = []
    for entry in _all_entries():
        score = 0
        if q in entry["title"].lower():
            score += 3
        if q in entry["content"].lower():
            score += 1
        for tag in entry.get("tags", []):
            if q in tag.lower():
                score += 2
        if score:
            results.append((score, entry))
    results.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in results[:limit]]


def list_entries(limit: int = 20) -> list[dict]:
    return _all_entries()[:limit]


def delete_entry(entry_id: str) -> bool:
    path = KB_DIR / f"{entry_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


# ── Plan generator ────────────────────────────────────────────────────────────

async def generate_social_plan(
    product: str,
    period: str,
    topic: str,
    extra_context: str = "",
) -> str:
    """Generate a social media content plan (AWO/update) using KB entries + Claude."""
    relevant = search_entries(topic) or search_entries(product)
    kb_context = "\n\n".join(
        f"[{e['title']}]\n{e['content']}" for e in relevant[:5]
    ) or "No specific knowledge entries found."

    prompt = f"""Bạn là Social Media Planner cho game {product} (VNGGames Vietnam).
Dựa trên kiến thức bên dưới, hãy tạo kế hoạch nội dung social media cho **{period}** với chủ đề: **{topic}**.

## Kiến thức sản phẩm
{kb_context}

## Yêu cầu bổ sung
{extra_context or 'Không có.'}

## Cấu trúc kế hoạch cần có:
1. Mục tiêu chiến dịch
2. Thông điệp chính (key message)
3. Lịch đăng bài theo ngày (bao gồm: ngày, kênh, dạng nội dung, caption gợi ý, hashtag)
4. KPI dự kiến
5. Lưu ý sản xuất nội dung

Trình bày rõ ràng, dùng bảng Markdown cho lịch đăng bài."""

    return chat([{"role": "user", "content": prompt}], max_tokens=3000)
