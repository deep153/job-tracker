# Job Tracker: On-demand job matching and tailored applications

**Status:** ready-for-agent

## Problem Statement

Applying for jobs is slow and repetitive. I have to check many company career pages by hand, read every posting to judge whether I'm a fit, and then either send the same generic resume everywhere (which matches poorly against keyword-driven screening) or spend a long time tweaking my resume for each job. Then I fill out the same application form fields over and over. Bulk auto-apply tools give me no control and produce low-quality, generic applications. They also often break the job platforms' terms of service.

## Solution

A local dashboard that I run on my own machine, only when I click "Run". I configure what I'm looking for (roles, locations, remote/hybrid/on-site, and which of Greenhouse, Lever and Ashby to search) in a Search settings panel on the dashboard; nothing about the search is hardcoded. Each run uses a web search API to discover companies on those platforms that hire for my roles and locations, then pulls new postings from their career boards. It drops jobs that fail my hard preferences, and uses Claude to score how well each remaining job fits my profile, with written reasons. Only strong matches appear.

When I choose to apply to a job, the system takes my real resume (an imported .docx), changes only the summary and the order of my skills to fit the job description, keeps the layout and length the same, and exports a PDF. It also drafts a cover letter if the form asks for one, and answers the application questions from a saved answer bank, with AI drafts for open-ended questions. I review everything in one screen, including a diff of my resume changes. Only after I approve does it fill and submit the company's application form in a browser I can watch.

## User Stories

### Running and discovering jobs
1. As a job seeker, I want to start a job run by clicking a "Run" button, so that jobs are only fetched when I decide.
2. As a job seeker, I want no scheduled or automatic runs, so that nothing happens without my action.
3. As a job seeker, I want each run to fetch postings from every company discovered for my search settings, so that I cover all relevant employers in one click.
4. As a job seeker, I want postings from Greenhouse, Lever and Ashby boards, so that I can use stable public APIs instead of brittle scraping.
5. As a job seeker, I want each run to process only jobs that are new since the last run, so that I don't pay to re-score jobs I've already seen.
6. As a job seeker, I want reposted or duplicate jobs detected, so that the same job doesn't show up twice.
7. As a job seeker, I want jobs that have closed on the company board marked as closed, so that I don't apply to dead postings.
8. As a job seeker, I want to see a run's progress (companies fetched, new jobs, filtered, scored), so that I know what the run is doing.
9. As a job seeker, I want one company's board failing not to fail the whole run, so that one bad board ID doesn't block everything else.
10. As a job seeker, I want a summary of each run (when, how many new jobs, how many matches, errors), so that I can see what changed.
11. As a job seeker, I want only one run active at a time, so that runs don't overlap and duplicate work.

### Search settings and company discovery
12. As a job seeker, I want to configure my roles, locations, work modes and which platforms to search in a Search settings panel on the dashboard, so that nothing about my search is hardcoded.
13. As a job seeker, I want each run to discover companies on my enabled platforms that hire for my roles and locations, using a web search API, so that I don't have to maintain a company list.
14. As a job seeker, I want to enter my search API key in the panel and store it locally, so that discovery works without sharing my key elsewhere.
15. As a job seeker, I want to block a discovered company, so that I stop getting jobs from employers I'm not interested in.
16. As a job seeker, I want to see discovered companies with when they were found, when they were last fetched and how many open jobs they have, so that I can spot dead or empty boards.

### Hard filters
17. As a job seeker, I want the roles in my search settings to also filter job titles, so that only relevant roles are considered.
18. As a job seeker, I want to set excluded keywords in titles, so that roles like "Manager" or "Principal" are dropped.
19. As a job seeker, I want the locations and remote, hybrid or on-site choice in my search settings to filter jobs, so that only jobs I can actually take are considered.
20. As a job seeker, I want to set my seniority and years of experience, so that roles far above or below my level are dropped.
21. As a job seeker, I want to say whether I need visa sponsorship, so that postings stating "no sponsorship" are excluded.
22. As a job seeker, I want to set a minimum salary that applies only when the posting lists a salary, so that underpaying roles are dropped without hiding postings that don't list pay.
23. As a job seeker, I want hard filters applied before any AI scoring, so that I don't pay to score jobs I'd never take.
24. As a job seeker, I want to see how many jobs each filter removed in a run, so that I can tell when a filter is too strict.
25. As a job seeker, I want to adjust the minimum match score shown (default 70), so that I control how selective the dashboard is.

