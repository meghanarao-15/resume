import json
import os
from pathlib import Path

from job_apply.cli import main
from job_apply.feeds import parse_job_feed
from job_apply.portals import (
    build_browser_searches,
    linkedin_jobs_search_url,
    naukri_jobs_search_url,
)
from job_apply.profile import load_profile, ROOT
from job_apply.sources import fetch_jobs


def test_linkedin_and_naukri_search_urls_from_profile():
    profile = load_profile()
    rows = build_browser_searches(profile, {})
    assert rows
    assert all(r["fetch_mode"] == "open-in-browser" for r in rows)
    linkedin = [r for r in rows if r["portal"] == "linkedin"]
    naukri = [r for r in rows if r["portal"] == "naukri"]
    assert linkedin and naukri
    assert any("linkedin.com/jobs/search" in r["url"] and "VAPT" in r["url"] for r in linkedin)
    assert any("naukri.com/" in r["url"] and "bangalore" in r["url"] for r in naukri)
    assert "Application+Security+Engineer" in linkedin_jobs_search_url(
        "Application Security Engineer", location="Bengaluru, India"
    )
    assert naukri_jobs_search_url("VAPT", city_slug="bangalore").endswith(
        "/vapt-jobs-in-bangalore"
    )


def test_optional_feed_parses_without_hitting_linkedin():
    xml = (ROOT / "data" / "sample_linkedin_feed.xml").read_text(encoding="utf-8")
    jobs = parse_job_feed(xml, source="linkedin")
    assert jobs[0].source == "linkedin-feed"
    assert jobs[0].extra["fetch_mode"] == "live-feed"
    assert "Application Security" in jobs[0].title


def test_cli_offline_prints_browser_searches(tmp_path: Path, capsys):
    assert main(["search", "--offline", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "open-in-browser" in out
    assert "linkedin.com/jobs/search" in out
    assert "naukri.com/" in out
    catalog = json.loads((tmp_path / "matches.json").read_text())
    assert catalog["browser_searches"]
    assert (tmp_path / "browser-searches.md").exists()


def test_cookie_env_does_not_fetch_portals(monkeypatch):
    monkeypatch.setenv("LINKEDIN_COOKIE", "li_at=fake")
    monkeypatch.setenv("NAUKRI_SESSION", "fake")
    errors: list[str] = []
    jobs = fetch_jobs({"user_agent": "test"}, only=["linkedin", "naukri"], on_error=lambda n, e: errors.append(f"{n}:{e}"))
    assert jobs == []
    assert any("cookie/session" in e.lower() for e in errors)
    assert os.environ.get("LINKEDIN_COOKIE")
