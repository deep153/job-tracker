# 05: Lever and Ashby sources and discovery

**What to build:** The Lever and Ashby platform switches in the Search settings panel start working. When enabled, a run discovers Lever and Ashby companies through the search API (e.g. `site:jobs.lever.co`, `site:jobs.ashbyhq.com` with my roles and locations) and fetches their jobs. Lever and Ashby adapters implement the same Job Board Source interface as Greenhouse and return the same normalized posting shape. Timestamps from all platforms are normalized so jobs from different boards sort correctly together.

**Blocked by:** 04 (Hard filters)

**Status:** done (6a08a80)

- [x] Lever adapter returns normalized postings from the public Lever postings API
- [x] Ashby adapter returns normalized postings from the public Ashby job-board API (unlisted jobs skipped)
- [x] Salary range, remote flag / work mode and locations are mapped when the platform provides them, and left empty otherwise
- [x] Board IDs are extracted from Lever and Ashby job URLs during discovery
- [x] The Lever and Ashby switches are no longer marked "coming soon"; disabling one stops both its discovery and its fetching
- [x] Posted/updated timestamps from all platforms are stored in one consistent form; the jobs list sorts correctly across platforms
- [x] Recorded fixtures for Lever and Ashby are added to the fake HTTP layer, plus fake search results pointing at them
- [x] Test: a run with all three platforms enabled stores jobs from all three, each with the correct source platform
- [x] Test: salary from a Lever or Ashby posting feeds the minimum-salary filter
