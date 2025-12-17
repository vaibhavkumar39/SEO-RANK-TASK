# serp_api_client.py
import os
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")


def get_serp_results(keyword: str, num_results: int = 50, gl: str = "us", hl: str = "en"):
    """
    Call SerpAPI to get Google search results for a keyword.
    num_results can be up to 100 (SerpAPI limit for Google).
    Returns list of organic_results.
    """
    if not SERPAPI_API_KEY:
        raise RuntimeError("SERPAPI_API_KEY is not set in environment variables.")

    # Clamp num_results between 10 and 100 for safety
    num_results = max(10, min(num_results, 100))

    params = {
        "engine": "google",
        "q": keyword,
        "api_key": SERPAPI_API_KEY,
        "num": num_results,
        "gl": gl,
        "hl": hl,
    }

    resp = requests.get("https://serpapi.com/search.json", params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("organic_results", [])


def extract_domain(url: str) -> str:
    """
    Extract plain domain like "example.com" from a URL.
    """
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def normalize_target_domain(domain_or_url: str) -> str:
    """
    User might enter:
      - example.com
      - www.example.com
      - https://www.example.com/path
    This normalizes all of them to "example.com".
    """
    text = domain_or_url.strip().lower()

    # If it looks like a URL, parse it
    if text.startswith("http://") or text.startswith("https://"):
        return extract_domain(text)

    # Otherwise treat it like a raw domain, strip any path
    # e.g. "example.com/page" -> "example.com"
    if "/" in text:
        text = text.split("/", 1)[0]

    if text.startswith("www."):
        text = text[4:]

    return text


def find_domain_rank(organic_results, target_domain: str):
    """
    Returns (rank, url) where domain first appears across all results, or (None, None).

    Rank uses the 'position' from SerpAPI, which corresponds to the
    global ranking position (1-based) on Google.
    """
    target_domain = normalize_target_domain(target_domain)

    found_position = None
    found_url = None

    for result in organic_results:
        link = result.get("link")
        position = result.get("position")
        if not link or position is None:
            continue

        domain = extract_domain(link)

        # Allow exact match or subdomain match:
        #   target: example.com
        #   match: example.com, blog.example.com, shop.example.com
        if domain == target_domain or domain.endswith("." + target_domain):
            found_position = position
            found_url = link
            break

    return found_position, found_url


def find_all_domain_positions(organic_results, target_domain: str):
    """
    Return ALL positions where this domain appears.
    Each item: { position, url }.
    """
    target_domain = normalize_target_domain(target_domain)
    hits = []

    for result in organic_results:
        link = result.get("link")
        position = result.get("position")
        if not link or position is None:
            continue

        domain = extract_domain(link)
        if domain == target_domain or domain.endswith("." + target_domain):
            hits.append(
                {
                    "position": position,
                    "url": link,
                }
            )

    hits.sort(key=lambda x: x["position"])
    return hits


def find_url_rank(organic_results, target_url: str):
    """
    Returns (rank, url) for the specific URL if present, otherwise (None, None).

    Matching is done by normalizing trailing slash and checking equality
    or startswith (in case of tracking params, etc.).
    """
    target_url = target_url.strip()
    if not target_url:
        return None, None

    # ensure scheme for fair comparison
    if target_url.startswith("www."):
        target_url = "https://" + target_url
    target_norm = target_url.rstrip("/")

    found_position = None
    found_url = None

    for result in organic_results:
        link = result.get("link")
        position = result.get("position")
        if not link or position is None:
            continue

        link_norm = link.rstrip("/")
        if link_norm == target_norm or link_norm.startswith(target_norm + "?"):
            found_position = position
            found_url = link
            break

    return found_position, found_url


def normalize_serp_results(organic_results):
    """
    Returns a cleaned list of dicts: position, title, link, domain, snippet.
    """
    cleaned = []
    for r in organic_results:
        link = r.get("link")
        position = r.get("position")
        if not link or position is None:
            continue
        cleaned.append(
            {
                "position": position,
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "link": link,
                "domain": extract_domain(link),
            }
        )
    cleaned.sort(key=lambda x: x["position"])
    return cleaned