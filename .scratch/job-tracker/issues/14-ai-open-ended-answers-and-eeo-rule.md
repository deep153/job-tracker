# 14: AI-drafted open-ended answers and the EEO rule

**What to build:** Open-ended questions like "Why do you want to work here?" arrive in review with a relevant draft instead of a blank. The Answer Engine sends my master resume and the job description to Claude (the writing model) to draft these, labelled "AI-drafted"; the prompt forbids inventing experience. EEO and demographic questions are never sent to the AI: they are answered only from my saved answer-bank choices (including "decline to answer"), and flagged as needs input if I have no saved choice. When I type an answer in review, I can choose to save it into the answer bank so the system learns over time.

**Blocked by:** 11 (Answer bank and reading the Greenhouse form)

**Status:** done

- [x] Open-ended questions without a bank match get an AI draft labelled "AI-drafted"
- [x] Questions the engine can't confidently answer remain "needs input"
- [x] EEO/demographic questions are never sent to the LLM; they use saved choices or are flagged as needs input
- [x] An answer typed in review can be saved to the answer bank with one action
- [x] Test: an open-ended question gets the fake LLM's draft with the "AI-drafted" label
- [x] Test: an EEO question with no saved choice is flagged as needs input and the fake LLM receives no call for it
- [x] Test: an answer saved from review is matched from the bank on the next application

**Notes:** Open-ended means an unanswered free-text question that's a textarea, ends in "?", or has six or more words; they go to the Answer Writer in one call with the tailoring (writing) model, and its cost shows as "Open-ended answers". The model answers null for anything it can't answer from the resume and the posting, which stays "needs input"; if the call fails, every one of them does. EEO questions are recognized by their label (gender, race, ethnicity, veteran, disability, pronouns, sexual orientation, self-identification…), never sent, and flagged as needs input even when optional, so approving waits for a deliberate choice (declining included). "Save to answer bank" (`POST /api/applications/{id}/answers/save-to-bank`) saves the question as worded on the form, as an EEO choice for EEO questions and "other" otherwise, replacing my saved answer to the same question.
