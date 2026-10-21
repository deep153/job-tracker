# 03: Title synonyms

**What to build:** Title matching understands common variants of a role, so equivalent titles aren't dropped. Before the existing "every word of the role appears in the title" check, both the title and the role are normalized with a small built-in synonym table, applied to phrases first and then to words:
- "back end" / "back-end" become "backend"; "front end" / "front-end" become "frontend".
- "developer" and "dev" become "engineer".
- "swe" becomes "software engineer".
- "sr" becomes "senior".

The table isn't user-configurable. Unrelated titles are still rejected.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] "Backend Developer", "Back End Software Engineer", "Back-End Engineer" and "Sr. Backend Engineer" pass a "Backend Engineer" role
- [x] "SWE, Backend" passes a "Backend Software Engineer" role
- [x] "Front End Developer" passes a "Frontend Engineer" role
- [x] "Lead Client Partner" and "Global Strategic Accounts" are still rejected for a "Backend Engineer" role
- [x] Seniority detection still treats "Sr" titles as senior
- [x] Test: through the API, a run with fixture postings using these titles shows the expected jobs passing and failing the role rule
