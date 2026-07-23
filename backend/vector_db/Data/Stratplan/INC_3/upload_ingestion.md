---
id: Stratplan_BCS
system: upload_ingestion
symptom: "BCS pull failed, historical snapshot not available in source"
severity: high
---

# Checks
- Query BCS source count for requested date + variant: `SELECT COUNT(*) FROM bcs_source WHERE business_date=<Date> A
- Query available source dates: `SELECT DISTINCT business_date FROM bcs_data ORDER BY business_date DESC LIMIT 12`
- Inspect `lnd_cfg_bcs_variant_filters` validity window for requested COB

# Common Causes
- Historical month-end data not present in BCS source
- Data type mismatch between source data and landing table.

# Next Actions
- If cause=no source data -> use the nearest available month-end and confirm business acceptance.
- If cause=data type mismatch -> correct the data type in the landing table or source data, then rerun ingestion.