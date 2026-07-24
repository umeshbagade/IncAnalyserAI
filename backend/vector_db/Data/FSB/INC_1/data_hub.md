# DataHub System - Root Cause Analysis Guide

## Data Hub Quality & Feed Status Check

id: data_process_failure
system: data_hub
symptom: "FSB report generation failure traced to Data Hub: the Monthly snapshot pipeline FAILED before completion and published an incomplete/partial snapshot that Saturn consumed — snapshot_status=FAILED, approval_status=REJECTED. This is the ROOT CAUSE; PE Ingestion staging is complete and healthy (ingestion_status=SUCCESS)."
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

- Data Hub Monthly snapshot pipeline FAILED before completion, publishing an incomplete/partial snapshot that Saturn then consumed (ROOT CAUSE).
- Snapshot job aborted / timed out mid-write, so fewer rows were persisted than were present in the complete PE staging table.
- Completeness gate flagged the partial snapshot and set approval_status = REJECTED, but the incomplete snapshot had already been consumed downstream.
- Threshold misconfiguration or overly strict validation rules
- Data schema mismatch with expected structure
- Duplicate records or unexpected null values
- Manual hold or approval workflow blocked

## Next Actions

- ROOT CAUSE IDENTIFIED at Data Hub — the Monthly snapshot pipeline failed and published an incomplete snapshot. Investigation STOPS here.
- Do NOT escalate to PE Ingestion — staging is complete and ingestion_status = SUCCESS for the incident COB, so there is nothing to investigate upstream.
- Re-run the Data Hub snapshot pipeline for the affected feed + COB, then re-approve once the completeness gate passes.
- Regenerate the Saturn / Tableau FSB report from the corrected, fully-approved snapshot.
- If cause=quality threshold → Review QA rule thresholds and adjust if needed

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

**End Point:** Data Hub is the root-cause layer for this incident — the Monthly snapshot pipeline failed and published an incomplete snapshot. Investigation stops here; PE Ingestion is proven healthy and is NOT investigated.