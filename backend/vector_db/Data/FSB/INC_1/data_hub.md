# DataHub System - Root Cause Analysis Guide

## Data Hub Quality & Feed Status Check

id: data_process_failure
system: data_hub
symptom: "Feed flagged, snapshot not approved, quality checks failed, snapshot not arrived" 
severity: high

## Checks

1. Query dh.dg results WHERE feed=? AND cob=?
2. Inspect failing rule + threshold for violations
3. Check dh.feed_approval_status for rejection reasons
4. Validate data completeness metrics (row counts, null percentages)
5. Inspect dh.data_lineage for upstream dependency status
6. Review dh.quality_metrics for trending issues
7. Check if reference data dependencies are satisfied
8. Verify calculation rules and formulas executed correctly

## Common Causes

- Late or partial upstream feed (from pe ingestion) 
- Reference data missing or out of date
- Threshold misconfiguration or overly strict validation rules
- Data schema mismatch with expected structure
- Duplicate records or unexpected null values
- Calculation logic errors in derived fields
- Reference data quality degradation
- Manual hold or approval workflow blocked

## Next Actions

- If cause=late feed → Drill into [ingestion.md](ingestion.md) for upstream investigation 
- If cause=ref data → Notify ref-data team and validate reference data feeds
- If cause=quality threshold → Review QA rule thresholds and adjust if needed 
- If cause=calculation error → Inspect Saturn transformation logic in [saturn.md](saturn.md) 
- If cause=manual hold → Check dh.approval_queue for blocking user/reason 
- If resolved → Escalate issue to Saturn pipeline for downstream impact assessment

## Data Quality Rule Categories

### Completeness Rules

- Check for required fields presence 
- Validate expected row count thresholds 
- Monitor NULL percentage trends

### Accuracy Rules

- Verify data against source of truth
- Validate against known constraints
- Cross-check calculated vs. source values

### Consistency Rules

- Check for duplicate entries
- Validate referential integrity
- Ensure data format consistency

### Timeliness Rules

- Monitor data arrival times
- Track processing latency
- Validate against SLA expectations

## Snapshot Approval Workflow

- **Draft** → Data loaded, awaiting QA checks
- **QA_IN_PROGRESS** → Quality validation running
- **QA_PASSED** -> Quality checks successful
- **QA_FAILED** -> Quality issues detected (investigate with checks above)
- **APPROVED** → Snapshot approved, ready for downstream
- **REJECTED** → Manual rejection or repeated failures (review approval notes)

**Previous Step:** [saturn.md](saturn.md) - Start from Saturn calculation/report failure triage 

**Next Step:** If issue is upstream feed-related, proceed to [ingestion.md](ingestion.md)