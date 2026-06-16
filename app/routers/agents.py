"""8 MindSpace mental-health agent endpoints.

System prompts are loaded from skills/<name>/SKILL.md at startup.
After each agent reply, a separate lightweight LLM call extracts score_update
for the dashboard — the agent itself never mentions scores.
"""
import re
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.utils.llm import chat as llm_chat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["MindSpace Agents"])

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_SKILLS_DIR   = _PROJECT_ROOT / "skills"
_SOUL_PATH    = _SKILLS_DIR / "SOUL.md"

_FEW_SHOT: dict[str, list[dict]] = {}

SKILLS = [
    "burnout-radar",
    "ritual-coach",
    "venting-space",
    "team-pulse",
    "focus-guard",
    "oneonone-facilitator",
    "boundary-keeper",
    "wellness-os",
]

# Per-agent extraction prompts — called separately, invisible to user
_EXTRACT = {
    "ritual-coach": (
        "mood",
        'Dựa trên đoạn hội thoại, tâm trạng của USER (1-10, 10=rất vui). '
        'Chỉ trả về JSON: {"type":"mood","value":<1-10>} '
        'hoặc {"type":null,"value":null} nếu không đủ thông tin.'
    ),
    "burnout-radar": (
        "burnout",
        'Dựa trên đoạn hội thoại, nguy cơ kiệt sức của USER (0-100, 100=kiệt sức hoàn toàn). '
        'Chỉ trả về JSON: {"type":"burnout","value":<0-100>} '
        'hoặc {"type":null,"value":null} nếu không đủ thông tin.'
    ),
    "focus-guard": (
        "cogload",
        'Dựa trên đoạn hội thoại, cognitive load của USER (0-100, 100=quá tải hoàn toàn). '
        'Chỉ trả về JSON: {"type":"cogload","value":<0-100>} '
        'hoặc {"type":null,"value":null} nếu không đủ thông tin.'
    ),
    "boundary-keeper": (
        "boundary",
        'Dựa trên đoạn hội thoại, ranh giới công việc của USER hôm nay. '
        'Chỉ trả về JSON: {"type":"boundary","value":"maintain"} '
        'hoặc {"type":"boundary","value":"breach"} '
        'hoặc {"type":null,"value":null} nếu không đủ thông tin.'
    ),
}


def _load_system(skill: str) -> str:
    soul = _SOUL_PATH.read_text(encoding="utf-8") if _SOUL_PATH.exists() else ""
    skill_path = _SKILLS_DIR / skill / "SKILL.md"
    if not skill_path.exists():
        logger.warning("SKILL.md not found for %s", skill)
        body = f"You are MindSpace agent: {skill}. Reply in Vietnamese."
    else:
        raw = skill_path.read_text(encoding="utf-8")
        body = re.sub(r"^---.*?---\s*", "", raw, flags=re.DOTALL).strip()

    return f"{soul}\n\n---\n\n{body}" if soul else body


_SYSTEM: dict[str, str] = {s: _load_system(s) for s in SKILLS}


def _extract_score(skill: str, user_msg: str, bot_reply: str) -> dict[str, Any]:
    if skill not in _EXTRACT:
        return {}
    _, prompt = _EXTRACT[skill]
    try:
        msgs = [{"role": "user", "content": f"User: {user_msg}\nAgent: {bot_reply}"}]
        raw = llm_chat(msgs, system=prompt, max_tokens=60)
        m = re.search(r'\{[^}]+\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            if data.get("type") and data.get("value") is not None:
                data["agent"] = skill
                return data
    except Exception as e:
        logger.warning("Score extraction failed for %s: %s", skill, e)
    return {}


class AgentRequest(BaseModel):
    message: str
    history: list[dict] = []


class AgentResponse(BaseModel):
    reply: str
    agent: str
    score_update: dict = {}


def _make_handler(skill: str):
    async def handler(req: AgentRequest) -> AgentResponse:
        seed = _FEW_SHOT.get(skill, []) if not req.history else []
        messages = seed + list(req.history) + [{"role": "user", "content": req.message}]
        logger.info("agent=%s history_len=%d", skill, len(req.history))
        reply = llm_chat(messages, system=_SYSTEM[skill], max_tokens=1500)
        score_update = _extract_score(skill, req.message, reply)
        return AgentResponse(reply=reply, agent=skill, score_update=score_update)
    handler.__name__ = skill.replace("-", "_")
    return handler


for _skill in SKILLS:
    router.post(f"/{_skill}", response_model=AgentResponse)(_make_handler(_skill))
