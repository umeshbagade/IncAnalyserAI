---
id: Stratplan_BCS
system: upload_ingestion
symptom: "BCS pull failed, historical snapshot not available in source"
severity: high
---

# Checks
- Query BCS source count for requested date + variant: `SELECT COUNT(*) FROM bcs_source WHERE business_date=<Date> AND variant_name=<name>`
- Query available source dates: `SELECT DISTINCT business_date FROM bcs_data ORDER BY business_date DESC LIMIT 12`
- Inspect `lnd_cfg_bcs_variant_filters` validity window for requested COB

# Common causes
- Historical month-end data not present in BCS source
- Check for the data type matches for the source data and landing table. If the data type does not match, it can cause the ingestion to fail.

# Next actions
- If cause=no source data -> use nearest available month-end and confirm business acceptance
- If cause=data type mismatch -> correct the data type in the landing table or source data to match and rerun the ingestion