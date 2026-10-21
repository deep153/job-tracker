# Job Tracker: Resume profile, reliable scoring, useful filters and stronger tailoring

**Status:** ready-for-agent

## Problem Statement

After the first real run and the first application, four problems showed up.

1. **Some jobs are never scored.** In my first run, 26 of the 56 jobs that passed the filters failed with "Claude's answer was cut off." The Fit Scorer allows 1,000 output tokens, and even successful answers averaged about 900. Those jobs sit unscored under "Below threshold", and the only retry is a full new run, which usually fails the same way for the same long postings.
2. **"Filtered out" is noise.** Discovery finds companies, and each run then pulls every opening on those companies' boards. Of 2,657 new jobs, 2,564 were rejected because the title didn't match my role ("Lead Client Partner", "Global Strategic Accounts"). The "Filtered out" tab lists all of them and grows with every company discovered, so it's useless for spotting a filter that's too strict. Meanwhile the title rule wrongly rejects real matches like "Backend Developer" and "Back End Software Engineer".
3. **Tailoring barely changes the resume.** On my first application, keyword coverage was 9 of 20 before tailoring and 9 of 20 after, and the Skills lines held exactly the same skills in a different order. The Resume Tailor can only rewrite the Summary and reorder skills. Its "allowed skills" are the skills already on the resume, so it can never add one. My experience bullets, where most of the evidence lives, are never touched. The coverage number uses exact phrase matching against vague keywords the tailor picks itself, and the tailored resume is never re-scored, so I can't tell whether tailoring helped.
4. **I fill in the same personal details on every form.** On my first application, First Name, Last Name, Email, Phone, LinkedIn, School, Degree and Discipline were all left as "needs input", because my answer bank was empty, even though all of that is on the resume I uploaded.

## Solution

