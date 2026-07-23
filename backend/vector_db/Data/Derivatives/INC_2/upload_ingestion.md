---
id: DRVC_INC_2_MULTIPLE_PIPELINE_TRIGGER
system: upload_ingestion
symptom: "Multiple versions created when DBTNT snapshot arrival triggered parallel jobs"
severity: high
---

## Checks

1. Confirm trigger timeline when `DBTNT_SNLP_SLEEPCOLL` snapshot arrives.
2. Verify configured parallel jobs: `import_saturn_snapshot`, `import_saturn_facts`, `import_saturn_rdb_dimension`.
3. Validate that `import_saturn_rdb_dimension` completed earlier while snapshot write was still in progress.
4. Confirm Serial Dimension and FX Rate flows were triggered before snapshot completion.
5. Confirm report DAG also triggered in parallel, causing read/write overlap and failure.

## Common causes

- Pipeline sequence configuration allows parallel execution for DBTNT snapshot flows.
- Downstream DAG triggers report while upstream write operation is still ongoing.
- Early completion of one branch triggers dependent flows prematurely.

## Next actions

- Create a separate DAG flow for DBTNT snapshots.
- Add dedicated DBTNT poller entry to isolate trigger path.
- Ensure report pipeline starts only after snapshot write completion dependency is met.
- Keep this as ingestion/orchestration RCA.