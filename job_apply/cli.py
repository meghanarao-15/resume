from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from . import __version__
from .apply import APPROVAL_FLAG, approve_job, draft_from_id
from .matcher import rank_jobs
from .profile import ROOT, load_profile
from .sources import fetch_jobs
from .store import DEFAULT_OUT, load_catalog, render_matches_md, write_matches

DEFAULT_SOURCES = ROOT / "config" / "sources.yaml"
SAMPLE_JOBS = ROOT / "data" / "sample_jobs.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job_apply",
        description=(
            "Fetch public job listings, score them against Meghana's profile, "
            "and draft apply packets. Never submits without an explicit per-job approval, "
            "and does not log into LinkedIn or click Easy Apply."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    search = sub.add_parser("search", help="Fetch openings and rank matches")
    search.add_argument("--offline", action="store_true", help="Score bundled sample jobs only")
    search.add_argument("--limit", type=int, default=25)
    search.add_argument("--min-score", type=float, default=35.0)
    search.add_argument("--source", action="append", dest="sources", help="Restrict to source name(s)")
    search.add_argument("--out", type=Path, default=DEFAULT_OUT)

    sub.add_parser("show", help="Print last ranked matches")
    show = sub.choices["show"]
    show.add_argument("--out", type=Path, default=DEFAULT_OUT)
    show.add_argument("--json", action="store_true")

    draft = sub.add_parser("draft", help="Write a review packet for one job id")
    draft.add_argument("job_id")
    draft.add_argument("--out", type=Path, default=DEFAULT_OUT)

    approve = sub.add_parser(
        "approve",
        help="Record that you reviewed this one job (does not submit the application)",
    )
    approve.add_argument("job_id")
    approve.add_argument(APPROVAL_FLAG, dest="confirmed", action="store_true")
    approve.add_argument("--out", type=Path, default=DEFAULT_OUT)

    batch = sub.add_parser(
        "batch-review",
        help="List a small set of job ids you may confirm together after reading each packet",
    )
    batch.add_argument("--out", type=Path, default=DEFAULT_OUT)
    batch.add_argument("--limit", type=int, default=5)
    return parser


def _load_source_config() -> dict[str, Any]:
    with DEFAULT_SOURCES.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_sample_jobs():
    from .models import Job

    raw = json.loads(SAMPLE_JOBS.read_text(encoding="utf-8"))
    return [Job.from_dict(item) for item in raw]


def cmd_search(args: argparse.Namespace) -> int:
    profile = load_profile()
    if args.offline:
        jobs = _load_sample_jobs()
        errors: list[str] = []
    else:
        errors = []
        config = _load_source_config()
        jobs = fetch_jobs(
            config,
            only=args.sources,
            on_error=lambda name, exc: errors.append(f"{name}: {exc}"),
        )
        if not jobs:
            print("No live listings fetched; falling back to sample jobs.", file=sys.stderr)
            jobs = _load_sample_jobs()
            errors.append("live-fetch-empty")
    matches = rank_jobs(jobs, profile, limit=args.limit, min_score=args.min_score)
    path = write_matches(matches, args.out)
    print(render_matches_md(matches))
    if errors:
        print("Source warnings:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
    print(f"Wrote {path} ({len(matches)} matches from {len(jobs)} listings).", file=sys.stderr)
    print("Next: python3 -m job_apply draft <job_id>", file=sys.stderr)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    catalog = load_catalog(args.out)
    if args.json:
        print(json.dumps(catalog["matches"], indent=2))
        return 0
    from .models import Job, Match

    matches = []
    jobs = catalog.get("jobs") or {}
    for row in catalog.get("matches") or []:
        job = Job.from_dict(jobs[row["id"]])
        matches.append(
            Match(
                job=job,
                score=row["score"],
                reasons=row["reasons"],
                skill_hits=row.get("skill_hits") or [],
                title_fit=row.get("title_fit", False),
                location_fit=row.get("location_fit", False),
            )
        )
    print(render_matches_md(matches))
    return 0


def cmd_draft(args: argparse.Namespace) -> int:
    profile = load_profile()
    folder = draft_from_id(profile, args.job_id, args.out)
    print(f"Packet ready for YOUR review (not submitted):\n  {folder}")
    print("Edit cover-letter.md, then apply on the company site.")
    print(f"After you submit yourself: python3 -m job_apply approve {args.job_id} {APPROVAL_FLAG}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    try:
        path = approve_job(args.job_id, confirmed=args.confirmed, out_dir=args.out)
    except PermissionError as exc:
        print(exc, file=sys.stderr)
        return 2
    print(
        f"Recorded human approval for {args.job_id} in {path}. "
        "No application was posted; use the packet checklist to submit on the official form."
    )
    return 0


def cmd_batch_review(args: argparse.Namespace) -> int:
    catalog = load_catalog(args.out)
    rows = (catalog.get("matches") or [])[: args.limit]
    print("Small batch for confirmation. Read each posting AND packet before approving.\n")
    for row in rows:
        print(f"- {row['id']}")
        print(f"  {row['score']:.0f}  {row['title']} @ {row['company']}")
        print(f"  {row['url']}")
        print(f"  python3 -m job_apply draft {row['id']}")
        print(f"  python3 -m job_apply approve {row['id']} {APPROVAL_FLAG}")
        print()
    print("Approvals are per job. There is no command that applies to all of these at once.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "search": cmd_search,
        "show": cmd_show,
        "draft": cmd_draft,
        "approve": cmd_approve,
        "batch-review": cmd_batch_review,
    }
    return handlers[args.cmd](args)