### Scoring and the dashboard
26. As a job seeker, I want each remaining job scored 0-100 for fit against my resume and preferences, so that I can focus on the jobs where I'm most likely to be selected.
27. As a job seeker, I want each score to come with short written reasons, so that I understand why a job ranks high or low.
28. As a job seeker, I want to see which job-description keywords I match and which I'm missing, so that I know what tailoring can and can't fix.
29. As a job seeker, I want the dashboard to list only jobs at or above my score threshold, sorted by score, so that the best matches come first.
30. As a job seeker, I want to filter and sort the dashboard by company, location, posted date and score, so that I can browse efficiently.
31. As a job seeker, I want to open the full job description inside the dashboard, so that I don't have to switch to the company site.
32. As a job seeker, I want a link to the original posting, so that I can check it on the company's site.
33. As a job seeker, I want to dismiss jobs I'm not interested in, so that they stop appearing.
34. As a job seeker, I want jobs I've scored but not acted on to stay visible across runs until I dismiss them or they close, so that I don't lose good matches.
35. As a job seeker, I want each job's score saved, so that re-opening the dashboard doesn't trigger new AI calls.
36. As a job seeker, I want to re-score a single job on demand after updating my resume, so that its score reflects my current profile.
37. As a job seeker, I want a cheaper model used for scoring and a stronger one for tailoring, with both configurable, so that costs stay low without hurting resume quality.

### Resume import and master profile
38. As a job seeker, I want to upload my existing resume as a .docx in the UI, so that the system uses my real resume as the template.
39. As a job seeker, I want the system to show my resume's paragraphs and let me mark which ones are the Summary and which are the Skills section, so that tailoring touches only those parts.
40. As a job seeker, I want to keep a master skills list (pre-filled from my resume and editable), so that tailoring can only use skills I actually have.
41. As a job seeker, I want to replace my master resume with a newer version, so that future tailoring uses my latest experience.
42. As a job seeker, I want a preview of my imported resume rendered as a PDF, so that I can confirm the import and conversion look right.
43. As a job seeker, I want the import rejected with a clear message if the file isn't a valid .docx or no Summary or Skills section can be mapped, so that I don't get broken output later.

### Tailoring
44. As a job seeker, I want to click "Apply" on a job to start tailoring, so that only jobs I choose get applications.
45. As a job seeker, I want the summary rewritten to reflect the job's main requirements, so that the top of my resume speaks to the role.
46. As a job seeker, I want my skills reordered so the most relevant come first, so that keyword screening and recruiters see them right away.
47. As a job seeker, I want keywords from the job description added to my skills only if they're in my master skills list, so that my resume never claims skills I don't have.
48. As a job seeker, I want my experience bullets, job titles, dates, employers and education left unchanged, so that edits stay minor and truthful.
49. As a job seeker, I want the original fonts, styles and layout preserved, so that the tailored resume looks exactly like mine.
50. As a job seeker, I want the tailored resume to keep the same page count as my master, so that tailoring never pushes it onto an extra page.
51. As a job seeker, I want the system to automatically shorten the edits and retry if the page count grows, so that I don't have to fix length myself.
52. As a job seeker, I want the final tailored resume as a PDF, so that it's what gets uploaded.
53. As a job seeker, I want the tailored .docx kept alongside the PDF, so that I can edit it by hand if needed.
54. As a job seeker, I want a keyword-coverage number before and after tailoring, so that I can see what the tailoring achieved.
55. As a job seeker, I want each tailored resume saved and linked to its job, so that I know exactly which version I sent where.

