---
id: FSB_TSY_DATAHUB_SNAPSHOT_PIPELINE_FAILURE
system: saturn
symptom: "FSB report data discrepancy — report numbers look inappropriate/incorrect and understated. The Saturn Treasury Liquidity Buffer report values are wrong (mismatch versus source) because the consumed Data Hub snapshot is incomplete for COB 14-Nov: trade count and buffer total are below expected."
severity: high
---

## Checks

1. Query `tableau.report_tsy_liquidity_buffer` WHERE cob_date=? and compare trade_count and total_amount for 2025-11-14 against the prior good COB 2025-11-13.
2. Confirm the report ran to completion (`report_status = 'PUBLISHED'`) — Saturn itself did not error.
3. Reconcile the Saturn report totals against the Data Hub snapshot it consumed (`dh.snapshot_tsy_liquidity_buffer`). They should match exactly.
4. Verify the expected trade population for the COB (expected 250 trades) versus the trades actually reflected in the report (180).
5. Confirm the discrepancy (70 missing trades / understated buffer) is inherited from upstream, not introduced by a Saturn calculation.

## Common Causes

- Saturn faithfully published whatever the upstream Data Hub snapshot contained; the snapshot was incomplete.
- No Saturn calculation, rule, or template error — the report simply consumed a partial snapshot.
- Missing trades and understated Liquidity Buffer total originate before Saturn, in the Data Hub snapshot layer.

## Next Actions

- If the Saturn report totals exactly match the Data Hub snapshot, the report is a faithful reflection of upstream — move to Data Hub and compare snapshot completeness (see [data_hub.md](data_hub.md)).
- Carry forward the impacted COB (2025-11-14), the expected trade count (250) and the observed count (180) for downstream validation.
- Do not raise a Saturn defect — Saturn has no calculation or reporting issue.
