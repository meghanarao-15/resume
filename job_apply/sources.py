from __future__ import annotations

import os
from typing import Any, Callable, Iterable
from urllib.parse import quote_plus, urlencode

from .html import strip_html
from .http import env_ready, get_json
from .models import Job
from .portals import cookie_env_warning, fetch_optional_portal_feeds

Fetcher = Callable[[dict[str, Any], str], list[Job]]


def _greenhouse(config: dict[str, Any], ua: str) -> list[Job]:
    jobs: list[Job] = []
    for board in config.get("greenhouse_boards") or []:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
        try:
            payload = get_json(url, user_agent=ua)
        except RuntimeError:
            continue
        for item in payload.get("jobs") or []:
            loc = ""
            if isinstance(item.get("location"), dict):
                loc = item["location"].get("name") or ""
            depts = ", ".join(
                d.get("name", "") for d in (item.get("departments") or []) if isinstance(d, dict)
            )
            jobs.append(
                Job(
                    id=f"greenhouse:{board}:{item.get('id')}",
                    source="greenhouse",
                    title=item.get("title") or "",
                    company=item.get("company_name") or board,
                    url=item.get("absolute_url") or "",
                    location=loc,
                    description=depts,
                    extra={"board": board, "departments": depts},
                )
            )
    return jobs


def _lever(config: dict[str, Any], ua: str) -> list[Job]:
    jobs: list[Job] = []
    for company in config.get("lever_companies") or []:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        try:
            payload = get_json(url, user_agent=ua)
        except RuntimeError:
            continue
        if not isinstance(payload, list):
            continue
        for item in payload:
            cats = item.get("categories") or {}
            loc = cats.get("location") or ""
            team = cats.get("team") or ""
            jobs.append(
                Job(
                    id=f"lever:{company}:{item.get('id')}",
                    source="lever",
                    title=item.get("text") or "",
                    company=company,
                    url=item.get("hostedUrl") or item.get("applyUrl") or "",
                    location=loc,
                    description=strip_html(item.get("descriptionPlain") or item.get("description") or team),
                    extra={"team": team, "commitment": cats.get("commitment") or ""},
                )
            )
    return jobs


def _ashby(config: dict[str, Any], ua: str) -> list[Job]:
    jobs: list[Job] = []
    for board in config.get("ashby_boards") or []:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
        try:
            payload = get_json(url, user_agent=ua)
        except RuntimeError:
            continue
        for item in payload.get("jobs") or []:
            loc = item.get("location") or ""
            if isinstance(loc, dict):
                loc = loc.get("name") or loc.get("locationSummary") or ""
            jobs.append(
                Job(
                    id=f"ashby:{board}:{item.get('id') or item.get('jobId')}",
                    source="ashby",
                    title=item.get("title") or "",
                    company=item.get("department") and board or board,
                    url=item.get("jobUrl") or item.get("applyUrl") or "",
                    location=str(loc),
                    description=strip_html(item.get("descriptionHtml") or item.get("descriptionPlain") or ""),
                    extra={"team": item.get("team") or item.get("department") or ""},
                )
            )
    return jobs


def _remotive(config: dict[str, Any], ua: str) -> list[Job]:
    block = config.get("remotive") or {}
    if not block.get("enabled", True):
        return []
    query = quote_plus(block.get("search") or "security")
    url = f"https://remotive.com/api/remote-jobs?search={query}"
    try:
        payload = get_json(url, user_agent=ua)
    except RuntimeError:
        return []
    jobs: list[Job] = []
    for item in payload.get("jobs") or []:
        jobs.append(
            Job(
                id=f"remotive:{item.get('id')}",
                source="remotive",
                title=item.get("title") or "",
                company=item.get("company_name") or "",
                url=item.get("url") or "",
                location=item.get("candidate_required_location") or "Remote",
                description=strip_html(item.get("description") or "")[:4000],
                extra={"category": item.get("category") or "", "tags": item.get("tags") or []},
            )
        )
    return jobs


def _arbeitnow(config: dict[str, Any], ua: str) -> list[Job]:
    block = config.get("arbeitnow") or {}
    if not block.get("enabled", True):
        return []
    try:
        payload = get_json("https://www.arbeitnow.com/api/job-board-api", user_agent=ua)
    except RuntimeError:
        return []
    jobs: list[Job] = []
    for item in payload.get("data") or []:
        title = item.get("title") or ""
        blob = f"{title} {item.get('description') or ''}".lower()
        if not any(tok in blob for tok in ("security", "vapt", "pentest", "appsec", "infosec")):
            continue
        jobs.append(
            Job(
                id=f"arbeitnow:{item.get('slug') or item.get('created_at')}",
                source="arbeitnow",
                title=title,
                company=item.get("company_name") or "",
                url=item.get("url") or "",
                location=item.get("location") or "",
                description=strip_html(item.get("description") or "")[:4000],
                extra={"remote": item.get("remote")},
            )
        )
    return jobs


