---
id: DRVC_MTM_DATA_SPIKE_FOR_TENOR_D60_61
system: data_hub
symptom: "D60/D61 mismatch between 2-Jul and 3-Jul in MTM Volatility Stress Cash Flows"
severity: high
---

## Checks

1. Compare the same tenor-level values for 2-Jul and 3-Jul in Data Hub.
2. Calculate the day-over-day and incremental tenor difference again for validation.
3. Check contributor attributes: `source_book_id`, `db_party_d_party_id`, `paragon_org_id`, `d_ubr_id`.
4. Confirm that several differing rows contribute to the overall gap.

## Common causes

- Data Hub reflects the same row-level differences received from upstream.
- Several differing rows across key attributes explain the total D60 gap.

## Next actions

- If the mismatch seen in Saturn matches Data Hub, escalate to `upload_ingestion`.
- If the mismatch does not match, continue Data Hub-specific validation.