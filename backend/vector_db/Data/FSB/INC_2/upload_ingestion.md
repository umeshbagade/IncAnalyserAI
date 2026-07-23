# Ingestion System - Balance Sheet Management RCA Guide

## PE INGESTION BSM Feed Status Check

id: bsm_snapshot_ingestion_failure
system: pe_ingestion
symptom: "BSM Feed delayed, incomplete, or failed to load into staging"
severity: high

## Checks

1. Query pe_ingestion.bsm_feed_status WHERE feed_name=? AND cob=?
2. Check feed scheduler logs for execution errors on specified COB date
3. Verify upstream source data availability (GL, Core Banking, Treasury Systems) as of COB
4. Inspect feed transformation logs for data quality/duplication issues during COB window
5. Validate schema mapping and field counts match expected BSM staging schema
6. Check disk space and network connectivity to source systems at time of COB load
7. Review ETL job execution time and performance metrics for the COB run 
8. Validate SLA compliance: Feed expected to complete by BSM COB close time

## Common Causes

- Source banking/GL system unavailable or connectivity issues
- Unannounced schema or file format changes from source systems
- Data duplication occurring during staging loads
- Business date alterations or misaligned timing parameters on source systems
- Missing or invalid authentication credentials
- Resource constraints (memory, disk, CPU) during peak COB extraction
- Late-arriving transaction data after COB cutoff time

## COB Context & Timeline

- **Close of Business (COB):** {cob}
- **Pre-COB:** Core systems accepting transactional balance updates
- **COB Cutoff:** Treasury close time (market close + buffer)
- **Post-COB:** BSM Extraction & Feed processing window begins
- **Expected Completion:** Feed should be fully loaded into PE staging and validated within SLA

**Key Considerations:**
- Balance sheet feeds must align with strict business date logic
- Weekend/holiday processing windows may apply special GL balancing rules

## Next Actions

- If cause=transformation/schema error → Review ETL logs and schema mapping
- If cause=source unavailable → Contact upstream GL/Core Banking system owner
- If cause=data quality issue → Drill into bsm_datahub for validation checks 
- If cause=resolved → Notify DataHub team and escalate to [bsm_datahub.md](bsm_datahub.md)

## Related Checks by Feed Type

### General Ledger & Position Feeds
- Verify GL provider connectivity and balance integrity
- Validate account mapping rules and balance sign conventions

### Liquidity & Cash Flow Feeds
- Confirm maturity profiles and cash flow schedule availability
- Inspect for duplicate transactions or missing balance movements

### Market & Interest Rate Feeds
- Confirm reference rate file location and permissions
- Check curve data completeness and yield conventions

**Previous Step:** [bsm_datahub.md](bsm_datahub.md) - Continue upstream drill-down from DataHub 

**End Point:** Ingestion is the final upstream step in this triage flow (`bsm_saturn.md` -> `bsm_datahub.md` -> `bsm_ingestion.md`)