### Cover letters and application answers
56. As a job seeker, I want a tailored cover letter generated only when the application form has a cover letter field, so that I don't get unnecessary documents.
57. As a job seeker, I want the cover letter based only on facts in my resume, so that it never invents experience.
58. As a job seeker, I want an answer bank for standard questions (work authorization, sponsorship, salary expectation, start date, LinkedIn/GitHub/portfolio links, EEO and demographic answers), so that the same questions are answered the same way every time.
59. As a job seeker, I want to manage the answer bank in Settings, so that I can add or correct answers.
60. As a job seeker, I want form questions matched to answer-bank entries even when the wording differs, so that small phrasing changes don't cause misses.
61. As a job seeker, I want open-ended questions (like "Why do you want to work here?") drafted by AI from my resume and the job, so that I start from a relevant draft.
62. As a job seeker, I want questions the system can't confidently answer flagged in the review screen, so that nothing gets submitted with a guess.
63. As a job seeker, I want the option to save an answer I type in review into the answer bank, so that the system learns over time.
64. As a job seeker, I want EEO and demographic questions answered only from my saved choices (including "decline to answer"), so that sensitive answers are never generated by AI.

### Review and approval
65. As a job seeker, I want a review screen before anything is submitted, so that I stay in control of every application.
66. As a job seeker, I want a side-by-side diff of my master and tailored summary and skills, so that I can see exactly what changed.
67. As a job seeker, I want to preview the tailored PDF in the review screen, so that I see exactly what the employer will see.
68. As a job seeker, I want to edit the tailored summary and skills in review and regenerate the PDF, so that I can fine-tune before submitting.
69. As a job seeker, I want to edit the cover letter and every form answer in review, so that I can correct anything.
70. As a job seeker, I want "Approve and submit" disabled while any required question is still flagged as unanswered, so that I can't submit an incomplete application.
71. As a job seeker, I want to cancel an application in review, so that I can change my mind without anything being sent.
72. As a job seeker, I want to save an application as a draft and come back later, so that I don't have to finish in one sitting.

### Submission
73. As a job seeker, I want the application submitted by filling the company's public form in a visible browser after I approve, so that I can watch what's sent.
74. As a job seeker, I want the tailored PDF uploaded as my resume and the cover letter attached or pasted as the form requires, so that the right documents are sent.
75. As a job seeker, I want the browser to stay open and hand control to me if a CAPTCHA or an unexpected field appears, so that I can finish by hand instead of the submission failing.
76. As a job seeker, I want the system to detect the form's confirmation and record success, so that I know the application went through.
77. As a job seeker, I want a failed submission recorded with the reason and a screenshot, so that I can retry or apply by hand.
78. As a job seeker, I want to be blocked from submitting twice to the same job, so that I never send duplicate applications.

### Tracking
79. As a job seeker, I want an Applications page listing every application with company, role, date, score and status, so that I can track my pipeline.
80. As a job seeker, I want each application to link to the exact resume PDF, cover letter and answers I sent, so that I can prepare for interviews.
81. As a job seeker, I want to update an application's status by hand (for example interviewing, rejected, offer), so that the tracker stays current.
82. As a job seeker, I want applied jobs removed from the main dashboard list, so that the dashboard shows only what's still to act on.

### Settings and privacy
83. As a job seeker, I want to enter my Anthropic API key in Settings and store it locally, so that the app can call Claude without sharing my key elsewhere.
84. As a job seeker, I want all my data (resume, answers, applications) stored only on my machine, so that my personal information stays private.
85. As a job seeker, I want to see the approximate AI cost of each run and each tailoring, so that I can keep spending in check.

## Implementation Decisions

### Architecture
- A single-user local web app: a Python FastAPI backend, a React (Vite) single-page frontend, and SQLite storage. It runs only on my machine. There's no authentication and no scheduler.
- Four external systems sit behind narrow interfaces (ports) so they can be swapped for fakes in tests: **Board Discovery** (web search API), **Job Board Source** (fetches postings), **LLM** (Claude), and **Form Submitter** (browser automation). Everything else is internal.

