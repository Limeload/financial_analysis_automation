"""
ArticleAnalyzer — LLM wrapper for market analysis.

Design choices for throughput:
  - asyncio.Semaphore caps concurrent LLM calls per process
  - Anthropic prompt caching on the system prompt (saves ~90% of system-prompt tokens
    after the first call; cache TTL is 5 min, refreshed on every call within that window)
  - tenacity retry with exponential back-off for transient API errors
  - Single LLM call per article returns companies + sentiment + event type together
"""
import asyncio
import json
import logging
import re

from tenacity import retry, stop_after_attempt, wait_exponential

from src.analysis.prompts import ANALYSIS_SYSTEM, analysis_user
from src.config import settings

logger = logging.getLogger(__name__)


class ArticleAnalyzer:
    def __init__(self) -> None:
        self._sem = asyncio.Semaphore(settings.analysis_concurrency)
        if settings.llm_provider == "anthropic":
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            self._call = self._call_anthropic
        else:
            import openai
            self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            self._call = self._call_openai

    async def analyze(
        self,
        article_id: int,
        title: str,
        body: str | None = None,
        summary: str | None = None,
    ) -> dict:
        async with self._sem:
            return await self._run(article_id, title, body, summary)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _run(
        self,
        article_id: int,
        title: str,
        body: str | None,
        summary: str | None,
    ) -> dict:
        try:
            user_msg = analysis_user(title, body, summary)
            raw = await self._call(user_msg)
            data = _safe_parse(raw)
        except Exception as exc:
            logger.warning("LLM analysis failed (%s), saving with defaults", exc)
            data = {"companies": [], "event_type": "other", "event_confidence": 0.0}
        data["article_id"] = article_id
        return data

    async def _call_anthropic(self, user_msg: str) -> str:
        # system is passed as a list to enable prompt caching on the static block
        resp = await self._client.messages.create(
            model=settings.llm_model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": ANALYSIS_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_msg}],
        )
        # Log cache hit info for observability
        usage = getattr(resp, "usage", None)
        if usage and getattr(usage, "cache_read_input_tokens", 0):
            logger.debug(
                "Cache hit — saved %d tokens", usage.cache_read_input_tokens
            )
        return resp.content[0].text

    async def _call_openai(self, user_msg: str) -> str:
        resp = await self._client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": ANALYSIS_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
        )
        return resp.choices[0].message.content or ""


def _safe_parse(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    logger.warning("Could not parse analysis response: %.200s", text)
    return {"companies": [], "event_type": "other", "event_confidence": 0.0}
