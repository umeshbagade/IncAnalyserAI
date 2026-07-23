---
id: DRVC_INC_2_MULTIPLE_PIPELINE_TRIGGER
system: saturn
symptom: "Report pipeline failed during DBTNT snapshot window"
severity: high
---

## Checks

1. Check Saturn report count/status for impacted COB.
2. Confirm whether report data count is impacted.

## Common causes

- Report run can fail if triggered while upstream write operation is still in progress.

## Next actions

- If Saturn counts are not impacted, move to Data Hub validation.
- If Saturn is impacted, hold publish and rerun after upstream completion.