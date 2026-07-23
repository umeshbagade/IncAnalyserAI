---
id: DRVC_INCF_3_IMGF_HIDDEN_ROWS
system: saturn
symptom: "IMGF data in derivatives report looked lower than expected and rollover did not happen"
severity: high
---

## Checks

1. Check IMGF counts/amounts in the derivatives report table for the impacted COB.
2. Compare report data with the previous date and confirm the decrease.
3. If Saturn data is lower than expected, trace back to Data Hub.

## Common causes

- Report output is impacted because upstream IMGF data is lower than expected.
- Rollover will not happen if IMGF rows are still present in the upload file.

## Next actions

- Move to Data Hub and validate whether the same IMGF decrease is present upstream.
- Carry forward the impacted COB and IMGF totals for further tracing.