---
id: NSFR_data_duplicate
system: upload_ingestion
symptom: "NSFR data duplication in both AG and GROUP reports"
severity: High
---

# Checks
- Check whether data is duplicated in the staging table for the given business date:
  `SELECT COUNT(*) FROM nsfr_staging WHERE business_date = <COB>;` -> compare with the expected count

# Common Causes
- The ingestion job was re-run for the same business date without cleaning the staging table.

# Next Actions
- If the staging table was not cleaned, delete duplicate records for the affected business date and
- If the ingestion job was re-run, ensure the staging table is cleaned before re-running ingestion f