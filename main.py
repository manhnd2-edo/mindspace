"""NOVA (No-touch Operations & Virtual Assistant) — AgentBase entrypoint.

Routes Vietnamese/English requests to one of four modules:
  - report     → Report Generator (Sprout Social data)
  - airtable   → Airtable Monitor (content plan anomalies)
  - knowledge  → Knowledge Base (store/search/generate social plans)
  - sentiment  → Sentiment Tracker (weekly community sentiment)
"""
import logging
import os
from datetime import date
from dotenv import load_dotenv
import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse
from greennode_agentbase import GreenNodeAgentBaseApp, RequestContext, PingStatus

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = GreenNodeAgentBaseApp()

# ── Intent detection ──────────────────────────────────────────────────────────

_REPORT_KW = {"report", "báo cáo", "weekly", "monthly", "quarterly", "yearly", "campaign", "hiệu suất", "thống kê"}
_AIRTABLE_KW = {"airtable", "content plan", "kiểm tra", "bất thường", "anomaly", "monitor", "lịch đăng", "unposted", "missing"}
_KB_KW = {"knowledge", "kiến thức", "kế hoạch", "content", "plan", "generate plan", "add entry", "thêm", "tìm kiếm", "search kb", "social plan"}
_SENTIMENT_KW = {"sentiment", "cảm xúc", "cộng đồng", "community", "inbox", "mention", "tình cảm", "phản hồi"}


