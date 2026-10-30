from __future__ import annotations

import re
from typing import Any, Iterable

from .models import Job, Match
from .profile import skill_weights

_WORD = re.compile(r"[a-z0-9+#]+")

TITLE_POSITIVE = (
    "security analyst",
    "security engineer",
    "application security",
    "appsec",
    "product security",
    "penetration",
    "pentest",
    "pentester",
    "vapt",
    "offensive security",
    "red team",
    "vulnerability",
    "cloud security",
    "ai security",
    "llm security",
    "security consultant",
    "security specialist",
    "infosec",
    "information security",
)

TITLE_NEGATIVE = (
    "sales",
    "account executive",
    "recruiter",
    "recruiting",
    "marketing",
    "content writer",
    "product manager",
    "program manager",
    " cop ",
    "police",
    "physical security guard",
)


def _norm(text: str) -> str:
    return " ".join(_WORD.findall(text.lower()))


def _contains_any(haystack: str, needles: Iterable[str]) -> list[str]:
    return [n for n in needles if n in haystack]


def score_job(job: Job, profile: dict[str, Any]) -> Match:
    blob = _norm(job.blob())
    title = _norm(job.title)
    location = _norm(f"{job.location} {job.extra.get('remote', '')}")

    avoid = [a.lower() for a in profile.get("avoid_roles") or []]
    if any(a in title for a in avoid if a):
        return Match(job, 0.0, ["Title matches an avoided role"], [], False, False)

    reasons: list[str] = []
    score = 0.0

    title_hits = _contains_any(title, TITLE_POSITIVE)
    title_fit = bool(title_hits)
    if title_fit:
        score += 40 + min(15, 5 * len(title_hits))
        reasons.append("Title aligns with target security roles: " + ", ".join(title_hits[:3]))
    else:
        # Weak signal if "security" appears only in the body
        if "security" in blob:
            score += 8
            reasons.append("Mentions security, but title is not a core target role")

    if _contains_any(title, TITLE_NEGATIVE):
        score -= 40
        reasons.append("Title looks off-target (sales/recruiting/etc.)")

    weights = skill_weights(profile)
    skill_hits: list[str] = []
    skill_score = 0.0
    for skill, weight in weights.items():
        if skill in blob:
            skill_hits.append(skill)
            skill_score += weight
    skill_score = min(35.0, skill_score * 1.4)
    score += skill_score
    if skill_hits:
        reasons.append("Skill overlap: " + ", ".join(skill_hits[:6]))

    preferred = [p.lower() for p in (profile.get("location") or {}).get("preferred") or []]
    location_fit = False
    india_markers = ("india", "bengaluru", "bangalore", "hyderabad", "chennai", "pune", "karnataka")
    us_centric = any(
        token in location for token in ("united states", "united kingdom", "canada", " u.s", " usa")
    ) or location.endswith(" us") or "remote - us" in location or "remote, us" in location
    india_listed = any(token in location or token in blob for token in india_markers)
    if india_listed:
        location_fit = True
        score += 14
        reasons.append("Location lists India / Bengaluru")
    elif "remote" in location or job.extra.get("remote") is True:
        location_fit = True
        if us_centric:
            score += 2
            reasons.append("Remote, but geography looks US/UK/CA — confirm India hiring before applying")
        else:
            score += 10
            reasons.append("Role appears remote (verify it hires in India)")
    elif any(p in location or p in blob for p in preferred):
        location_fit = True
        score += 8
        reasons.append("Partial location match against preferred cities/regions")
    else:
        score -= 4
        reasons.append("Location not clearly Bengaluru/India/remote")

    # Seniority: she is senior analyst; intern/junior is a weaker fit
    if "intern" in title or "junior" in title or "graduate" in title:
        score -= 15
        reasons.append("Seniority looks more junior than current Senior Security Analyst role")
    if "senior" in title or "staff" in title or "lead" in title:
        score += 6
        reasons.append("Seniority is a peer/step-up from current title")

    if not reasons:
        reasons.append("Little overlap with the candidate profile")

    score = max(0.0, min(100.0, score))
    return Match(job, score, reasons, skill_hits, title_fit, location_fit)


def rank_jobs(
    jobs: Iterable[Job],
    profile: dict[str, Any],
    *,
    limit: int = 25,
    min_score: float = 35.0,
) -> list[Match]:
    matches = [score_job(job, profile) for job in jobs]
    matches.sort(key=lambda m: m.score, reverse=True)
    return [m for m in matches if m.score >= min_score][:limit]
