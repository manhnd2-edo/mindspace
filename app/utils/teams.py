import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


async def send_teams_message(title: str, text: str, color: str = "0078D7") -> bool:
    """Send an Adaptive Card message to the Teams webhook."""
    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": title,
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                        },
                        {
                            "type": "TextBlock",
                            "text": text,
                            "wrap": True,
                        },
                    ],
                },
            }
        ],
    }
    if not settings.teams_webhook_url:
        logger.debug("TEAMS_WEBHOOK_URL not configured — skipping Teams notification")
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(settings.teams_webhook_url, json=payload)
            r.raise_for_status()
            return True
    except Exception as e:
        logger.error("Failed to send Teams message: %s", e)
        return False
