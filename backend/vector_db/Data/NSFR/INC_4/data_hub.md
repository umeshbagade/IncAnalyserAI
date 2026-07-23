---
id: Stratplan_BCS
system: data_hub
symptom: "BCS pull failed, historical snapshot not available in source"
severity: high
---

# Checks
- Query BCS source count for requested date + variant: `SELECT COUNT(*) FROM bcs_source WHERE business_date=<Date> AND variant_name=<name>`
- Query available source dates: `SELECT DISTINCT business_date FROM bcs_data ORDER BY business_date DESC LIMIT 12`
- Inspect `lnd_cfg_bcs_variant_filters` validity window for requested COB
- Verify UBR/FSI config aligns with requested historical period
- Check BCS retention window with source owner

# Common causes
- Historical month-end data not present in BCS source
- BCS retention policy purged older snapshots
- Variant/process not active for requested historical date
- Config dates valid but source data absent

# Next actions
- If cause=no source data -> use nearest available month-end and confirm business acceptance
- If cause=retention purge -> request archive restore from BCS owner
- If cause=variant mismatch -> correct variant/process mapping for requested period
- If cause=config-date mismatch -> align UBR/FSI validity dates with pull date
- Document BCS lookback limit and pre-check source availability before reruns