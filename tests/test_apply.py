import json
from pathlib import Path

import pytest

from job_apply.apply import APPROVAL_FLAG, approve_job, write_packet
from job_apply.cli import main
from job_apply.models import Job
from job_apply.profile import load_profile
from job_apply.store import write_matches
from job_apply.matcher import score_job


def test_draft_stops_at_review(tmp_path: Path):
    profile = load_profile()
    job = Job(
        id="sample:vapt-1",
        source="sample",
        title="Senior Security Analyst — VAPT",
        company="Peer",
        url="https://example.com/jobs/vapt-senior",
        location="Bengaluru",
        description="VAPT web application security",
    )
    match = score_job(job, profile)
    folder = write_packet(profile, job, match.to_dict(), tmp_path)
    letter = (folder / "cover-letter.md").read_text()
    assert letter.startswith("Dear")
    assert "Title aligns with target" not in letter
    assert "does **not** submit" in (folder / "CHECKLIST.md").read_text()
    assert APPROVAL_FLAG in (folder / "CHECKLIST.md").read_text()


def test_approve_requires_explicit_flag(tmp_path: Path):
    profile = load_profile()
    job = Job(
        id="sample:vapt-1",
        source="sample",
        title="Senior Security Analyst — VAPT",
        company="Peer",
        url="https://example.com/x",
        location="Bengaluru",
        description="VAPT",
    )
    write_matches([score_job(job, profile)], tmp_path)
    with pytest.raises(PermissionError):
        approve_job("sample:vapt-1", confirmed=False, out_dir=tmp_path)
    path = approve_job("sample:vapt-1", confirmed=True, out_dir=tmp_path)
    data = json.loads(path.read_text())
    assert data["approvals"][0]["submit_action"] == "manual"


def test_record_then_draft_naukri_packet(tmp_path: Path, capsys):
    url = "https://www.naukri.com/job-listings-example-123"
    assert (
        main(
            [
                "record",
                "--url",
                url,
                "--title",
                "Technical Lead - Penetration Testing",
                "--company",
                "Example Co",
                "--location",
                "Bengaluru",
                "--source",
                "naukri",
                "--id",
                "naukri:123",
                "--description",
                "VAPT web application security OWASP penetration testing AI security prompt injection",
                "--out",
                str(tmp_path),
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "Penetration Testing" in out
    assert main(["draft", "naukri:123", "--out", str(tmp_path)]) == 0
    packet = tmp_path / "packets" / "naukri_123"
    assert "Naukri" in (packet / "CHECKLIST.md").read_text()
    assert "does **not** submit" in (packet / "CHECKLIST.md").read_text()


def test_cli_offline_search_and_refuses_approve_without_flag(tmp_path: Path, capsys):
    assert main(["search", "--offline", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Senior Security Analyst" in out
    assert "Account Executive" not in out
    assert main(["approve", "sample:vapt-1", "--out", str(tmp_path)]) == 2
