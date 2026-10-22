# 06: Marking experience bullets on the Resume page

**What to build:** On the Resume page's mapping screen, I can mark paragraphs as "Experience bullet", alongside Summary and Skills. The marking is prefilled with every list-item paragraph after the last Summary or Skills paragraph. In my resume that's the bullets under each job, and not the publications, which aren't list items. I can untick any of them. A paragraph can belong to only one of Summary, Skills or Experience bullets, and blank paragraphs can't be bullets. Bullets are optional: resumes marked before this change, or marked without bullets, stay ready and keep tailoring the Summary and Skills as before.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] A resume version stores its experience-bullet paragraph indexes; older versions have none
- [x] The resume data includes a proposed default bullet marking
- [x] Saving the markings accepts bullets, and refuses overlaps with Summary or Skills and blank paragraphs
- [x] The mapping screen shows the third marking, prefilled with the proposal, and lets me untick paragraphs
- [x] A resume with no bullets marked is still ready, and tailoring works as before
- [x] Test fixture: a resume with list-item experience bullets that have bold labels and numbers
- [x] Test: the proposed default is exactly the list items after the Skills section
- [x] Test: saving a bullet that is also marked as Summary is refused
- [x] Test: a resume saved without bullets still tailors successfully
