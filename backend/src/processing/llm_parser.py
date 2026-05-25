import json
import logging

from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models.schemas import ParsedArticle, RawArticle
from src.processing.prompts import EXTRACTION_SYSTEM, extraction_user

logger = logging.getLogger(__name__)


class LLMParser:
    """Wraps Anthropic (primary) or OpenAI (fallback) to extract structured fields."""

    def __init__(self) -> None:
        if settings.llm_provider == "anthropic":
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            self._call = self._call_anthropic
        else:
            import openai
            self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            self._call = self._call_openai

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def parse(self, raw: RawArticle) -> ParsedArticle:
        user_msg = extraction_user(raw.title, raw.body)
        raw_json = await self._call(user_msg)
        data = _safe_parse(raw_json)
        return ParsedArticle(
            **raw.model_dump(),
            summary=data.get("summary"),
            sector=data.get("sector"),
            tags=data.get("tags") or [],
        )

    async def _call_anthropic(self, user_msg: str) -> str:
        response = await self._client.messages.create(
            model=settings.llm_model,
            max_tokens=512,
            system=EXTRACTION_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text

    async def _call_openai(self, user_msg: str) -> str:
        response = await self._client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=512,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
        )
        return response.choices[0].message.content or ""


def _safe_parse(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Strip markdown fences if the model wrapped the response anyway
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    logger.warning("Could not parse LLM response as JSON: %s", text[:200])
    return {}
