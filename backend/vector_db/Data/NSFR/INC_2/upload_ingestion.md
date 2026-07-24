---
id: NSFR_Business_date_Alteration
system: upload_ingestion
symptom: "LCR data business date altered for some records"
severity: High
---

# Checks
- Check whether the business date is altered in the uploaded LCR data for the given COB.
- Check the date format in the source file before upload.
- Verify that the date column data type matches the landing table schema:
  `SELECT data_type FROM information_schema.columns WHERE table_name='lcr_landing' AND column_name='business_da

# Common Causes
- Date format mismatch between source file and landing table (e.g., YYYY-MM-DD vs DD-MM-YYYY)
- Source file contains dates in wrong timezone causing conversion issues
- Incompatible date parsing during Spark ingestion (missing date format specification)
- Source data contains mixed date formats within same file

# Next Actions
- If cause=date format mismatch in source -> correct the date format in source file or add format specification
- If cause=timezone issue -> verify TZ handling in Spark configuration and adjust UTC offset
- If cause=parsing error -> add explicit date_format parameter to Spark read operation: `.option("dateFormat", "y
- If cause=mixed formats -> pre-process source to standardize format before ingestion
- After fix -> re-run ingestion for affected records and validate date values match COB