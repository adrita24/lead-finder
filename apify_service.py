import logging
import re
from typing import Optional
from apify_client import ApifyClient
from datetime import timedelta
from models import Lead

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_ACTOR = "apify/google-search-scraper"

LINKEDIN_PROFILE_PATTERN = re.compile(
    r"https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+/?",
    re.IGNORECASE,
)

SEARCH_QUERIES: list[str] = [
    'site:linkedin.com/in "Open to Work" "AI Engineer" "India"',
    'site:linkedin.com/in "Open to Work" "Generative AI Engineer" "India"',
    'site:linkedin.com/in "Open to Work" "Machine Learning Engineer" "India"',
    'site:linkedin.com/in "Open to Work" "LLM Engineer" "India"',
    'site:linkedin.com/in "Open to Work" "GenAI Engineer" "India"',
    'site:linkedin.com/in "Open to Work" "AI/ML Engineer" "India"',
    'site:linkedin.com/in "Open to Work" "NLP Engineer" "India"',
    'site:linkedin.com/in "Open to Work" "Deep Learning Engineer" "India"',
    'site:linkedin.com/in "Open to Work" "MLOps Engineer" "India"',
    'site:linkedin.com/in "Open to Work" "Applied AI Engineer" "India"',
]

OTW_SIGNALS = ["open to work", "open for work", "#opentowork", "opentowork"]

INDIA_SIGNALS = [
    "india", "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad",
    "chennai", "pune", "kolkata", "noida", "gurugram", "gurgaon",
    "ahmedabad", "jaipur", "kochi", "indore",
]


def _run_actor(client, actor_id, run_input, timeout_secs=300):
    try:
        td = timedelta(seconds=timeout_secs)
        run = client.actor(actor_id).call(
            run_input=run_input, run_timeout=td, wait_duration=td,
        )
        if not run:
            return []
        dataset_id = run.default_dataset_id
        if not dataset_id:
            return []
        return list(client.dataset(dataset_id).iterate_items())
    except Exception as exc:
        logger.error("Actor '%s' failed: %s", actor_id, exc)
        return []


def _normalise_linkedin_url(url):
    url = url.split("?")[0].split("#")[0].rstrip("/")
    url = re.sub(r"^https?://(www\.)?linkedin", "https://www.linkedin", url)
    return url


def _snippet_contains(text, signals):
    low = text.lower()
    return any(s in low for s in signals)


def _extract_location(text):
    low = text.lower()
    for city in INDIA_SIGNALS[1:]:
        if city in low:
            return city.title(), "India"
    if "india" in low:
        return "", "India"
    return "", ""


def _parse_google_result(result):
    url   = result.get("url") or result.get("link", "")
    title = result.get("title", "")
    desc  = result.get("description", "") or result.get("snippet", "")
    combined = f"{title} {desc}"

    if not LINKEDIN_PROFILE_PATTERN.search(url):
        return None

    otw_confirmed = _snippet_contains(combined, OTW_SIGNALS)

    clean_title = re.sub(r"\s*\|\s*LinkedIn\s*$", "", title, flags=re.IGNORECASE).strip()
    parts = [p.strip() for p in clean_title.split(" - ")]
    full_name = parts[0] if parts else "Unknown"
    headline  = parts[1] if len(parts) > 1 else ""

    if not re.search(r"[A-Za-z]", full_name):
        return None

    city, country = _extract_location(combined)

    company = ""
    at_match = re.search(r"\bat\s+([A-Z][^.|\n]{2,40})", desc)
    if at_match:
        company = at_match.group(1).strip()
    if not company:
        hl_match = re.search(r"@\s*([A-Za-z][^|@\n]{2,40})", headline)
        if hl_match:
            company = re.split(r"\s*\|\s*", hl_match.group(1).strip())[0].strip()

    return Lead(
        full_name=full_name,
        headline=headline,
        company_name=company,
        city=city,
        country=country,
        url=_normalise_linkedin_url(url),
        open_to_work=otw_confirmed,
    )


def search_google(client: ApifyClient) -> list[dict]:
    logger.info("Searching Google for LinkedIn profiles...")
    run_input = {
        "queries": "\n".join(SEARCH_QUERIES),
        "resultsPerPage": 10,
        "maxPagesPerQuery": 5,
        "languageCode": "en",
        "countryCode": "in",
    }
    items = _run_actor(client, GOOGLE_SEARCH_ACTOR, run_input, timeout_secs=360)
    logger.info("Google search returned %d raw result item(s).", len(items))
    return items


def extract_linkedin_urls(raw_results: list[dict]) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for item in raw_results:
        organic = item.get("organicResults") or []
        for result in organic:
            if not isinstance(result, dict):
                continue
            for key in ("url", "link"):
                val = result.get(key, "")
                if val and LINKEDIN_PROFILE_PATTERN.search(val):
                    n = _normalise_linkedin_url(val)
                    if n not in seen:
                        seen.add(n)
                        urls.append(n)
    logger.info("Extracted %d unique LinkedIn profile URL(s).", len(urls))
    return urls


def enrich_profile(client, url):
    return None


def build_leads_from_results(raw_results: list[dict]) -> list[Lead]:
    seen_urls: set[str] = set()
    leads: list[Lead] = []
    for item in raw_results:
        organic = item.get("organicResults") or []
        for result in organic:
            if not isinstance(result, dict):
                continue
            lead = _parse_google_result(result)
            if lead is None:
                continue
            if lead.url in seen_urls:
                continue
            seen_urls.add(lead.url)
            leads.append(lead)
            logger.info("  ✓ Lead parsed: %s — %s", lead.full_name, lead.headline)
    logger.info("Built %d lead(s) from Google results.", len(leads))
    return leads


def filter_open_to_work(leads: list[Lead]) -> list[Lead]:
    for lead in leads:
        lead.open_to_work = True
    logger.info("%d candidate(s) total.", len(leads))
    return leads


def enrich_all_profiles(client, urls):
    return []