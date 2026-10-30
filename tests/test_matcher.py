from job_apply.matcher import rank_jobs, score_job
from job_apply.models import Job
from job_apply.profile import load_profile, skill_weights


def _job(**kwargs) -> Job:
    base = dict(
        id="t",
        source="test",
        title="Role",
        company="Co",
        url="https://example.com",
        location="",
        description="",
        extra={},
    )
    base.update(kwargs)
    return Job(**base)


def test_profile_loads():
    profile = load_profile()
    assert profile["name"] == "Meghana Rao"
    assert "VAPT" in " ".join(profile["skills"]["keywords"])


def test_governance_domains_are_not_used_for_matching():
    profile = load_profile()
    banned = {
        "siem",
        "edr",
        "dlp",
        "active directory",
        "firewall",
        "governance",
        "web proxy",
        "av/edr",
        "proxy",
    }
    weights = set(skill_weights(profile))
    keywords = {k.lower() for k in profile["skills"]["keywords"]}
    blob = str(profile.get("talks_and_writing") or "").lower()
    assert not (banned & weights)
    assert not (banned & keywords)
    match = score_job(
        _job(
            title="SIEM Engineer",
            location="Bengaluru",
            description="SIEM EDR DLP firewall Active Directory web proxy AV/EDR governance",
        ),
        profile,
    )
    assert not (banned & set(match.skill_hits))
    assert "governance activity calendar" not in blob


def test_vapt_outscores_sales_and_unrelated():
    profile = load_profile()
    vapt = _job(
        id="v",
        title="Senior Security Analyst VAPT",
        location="Bengaluru",
        description="web application security mobile security cloud security OWASP",
    )
    sales = _job(id="s", title="Enterprise Account Executive", location="Bengaluru", description="enterprise software sales")
    nurse = _job(id="n", title="Registered Nurse", location="London", description="patient care")
    ranked = rank_jobs([nurse, sales, vapt], profile, min_score=0, limit=10)
    assert ranked[0].job.id == "v"
    assert ranked[0].score > score_job(sales, profile).score
    assert score_job(sales, profile).score == 0
    assert ranked[0].skill_hits


def test_us_remote_is_weaker_than_india_and_pm_is_downranked():
    profile = load_profile()
    india = score_job(
        _job(
            title="Senior Security Engineer",
            location="Bengaluru, India",
            description="application security VAPT",
        ),
        profile,
    )
    us_remote = score_job(
        _job(
            title="Senior Security Engineer",
            location="Remote - US",
            description="application security VAPT",
        ),
        profile,
    )
    pm = score_job(
        _job(
            title="Senior Product Manager, Vulnerability Research",
            location="Remote, United States",
            description="security product roadmap",
        ),
        profile,
    )
    assert india.score > us_remote.score
    assert "confirm India hiring" in " ".join(us_remote.reasons)
    assert pm.score < india.score


def test_intern_is_penalized_vs_senior():
    profile = load_profile()
    senior = score_job(
        _job(
            title="Senior Application Security Engineer",
            location="Remote India",
            description="application security OWASP product security",
        ),
        profile,
    )
    intern = score_job(
        _job(
            title="Cybersecurity Intern",
            location="Remote",
            description="application security OWASP",
        ),
        profile,
    )
    assert senior.score > intern.score
