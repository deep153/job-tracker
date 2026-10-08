# 06: Resume import and master profile

**What to build:** I upload my real resume as a .docx and it becomes the master template for scoring and tailoring. The app splits it into paragraphs with their style info and shows them to me; I mark which paragraphs are the Summary and which are the Skills section. A master skills list is pre-filled from the Skills section and I can edit it; tailoring may only ever use skills from this list. I see a PDF preview of the imported resume (converted with headless LibreOffice) to confirm it looks right, and its page count is recorded. I can replace the master with a newer version, which creates a new resume version.

The app checks at startup that LibreOffice is installed and shows a clear message if it isn't.

**Blocked by:** 01 (Walking skeleton)

**Status:** ready-for-agent

- [ ] Uploading a .docx stores the original file and returns its paragraphs with style info
- [ ] I can save a mapping of Summary paragraph(s) and Skills paragraph(s)
- [ ] The master skills list is pre-filled from the mapped Skills section and is editable
- [ ] A preview PDF is generated via LibreOffice and its page count is stored
- [ ] Uploading a non-.docx or corrupt file is rejected with a clear message
- [ ] Saving a mapping without a Summary or without a Skills section is rejected with a clear message
- [ ] Replacing the master creates a new resume version; earlier versions are kept
- [ ] Missing LibreOffice is detected at startup and reported clearly in the UI
- [ ] Tests use real python-docx and real LibreOffice conversion
- [ ] Test: importing a sample resume, mapping it, and fetching the preview yields a PDF whose text matches the resume and whose page count is recorded
- [ ] Test: invalid file and incomplete mapping are each rejected
