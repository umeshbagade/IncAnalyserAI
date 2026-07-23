---
id: DRVC_INCF_3_IMGF_HIDDEN_ROWS
system: data_hub
symptom: "IMGF data at Data Hub level was lower than previous date"
severity: high
---

## Checks

1. Check IMGF counts/amounts in Data Hub for the impacted COB.
2. Compare with the previous date and confirm the decrease is already present.
3. If the same decrease is visible in Data Hub, trace back to upload ingestion.

## Common causes

- Data Hub reflects reduced IMGF data received from source upload.
- Hidden IMGF rows in source file can prevent rollover logic from triggering.

## Next actions

- Escalate to `upload_ingestion` if Data Hub shows the same IMGF decrease.
- Carry forward the IMGF count/amount comparison as source evidence.