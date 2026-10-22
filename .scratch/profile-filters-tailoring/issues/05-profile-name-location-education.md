# 05: Profile: name, location and education from one AI call

**What to build:** The profile review form also proposes my first and last name, my location and my education, read by one structured AI call (the tailoring model). Names come back in proper case even when my resume shows them in all caps ("Deep Gandhi"). Location comes back as city, region and country, and Country is prefilled from it. Education comes back as a list of entries (school, degree written in full such as "Master of Science", discipline, end month, end year). The highest or most recent degree is preselected, and a switcher lets me choose another. When I confirm, these are saved as answer-bank entries alongside the ones from ticket 04:
- personal: First Name, Last Name, Location (City), Country
- other: School, Degree, Discipline, End date month, End date year

The same conflict rule applies: differing existing answers are kept unless I choose to replace them. The call is recorded as AI usage of kind "profile". Without an Anthropic API key, the form still opens with the code-found fields and says the AI part needs the key.

**Blocked by:** 04 (Profile: contact details, links and standard questions into the answer bank)

**Status:** done

- [x] Extraction makes one structured LLM call and merges its fields into the proposal
- [x] Names are proper-cased; degrees are written in full
- [x] The highest or most recent degree is preselected, and the others are returned as alternatives
- [x] Choosing another degree in the form changes the School, Degree, Discipline and end-date values that will be saved
- [x] The AI usage is recorded with kind "profile" and shows in the cost summary
- [x] Without an API key, the code-found fields are still proposed and the missing AI part is explained
- [x] The scripted fake LLM recognizes profile-extraction calls and no longer treats them as scoring
- [x] Test fixture: a resume with an all-caps name and two degrees
- [x] Test: the proposal has a proper-cased first and last name and preselects the higher degree
- [x] Test: after applying, a new application's Greenhouse form fixture shows First Name, Last Name and School answered from the bank
