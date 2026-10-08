# 14: AI-drafted open-ended answers and the EEO rule

**What to build:** Open-ended questions like "Why do you want to work here?" arrive in review with a relevant draft instead of a blank. The Answer Engine sends my master resume and the job description to Claude (the writing model) to draft these, labelled "AI-drafted"; the prompt forbids inventing experience. EEO and demographic questions are never sent to the AI: they are answered only from my saved answer-bank choices (including "decline to answer"), and flagged as needs input if I have no saved choice. When I type an answer in review, I can choose to save it into the answer bank so the system learns over time.

**Blocked by:** 11 (Answer bank and reading the Greenhouse form)

**Status:** ready-for-agent

- [ ] Open-ended questions without a bank match get an AI draft labelled "AI-drafted"
- [ ] Questions the engine can't confidently answer remain "needs input"
- [ ] EEO/demographic questions are never sent to the LLM; they use saved choices or are flagged as needs input
- [ ] An answer typed in review can be saved to the answer bank with one action
- [ ] Test: an open-ended question gets the fake LLM's draft with the "AI-drafted" label
- [ ] Test: an EEO question with no saved choice is flagged as needs input and the fake LLM receives no call for it
- [ ] Test: an answer saved from review is matched from the bank on the next application
