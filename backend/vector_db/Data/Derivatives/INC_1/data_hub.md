---
id: DRVC_MTM_DATA_SPIKE_FOR_TENOR_D60_61
system: saturn
symptom: "D60/D61 mismatch visible in MTM Volatility Stress Cash Flows between 2-Jul and 3-Jul"
severity: high
---

## Checks

1. Check tenor-wise amounts and counts for 2-Jul and 3-Jul.
2. Compare the tenor values between both dates.
3. Calculate incremental differences from previous tenor (`D2-D1`, `D3-D2`, ..., `D60-D59`).
4. Confirm that an additional amount is added at `D60` on 2-Jul.

## Common causes

- Cumulative tenor logic makes a single large incremental value appear as a tenor-level drop.
- Additional amount at `D60` on 2-Jul is driving the mismatch.

## Next actions

- If the mismatch is confirmed in Saturn, move to Data Hub and compare the same tenor-level values.
- Carry forward the impacted tenor and amount details for downstream validation.