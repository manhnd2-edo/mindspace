"""Shared OpenAI-compatible client pointed at GreenNode MaaS."""
import logging
from openai import OpenAI, APIError
from app.config import settings

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=settings.greennode_api_key,
    base_url=settings.greennode_base_url,
)
PRIMARY_MODEL = settings.greennode_model
FALLBACK_MODEL = settings.greennode_fallback_model


def chat(messages: list[dict], max_tokens: int = 4096, system: str | None = None) -> str:
    """Call the model and return the assistant reply text. Falls back to FALLBACK_MODEL on error."""
    import re as _re
    if system:
        messages = [{"role": "system", "content": system}] + list(messages)
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
            )
            msg = response.choices[0].message
            content = msg.content or ""
            # Strip <think>...</think> blocks that some models leak into content
            content = _re.sub(r"<think>.*?</think>", "", content, flags=_re.DOTALL).strip()
            if content:
                return content
            logger.warning("Model %s returned empty content, trying next.", model)
        except APIError as e:
            logger.warning("Model %s failed (%s), trying next.", model, e)
    raise RuntimeError("All models failed")
