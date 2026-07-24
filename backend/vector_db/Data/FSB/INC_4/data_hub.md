---
id: FSB_TSY_DATAHUB_SNAPSHOT_PIPELINE_FAILURE
system: data_hub
symptom: "FSB report discrepancy / incorrect report numbers traced to Data Hub: the Treasury snapshot pipeline FAILED and published an incomplete/partial snapshot (180 of 250 trades) for COB 14-Nov, causing the mismatch between report and staging; snapshot_status=FAILED, approval_status=REJECTED."
severity: high
---

## Checks

1. Query `dh.snapshot_tsy_liquidity_buffer` WHERE feed_name='TSY_LIQUIDITY_BUFFER' AND cob_date='2025-11-14' and count the rows actually written (180) versus expected (250).
2. Inspect `snapshot_status` for the COB run — it is `FAILED` (pipeline stopped before completion / partial snapshot written).
3. Inspect `approval_status` — the incomplete snapshot was auto-`REJECTED` by the completeness gate.
4. Reconcile the snapshot against the upstream staging table `oracle_fsb_staging.tsy_liquidity_buffer` for the same COB: staging holds 250 trades, snapshot holds 180 — 70 trades are missing.
5. Confirm the 70 missing trades are exactly the trades absent from the Saturn report (the discrepancy matches end-to-end).
6. Confirm PE Ingestion / staging is complete and healthy for this COB (`ingestion_status='SUCCESS'`, 250 rows) — the loss occurred at the snapshot step, not upstream.

## Common Causes

- Treasury Data Hub snapshot pipeline failed before completion, publishing an incomplete/partial snapshot (180 of 250 trades) that Saturn then consumed.
- Snapshot job interrupted mid-write, leaving a partial snapshot with `snapshot_status=FAILED`.
- Completeness/approval gate flagged the short row count and set `approval_status=REJECTED`, but the partial snapshot was still visible to Saturn.
- Root cause is fully contained at the Data Hub snapshot layer; upstream staging is complete.

## Next Actions

- ROOT CAUSE IDENTIFIED at Data Hub — the incomplete snapshot is the source of the incorrect Saturn report. Investigation stops here.
- Do NOT escalate to PE Ingestion: the staging table is complete and healthy (250 trades, ingestion_status=SUCCESS), so there is nothing to investigate upstream.
- Re-run the Treasury Data Hub snapshot pipeline for COB 2025-11-14 to produce a COMPLETE snapshot (all 250 staged trades).
- Once the re-run snapshot passes the completeness gate and reaches `approval_status=APPROVED`, trigger Saturn report regeneration for the COB.
- Publish RCA: Treasury Data Hub Snapshot Pipeline Failure — an incomplete snapshot propagated to Saturn reporting.
