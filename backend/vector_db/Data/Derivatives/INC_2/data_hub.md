---
id: DRVC_INC_2_MULTIPLE_PIPELINE_TRIGGER
system: data_hub
symptom: "No count mismatch observed at Data Hub for impacted COB"
severity: high
---

## Checks

1. Check Data Hub snapshot/feed count for impacted COB.
2. Confirm no count mismatch at Data Hub level.

## Common causes

- Data Hub may be healthy even when downstream orchestration timing causes failure.

## Next actions

- If Data Hub counts match expected, proceed to ingestion/orchestration checks.
- Capture evidence that issue is not due to Data Hub data quality.