def _adzuna(config: dict[str, Any], ua: str) -> list[Job]:
    block = config.get("adzuna") or {}
    names = block.get("enabled_if_env") or ["ADZUNA_APP_ID", "ADZUNA_APP_KEY"]
    if not env_ready(names):
        return []
    country = block.get("country") or "in"
    params = {
        "app_id": os.environ["ADZUNA_APP_ID"],
        "app_key": os.environ["ADZUNA_APP_KEY"],
        "what": block.get("what") or "security analyst",
        "where": block.get("where") or "Bangalore",
        "results_per_page": 50,
        "content-type": "application/json",
    }
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1?{urlencode(params)}"
    try:
        payload = get_json(url, user_agent=ua)
    except RuntimeError:
        return []
    jobs: list[Job] = []
    for item in payload.get("results") or []:
        company = (item.get("company") or {}).get("display_name") or ""
        loc = (item.get("location") or {}).get("display_name") or ""
        jobs.append(
            Job(
                id=f"adzuna:{item.get('id')}",
                source="adzuna",
                title=item.get("title") or "",
                company=company,
                url=item.get("redirect_url") or item.get("adref") or "",
                location=loc,
                description=strip_html(item.get("description") or "")[:4000],
            )
        )
    return jobs


def _reed(config: dict[str, Any], ua: str) -> list[Job]:
    block = config.get("reed") or {}
    if not env_ready(block.get("enabled_if_env") or ["REED_API_KEY"]):
        return []
    import base64

    token = base64.b64encode(f"{os.environ['REED_API_KEY']}:".encode()).decode()
    params = urlencode(
        {"keywords": block.get("keywords") or "security analyst", "resultsToTake": 50}
    )
    url = f"https://www.reed.co.uk/api/1.0/search?{params}"
    try:
        payload = get_json(
            url,
            user_agent=ua,
            headers={"Authorization": f"Basic {token}"},
        )
    except RuntimeError:
        return []
    jobs: list[Job] = []
    for item in payload.get("results") or []:
        jobs.append(
            Job(
                id=f"reed:{item.get('jobId')}",
                source="reed",
                title=item.get("jobTitle") or "",
                company=item.get("employerName") or "",
                url=item.get("jobUrl") or "",
                location=item.get("locationName") or "",
                description=strip_html(item.get("jobDescription") or "")[:4000],
            )
        )
    return jobs


def _linkedin(config: dict[str, Any], ua: str) -> list[Job]:
    """Optional RSS/JSON feed only. Guest HTML / cookie scrape is not implemented."""
    return fetch_optional_portal_feeds(config, ua, only={"linkedin"})


def _naukri(config: dict[str, Any], ua: str) -> list[Job]:
    """Optional RSS/JSON feed only. Naukri HTML / cookie scrape is not implemented."""
    return fetch_optional_portal_feeds(config, ua, only={"naukri"})


FETCHERS: list[tuple[str, Fetcher]] = [
    ("greenhouse", _greenhouse),
    ("lever", _lever),
    ("ashby", _ashby),
    ("remotive", _remotive),
    ("arbeitnow", _arbeitnow),
    ("adzuna", _adzuna),
    ("reed", _reed),
    ("linkedin", _linkedin),
    ("naukri", _naukri),
]


def fetch_jobs(
    config: dict[str, Any],
    *,
    only: Iterable[str] | None = None,
    on_error: Callable[[str, Exception], None] | None = None,
) -> list[Job]:
    ua = config.get("user_agent") or "meghana-job-apply/0.1"
    allow = set(only) if only else None
    collected: list[Job] = []
    seen: set[str] = set()
    cookie_note = cookie_env_warning()
    if cookie_note and on_error:
        on_error("portals", RuntimeError(cookie_note))
    for name, fn in FETCHERS:
        if allow is not None and name not in allow:
            continue
        try:
            batch = fn(config, ua)
        except Exception as exc:  # noqa: BLE001 — isolate a bad source
            if on_error:
                on_error(name, exc)
            continue
        for job in batch:
            key = job.url or job.id
            if key in seen:
                continue
            seen.add(key)
            collected.append(job)
    return collected
