---
id: DRVC_INCF_3_IMGF_HIDDEN_ROWS
system: upload_ingestion
symptom: "Rollover did not happen because hidden IMGF rows were present in the upload file"
severity: high
---

## Checks

1. Check the original upload file for IMGF rows for the impacted COB.
2. Verify whether any IMGF rows are hidden in the source file.
3. Confirm that rollover logic did not trigger because IMGF data was still present in hidden rows.
4. Validate that reduced IMGF data then flowed to Data Hub and Saturn.

## Common causes

- Hidden rows in the upload file contained IMGF data.
- Rollover only works when no IMGF data is present in the upload file.

## Next actions

- Unhide and validate all rows in the upload file before ingestion.
- Add source-file validation for hidden rows before rollover decisioning.
- Publish RCA that this is an upload ingestion issue caused by hidden IMGF rows.