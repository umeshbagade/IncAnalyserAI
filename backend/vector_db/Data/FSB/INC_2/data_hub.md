# DataHub System - Balance Sheet Management RCA Guide

## Data Hub BSM Quality & Feed Status Check

id: bsm_data_process_failure
system: data_hub
symptom: "BSM Feed flagged, snapshot not approved, quality checks failed, balance sheet snapshot not arrived" 
severity: high

## Checks

1. Query dh.bsm_dg_results WHERE feed=? AND cob=?
2. Inspect failing rule + threshold for violations (e.g., balance integrity, null checks)
3. Check dh.bsm_feed_approval_status for rejection reasons
4. Validate data completeness metrics (row counts, null percentages, balance totals)
5. Inspect dh.data_lineage for upstream staging/ingestion status
6. Review dh.bsm_quality_metrics for trending issues or unexpected balance shifts
7. Check if GL reference data dependencies are satisfied
8. Verify calculation rules and aggregation formulas executed correctly

## Common Causes

- Late or partial upstream balance sheet feed (from pe ingestion)
- Reference data missing or out-of-date GL mapping
- Strict validation thresholds triggered by unexpected portfolio movements
- Data schema mismatch with expected BSM structure
- Duplicate records in staging or unexpected null balance values
- Manual hold or ALM approval workflow blocked

## Next Actions

- If cause=late feed → Drill into [bsm_ingestion.md](bsm_ingestion.md) for upstream investigation 
- If cause=ref data → Notify ref-data/GL team and validate reference data feeds
- If cause=quality threshold → Review QA rule thresholds and adjust if valid business shift
- If cause=calculation error → Inspect Saturn transformation logic in [bsm_saturn.md](bsm_saturn.md) 
- If cause=manual hold → Check dh.bsm_approval_queue for blocking user/reason 
- If resolved → Escalate issue to Saturn BSM pipeline for downstream impact assessment

## Data Quality Rule Categories

### Completeness Rules

- Check for required balance, currency, and account fields
- Validate expected row count and balance sum thresholds 
- Monitor NULL percentage trends across balance sheet line items

### Accuracy Rules

- Verify balance sheet data against source of truth (General Ledger)
- Validate against known liquidity and maturity constraints
- Cross-check calculated vs. source values

### Consistency Rules

- Check for duplicate entries (especially across LCR/NSFR staging feeds)
- Validate referential integrity against enterprise chart of accounts
- Ensure data format and date consistency across feeds

### Timeliness Rules

- Monitor BSM data arrival times against SLA
- Track processing latency for COB cutoff
- Validate against treasury SLA expectations

## Snapshot Approval Workflow

- **Draft** → BSM Data loaded, awaiting QA checks
- **QA_IN_PROGRESS** → Quality and reconciliation validation running
- **QA_PASSED** → Quality checks successful
- **QA_FAILED** → Quality issues detected (investigate with checks above)
- **APPROVED** → Snapshot approved, ready for downstream BSM/Saturn execution
- **REJECTED** → Manual rejection or repeated failures (review approval notes)

**Previous Step:** [bsm_saturn.md](bsm_saturn.md) - Start from Saturn BSM calculation/report failure triage 

**Next Step:** If issue is upstream feed-related, proceed to [bsm_ingestion.md](bsm_ingestion.md)