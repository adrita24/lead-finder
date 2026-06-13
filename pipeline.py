from typing import Callable, Optional
from apify_client import ApifyClient

from apify_service import (
    build_leads_from_results,
    extract_linkedin_urls,
    filter_open_to_work,
    search_google,
)
from email_service import find_and_verify_email, RateLimitExceeded
from models import Lead

TARGET_LEADS = 10


def run_pipeline(
    apify_token: str,
    prospeo_key: str,
    log: Callable[[str], None] = print,
) -> list[Lead]:
    """
    Full pipeline. `log` receives status strings in real time.
    Returns leads with verified emails (up to TARGET_LEADS).
    Stops email stage gracefully on rate limit.
    """
    client = ApifyClient(apify_token)

    log("🔍 Searching Google for LinkedIn profiles...")
    raw_results = search_google(client)
    if not raw_results:
        log("❌ Google search returned no results.")
        return []

    urls = extract_linkedin_urls(raw_results)
    log(f"✅ Found {len(urls)} LinkedIn URL(s)")

    log("⚙️  Parsing leads from search snippets...")
    all_leads = build_leads_from_results(raw_results)
    candidates = filter_open_to_work(all_leads)
    log(f"👥 Candidates: {len(candidates)} lead(s)")

    log("📧 Finding and verifying emails via Prospeo...")
    leads_with_email: list[Lead] = []

    for lead in candidates:
        if len(leads_with_email) >= TARGET_LEADS:
            break
        try:
            email = find_and_verify_email(
                api_key=prospeo_key,
                full_name=lead.full_name,
                linkedin_url=lead.url,
                company_name=lead.company_name,
                headline=lead.headline,
            )
        except RateLimitExceeded:
            log(f"⚠️  Prospeo rate limit hit — stopping early with {len(leads_with_email)} verified email(s).")
            break

        if email:
            lead.email = email
            leads_with_email.append(lead)
            log(f"  ✉  [{len(leads_with_email)}/{TARGET_LEADS}] {lead.full_name} → {email}")
        else:
            log(f"  ✗  No email for {lead.full_name}")

    log(f"\n✅ Done — {len(leads_with_email)} lead(s) with verified emails.")
    return leads_with_email
