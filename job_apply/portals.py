from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import quote_plus, urlencode

from .feeds import fetch_job_feed
from .models import Job

# Public LinkedIn job-search URL geo IDs (query params on linkedin.com/jobs/search).
BENGALURU_GEO = "105214831"
INDIA_GEO = "102713980"

FETCH_MODE_BROWSER = "open-in-browser"
FETCH_MODE_LIVE = "live-feed"

_SLUG = re.compile(r"[^a-z0-9]+")


def naukri_slug(phrase: str) -> str:
    slug = _SLUG.sub("-", phrase.lower()).strip("-")
    return slug


def linkedin_jobs_search_url(
    keywords: str,
    *,
    location: str,
    geo_id: str | None = None,
    remote: bool = False,
) -> str:
    params: dict[str, str] = {
        "keywords": keywords,
        "location": location,
    }
    if geo_id:
        params["geoId"] = geo_id
    if remote:
        params["f_WT"] = "2"
    return "https://www.linkedin.com/jobs/search/?" + urlencode(params, quote_via=quote_plus)


def naukri_jobs_search_url(phrase: str, *, city_slug: str | None = None) -> str:
    slug = naukri_slug(phrase)
    if not slug.endswith("-jobs"):
        slug = f"{slug}-jobs"
    if city_slug:
        slug = f"{slug}-in-{naukri_slug(city_slug)}"
    return f"https://www.naukri.com/{slug}"


def _queries(profile: dict[str, Any], config: dict[str, Any]) -> list[str]:
    block = (config.get("linkedin") or {}).get("queries") or (config.get("naukri") or {}).get(
        "queries"
    )
    if block:
        return [str(q) for q in block]
    roles = [str(r) for r in (profile.get("target_roles") or [])]
    # Compact set so the checklist stays usable.
    preferred = [
        "Senior Security Analyst",
        "Application Security Engineer",
        "VAPT",
        "Penetration Tester",
        "Cloud Security Engineer",
        "AI Security Engineer",
        "Offensive Security Engineer",
    ]
    chosen = [r for r in preferred if any(r.lower() in x.lower() or x.lower() in r.lower() for x in roles)]
    if not chosen:
        chosen = roles[:6]
    return chosen


def build_browser_searches(profile: dict[str, Any], config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Build LinkedIn/Naukri search URLs. These are not live listing fetches."""
    cfg = config or {}
    queries = _queries(profile, cfg)
    loc = profile.get("location") or {}
    city = loc.get("city") or "Bengaluru"
    li_geo = (cfg.get("linkedin") or {}).get("bengaluru_geo_id") or BENGALURU_GEO
    naukri_city = (cfg.get("naukri") or {}).get("city_slug") or "bangalore"
    rows: list[dict[str, Any]] = []

    for query in queries:
        rows.append(
            {
                "id": f"linkedin-search:{naukri_slug(query)}:bengaluru",
                "portal": "linkedin",
                "fetch_mode": FETCH_MODE_BROWSER,
                "title": f"LinkedIn search: {query} in {city}",
                "query": query,
                "location": f"{city}, India",
                "url": linkedin_jobs_search_url(query, location=f"{city}, India", geo_id=li_geo),
                "note": "Open this LinkedIn job search in your browser. Individual openings are not live-fetched (no public LinkedIn job-search API).",
            }
        )
        rows.append(
            {
                "id": f"linkedin-search:{naukri_slug(query)}:remote",
                "portal": "linkedin",
                "fetch_mode": FETCH_MODE_BROWSER,
                "title": f"LinkedIn search: {query} (Remote)",
                "query": query,
                "location": "Remote",
                "url": linkedin_jobs_search_url(
                    query, location="India", geo_id=INDIA_GEO, remote=True
                ),
                "note": "Open this LinkedIn remote/India search in your browser. Confirm the posting hires in India.",
            }
        )
        rows.append(
            {
                "id": f"naukri-search:{naukri_slug(query)}:bangalore",
                "portal": "naukri",
                "fetch_mode": FETCH_MODE_BROWSER,
                "title": f"Naukri search: {query} in Bangalore",
                "query": query,
                "location": "Bangalore",
                "url": naukri_jobs_search_url(query, city_slug=naukri_city),
                "note": "Open this Naukri job search in your browser. Individual openings are not live-fetched (Naukri has no public candidate job-search API).",
            }
        )
    return rows


def _cookie_env_set() -> list[str]:
    names = [
        "LINKEDIN_COOKIE",
        "LINKEDIN_LI_AT",
        "NAUKRI_COOKIE",
        "NAUKRI_SESSION",
    ]
    return [n for n in names if os.environ.get(n)]


def cookie_env_warning() -> str | None:
    cookies = _cookie_env_set()
    if not cookies:
        return None
    return (
        "Ignoring "
        + ", ".join(cookies)
        + " — cookie/session fetch of LinkedIn or Naukri is not implemented (ToS)."
    )


def fetch_optional_portal_feeds(
    config: dict[str, Any],
    ua: str,
    *,
    only: set[str] | None = None,
    on_error=None,
) -> list[Job]:
    """Live-fetch only if she set a documented RSS/JSON feed URL. Never uses session cookies."""
    jobs: list[Job] = []
    mapping = [
        ("linkedin", "LINKEDIN_JOBS_FEED_URL"),
        ("naukri", "NAUKRI_JOBS_FEED_URL"),
    ]
    for portal, env_name in mapping:
        if only is not None and portal not in only:
            continue
        url = os.environ.get(env_name, "").strip()
        if not url:
            continue
        try:
            jobs.extend(fetch_job_feed(url, source=portal, user_agent=ua))
        except Exception as exc:  # noqa: BLE001
            if on_error:
                on_error(f"{portal}-feed", exc)
    return jobs
