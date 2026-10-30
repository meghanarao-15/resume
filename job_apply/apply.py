from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Job
from .store import DEFAULT_OUT, job_from_catalog, record_approval

APPROVAL_FLAG = "--i-have-read-this-posting"


def _bullets(profile: dict[str, Any]) -> list[str]:
    items: list[str] = []
    for role in profile.get("experience") or []:
        company = role.get("company")
        title = role.get("title")
        for line in role.get("highlights") or []:
            items.append(f"{title} at {company}: {line}")
    for talk in (profile.get("talks_and_writing") or [])[:4]:
        items.append(f"Public work: {talk.get('title')} ({talk.get('venue')})")
    return items


def draft_cover_letter(profile: dict[str, Any], job: Job, match: dict[str, Any]) -> str:
    name = profile.get("full_name") or profile.get("name")
    hits = ", ".join(match.get("skill_hits") or []) or "security assessment work"
    reasons = " ".join(match.get("reasons") or [])
    return f"""Dear {job.company} hiring team,

I am {name}, a Senior Security Analyst at Deep Armor in Bengaluru. I am writing about the {job.title} role.

My recent work is hands-on VAPT and security assessment across web, mobile, cloud, and emerging AI tool chains, including leading assessments and taking projects from scoping through reporting. That maps to this posting because: {reasons}

Most relevant overlap: {hits}.

I also speak and write in public (WiCyS, Wicked6, IoT Show, OWASP community, Medium) on practical exploitation, IoT security, cloud compliance, and defending AI-driven tools against prompt injection and tool-chain abuse.

I would welcome a conversation about how I can contribute to {job.company}'s security program. This letter was drafted for my review; I will submit it myself after I confirm the posting.

Thank you,
{name}
{profile.get("links", {}).get("linkedin", "")}
"""


def draft_answers(profile: dict[str, Any], job: Job) -> str:
    loc = (profile.get("location") or {}).get("city")
    return f"""# Suggested application answers (edit before sending)

## Why this role?
I am a Senior Security Analyst focused on VAPT and practical testing of web, mobile, cloud, and AI-agent systems. {job.company}'s {job.title} posting is a direct use of that experience.

## Work authorization / location
Based in {loc}, India. Open to Bengaluru on-site/hybrid and remote roles that hire in India. Confirm visa/work-auth language on the posting before applying.

## Notice period
Confirm current Deep Armor notice period before stating a date.

## Salary
Do not auto-fill. Decide per company.

## How did you hear about us?
Company careers page / public job board ({job.source}), found via a personal matcher against my skills — not a mass-apply bot.
"""


def apply_checklist(job: Job) -> str:
    return f"""# How to apply (human-only)

This tool does **not** submit applications. There is no legitimate public “apply for me”
API for Greenhouse/Lever/Ashby candidate submissions that we should call.

1. Open the posting: {job.url}
2. Read the full description, location, and work-auth requirements.
3. Edit `cover-letter.md` and `answers.md` in this folder so they sound like you.
4. Attach or paste your resume (this repo still needs a real CV file if you want it bundled).
5. Submit on the company’s official apply form yourself.
6. Record the outcome in `out/approvals.json` by running:

   `python3 -m job_apply approve {job.id} {APPROVAL_FLAG}`

Do not paste credentials into this tool. Do not use LinkedIn Easy Apply automation.
"""


def write_packet(
    profile: dict[str, Any],
    job: Job,
    match: dict[str, Any],
    out_dir: Path | None = None,
) -> Path:
    folder = (out_dir or DEFAULT_OUT) / "packets" / _safe_id(job.id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "job.json").write_text(
        _pretty(
            {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "url": job.url,
                "location": job.location,
                "source": job.source,
                "score": match.get("score"),
                "reasons": match.get("reasons"),
                "skill_hits": match.get("skill_hits"),
            }
        ),
        encoding="utf-8",
    )
    (folder / "cover-letter.md").write_text(draft_cover_letter(profile, job, match), encoding="utf-8")
    (folder / "answers.md").write_text(draft_answers(profile, job), encoding="utf-8")
    (folder / "CHECKLIST.md").write_text(apply_checklist(job), encoding="utf-8")
    (folder / "talking-points.md").write_text(
        "# Talking points\n\n" + "\n".join(f"- {b}" for b in _bullets(profile)) + "\n",
        encoding="utf-8",
    )
    return folder


def _safe_id(job_id: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in job_id)[:180]


def _pretty(data: dict[str, Any]) -> str:
    import json

    return json.dumps(data, indent=2)


def draft_from_id(profile: dict[str, Any], job_id: str, out_dir: Path | None = None) -> Path:
    job, match = job_from_catalog(job_id, out_dir)
    return write_packet(profile, job, match, out_dir)


def approve_job(job_id: str, *, confirmed: bool, out_dir: Path | None = None) -> Path:
    if not confirmed:
        raise PermissionError(
            f"Refusing to mark an application ready without {APPROVAL_FLAG}. "
            "Read the posting and packet first."
        )
    job_from_catalog(job_id, out_dir)  # ensure it is a known match
    return record_approval(job_id, out_dir)
