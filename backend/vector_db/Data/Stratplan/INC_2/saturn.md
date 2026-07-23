---
id: NSFR_Business_date_Alteration
system: saturn
symptom: "LCR data business date altered for some records"
severity: High
---

# Checks
- Check whether loading and appending into the main table completed correctly for the given COB.
- Check the date format stored in the main table.

# Common Causes
- Date format mismatch between the source and the main table, leading to incorrect business dates being st

# Next Actions
- If there is a date format mismatch, correct the date format in the source or main table and re-run ingest