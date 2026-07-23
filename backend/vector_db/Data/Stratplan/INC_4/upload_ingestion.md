---
id: stratplan_coefficient_data_failure
system: upload_ingestion
symptom: "Coefficient run failed for current key_date"
severity: critical
---

# Checks
- Check whether uploaded LRD and BS data is stored and mapped correctly for the current key_date.
- Check whether uploaded UBR refresh and other configuration data is stored and mapped correctly.
- Check whether all BS data has corresponding LRD data for the current key_date.

# Common Causes
- Data loading failed for LRD or BS data.
- Data loading failed for UBR refresh or related configuration data.
- Missing LRD or BS related data.

# Next Actions
- If cause=data loading issue -> re-upload LRD/BS or UBR refresh/configuration data, then verify storage an
- If cause=missing data -> validate the source data and re-upload missing LRD or BS data.