# Saturn Pipelines Root Cause Analysis Guide

## Saturn Calculation & Report Pipeline Failure

id: fsb report generation failure
system: saturn
symptom: "Calculation failed, report generation blocked, metrics missing from report" 
severity: high

## Checks

1. Query saturn.job status WHERE pipeline=? AND cob=? ORDER BY timestamp DESC 
2. Inspect saturn.calculation logs for execution errors and stack traces
3. Check saturn.data validation for input data quality issues
4. Verify all dependent datahub snapshots are APPROVED (from datahub.md)
5. Inspect saturn.rule engine for calculation rule failures
6. Check saturn.report queue for stuck or failed report generation tasks 
7. Validate calculation dependencies and DAG execution order

## Common Causes

- Upstream DataHub snapshot not approved (reference [datahub.md](datahub.md))
- Missing or invalid input data from dependent calculations
- Calculation rule logic errors or formula misconfigurations 
- Reference data missing or stale (validate in datahub.md)
- Report template corruption or missing configuration
- Job timeout due to resource constraints or data volume
- Circular dependency detected in calculation DAG
- Manual approval hold on report generation

## Next Actions

- If cause=upstream snapshot → Review [datahub.md](datahub.md) for quality issues
- If cause=calculation error → Inspect rule engine configuration and test formula independently 
- If cause=reference data → Cross-check reference data sources in [datahub.md](datahub.md)

## Saturn Pipeline Architecture

### Stage 1: Data Ingestion & Validation 
- Consume approved DataHub snapshots 
- Validate schema and completeness
- Check data freshness and timeliness

### Stage 2: Calculation Pipeline
- Execute base calculations in dependency order
- Run derived metric calculations
- Aggregate results across dimensions
- Apply business rule logic

### Stage 3: Quality Assurance
- Validate calculation results against expected ranges
- Check for anomalies and outliers
- Perform reconciliation against external sources
- Verify calculation completeness

### Stage 4: Report Generation
- Format data for report output
- Apply presentation rules and thresholds
- Generate visualizations and aggregates
- Apply security/masking rules

## Common Calculation Errors

### Data Type Mismatches
- Verify numeric fields are not null
- Check date format compliance
- Validate string encoding and length

### Logic Errors
- Review condition/branching logic in rules
- Test edge cases (zeros, nulls, negative values)
- Validate assumption prerequisites

### Performance Issues
- Monitor calculation execution time
- Check for unnecessary full table scans
- Verify index usage and query optimization

### Integration Failures
- Validate API connectivity to external systems
- Check authentication tokens and credentials
- Verify network timeouts and retry logic

## Report Status Workflow

- **QUEUED** → Waiting for upstream data 
- **PROCESSING** → Calculations running
- **VALIDATING** → Quality checks in progress 
- **GENERATING** → Report formatting
- **GENERATED** -> Report ready for delivery
- **FAILED** -> Error occurred (check logs and checks above) 
- **HOLD** -> Manual hold for review/approval (check approval queue) 
- **DELIVERED** -> Report successfully distributed

## Root Cause Analysis Path

1. Start here if Saturn calculation failed
2. If data issue -> Check [datahub.md](datahub.md) for quality validation
3. If upstream problem → Review [ingestion.md](ingestion.md) for feed ingestion status 
4. If resolved → Validate downstream consumers are notified

**Investigation Order:** `saturn.md` -> `datahub.md` -> `ingestion.md`
**Next Step:** If Saturn depends on missing or flagged input, proceed to [datahub.md](datahub.md)
**End Point:** Saturn is the starting point for this triage flow