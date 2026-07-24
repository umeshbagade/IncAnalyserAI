---
id: NSFR_Business_date_Alteration
system: data_hub
symptom: "LCR data business date altered for some records"
severity: High
---

# Checks
- Check whether the business date is altered in the LCR staging table for the given COB.
- Check the date format stored in the staging table.

# Common Causes
- Date format mismatch between the source and the staging table, leading to incorrect business da

# Next Actions
- If there is a date format mismatch, correct the date format in the source or staging table and