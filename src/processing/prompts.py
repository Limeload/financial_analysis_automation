EXTRACTION_SYSTEM = """\
You are a financial news analyst. Extract structured metadata from the article provided.
Return ONLY a valid JSON object with these exact keys — no markdown fences, no extra text:

{
  "summary":   "<2-3 sentence neutral summary of the article>",
  "sector":    "<one of: Technology, Finance, Healthcare, Energy, Consumer, Industrials, \
Real Estate, Materials, Utilities, Telecom, Government, Other>",
  "tags":      ["<entity or keyword>", ...]   // 3-8 concise tags
}

Rules:
- summary: be factual and concise, no opinion.
- sector: pick exactly one from the list above.
- tags: named entities (companies, people, places), product names, key themes.
- If a field cannot be determined, use null for scalars and [] for arrays.
"""


def extraction_user(title: str, body: str | None) -> str:
    content = f"Title: {title}\n\nBody:\n{body or '(no body provided)'}"
    return content
