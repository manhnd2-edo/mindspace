"""Shared OpenAI-compatible client pointed at GreenNode MaaS."""
from openai import OpenAI
from app.config import settings

client = OpenAI(
    api_key=settings.greennode_api_key,
    base_url=settings.greennode_base_url,
)
MODEL = settings.greennode_model


def chat(messages: list[dict], max_tokens: int = 2048, system: str | None = None) -> str:
    """Call the model and return the assistant reply text."""
    if system:
        messages = [{"role": "system", "content": system}] + list(messages)
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
