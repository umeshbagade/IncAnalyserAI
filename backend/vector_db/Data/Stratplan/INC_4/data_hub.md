---
id: stratplan_coefficient_data_failure
system: data_hub
symptom: "Coefficient run failed for current key_date"
severity: critical
---

# Checks
- Check whether complete LDR and balance-sheet data exists for the current key_date.
- Check whether complete UBR refresh and related configuration data exists for the current key_date.
- Check whether all BS data has corresponding LRD data for the current key_date.

# Common Causes
- UBR refresh dataset end_date not extended to current business_date
- Missing active date-range record in `cfg_ubr_refresh_dataset`
- Month-end rollover created a one-day gap in refresh coverage
- Missing LRD or BS related data.

# Next Actions
- If cause=end_date stale -> extend end_date to cover current key_date for active `ubr_dataset_id`
- If cause=missing range -> insert new date-range row covering current/future run dates
- If cause=refresh lag -> rerun/confirm upstream UBR refresh before coefficient run
- If cause=ME gap -> schedule UBR refresh earlier and add date-range pre-check before