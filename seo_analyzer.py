# seo_analyzer.py
import re
from typing import Dict, Any

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SEOProjectBot/1.0; +https://example.com/bot)"
}


def fetch_page_html(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def analyze_page(html: str | None, url: str, keyword: str) -> Dict[str, Any]:
    keyword_lower = keyword.lower()

    if not html:
        return {
            "url": url,
            "title": "",
            "meta_description": "",
            "h1": "",
            "word_count": 0,
            "keyword_in_title": False,
            "keyword_in_description": False,
            "keyword_in_h1": False,
            "keyword_in_url": False,
            "keyword_density": 0.0,
            "score": 0,
        }

    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Meta description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = desc_tag.get("content", "").strip() if desc_tag else ""

    # H1
    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag else ""

    # Remove non-content elements
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text)
    words = [w for w in text.split(" ") if w.strip()]
    word_count = len(words)

    text_lower = text.lower()
    keyword_count = text_lower.count(keyword_lower)
    keyword_density = (keyword_count / word_count) if word_count > 0 else 0.0

    keyword_in_title = keyword_lower in title.lower()
    keyword_in_description = keyword_lower in meta_description.lower()
    keyword_in_h1 = keyword_lower in h1.lower()
    keyword_in_url = (keyword_lower.replace(" ", "-") in url.lower()) or (
        keyword_lower in url.lower()
    )

    # crude scoring
    score = 0
    if keyword_in_title:
        score += 2
    if keyword_in_h1:
        score += 2
    if keyword_in_description:
        score += 1
    if keyword_in_url:
        score += 1
    if 800 <= word_count <= 2500:
        score += 2
    if 0.005 <= keyword_density <= 0.03:
        score += 1

    return {
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "h1": h1,
        "word_count": word_count,
        "keyword_in_title": keyword_in_title,
        "keyword_in_description": keyword_in_description,
        "keyword_in_h1": keyword_in_h1,
        "keyword_in_url": keyword_in_url,
        "keyword_density": keyword_density,
        "score": score,
    }


def analyze_target_vs_top(keyword: str, target_url: str | None, top_urls: list[str]):
    competitors = []
    for url in top_urls:
        html = fetch_page_html(url)
        competitors.append(analyze_page(html, url, keyword))

    target_analysis = None
    if target_url:
        html = fetch_page_html(target_url)
        target_analysis = analyze_page(html, target_url, keyword)

    return {
        "target": target_analysis,
        "competitors": competitors,
    }
