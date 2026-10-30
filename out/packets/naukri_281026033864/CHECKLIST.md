# How to apply on Naukri (human-only)

This tool does **not** submit applications and does not log into Naukri.

1. Open the posting while logged in as yourself: https://www.naukri.com/job-listings-technical-lead-penetration-testing-happiest-minds-technologies-bengaluru-5-to-8-years-281026033864?src=simjobsjd_rt
2. Re-read the full description, experience band, and any questions Naukri shows.
3. Edit `cover-letter.md` and `answers.md` so they sound like you.
4. Fill Naukri profile fields yourself: notice period, current/expected CTC, current company, and experience. Do not guess.
5. Attach your resume (PDF). This repo does not bundle a CV file.
6. Paste or upload the cover letter only after you have edited it. Click Apply yourself.
7. Record the outcome locally (still not a submit):

   `python3 -m job_apply approve naukri:281026033864 --i-have-read-this-posting`

Do not paste Naukri passwords or session cookies into this tool.