- **Profile from my resume.** After I mark up my resume on the Resume page, the app reads my contact details, links, location and education from it (code finds the email, phone and links; one AI call reads the name, city and degrees). It shows them in a review form. The form also asks the standard questions a resume can't answer (work authorization, sponsorship, how I heard about the job, referral). When I confirm, the answers are saved as regular answer-bank entries, so the existing Answer Engine fills them in on every Greenhouse, Lever and Ashby form. Re-uploading a resume shows what changed and never overwrites an answer unless I choose to.
- **Reliable scoring.** The Fit Scorer gets enough room to finish its answer, and the dashboard offers "Score N unscored jobs", which scores only those, without searching or fetching.
- **Near misses only in "Filtered out".** The tab lists only jobs whose title matched my role but which were rejected by a narrower rule (location, seniority, experience, salary, sponsorship). Title mismatches are kept but not listed; the run summary shows them as one line ("2,564 other roles at these companies skipped"). Title matching understands common variants ("back end" = "backend", "developer" = "engineer", "SWE" = "software engineer", "Sr" = "Senior").
- **Tailoring that moves the score.**
  - I mark my experience bullets on the Resume page, as I do for the Summary and Skills (prefilled from Word's list items).
  - The Resume Tailor may reword the text of a bullet after its bold label, using the posting's terms where the bullet backs them up. It must keep every number and stay close to the original length.
  - Code reverts any bullet that changes a number or brings in a skill that's neither in the original bullet nor on my master skills list.
  - The tailor targets the keywords the Fit Scorer found, and reports the ones it couldn't honestly cover as gaps.
  - On the review screen I see a before/after fit score, a per-bullet diff I can edit or revert, and the gaps list. Each gap has "Add to my skills", which adds it to my master skills list and puts it on the Skills line I pick, without another AI call.

## User Stories

### Profile from my resume
1. As a job seeker, I want my contact details read from the resume I upload, so that I don't type them into every application.
2. As a job seeker, I want my email found even when it's only a link in the document, so that nothing on my resume is missed.
3. As a job seeker, I want my LinkedIn, GitHub and personal website found, including when the visible text is just "LinkedIn" and the URL is in the link, so that link fields get filled.
4. As a job seeker, I want my phone number found in the format I wrote it, so that forms get the number I use.
5. As a job seeker, I want my first and last name split correctly and in normal capitalization even if my resume shows my name in all caps, so that forms don't get "DEEP".
6. As a job seeker, I want my city, state and country read from my resume header, so that location questions are answered.
7. As a job seeker, I want my education read from the resume (school, degree, field of study, graduation month and year), so that education fields get filled.
8. As a job seeker, I want the highest or most recent degree used by default when my resume lists several, so that single-education forms get the most relevant one.
9. As a job seeker, I want to switch to a different degree in the review form, so that I can choose which one forms use.
10. As a job seeker, I want degrees written out in full ("Master of Science"), so that degree dropdowns on forms can match them.
11. As a job seeker, I want the extraction to start automatically after I save my resume's markings, so that I don't have to remember a separate step.
12. As a job seeker, I want to review every extracted value before anything is saved, so that a misread doesn't end up on an application.
13. As a job seeker, I want to edit any extracted value in the review form, so that I can fix mistakes before saving.
14. As a job seeker, I want to skip any field in the review form, so that I only save what I want forms to use.
15. As a job seeker, I want the same form to ask the common questions my resume can't answer (authorized to work in the US, need for sponsorship, how I heard about the job, whether I was referred), so that I answer them once.
16. As a job seeker, I want the sponsorship question prefilled from my search settings, so that my answers stay consistent.
17. As a job seeker, I want the country prefilled from my resume's location, so that I type less.
18. As a job seeker, I want my confirmed answers saved as normal answer-bank entries, so that I can see and edit them in the Answer bank like any other saved answer.
19. As a job seeker, I want those entries worded the way application forms word them ("First Name", "LinkedIn Profile", "School"), so that the existing question matching fills them without extra work.
20. As a job seeker, I want my existing answers never overwritten silently, so that answers I've corrected by hand survive a new resume upload.
21. As a job seeker, I want the review form to show "current vs from resume" only for answers that differ, with my current answer kept by default, so that updating after a new upload is quick.
22. As a job seeker, I want to reopen the review form later ("Update profile from resume"), so that I can refresh my profile after changing my resume.
23. As a job seeker, I want the extraction's AI cost recorded like other AI calls, so that the cost summary stays complete.
24. As a job seeker, I want a clear message if extraction needs my Anthropic API key and it isn't set, so that I know what to do.
25. As a job seeker, I want the next application after confirming my profile to show those fields as "from bank", so that I can see it worked.

### Reliable scoring
26. As a job seeker, I want every job that passes the filters to get a score, so that good matches aren't hidden among unscored jobs.
27. As a job seeker, I want the Fit Scorer to have enough room to finish its answer on long postings, so that long postings aren't the ones that fail.
28. As a job seeker, I want the scorer told how many reasons and keywords to give, so that answers stay short and cheap.
29. As a job seeker, I want a "Score N unscored jobs" button on the dashboard when some jobs have no score, so that I can fill the gaps without a full run.
30. As a job seeker, I want that button to score only the unscored jobs, without searching or fetching boards, so that it's quick and costs nothing beyond those scores.
31. As a job seeker, I want a scoring-only run to show progress and appear in run history like other runs, labelled as scoring only, so that I can tell runs apart.
32. As a job seeker, I want a scoring-only run refused while another run is active, so that runs never overlap.
33. As a job seeker, I want scoring errors from a scoring-only run reported the same way as in a full run, so that failures stay visible.

### Filtered out and title matching
34. As a job seeker, I want "Filtered out" to list only jobs whose title matched my role but that another filter rejected, so that the tab shows me jobs worth a second look.
35. As a job seeker, I want jobs rejected only for a non-matching title kept out of every list, so that sales and account roles at discovered companies don't clutter the dashboard.
36. As a job seeker, I want those title-mismatched jobs still stored, so that if I add a role to my search settings, matching jobs come back without a new run.
37. As a job seeker, I want the run summary to show title mismatches as one line ("N other roles at these companies skipped"), so that I know they exist without reviewing them.
38. As a job seeker, I want the "Review filtered jobs" prompt to count only near misses, so that it only appears when there's something worth reviewing.
39. As a job seeker, I want "Backend Developer" to match my "Backend Engineer" role, so that equivalent titles aren't dropped.
40. As a job seeker, I want "Back End" and "Back-End" treated as "Backend" (and likewise "Front End"), so that spacing and hyphens don't matter.
41. As a job seeker, I want "SWE" to match "Software Engineer" and "Sr" to match "Senior", so that abbreviated titles aren't dropped.
42. As a job seeker, I want unrelated titles like "Lead Client Partner" still rejected, so that the synonyms don't let noise through.

### Marking experience bullets
43. As a job seeker, I want to mark which paragraphs of my resume are experience bullets, so that the tailor knows what it may reword.
44. As a job seeker, I want that marking prefilled with the bulleted list items that come after my Summary and Skills, so that marking takes one look.
45. As a job seeker, I want to untick any paragraph (for example publications), so that only the bullets I choose can change.
46. As a job seeker, I want a paragraph to belong to only one of Summary, Skills or Experience bullets, so that the markings never conflict.
47. As a job seeker, I want resumes I marked before this change to keep working, tailoring only the Summary and Skills until I mark bullets, so that nothing breaks.

### Tailoring
48. As a job seeker, I want the tailor to reword my experience bullets toward the posting's wording where my experience backs it up, so that my resume speaks the job's language.
49. As a job seeker, I want each bullet's bold label kept exactly as it is, so that my resume's structure and look don't change.
50. As a job seeker, I want every number in a bullet (percentages, times, counts, "9+") kept exactly, so that no metric is ever altered.
51. As a job seeker, I want rewritten bullets kept close to their original length, so that my resume keeps its page count.
52. As a job seeker, I want the tailor free to leave a bullet unchanged when it already fits, so that it doesn't make change for its own sake.
53. As a job seeker, I want code, not only the prompt, to revert any bullet that changes or drops a number, so that metrics are guaranteed.
54. As a job seeker, I want code to revert any bullet that adds a skill or tool that's neither in the original bullet nor on my master skills list, so that the tailor can't invent experience.
55. As a job seeker, I want code to revert any bullet that grew too much, so that one bullet can't push the resume to another page.
56. As a job seeker, I want reverted bullets marked on the review screen with the reason, so that I understand what was rejected.
57. As a job seeker, I want the tailor to aim at the keywords the Fit Scorer found (matched and missing) for this job, so that tailoring targets what actually lowers my score.
58. As a job seeker, I want the tailor to list the keywords it couldn't honestly cover as gaps, so that I can see what my resume really lacks.
59. As a job seeker, I want only skills on my master skills list ever added to my Skills section, so that my resume claims nothing I didn't list.
60. As a job seeker, I want the Summary and Skills tailoring to keep working as before, alongside bullet rewording, so that nothing I rely on is lost.
61. As a job seeker, I want the shorten-and-retry step to also cover bullets, so that a too-long tailored resume still ends at my master's page count.

### Measuring and reviewing the result
62. As a job seeker, I want the tailored resume re-scored by the Fit Scorer and shown next to the original score, so that I can see whether tailoring helped.
63. As a job seeker, I want keyword coverage measured against the scorer's keywords, so that the number reflects the job's real requirements.
64. As a job seeker, I want coverage to ignore case, punctuation and plurals, and to count "Observability (Grafana, Kibana)" as covering "Observability", so that coverage isn't understated.
65. As a job seeker, I want a before/after diff for every changed bullet on the review screen, so that I can check each change.
66. As a job seeker, I want to edit any rewritten bullet's text on the review screen, so that I can fix wording I don't like.
67. As a job seeker, I want a "Use original" button on each changed bullet, so that I can undo one rewrite without losing the others.
68. As a job seeker, I want my bullet edits checked by the same number and skill rules as the tailor's, so that a typo can't change a metric unnoticed.
69. As a job seeker, I want the resume re-scored after I regenerate it with my edits, so that the score always matches what I'll send.
70. As a job seeker, I want a gaps list on the review screen, so that I can see which requirements my resume doesn't show.
71. As a job seeker, I want an "Add to my skills" button on each gap, so that skills I really have but left off my resume can be added.
72. As a job seeker, I want to choose which Skills line a gap goes on, with the best guess preselected, so that it lands in the right group.
73. As a job seeker, I want adding a gap to update this application's resume and PDF right away without another AI call, so that it's instant and free.
74. As a job seeker, I want a skill added from a gap saved to my master skills list, so that future applications can use it.
75. As a job seeker, I want the page-count check to apply after adding a gap, so that the resume stays the same length.

## Implementation Decisions

### Fit Scorer and runs
- The Fit Scorer's output limit rises from 1,000 to 3,000 tokens. Its system prompt states the caps (at most 5 reasons, 15 matched and 15 missing keywords) instead of relying only on trimming afterward.
- Runs gain a kind, either full or scoring-only. A scoring-only run skips discovery and fetching and scores the same set of jobs a full run's scoring stage would: open, visible, passed the filters, and no score for the current resume version and content. It uses the same one-run-at-a-time lock, progress counters, error reporting and cost recording as full runs. Existing runs are full runs.
- The dashboard needs the number of unscored jobs, to show or hide the "Score N unscored jobs" button.

### Hard Filters and the dashboard
- The filtered-out job list leaves out jobs rejected by the role (title) rule. They stay stored with their rejection, so re-filtering after a settings change can bring them back.
- The run summary keeps per-rule counts. The dashboard presents the role count as a single "other roles skipped" line, and only the other rules count toward the "Review filtered jobs" prompt.
- Title matching normalizes both the title and each role before the existing "every role word appears in the title" check. It uses a small built-in synonym table, applied to phrases before words:
  - "back end" / "back-end" become "backend", and "front end" / "front-end" become "frontend".
  - "developer" and "dev" become "engineer".
  - "swe" becomes "software engineer".
  - "sr" becomes "senior".
- The table isn't user-configurable.

### Resume Master
- A resume version gains a third marking, the experience bullets: a list of paragraph indexes alongside the Summary and Skills markings.
- Saving the markings validates that the three sets don't overlap and that bullets aren't blank. Bullets are optional, and versions without them stay ready.
- The proposed default for bullets is every list-item paragraph that comes after the last Summary or Skills paragraph.
- A bullet's label is the text up to and including its first colon, the same rule Skills lines already use. A bullet without a colon has no label and can be reworded whole.

### Profile extraction (new module: Profile Extractor)
- Input: the current resume version's .docx and paragraphs. Output: a proposal of profile fields.
- Code reads the email, phone and URLs from paragraph text and from the document's hyperlink targets, and sorts the URLs into LinkedIn, GitHub and website.
- One structured LLM call (the tailoring model, recorded as AI usage of kind "profile") returns:
  - first name and last name, in proper case;
  - city, region and country;
  - a list of education entries, each with school, degree written in full, discipline, end month and end year.
- The highest or most recent degree is preselected; the others are offered as alternatives.
- Proposed answer-bank entries use fixed wording so the existing Answer Engine matches form labels:
  - personal: First Name, Last Name, Email, Phone, Location (City), Country
  - links: LinkedIn Profile, GitHub, Website
  - other: School, Degree, Discipline, End date month, End date year
  - Questions not on the resume: authorization to work in the US (work_authorization), sponsorship (sponsorship, prefilled from search settings), how I heard about the job (other), whether I was referred (other).
- Each proposed field carries the extracted value and the current answer-bank value for the same question, if any.
- Applying the proposal:
  - New questions are created.
  - Existing ones are updated only when I explicitly chose to replace them.
  - Skipped fields are not saved.
  - Duplicate-question rules of the answer bank still apply.
- Extraction runs automatically after the markings are saved, when the Anthropic API key is set. It can be requested again later. Nothing is saved without confirmation.

### Resume Tailor
- The tailoring request adds:
  - the experience bullets, each with its paragraph index, label and text after the label;
  - the target keywords: the job's latest Fit Scorer matched and missing keywords. If the job has no score yet, the tailor picks keywords itself, as before.
- The tailoring answer adds:
  - rewritten bullets, listing only the bullets that changed, by bullet number;
  - gaps: target keywords it couldn't cover honestly.
- Prompt rules for bullets: reword only the text after the label; keep every number; stay within about 10% of the original length; use the posting's wording only where the bullet supports it; leaving a bullet unchanged is fine.
- A code-level fact guard runs on every rewritten or hand-edited bullet. The bullet reverts to the original, with a recorded reason, if any of these hold:
  - its multiset of numbers (including percentages and "+" forms) differs from the original's;
  - it names a skill from the master skills list or the target keywords that appears in neither the original bullet nor the master skills list;
  - it is more than 15% longer than the original.
- The existing master-list rule for Skills lines is unchanged.
- The shorten-and-retry step passes the bullets back too and asks for a shorter result overall.

### Resume Renderer
- Rendering accepts bullet replacements by paragraph index. It replaces only the text after the label, inside the existing runs, so the bold label and all formatting stay exactly as in the master.
- All paragraphs that weren't marked stay identical to the master.

### Tailored resume version and scoring
- After rendering, the tailored text is scored by the Fit Scorer (scoring model). Both the before score (the job's latest score) and the after score are stored on the tailored resume version.
- Keyword coverage uses the target keywords, matched loosely: case-insensitive, punctuation-insensitive, simple plural folding, and a skill with a parenthetical counts for the term before the parenthesis.
- The tailored resume version additionally stores: the master bullets, the tailored bullets, reverted bullets with reasons, gaps, the before score and the after score. Versions created before this change have none of these and display as before.
- Editing the tailored resume accepts bullet text along with the Summary and Skills, runs the fact guard, regenerates the files and re-scores.
- Adding a gap takes the keyword and the target Skills line. It adds the keyword to the master skills list, places it on that line of this application's resume, regenerates the files and re-scores. It makes no tailoring call. If the page count grows past the master's, it's refused with a clear message, the same way edits that grow the resume are flagged today.

### HTTP API additions
- Runs: start a scoring-only run. The dashboard data includes the unscored-jobs count.
- Jobs: the filtered-out list excludes role rejections.
- Resume: saving the markings accepts bullets; there's a proposed default marking; extract a profile proposal; apply a profile proposal with my choices.
- Applications: the review bundle includes bullets (master, tailored, reverted with reasons), gaps, and before/after fit scores. Updating edits accepts bullets. Add a gap to a Skills line.

### Supersedes
- This spec replaces the original spec's out-of-scope item "rewriting or reordering experience bullets" for rewording only. Reordering bullets, and changing titles, dates, employers or education, remain out of scope.

## Testing Decisions

- **One seam: the backend HTTP API**, as in the original spec. Tests drive the app the way the dashboard does and check only observable results: API responses, the tailored .docx and PDF (text, formatting of labels, page count), answer-bank contents, and how forms are prefilled. They don't check prompt wording, internal calls or table layout.
- **The only fake is the existing scripted LLM**, extended to recognize profile-extraction calls, to script bullet rewrites and gaps in tailoring answers, and to score the tailored resume. Job boards, search and forms keep their existing fakes. SQLite, python-docx and LibreOffice stay real.
- **A new fixture resume** with list-item experience bullets that have bold labels and numbers, a LinkedIn URL that only exists as a hyperlink target, an all-caps name, and two degrees.
- **Behaviors to test:**
  - Scoring: a run where some scoring answers are cut off leaves those jobs unscored. A scoring-only run then scores exactly those jobs, makes no search or board calls, and is refused while another run is active.
  - Filtered out: role rejections are absent from the filtered-out list and location rejections are present. "Backend Developer", "Back End Software Engineer" and "Sr. Backend Engineer" pass a "Backend Engineer" role, and "Lead Client Partner" doesn't. Adding a role in search settings brings back a previously role-rejected job.
  - Profile:
    - The proposal finds the hyperlinked LinkedIn URL, the email and the phone; proper-cases the name; and preselects the higher degree.
    - Applying it creates answer-bank entries.
    - A following application's Greenhouse form fixture shows First Name, Email, LinkedIn Profile and School answered from the bank.
    - A differing existing entry is kept unless replacement was chosen.
  - Bullet marking: the proposed default is the list items after Skills. Overlapping markings are refused. A resume marked without bullets still tailors.
  - Tailoring:
    - A scripted bullet rewrite appears in the tailored .docx with its label still bold and all other paragraphs unchanged.
    - A rewrite that changes "60%" to "70%" is reverted, and the reason shows in the review bundle.
    - A rewrite adding a skill not in the original bullet or the master list is reverted.
    - Page count still matches the master.
    - Before and after scores are present.
    - Gaps from the tailoring answer appear in the review bundle.
  - Editing and gaps: a hand edit that changes a number is reverted. Adding a gap puts it on the chosen Skills line in the PDF text, adds it to the master skills list, and makes no tailoring call.
- **Prior art:** the API tests for scoring, filters, runs, resume, review edits and answers already in the backend test suite, plus their support helpers (scripted fake LLM, fake job boards, fake forms, ready-resume helper).

## Out of Scope

- Reordering experience bullets, or changing job titles, employers, dates, education or publications.
- Letting the AI add skills that aren't on my master skills list, even flagged.
- A separate structured profile store outside the answer bank.
- Saving more than one education entry for forms that ask for several.
- User-configurable title synonyms.
- Removing the "Filtered out" tab altogether, or deleting role-rejected jobs.
- Automatic re-tailoring when a gap is added.
- Fixing the matching of education start dates, which resumes usually don't state.

## Further Notes

- Evidence for the problems comes from the first real run and application in my local database. Scoring answers averaged 892 output tokens against the 1,000 cap (maximum 990). 2,564 of 2,657 new jobs were role rejections. The first tailored resume had 9 of 20 keywords covered both before and after tailoring.
- The re-score costs about one extra scoring-model call per application and per regenerate, which is small next to tailoring.
- Suggested delivery order for `/to-tickets`:
  1. Scoring fix and the scoring-only run.
  2. Near-miss filtered list and title synonyms.
  3. Profile extraction.
  4. Bullet marking.
  5. Bullet tailoring with the fact guard, re-scoring, the gaps list and the review UI.
