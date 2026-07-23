---
id: stratplan_coefficient_data_failure
system: saturn
symptom: "Coefficient run failed for current key_date"
severity: critical
---

# Checks
- Query `cfg_ubr_refresh_dataset` for failed key_date: `start_date <= key_date AND end_date >= key_da
- Compare failing key_date vs configured end_date (example: 28.02.2025 vs 27.02.2025)
- Validate latest `ubr_dataset_id` record exists and date range is active
- Confirm upstream UBR refresh job completed for current business_date

# Common Causes
- UBR refresh dataset end_date not extended to current business_date
- Missing active date-range record in `cfg_ubr_refresh_dataset`
- Month-end rollover created a one-day gap in refresh coverage
- Stale reference data after delayed UBR refresh run

# Next Actions
- If cause=end_date stale -> extend end_date to cover current key_date for active `ubr_dataset_id`
- If cause=missing range -> insert new date-range row covering current/future run dates
- If cause=refresh lag -> rerun/confirm upstream UBR refresh before coefficient run
- If cause=ME gap -> schedule UBR refresh earlier and add date-range pre-check before run