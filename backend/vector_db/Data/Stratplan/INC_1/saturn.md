---
id: NSFR_data_duplicate
system: saturn
symptom: "NSFR data duplication in both AG and GROUP reports"
severity: High
---

# Checks
- Check whether data is duplicated in the reporting table for the given business date.
- Check the write mode configured for the reporting table.

# Common Causes
- The ingestion job was re-run for the same business date without cleaning the reporting table.
- The ingestion job was re-run for the same business date with append mode instead of overwrite mode.

# Next Actions
- If the reporting table was not cleaned, delete duplicate records for the affected business date and re-run
- If the ingestion job was re-run in append mode, switch to overwrite mode for the same business date to prev