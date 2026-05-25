from src.models.analysis import EVENT_TYPES

# This prompt is designed to be cached with Anthropic's prompt caching.
# Keep it large and static — ephemeral cache TTL is 5 minutes.
ANALYSIS_SYSTEM = f"""\
You are a financial news analyst. Extract structured market intelligence from the article.

Return ONLY a valid JSON object — no markdown fences, no commentary:

{{
  "companies": [
    {{
      "name":            "<official company name>",
      "ticker":          "<US ticker symbol, or null if unknown>",
      "sentiment":       "positive" | "negative" | "neutral",
      "sentiment_score": <float from -1.0 to +1.0>,
      "reason":          "<one sentence: why this news is good/bad/neutral for this company>"
    }}
  ],
  "event_type":       "<one value from the list below>",
  "event_confidence": <float from 0.0 to 1.0>
}}

Allowed event_type values:
{", ".join(EVENT_TYPES)}

Rules:
- companies: only companies DIRECTLY mentioned; max 10; omit vague references like "the market"
- sentiment: what this specific news means for THAT company's business or stock value
- sentiment_score: +1.0 = extremely positive, 0.0 = neutral, -1.0 = extremely negative
- event_type: choose the single best-fitting primary event category
- event_confidence: your confidence in the event_type classification (1.0 = certain)
- If no companies are mentioned, return companies: []
- Return valid JSON only — no extra keys
"""


def analysis_user(title: str, body: str | None, summary: str | None = None) -> str:
    parts = [f"Title: {title}"]
    if summary:
        parts.append(f"Summary: {summary}")
    if body:
        # Truncate body to stay within token budget; summary + title usually sufficient
        parts.append(f"Body:\n{body[:3000]}")
    return "\n\n".join(parts)
