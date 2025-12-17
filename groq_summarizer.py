# groq_summarizer.py
import os
from typing import Any, Dict

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def _build_summary_prompt(
    keyword: str,
    domain: str,
    rank: int | None,
    serp_rows: list[Dict[str, Any]],
    analysis: Dict[str, Any],
) -> str:
    lines = []
    lines.append(f"Keyword: {keyword}")
    lines.append(f"Target domain: {domain}")
    lines.append(f"Current rank: {rank if rank is not None else 'Not in top 10'}")

    lines.append("\nTop 5 search results:")
    for row in serp_rows[:5]:
        lines.append(
            f"- #{row['position']} | {row['domain']} | title: {row['title'][:80]}"
        )

    target = analysis.get("target")
    comps = analysis.get("competitors", [])

    lines.append("\nTarget page analysis:")
    if target:
        lines.append(
            f"- URL: {target['url']}\n"
            f"- score: {target['score']}\n"
            f"- word_count: {target['word_count']}\n"
            f"- keyword_in_title: {target['keyword_in_title']}\n"
            f"- keyword_in_h1: {target['keyword_in_h1']}\n"
            f"- keyword_in_description: {target['keyword_in_description']}\n"
        )
    else:
        lines.append("- Target site is not in the SERP, so we could not analyze it.")

    lines.append("\nCompetitor pages (usually top results):")
    for c in comps[:3]:
        lines.append(
            f"- URL: {c['url']}\n"
            f"  score: {c['score']}, words: {c['word_count']}, "
            f"keyword_in_title: {c['keyword_in_title']}, "
            f"keyword_in_h1: {c['keyword_in_h1']}, "
            f"keyword_in_description: {c['keyword_in_description']}"
        )

    lines.append(
        "\nBased on this data, explain in simple language why the target site "
        "is not ranking at the top for this keyword, and give 4–6 specific, "
        "actionable improvements. Use short bullet points."
    )

    return "\n".join(lines)


def summarize_with_groq(
    keyword: str,
    domain: str,
    rank: int | None,
    serp_rows: list[Dict[str, Any]],
    analysis: Dict[str, Any],
) -> str:
    if not GROQ_API_KEY:
        return (
            "GROQ_API_KEY is not set. Cannot generate AI summary. "
            "You can still inspect the raw metrics above."
        )

    client = Groq(api_key=GROQ_API_KEY)

    prompt = _build_summary_prompt(keyword, domain, rank, serp_rows, analysis)

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an SEO expert. Be concise and practical. "
                    "Use simple language and bullet points."
                    "Do not make information on your own heavily rely on the information provided to you."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.4,
    )

    return chat_completion.choices[0].message.content.strip()