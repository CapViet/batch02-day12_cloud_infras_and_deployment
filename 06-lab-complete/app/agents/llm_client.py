"""Shared LLM client — Gemini via Google's OpenAI-compatible endpoint.

Falls back to ``None`` (mock mode) when GOOGLE_API_KEY is not configured, or
when the Gemini call itself fails (rate limit, outage, etc.), so the service
degrades gracefully instead of returning a 500.
"""
import logging

from openai import AsyncOpenAI, OpenAIError

from app.config import settings

logger = logging.getLogger(__name__)

GOOGLE_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

_client: AsyncOpenAI | None = None
if settings.google_api_key:
    _client = AsyncOpenAI(api_key=settings.google_api_key, base_url=GOOGLE_OPENAI_BASE_URL)


async def chat(system_prompt: str, question: str) -> str | None:
    """Run a single-turn chat completion. Returns None in mock mode or on error."""
    if _client is None:
        return None

    try:
        response = await _client.chat.completions.create(
            model=settings.google_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except OpenAIError:
        logger.warning("Gemini call failed, falling back to mock response", exc_info=True)
        return None
