from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Job, Match

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "out"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_matches(matches: list[Match], out_dir: Path | None = None) -> Path:
    dest = out_dir or DEFAULT_OUT
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "matches.json"
    payload = {
        "generated_at": _now(),
        "count": len(matches),
        "matches": [m.to_dict() for m in matches],
        "jobs": {m.job.id: m.job.to_dict() for m in matches},
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (dest / "matches.md").write_text(render_matches_md(matches), encoding="utf-8")
    return path


def render_matches_md(matches: list[Match]) -> str:
    lines = [
        "# Ranked job matches",
        "",
        "Human review required before any application. Nothing is submitted automatically.",
        "",
        "| Score | Title | Company | Location | Why | Link |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for match in matches:
        reasons = "; ".join(match.reasons)
        lines.append(
            f"| {match.score:.0f} | {match.job.title} | {match.job.company} | "
            f"{match.job.location} | {reasons} | {match.job.url} |"
        )
    lines.append("")
    return "\n".join(lines)


def load_catalog(out_dir: Path | None = None) -> dict[str, Any]:
    path = (out_dir or DEFAULT_OUT) / "matches.json"
    if not path.exists():
        raise FileNotFoundError("No matches yet. Run: python3 -m job_apply search")
    return json.loads(path.read_text(encoding="utf-8"))


def job_from_catalog(job_id: str, out_dir: Path | None = None) -> tuple[Job, dict[str, Any]]:
    catalog = load_catalog(out_dir)
    jobs = catalog.get("jobs") or {}
    match_row = next((m for m in catalog.get("matches") or [] if m["id"] == job_id), None)
    raw = jobs.get(job_id)
    if not raw:
        raise KeyError(f"Unknown job id: {job_id}")
    return Job.from_dict(raw), match_row or {}


def record_approval(job_id: str, out_dir: Path | None = None, note: str = "") -> Path:
    dest = out_dir or DEFAULT_OUT
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "approvals.json"
    data: dict[str, Any] = {"approvals": []}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("approvals", []).append(
        {
            "job_id": job_id,
            "approved_at": _now(),
            "approved_by": "human",
            "submit_action": "manual",
            "note": note
            or "No legitimate public apply API for this posting. Use the packet checklist.",
        }
    )
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path
