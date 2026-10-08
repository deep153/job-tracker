# 03: Search settings on the dashboard and Greenhouse company discovery

**What to build:** I configure what to search for in a Search settings panel on the dashboard, and a run finds companies for me. Nothing about what to search is hardcoded.

The panel holds:
- Roles: the job titles I'm looking for (e.g. "Software Engineer", "Backend Engineer")
- Locations: the places I can work (e.g. "New York, NY", "Austin, TX")
- Work mode: any combination of remote, hybrid and on-site
- Platforms: on/off switches for Greenhouse, Lever and Ashby (only Greenhouse works in this ticket; Lever and Ashby are shown as coming soon until ticket 05)
- Search API key: the key for the web search API used to discover companies, stored locally only

Greenhouse, Lever and Ashby only list jobs per company, so a run discovers companies first. Board Discovery is a new external port (a web search API, Brave Search by default) faked in tests. For each enabled platform it queries the search API with my roles and locations (e.g. `site:job-boards.greenhouse.io "Backend Engineer" "New York"`), extracts company board IDs from the result URLs, and saves newly found companies with when and from which query they were found. The run then fetches every discovered, non-blocked company on an enabled platform through the official job board API (with ticket 02's de-duplication, closing and failure isolation).

The panel also lists discovered companies with platform, when found, last fetched, open job count and last error, and lets me block a company so it is never fetched again (and unblock it). There is no way to add a company by hand.

"Run" is disabled, with a pointer to the panel explaining what's missing, until there is at least one role, at least one location or the remote work mode, at least one enabled platform, and a search API key.

**Blocked by:** 02 (Reliable runs)

**Status:** done (8c53c81)

- [x] Search settings (roles, locations, work modes, platform switches) can be read and updated via the API and edited in a panel on the dashboard
- [x] The search API key can be set from the panel, is stored only on this machine, and is never returned in full by the API
- [x] Run is disabled with a clear explanation when roles, location/remote, enabled platform or search key is missing; the API also refuses such a run
- [x] A run first discovers companies via the search API for each enabled platform from my roles and locations, then fetches them
- [x] Board IDs are extracted correctly from Greenhouse job URLs (both `boards.greenhouse.io` and `job-boards.greenhouse.io` forms); duplicates and non-board URLs are ignored
- [x] Newly discovered companies are saved with the query that found them; previously discovered companies are kept across runs
- [x] Blocked companies are never fetched; blocking and unblocking work from the panel
- [x] Discovered companies are listed with platform, found date, last fetched, open job count and last error
- [x] Run progress shows a discovery stage (queries made, companies found) before fetching
- [x] The number of search queries per run is capped, and the count used is shown in the run summary
- [x] A search API failure is recorded in the run's errors; already-discovered companies are still fetched
- [x] Tests use a fake search API returning scripted results
- [x] Test: with roles and a location set, a run discovers the boards in the fake search results and stores their jobs
- [x] Test: a run is refused when no role is configured
- [x] Test: a blocked company is not fetched on the next run
- [x] Test: a disabled platform is neither searched nor fetched
