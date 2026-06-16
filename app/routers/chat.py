"""Conversational chat endpoint.

The agent interprets free-text requests and routes them to the correct module,
or answers general questions about game products using the knowledge base.
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.modules.knowledge_base import search_entries
from app.utils.llm import chat as llm_chat

logger = logging.getLogger(__name__)
router = APIRouter()

SYSTEM_PROMPT = """Bạn là NOVA (No-touch Operations & Virtual Assistant) – trợ lý AI cho team Social Media của VNGGames (PUBG Mobile VN, VALORANT, Roblox, TFT, LoL).

Bạn có thể giúp:
1. Tạo report (Weekly/Monthly/Quarterly/Yearly/Campaign) – dùng /report/generate
2. Tạo kế hoạch nội dung social (AWO/update plan) – dùng /knowledge/plan
3. Thêm kiến thức sản phẩm mới – dùng /knowledge/entries
4. Kiểm tra Airtable – dùng /airtable/check
5. Tạo báo cáo sentiment – dùng /sentiment/report

Trả lời ngắn gọn, dùng tiếng Việt. Nếu user yêu cầu hành động, hướng dẫn họ gọi đúng API endpoint hoặc cung cấp thông tin cần thiết.
"""


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("")
async def chat(req: ChatRequest):
    # Retrieve relevant KB context
    kb_hits = search_entries(req.message, limit=3)
    kb_context = ""
    if kb_hits:
        kb_context = "\n\n[Kiến thức liên quan từ Knowledge Base]\n" + "\n".join(
            f"- {e['title']}: {e['content'][:300]}" for e in kb_hits
        )

    messages = list(req.history)
    messages.append({"role": "user", "content": req.message + kb_context})

    reply = llm_chat(messages, max_tokens=1024, system=SYSTEM_PROMPT)
    return {"reply": reply}
