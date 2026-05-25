import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.models.schemas import RawArticle
from src.processing.llm_parser import LLMParser, _safe_parse


RAW = RawArticle(
    source="thenewsapi",
    url="https://example.com/1",
    title="Apple reports record Q2 earnings",
    body="Apple Inc. reported record quarterly earnings on Monday...",
)

LLM_JSON = json.dumps({
    "summary": "Apple posted record Q2 earnings driven by iPhone sales.",
    "sector": "Technology",
    "tags": ["Apple", "AAPL", "earnings", "iPhone"],
})


@pytest.mark.asyncio
async def test_llm_parser_anthropic():
    with patch("anthropic.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=LLM_JSON)]
        mock_client.messages.create = AsyncMock(return_value=mock_msg)

        with patch("src.config.settings") as mock_settings:
            mock_settings.llm_provider = "anthropic"
            mock_settings.anthropic_api_key = "test"
            mock_settings.llm_model = "claude-sonnet-4-6"
            parser = LLMParser()
            parser._client = mock_client
            parser._call = parser._call_anthropic

            parsed = await parser.parse(RAW)

    assert parsed.sector == "Technology"
    assert "Apple" in parsed.tags
    assert parsed.summary.startswith("Apple posted")


def test_safe_parse_clean_json():
    result = _safe_parse(LLM_JSON)
    assert result["sector"] == "Technology"


def test_safe_parse_with_fences():
    wrapped = f"```json\n{LLM_JSON}\n```"
    result = _safe_parse(wrapped)
    assert result["sector"] == "Technology"


def test_safe_parse_invalid_returns_empty():
    result = _safe_parse("not json at all")
    assert result == {}