### Modules
- **Board Discovery**: given my roles, locations and enabled platforms, queries a web search API (Brave Search by default) with site-restricted searches (e.g. `site:job-boards.greenhouse.io "Backend Engineer" "New York"`) and extracts company board IDs from the result URLs. The number of queries per run is capped. A search failure is recorded and the run continues with already-discovered companies.
- **Job Board Sources**: one adapter each for Greenhouse, Lever and Ashby, all with the same interface: given a company board ID, return a list of normalized job postings. A posting has: source platform, company board ID, external job ID, title, location(s), remote flag if known, salary range if given, description text, posting URL, application URL, and posted/updated timestamp. They use the public read-only job-board APIs.
- **Run Orchestrator**: runs one job run at a time, in the background. It first runs discovery and saves newly found companies, then fetches all discovered, non-blocked companies on enabled platforms in parallel, stores only new or changed postings (de-duplicated by platform + external ID, plus a content hash to catch reposts), marks postings missing from a board as closed, applies filters, scores the jobs that pass, and records run statistics and per-company errors. A failing company is recorded and skipped; the run continues.
- **Hard Filters**: pure, deterministic rules over a normalized posting and my search settings: title include (my roles) / exclude, location and remote mode, seniority and years, visa sponsorship (detects "no sponsorship" wording), and minimum salary (only when salary is listed). Each rule reports why it rejected a job so the numbers can be shown.
- **Fit Scorer**: sends my master resume text, preferences and the job description to the LLM and gets back structured output: score 0-100, short reasons, matched keywords, and missing keywords. Results are cached per job and resume version. Re-scoring is explicit.
- **Resume Master**: imports a .docx, splits it into paragraphs with their style info, stores the original file, and saves my mapping of which paragraphs are the Summary and which are Skills, plus the editable master skills list.
- **Resume Tailor**: takes the master resume, mapping, master skills list and job description, and gets a structured edit from the LLM: new summary text, plus an ordered skills list that may only contain items from the master skills list. It enforces the allowed-skills rule in code, not only in the prompt.
- **Resume Renderer**: writes the edits into a copy of the master .docx by replacing text inside the existing formatting segments of the mapped paragraphs (preserving styles), converts it to PDF with headless LibreOffice, checks that the page count equals the master's, and asks the Tailor to shorten and retry once if it doesn't.
- **Answer Engine**: matches form questions to answer-bank entries (normalized text plus fuzzy matching), uses the LLM for open-ended questions, never uses the LLM for EEO/demographic questions, and labels each answer as from the bank, AI-drafted, or needs input.
- **Cover Letter Writer**: produced only when the form has a cover letter field. It uses facts from the master resume and the job description only.
- **Form Submitter**: one Playwright adapter per platform form (Greenhouse, Lever, Ashby). It runs a visible browser, reads the form's fields (used before review to know which questions to answer), fills fields, uploads the PDF, submits, and detects the confirmation. On a CAPTCHA or an unrecognized required field it hands over to me by leaving the browser open and marking the application "needs manual completion".
- **Application Tracker**: holds application records and their lifecycle.

### Application lifecycle
- Statuses: `drafting` -> `in_review` -> `submitting` -> `submitted` | `needs_manual` | `failed`. After submission I can set `interviewing`, `rejected`, `offer` or `withdrawn` by hand. A job can have at most one application past `in_review`.

### Data model (tables)
- companies (platform, board ID, discovered at, discovering query, blocked, last fetched, last error)
- jobs (normalized posting fields, content hash, first seen, last seen, closed flag, dismissed flag)
- runs (start and finish times, counts per stage, filter-rejection counts, errors, estimated cost)
- scores (job, resume version, score, reasons, matched and missing keywords, model)
- resume_master (versions of the original .docx, paragraph mapping, master skills list, page count)
- resume_versions (job, tailored summary, skills order, .docx and PDF locations, keyword coverage before and after)
- answer_bank (canonical question, answer, category including EEO, last used)
- applications (job, resume version, cover letter, answers with their source labels, status, timestamps, failure reason, screenshot location)
- search_settings (roles, locations, work modes, enabled platforms, other filters, score threshold)
- settings (API keys for Claude and the search API, model choices)

