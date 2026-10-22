# 04: Profile: contact details, links and standard questions into the answer bank (no AI)

**What to build:** After I save my resume's markings, a profile review form opens, prefilled from my resume. Code (no AI) finds my email, phone, and LinkedIn, GitHub and website URLs. It reads both the paragraph text and the document's hyperlink targets, so a URL that only exists inside a "LinkedIn" link is still found. The same form has a second section for the questions a resume can't answer: authorized to work in the US, need for sponsorship (prefilled from my search settings), how I heard about the job, and whether I was referred.

Each field shows the extracted value, and the current answer-bank value if one exists for the same question. If they differ, my current answer is kept by default and I can tick "replace". Unchanged fields are hidden. I can edit or skip any field. When I confirm, answers are saved as regular answer-bank entries, worded so the existing Answer Engine matches form labels:
- personal: Email, Phone
- links: LinkedIn Profile, GitHub, Website
- work_authorization: authorized to work in the US
- sponsorship: sponsorship
- other: how I heard about the job, referral

Nothing is saved without confirmation. I can reopen the form later with "Update profile from resume".

**Blocked by:** None (can start immediately)

**Status:** done

- [x] The extract endpoint returns a proposal with, per field: question, category, extracted value and current bank value
- [x] Email, phone and URLs are found in paragraph text and in hyperlink targets; URLs are sorted into LinkedIn, GitHub and website
- [x] The standard-questions section is included, with sponsorship prefilled from search settings
- [x] The apply endpoint creates new entries, updates existing ones only when replace was chosen, and skips fields left empty
- [x] The answer bank's duplicate-question rule still holds
- [x] The Resume page opens the review form after the markings are saved, and offers "Update profile from resume" later
- [x] Test fixture: a resume whose LinkedIn URL exists only as a hyperlink target
- [x] Test: the proposal includes the hyperlinked LinkedIn URL, the email and the phone
- [x] Test: after applying, a new application's Greenhouse form fixture shows Email and LinkedIn Profile answered from the bank
- [x] Test: an existing differing Phone entry is kept unless replacement was chosen
