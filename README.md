# Job search (human-approved apply)

First-version matcher and apply-drafting pipeline for **Meghana Rao (Meghana Bidarahalli Rao)**, Senior Security Analyst at Deep Armor in Bengaluru.

The original resume file in this repo was only a stub (`my resume`). The candidate profile in [`profile/candidate.yaml`](profile/candidate.yaml) is assembled from that plus **public** sources (LinkedIn public profile text, Sessionize, IoT Show speaker page, Medium, GitHub). No LinkedIn login or scraping automation.

## What this does

1. Loads the structured profile (skills, titles, locations).
2. Fetches openings from **documented public APIs** (Greenhouse, Lever, Ashby, Remotive, Arbeitnow; optional Adzuna/Reed if you set keys).
3. Builds **LinkedIn and Naukri job-search URLs** from her target roles (open in the browser — those sites have no public candidate search API). Optional live listings only if `LINKEDIN_JOBS_FEED_URL` / `NAUKRI_JOBS_FEED_URL` point at an RSS/Atom/JSON feed she may GET.
4. Scores live listings against VAPT / AppSec / cloud / AI-security skills and prints **title, company, link, score, and reasons**.
5. Drafts a cover letter + answers packet and **stops for your review**.

## What this will not do

- Mass-apply or auto-submit.
- Log into LinkedIn or Naukri, drive Easy Apply, solve CAPTCHAs, reuse session cookies, or scrape those sites.
- Call any “apply” HTTP endpoint. Greenhouse/Lever/Ashby **job boards** are public read APIs; submitting an application still happens on the company’s site, by you.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional keys (search works without them): copy [`.env.example`](.env.example).

## Usage

```bash
# Rank live public listings + print LinkedIn/Naukri search URLs (network for ATS APIs only)
python3 -m job_apply search

# LinkedIn/Naukri URLs only (plus any optional feeds), no Greenhouse fetch
python3 -m job_apply search --source linkedin --source naukri

# Same scoring, bundled fixtures only (no network)
python3 -m job_apply search --offline

# Re-print the last ranking
python3 -m job_apply show

# Draft materials for ONE job id from the ranking
python3 -m job_apply draft '<job-id>'

# After you have read the posting and packet, record that you confirmed this job.
# This still does not submit an application.
python3 -m job_apply approve '<job-id>' --i-have-read-this-posting

# Show a small batch (default 5) to confirm one-by-one — there is no apply-all
python3 -m job_apply batch-review
```

Packets land in `out/packets/<job-id>/`:

- `cover-letter.md`
- `answers.md`
- `talking-points.md`
- `CHECKLIST.md` — how to submit on the official form
- `job.json`

## Tests

```bash
python3 -m pytest -q
```

## LinkedIn and Naukri

| Mode | What happens |
| --- | --- |
| **open-in-browser** (default) | `search` writes `out/browser-searches.md` with LinkedIn `jobs/search` and Naukri public search URLs for her target roles in Bengaluru / India / remote. Open them yourself. |
| **live-feed** (optional) | Set `LINKEDIN_JOBS_FEED_URL` or `NAUKRI_JOBS_FEED_URL` to an RSS, Atom, or JSON jobs feed you are allowed to GET. Those items are scored like other listings (`linkedin-feed` / `naukri-feed`). |

Not used: `LINKEDIN_COOKIE` / Naukri session cookies (ignored if set). `LINKEDIN_ACCESS_TOKEN` and `NAUKRI_API_KEY` are documented placeholders — LinkedIn’s official Job Posting API cannot search candidate openings; Naukri has no public candidate search API.

## Profile notes

Edit `profile/candidate.yaml` when you have a fuller CV (notice period, salary bands, exact tool list). Target roles default to senior analyst / AppSec / VAPT / cloud security / AI security, locations Bengaluru / India / remote.
