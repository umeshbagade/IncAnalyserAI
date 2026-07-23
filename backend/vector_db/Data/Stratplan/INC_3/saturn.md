---
id: Stratplan_BCS
system: saturn
symptom: "BCS pull failed, historical snapshot not available in source"
severity: high
---

# Checks
- Verify that BCS jobs completed successfully without unrelated failures.
- Verify that a job handle was created for the requested date and variant in the BCS job history table.
- Verify UBR/FSI config aligns with requested historical period
- Check BCS retention window with source owner

# Common Causes
- Historical month-end data not present in BCS source
- The job failed due to another issue and did not complete successfully.
- BCS API returning incorrect row count in metadata
- Variant/process not active for requested historical date
- Config dates valid but source data absent

# Next Actions
- If cause=network interruption -> implement retry and backoff logic review
- If cause=incomplete transmission -> check HTTP content-length header
- If cause=JSON parsing -> validate JSON structure against expected schema
- If cause=encoding -> verify gzip decompression and charset handling