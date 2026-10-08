# 07: API key, Fit Scorer and a dashboard of matches only

**What to build:** After filtering, every remaining new job is scored for fit, and the dashboard shows only strong matches. I enter my Anthropic API key in Settings; it's stored locally only. The Fit Scorer sends my master resume text, preferences and the job description to Claude (via the official SDK, with structured output) and gets back a score 0-100, short reasons, matched keywords and missing keywords. Scores are saved per job and resume version, so reopening the dashboard never triggers new AI calls. The dashboard lists only jobs at or above my score threshold (default 70, adjustable in the Search settings panel), sorted by score, each showing its reasons and matched/missing keywords. Scoring uses a cheaper Haiku-class model by default and tailoring a Sonnet-class model; both are configurable. Each run records and shows its approximate AI cost.

This introduces the LLM port. Tests use a scripted fake LLM that returns set structured outputs.

**Blocked by:** 04 (Hard filters), 06 (Resume import and master profile)

**Status:** ready-for-agent

- [ ] API key can be set in Settings and is stored only on this machine; it is never returned in full by the API
- [ ] Runs score only jobs that passed the hard filters
- [ ] Score, reasons, matched and missing keywords and the model used are saved per job and resume version
- [ ] Listing or reopening jobs does not call the LLM again
- [ ] Dashboard shows only jobs with score at or above the threshold, sorted by score descending
- [ ] Score threshold is editable in the Search settings panel; scoring and tailoring models are editable in Settings
- [ ] Run progress and summary include scored and matched counts
- [ ] Each run records an estimated AI cost; a cost summary is available in Settings
- [ ] A run without an API key or master resume fails clearly rather than silently skipping scoring
- [ ] Test: with a scripted fake LLM, jobs above and below the threshold are shown and hidden respectively
- [ ] Test: a second run over unchanged jobs makes no new LLM calls
