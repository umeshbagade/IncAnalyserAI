# Saturn BSM Pipelines Root Cause Analysis Guide

## Saturn BSM Calculation & Report Pipeline Failure

id: bsm_report_generation_failure
system: saturn
symptom: "BSM calculation failed, LCR/NSFR report generation blocked, Stratplan metrics missing" 
severity: high

## Checks

1. Query saturn.bsm_job_status WHERE pipeline=? AND cob=? ORDER BY timestamp DESC 
2. Inspect saturn.bsm_calculation logs for execution errors, UBR refresh logs, and coefficient calculation traces
3. Check saturn.bsm_data_validation for input balance sheet data gaps
4. Verify all dependent datahub snapshots are APPROVED (from bsm_datahub.md)
5. Inspect saturn.bsm_rule_engine for ALM, LCR, and NSFR formula errors
6. Check saturn.bsm_report_queue for stuck or failed report generation tasks 
7. Validate calculation dependencies and execution order for Stratplan coefficients

## Common Causes

- Upstream DataHub balance sheet snapshot not approved (reference [bsm_datahub.md](bsm_datahub.md))
- Missing or invalid staging data (e.g., UBR refresh failure or missing balance sheet data gaps)
- Data duplication in NSFR/LCR calculation pipelines
- Calculation rule logic errors or formula misconfigurations in ALM models
- Reference data missing or stale (validate in bsm_datahub.md)
- Job timeout due to high transaction volume or complex aggregation DAGs
- Unhandled business date alterations during COB updates

## Next Actions

- If cause=upstream snapshot → Review [bsm_datahub.md](bsm_datahub.md) for quality issues
- If cause=calculation error → Inspect Stratplan logic / ALM rule engine configuration and test formula independently 
- If cause=reference data → Cross-check balance sheet reference data sources in [bsm_datahub.md](bsm_datahub.md)

## Saturn BSM Pipeline Architecture

### Stage 1: Data Ingestion & Validation 
- Consume approved DataHub balance sheet snapshots 
- Validate schema and balance sheet completeness
- Check data freshness and business date alignment

### Stage 2: Calculation Pipeline
- Execute base liability and asset calculations in dependency order
- Compute derived metrics (LCR, NSFR, Liquidity Buffers, Stratplan Coefficients)
- Aggregate results across legal entities, currencies, and business lines

### Stage 3: Quality Assurance
- Validate calculation results against expected balance sheet thresholds
- Check for duplication, metric anomalies, and outliers
- Perform reconciliation against general ledger (GL) sources
- Verify calculation completeness

### Stage 4: Report Generation
- Format data for BSM regulatory and internal outputs
- Apply presentation rules and liquidity risk thresholds
- Generate visualizations and publish to Tableau dashboards

## Common Calculation Errors

### Data Duplication & Schema Mismatches
- Check for duplicate entries in NSFR/LCR staging tables
- Verify numeric liquidity fields are not null
- Validate date format compliance and business date alterations

### Logic & Coefficient Errors
- Review condition/branching logic for Stratplan coefficient runs
- Test edge cases (zeros, nulls, unexpected negative cash flows)
- Validate UBR refresh status and dependency prerequisites

### Performance Issues
- Monitor execution time during peak COB processing
- Check for unindexed joins across large balance sheet staging tables

## Report Status Workflow

- **QUEUED** → Waiting for upstream balance sheet data 
- **PROCESSING** → ALM & liquidity calculations running
- **VALIDATING** → Quality checks and GL reconciliation in progress 
- **GENERATING** → BSM report formatting
- **GENERATED** → Report ready for delivery
- **FAILED** → Error occurred (check logs and checks above) 
- **HOLD** → Manual hold for treasury/ALM approval 
- **DELIVERED** → Report successfully distributed to Tableau/Regulators

## Root Cause Analysis Path

1. Start here if Saturn BSM calculation or report generation failed
2. If data issue -> Check [bsm_datahub.md](bsm_datahub.md) for quality validation
3. If upstream problem -> Review [bsm_ingestion.md](bsm_ingestion.md) for feed ingestion status 

**Investigation Order:** `bsm_saturn.md` -> `bsm_datahub.md` -> `bsm_ingestion.md`
**Next Step:** If Saturn depends on missing or flagged balance sheet input, proceed to [bsm_datahub.md](bsm_datahub.md)
**End Point:** Saturn BSM is the starting point for this triage flow