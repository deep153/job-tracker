# 04: Hard filters

**What to build:** Discovered companies return all their open jobs, so runs drop any job that doesn't fit my search settings and hard requirements before anything else happens to it. Hard Filters are pure, deterministic rules over a normalized posting and my settings, and each rule reports why it rejected a job. After a run I can see how many jobs each filter removed, so I can tell when one is too strict.

Roles, locations and work mode come from the Search settings panel (ticket 03). The remaining requirements are edited in a "More filters" section of the same panel.

Rules:
- Title: must match one of my roles; must not contain any excluded keyword (e.g. "Manager", "Principal")
- Location and work mode: must be in one of my locations, or remote when I've chosen remote; hybrid / on-site only when chosen
- Seniority and years of experience: drop roles far above or below my level
- Visa sponsorship: if I need sponsorship, drop postings stating "no sponsorship" (or equivalent wording)
- Minimum salary: applies only when the posting lists a salary; postings without pay are kept

**Blocked by:** 03 (Search settings and Greenhouse discovery)

**Status:** done (09a4734)

- [x] Excluded keywords, seniority, years of experience, sponsorship need and minimum salary can be read and updated via the API and edited in the panel's "More filters" section
- [x] Filters run on new/changed jobs during a run, before any scoring step
- [x] Each rule records a rejection reason on rejected jobs
- [x] Per-filter rejection counts are stored on the run and shown in the run summary
- [x] Rejected jobs do not appear on the dashboard
- [x] Changing search settings re-applies the filters to stored open jobs without a new fetch
- [x] Test (one per rule): a fixture posting that violates the rule is rejected with that rule's reason; a compliant one passes
- [x] Test: a remote posting passes when remote is chosen even if its location isn't in my list
- [x] Test: a posting with no salary passes the minimum-salary rule; one listing a lower salary is rejected
- [x] Test: "no sponsorship" wording is rejected only when I need sponsorship
