# 16: Applications tracker

**What to build:** An Applications page where I track my pipeline. It lists every application with company, role, date, score and status. Each application links to the exact resume PDF, cover letter and answers that were sent, so I can prepare for interviews. After submission I can update the status by hand to `interviewing`, `rejected`, `offer` or `withdrawn`. Jobs I've applied to no longer appear on the main dashboard.

**Blocked by:** 12 (Submitting to Greenhouse)

**Status:** ready-for-agent

- [ ] Applications list shows company, role, date, score and status, and can be sorted by date and status
- [ ] Each application shows the exact resume PDF, cover letter (if any) and answers with their source labels
- [ ] Status can be updated by hand to `interviewing`, `rejected`, `offer` or `withdrawn` only after submission
- [ ] Jobs with a submitted (or later) application are removed from the dashboard
- [ ] Test: after submitting, the application appears in the list with its artifacts and the job is gone from the dashboard
- [ ] Test: a manual status update is saved and reflected in the list