def _detect_intent(text: str) -> str:
    if not isinstance(text, str):
        return "unknown"
    t = text.lower()
    scores = {
        "report": sum(1 for kw in _REPORT_KW if kw in t),
        "airtable": sum(1 for kw in _AIRTABLE_KW if kw in t),
        "knowledge": sum(1 for kw in _KB_KW if kw in t),
        "sentiment": sum(1 for kw in _SENTIMENT_KW if kw in t),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def _parse_date(val: str | None) -> date | None:
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None


# ── Module handlers ───────────────────────────────────────────────────────────

async def _handle_report(payload: dict) -> dict:
    from app.modules.report_generator import generate_report, ReportPeriod

    period: ReportPeriod = payload.get("period", "weekly")
    valid_periods = {"weekly", "monthly", "quarterly", "yearly", "campaign"}
    if period not in valid_periods:
        return {"error": f"Invalid period '{period}'. Must be one of: {sorted(valid_periods)}"}

    start = _parse_date(payload.get("start_date"))
    end = _parse_date(payload.get("end_date"))
    product = payload.get("product", "PUBG Mobile VN")
    send_to_teams = payload.get("send_to_teams", True)

    report = await generate_report(period=period, product=product, start=start, end=end, send_to_teams=send_to_teams)
    if not report:
        logger.warning("generate_report returned empty/None for period=%s product=%s", period, product)
        return {"module": "report", "period": period, "product": product, "report": None,
                "error": "LLM returned empty content — please retry"}
    return {"module": "report", "period": period, "product": product, "report": report}


async def _handle_airtable(payload: dict) -> dict:
    from app.modules.airtable_monitor import run_daily_check, get_records_summary

    action = payload.get("action", "check")
    if action == "summary":
        summary = await get_records_summary()
        return {"module": "airtable", "action": "summary", "data": summary}

    issues = await run_daily_check()
    return {
        "module": "airtable",
        "action": "check",
        "issues_found": len(issues),
        "issues": issues,
    }


async def _handle_knowledge(payload: dict) -> dict:
    from app.modules.knowledge_base import (
        add_entry, search_entries, list_entries, delete_entry, generate_social_plan
    )

    action = payload.get("action", "list")

    if action == "add":
        title = payload.get("title", "")
        content = payload.get("content", "")
        if not title or not content:
            return {"error": "Fields 'title' and 'content' are required for action 'add'"}
        tags = payload.get("tags", [])
        entry = add_entry(title=title, content=content, tags=tags)
        return {"module": "knowledge", "action": "add", "entry": entry}

    if action == "search":
        query = payload.get("query", "")
        if not query:
            return {"error": "Field 'query' is required for action 'search'"}
        results = search_entries(query=query, limit=payload.get("limit", 10))
        return {"module": "knowledge", "action": "search", "query": query, "results": results}

    if action == "list":
        entries = list_entries(limit=payload.get("limit", 20))
        return {"module": "knowledge", "action": "list", "entries": entries}

    if action == "delete":
        entry_id = payload.get("entry_id", "")
        if not entry_id:
            return {"error": "Field 'entry_id' is required for action 'delete'"}
        deleted = delete_entry(entry_id)
        return {"module": "knowledge", "action": "delete", "entry_id": entry_id, "deleted": deleted}

    if action == "generate_plan":
        product = payload.get("product", "PUBG Mobile VN")
        period = payload.get("period", "tuần này")
        topic = payload.get("topic", "")
        if not topic:
            return {"error": "Field 'topic' is required for action 'generate_plan'"}
        plan = await generate_social_plan(
            product=product,
            period=period,
            topic=topic,
            extra_context=payload.get("extra_context", ""),
        )
        return {"module": "knowledge", "action": "generate_plan", "plan": plan}

    return {"error": f"Unknown knowledge action '{action}'. Valid: add, search, list, delete, generate_plan"}


async def _handle_sentiment(payload: dict) -> dict:
    from app.modules.sentiment_tracker import generate_sentiment_report

    start = _parse_date(payload.get("start_date"))
    end = _parse_date(payload.get("end_date"))
    product = payload.get("product", "PUBG Mobile VN")
    send_to_teams = payload.get("send_to_teams", True)

    report = await generate_sentiment_report(start=start, end=end, product=product, send_to_teams=send_to_teams)
    return {"module": "sentiment", "product": product, "report": report}


# ── Main entrypoint ───────────────────────────────────────────────────────────

@app.entrypoint
async def handler(payload: dict, context: RequestContext) -> dict:
    """Route request to the correct module based on 'module' field or intent detection."""
    module = payload.get("module") or _detect_intent(payload.get("message", ""))

    logger.info("Request module=%s session=%s", module, context.session_id)

    try:
        return await _dispatch(module, payload)
    except Exception as e:
        logger.error("Handler error: %s", e)
        return {"error": str(e), "module": module}


async def _dispatch(module: str, payload: dict) -> dict:
    if module == "report":
        return await _handle_report(payload)
    if module == "airtable":
        return await _handle_airtable(payload)
    if module == "knowledge":
        return await _handle_knowledge(payload)
    if module == "sentiment":
        return await _handle_sentiment(payload)
    return await _handle_chat(payload)


async def _handle_chat(payload: dict) -> dict:
    """Conversational fallback: pass the user message to the LLM directly."""
    from app.utils.llm import chat

    message = payload.get("message", "")
    if not message:
        return {
            "error": "Could not determine module. Set 'module' to one of: report, airtable, knowledge, sentiment",
            "hint": "Or include keywords in 'message' field for auto-routing (EN/VI supported)",
            "modules": {
                "report": "Generate weekly/monthly/quarterly/yearly/campaign social media reports",
                "airtable": "Check content planning anomalies (missing links, unposted, low count)",
                "knowledge": "Store/search game knowledge and generate social content plans",
                "sentiment": "Weekly sentiment summary from social channels",
            },
        }

    system = (
        "Bạn là NOVA - AI assistant cho social media team PUBG Mobile VN tại VNGGames. "
        "Bạn thông minh, thân thiện, trả lời tiếng Việt. "
        "Bạn có thể giúp về: báo cáo social media, kiểm tra content plan Airtable, "
        "phân tích sentiment, knowledge base game. "
        "Nếu user hỏi về các chủ đề khác, hãy trả lời tự nhiên và gợi ý các chức năng của NOVA."
    )
    reply = chat([{"role": "user", "content": message}], system=system)
    logger.info("Chat fallback reply length=%d", len(reply))
    return {"module": "chat", "message": message, "reply": reply}


@app.ping
def health_check() -> PingStatus:
    return PingStatus.HEALTHY


# ── Zalo webhook ──────────────────────────────────────────────────────────────

async def _zalo_reply(chat_id: str, text: str) -> None:
    token = os.environ.get("ZALO_BOT_TOKEN", "")
    if not token:
        logger.warning("ZALO_BOT_TOKEN not set — skipping reply")
        return
    url = f"https://bot-api.zaloplatforms.com/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text[:2000]}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload)
        if r.status_code != 200:
            logger.error("Zalo reply failed: %s %s", r.status_code, r.text)


async def zalo_webhook(request: Request) -> JSONResponse:
    """Handle POST /zalo-webhook from Zalo Bot API."""
    secret_token = os.environ.get("ZALO_SECRET_TOKEN", "")
    if secret_token:
        # Zalo Bot API sends the secret as a plain header X-Bot-Api-Secret-Token
        incoming = request.headers.get("x-bot-api-secret-token", "")
        if incoming != secret_token:
            logger.warning("Zalo webhook token mismatch (got=%r)", incoming[:8] + "..." if incoming else "(empty)")
            return JSONResponse({"error": "Forbidden"}, status_code=403)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    result_obj = body.get("result") or body
    event = result_obj.get("event_name", "")
    if event != "message.text.received":
        return JSONResponse({"ok": True})

    message = result_obj.get("message") or {}
    text = message.get("text", "").strip()
    chat_id = (message.get("chat") or {}).get("id", "")

    logger.info("Zalo message chat=%s text=%r", chat_id, text[:80])

    if not text:
        return JSONResponse({"ok": True})

    module = _detect_intent(text)
    try:
        result = await _dispatch(module, {"message": text, "send_to_teams": False})
        reply_text = (
            result.get("report")
            or result.get("plan")
            or result.get("reply")
            or result.get("error")
            or str(result)
        )
    except Exception as e:
        logger.error("Zalo dispatch error: %s", e)
        reply_text = f"Xin lỗi, đã có lỗi xảy ra: {e}"

    await _zalo_reply(chat_id, reply_text)
    return JSONResponse({"ok": True})


async def zalo_webhook_verify(request: Request) -> JSONResponse:
    """Handle GET /zalo-webhook — Zalo webhook URL verification."""
    return JSONResponse({"ok": True})


app.add_route("/zalo-webhook", zalo_webhook, methods=["POST"])
app.add_route("/zalo-webhook", zalo_webhook_verify, methods=["GET"])


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