### HTTP API (the testing seam)
- Run: start a run, get run status and progress, list past runs.
- Jobs: list matched jobs (filter and sort), get job detail, dismiss, re-score.
- Companies: list discovered companies, block or unblock.
- Search settings: get and update. A run is refused until roles, a location or remote, an enabled platform and a search API key are set.
- Resume: upload .docx, get paragraphs, save mapping and master skills list, get preview PDF.
- Applications: start an application for a job (tailor, read form fields, draft answers and cover letter -> `in_review`), get review bundle (diff, PDF, cover letter, answers with source labels), update edits and regenerate PDF, approve and submit, cancel, list, update status by hand.
- Answer bank: list, add, update, delete.
- Settings: set the Claude and search API keys, get the cost summary.

### LLM usage
- Anthropic Claude through the official SDK, always with structured (tool or JSON-schema) output. Scoring defaults to a Haiku-class model; tailoring, cover letters and open-ended answers default to a Sonnet-class model. Both are configurable.
- Every tailoring and writing prompt says: never invent experience, employers, dates, metrics or skills. The rules that matter (skills only from the master list; only Summary and Skills change) are also checked in code after the model responds.

## Testing Decisions

- **One seam: the backend HTTP API.** Tests drive the system the way the dashboard does, through its HTTP endpoints, and only check observable results: API responses, files produced (the PDF's text and page count), and recorded application outcomes. Tests don't check internal function calls, prompt wording, or table layout.
- **Fakes at the four external boundaries only:**
  - Board Discovery: a fake search API returning scripted result URLs, including non-board URLs, duplicates and a failing search.
  - Job Board Source: recorded real response fixtures for Greenhouse, Lever and Ashby, served by a fake HTTP layer. The fixtures include new, changed, reposted and closed postings, plus a failing board.
  - LLM: a scripted fake that returns set structured outputs, including bad outputs (skills not in the master list, a summary too long to fit) to prove the code-level guards work.
  - Form Submitter: real Playwright pointed at local fake application pages imitating each platform's form, including variants with a cover letter field, unknown required questions, and a CAPTCHA placeholder.
- **Good tests check behavior, not implementation.** For example: "after two runs where the second fixture adds one posting, only one new job is scored"; "a tailored PDF has the same page count as the master, and its text contains only master-list skills"; "Approve is rejected while a required question is unanswered"; "submitting the same job twice is refused"; "a CAPTCHA form ends in needs_manual".
- **Modules covered (all through the API):** discovery and blocking; run de-duplication and closing; each hard filter; showing scores and the threshold; resume import and mapping; tailoring guards and page-count retry; answer-bank matching and the no-AI rule for EEO questions; the cover letter appearing only when there's a field; the review/approve/submit lifecycle; tracker updates.
- **Real dependencies kept in tests:** SQLite (a temporary database per test), python-docx, and LibreOffice conversion, because preserving formatting and page count is a core promise that fakes can't check.
- **Prior art:** none. This is a new project, and these API-level tests set the pattern for future work.

## Out of Scope

- LinkedIn, Indeed, Glassdoor, ZipRecruiter, Workday and any other source besides Greenhouse, Lever and Ashby.
- Scheduled or automatic runs, and background daemons.
- Submitting without my review and approval.
- Rewriting or reordering experience bullets, or changing titles, dates, employers or education.
- Resumes in formats other than .docx, and outputs other than PDF (plus the kept .docx).
- Adding companies by hand, and built-in or seeded company lists.
- Reading email for recruiter replies, and automatic follow-up messages.
- Multiple users, authentication, cloud hosting, or syncing between devices.
- Solving CAPTCHAs automatically.
- Predicting real hiring probability. The score measures fit, not likelihood of an offer.

## Further Notes

- The Greenhouse, Lever and Ashby submit APIs need each employer's private key, which is why submission uses browser automation on the public form.
- LibreOffice must be installed locally for PDF conversion. The app should check for it at startup and show a clear message if it's missing.
- Keyword coverage will be limited because only the summary and skills change. If coverage proves too low in practice, a later spec could allow rephrasing bullets within a job while keeping the facts identical.
- Greenhouse, Lever and Ashby only list jobs per company; there is no public cross-company job search. That is why discovery goes through a web search API, and why roles and locations are also applied as filters to everything a discovered company lists.
- Suggested delivery order, which `/to-tickets` should turn into vertical slices: fetch, search settings and discovery, filter, score and dashboard first; then resume import, tailoring and review; then form submission and the answer bank.
