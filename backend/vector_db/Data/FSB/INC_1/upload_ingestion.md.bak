# Ingestion System - Root Cause Analysis Guide

## PE INGESTION Feed Status Check

id: snapshot_ingestion_failure
system: pe_ingestion
symptom: "Feed delayed, incomplete, or failed to load"
severity: high

## Checks

1. Query pe_ingestion.feed_status WHERE feed_name=? AND cob=? (Use provided feed_name and cob values) 
2. Check feed scheduler logs for execution errors on specified COB date
3. Verify upstream source data availability as of COB
4. Inspect feed transformation logs for data quality issues during COB processing window
5. Validate schema mapping and field counts match expected for this feed
6. Check disk space and network connectivity to source at time of COB load
7. Review ETL job execution time and performance metrics for the COB run 
8. Validate SLA compliance: Feed expected to complete by COB close time

## Common Causes

- Source system unavailable or connectivity issues
- File format changed or malformed input data
- Missing or invalid authentication credentials
- Transformation logic errors (schema/data type mismatches)
- Resource constraints (memory, disk, CPU)
- Network timeouts or latency issues
- Scheduled job failed to trigger on COB date
- Data validation rules failed on incoming data
- COB-specific processing rules not applied correctly 
- Late-arriving data after COB cutoff time

## COB Context & Timeline

- **Close of Business (COB):** {cob}
- **Pre-COB:** Source system still accepting updates
- **COB Cutoff:** Specified close time (typically market close + delay buffer)
- **Post-COB:** Feed processing window begins
- **Expected Completion:** Feed should be fully loaded and validated within SLA

**Key Considerations:**
- Some feeds may accept late arrivals with timestamp adjustments
- Holiday calendars affect COB timing (check business calendar)
- Time zone differences between source and reporting systems
- Weekend/holiday processing windows may differ from weekday schedule

## Next Actions

- If cause=transformation error → Review ETL logs and schema validation 
- If cause=source unavailable → Contact upstream system owner
- If cause=data quality issue → Drill into datahub for validation checks 
- If cause=resolved → Notify datahub team and escalate to datahub.md for next analysis

## Related Checks by Feed Type

### Market Data Feeds
- Verify market data provider connectivity
- Check if trading hours match expected schedule 
- Validate market conventions and holiday calendars

### Reference Data Feeds
- Confirm reference data file location and permissions 
- Check data lineage and source system health 
- Validate reference data uniqueness constraints

### Transaction Feeds
- Check transaction processing pipeline status
- Verify message queue depth
- Inspect for duplicate transaction IDs

**Previous Step:** [datahub.md](datahub.md) - Continue upstream drill-down from DataHub 

**End Point:** Ingestion is the final upstream step in this triage flow (`saturn.md` -> `datahub.md` -> `ingestion.md`)