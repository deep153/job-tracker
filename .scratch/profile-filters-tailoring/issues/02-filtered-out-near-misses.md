# 02: "Filtered out" shows only near misses

**What to build:** The "Filtered out" tab lists only jobs whose title matched one of my roles but that a narrower rule rejected (location, excluded keyword, seniority, experience, salary or sponsorship). Jobs rejected only because the title doesn't match a role (sales, account and other unrelated openings at discovered companies) are no longer listed anywhere. They stay stored with their rejection, so adding a role in search settings brings matching ones back without a new run. The run summary still counts rejections per rule, but shows title mismatches as a single line ("2,564 other roles at these companies skipped"), and the "Review filtered jobs" prompt counts only near misses.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] The filtered-out job list excludes jobs rejected by the role rule
- [x] Jobs rejected by any other rule are still listed
- [x] Role-rejected jobs stay stored and are re-checked when search settings change
- [x] The run summary shows role rejections as one "other roles at these companies skipped" line, separate from the per-rule near-miss counts
- [x] The "Review filtered jobs" prompt and the tab's count include only near misses, and the prompt is hidden when there are none
- [x] Test: after a run with one role-rejected and one location-rejected job, the filtered-out list contains only the location-rejected job
- [x] Test: adding a role in search settings that matches a previously role-rejected job brings it back into the scoring path
