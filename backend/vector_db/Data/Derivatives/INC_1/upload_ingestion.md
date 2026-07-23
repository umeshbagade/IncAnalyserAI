---
id: DRVC_MTM_DATA_SPIKE_FOR_TENOR_D60_61
system: upload_ingestion
symptom: "Source-side difference between 2-Jul and 3-Jul causes additional D60 amount downstream"
severity: high
---

## Checks

1. Compare source records for 2-Jul and 3-Jul for the impacted tenor population.
2. Validate contributor attributes: `source_book_id`, `db_party_d_party_id`, `paragon_org_id`, `d_ubr_id`.
3. Confirm that several differing source rows contribute to the D60 gap.
4. Verify the additional D60 amount on 2-Jul is already present in source data.
5. Verify no hidden rows are filtered/suppressed in the source extract.

## Common causes

- Upstream/source data differs between 2-Jul and 3-Jul for impacted rows.
- Additional D60 value entered through ingestion on 2-Jul.

## Next actions

- Reconcile the differing source rows with upstream provider data.
- Publish RCA that the incident is a source/ingestion issue.