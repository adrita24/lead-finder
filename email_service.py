import logging
import re
import time
import requests
from typing import Optional
from models import Lead

logger = logging.getLogger(__name__)

PROSPEO_ENRICH   = "https://api.prospeo.io/enrich-person"
RATE_LIMIT_SLEEP = 2.5


class RateLimitExceeded(Exception):
    pass


def _company_to_domain(company_name: str) -> Optional[str]:
    if not company_name:
        return None
    cleaned = re.sub(
        r"\b(pvt|ltd|llc|inc|corp|private|limited|technologies|tech|solutions|services|india)\b",
        "", company_name, flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[^a-z0-9]", "", cleaned.lower()).strip()
    return f"{cleaned}.com" if len(cleaned) >= 3 else None


def _post(api_key: str, payload: dict) -> Optional[dict]:
    try:
        resp = requests.post(
            PROSPEO_ENRICH,
            json=payload,
            headers={"X-KEY": api_key, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 429:
            raise RateLimitExceeded("Prospeo rate limit hit")
        resp.raise_for_status()
        return resp.json()
    except RateLimitExceeded:
        raise
    except requests.HTTPError as exc:
        try:
            code = exc.response.json().get("error_code", "")
            if code == "NO_MATCH":
                logger.debug("NO_MATCH for %s", payload)
                return None
        except Exception:
            pass
        logger.warning("Prospeo HTTP error: %s", exc)
        return None
    except requests.RequestException as exc:
        logger.error("Prospeo request failed: %s", exc)
        return None


def _extract_email(body: dict) -> Optional[str]:
    if not body or body.get("error"):
        return None
    person    = body.get("person") or {}
    email_obj = person.get("email") or {}
    email     = email_obj.get("email", "")
    status    = (email_obj.get("status") or "").upper()
    revealed  = email_obj.get("revealed", True)
    if not email or not revealed:
        return None
    if status and status not in ("VERIFIED", "ACCEPT_ALL"):
        return None
    return email


def find_and_verify_email(
    api_key: str,
    full_name: str,
    linkedin_url: str = "",
    company_name: str = "",
    headline: str = "",
) -> Optional[str]:
    """
    Returns email string or None.
    Raises RateLimitExceeded if Prospeo returns 429 — caller should stop.
    """
    time.sleep(RATE_LIMIT_SLEEP)

    if linkedin_url:
        body  = _post(api_key, {"data": {"linkedin_url": linkedin_url}})
        email = _extract_email(body)
        if email:
            logger.info("  ✉  %s → %s (via LinkedIn URL)", full_name, email)
            return email

    domain = None
    at_match = re.search(r"@\s*([A-Za-z][^|@\n]{2,40})", headline)
    if at_match:
        candidate = re.split(r"\s*\|\s*", at_match.group(1).strip())[0].strip()
        domain = _company_to_domain(candidate)
    if not domain:
        domain = _company_to_domain(company_name)

    if domain and len(full_name.split()) >= 2:
        time.sleep(RATE_LIMIT_SLEEP)
        body  = _post(api_key, {"data": {"full_name": full_name, "company_website": domain}})
        email = _extract_email(body)
        if email:
            logger.info("  ✉  %s → %s (via name+domain)", full_name, email)
            return email

    return None