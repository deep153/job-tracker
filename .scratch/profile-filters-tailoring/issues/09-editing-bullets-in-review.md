# 09: Editing bullets on the review screen

**What to build:** On the review screen, each changed bullet has an editable text box and a "Use original" button, next to the existing Summary and Skills editing. When I regenerate, my bullet edits go through the same fact check as the tailor's rewrites. A hand edit that changes a number, adds an unlisted skill or grows by more than 15% is reverted, and the review screen shows why. The tailored .docx and PDF are rebuilt, coverage is recomputed, and the resume is re-scored, so the after score always matches what I'll send. As today, a resume that grows past the master's page count is saved and flagged.

**Blocked by:** 07 (Tailor rewords bullets, with the code check on facts), 08 (Tailoring targets the scorer's keywords, with a before/after fit score)

**Status:** done

- [x] Updating the tailored resume accepts bullet text along with the Summary and Skills
- [x] Edited bullets pass the fact check; failures revert to the original with a reason in the review bundle
- [x] "Use original" restores one bullet without affecting the others
- [x] Regenerating rebuilds the files, recomputes coverage and re-scores the resume, and records the re-score's cost
- [x] The page-count flag behaves as it does for Summary and Skills edits
- [x] Test: a hand edit that changes a bullet's number is reverted, and the reason is in the review bundle
- [x] Test: a valid hand edit appears in the regenerated PDF text with the label still bold, and the after score is updated
