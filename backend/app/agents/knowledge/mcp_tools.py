"""
MCP tool layer — the read-only tools now resolve against the REAL incident
knowledge base (see `incident_kb`, backed by vector_db/Data/**).

  "Each [specialist] is a small agent with tools exposed via MCP servers
   (log query, metric query, run diagnostic script, fetch job status)."
  "[Remediation] executes via the same MCP tool layer with signed, audited
   calls."

`investigate_layer` is the incident-aware entry point: given the matched
incident case and a layer, it returns that layer's *actual* checks, observed
discrepancy, common causes and escalation guidance from the curated runbooks.
The generic `log_query` / `metric_query` / `run_diagnostic` remain as
fallbacks for incidents with no matching runbook. Only
`execute_remediation_action` stays a simulated write path.
"""

from __future__ import annotations

from typing import Any, Dict

from . import incident_kb
from .incident_kb import IncidentCase


# ---------------------------------------------------------------------------
# Real, incident-aware investigation surface
# ---------------------------------------------------------------------------

def investigate_layer(case: IncidentCase, layer: str) -> Dict[str, Any]:
    """
    Run the full read-only tool sweep for one layer of one incident and return
    a structured result the Specialist agent turns into a Finding.

    The presence of a runbook for a layer means the curated knowledge base has
    a documented discrepancy at that layer for this incident — so `detected`
    is True and the checks/causes/next-actions are the real runbook content.
    """
    doc = incident_kb.get_layer_doc(case, layer)
    label = incident_kb.LAYER_LABELS.get(layer, layer.title())

    if doc is None:
        return {
            "layer": layer,
            "label": label,
            "detected": False,
            "is_root_cause": False,
            "symptom": "",
            "checks": [],
            "common_causes": [],
            "next_actions": [],
            "log_query": {"system": layer, "matches": []},
            "metric_query": {"system": layer, "series": []},
            "diagnostic": {"system": layer, "output": f"{label}: no runbook signal for this incident."},
        }

    is_root = layer == case.root_cause_layer
    verdict = (
        "ROOT CAUSE — source discrepancy confirmed"
        if is_root
        else "Discrepancy detected — consistent with an upstream source difference"
    )

    return {
        "layer": layer,
        "label": label,
        "detected": True,
        "is_root_cause": is_root,
        "symptom": doc.symptom,
        "checks": doc.checks,
        "common_causes": doc.common_causes,
        "next_actions": doc.next_actions,
        "log_query": {
            "system": layer,
            "query": f"runbook checks for {case.key}",
            "matches": [{"level": "WARN", "message": c} for c in doc.checks],
        },
        "metric_query": {
            "system": layer,
            "metric": "discrepancy_check",
            "observed": doc.symptom,
        },
        "diagnostic": {
            "system": layer,
            "output": f"{label}: {verdict}. {doc.symptom}",
            "checks_run": len(doc.checks),
        },
    }


# ---------------------------------------------------------------------------
# Generic read tools (kept for non-catalogued incidents / backwards-compat)
# ---------------------------------------------------------------------------

def log_query(system_id: str, query: str, window_minutes: int = 120) -> Dict[str, Any]:
    """Stub: pull matching log lines for a system in a time window."""
    return {
        "system": system_id,
        "query": query,
        "window_minutes": window_minutes,
        "matches": [
            {"timestamp": "10:03:00", "level": "ERROR", "message": f"Connection timeout in {system_id}"},
            {"timestamp": "10:04:15", "level": "ERROR", "message": f"Retry attempt failed for {system_id}"},
            {"timestamp": "10:05:30", "level": "WARN", "message": f"Circuit breaker opened for {system_id}"},
        ] if "error" in query.lower() or "fail" in query.lower() else [],
    }


def metric_query(system_id: str, metric: str, window_minutes: int = 60) -> Dict[str, Any]:
    """Stub: pull a metric time series for a system."""
    return {
        "system": system_id,
        "metric": metric,
        "window_minutes": window_minutes,
        "series": [
            {"timestamp": "10:00:00", "value": 0.02},
            {"timestamp": "10:05:00", "value": 0.15},
            {"timestamp": "10:10:00", "value": 0.45},
            {"timestamp": "10:15:00", "value": 0.12},
        ] if "error" in metric.lower() else [
            {"timestamp": "10:00:00", "value": 0.95},
            {"timestamp": "10:05:00", "value": 0.94},
            {"timestamp": "10:10:00", "value": 0.93},
            {"timestamp": "10:15:00", "value": 0.95},
        ],
    }


def run_diagnostic(system_id: str, script: str) -> Dict[str, Any]:
    """Stub: run a named diagnostic script against a system."""
    return {
        "system": system_id,
        "script": script,
        "output": f"Health check for {system_id}: PASSED\nAll subsystems operational.",
    }


def fetch_job_status(system_id: str, job_id: str) -> Dict[str, Any]:
    """Stub: check a batch/async job's status."""
    return {"system": system_id, "job_id": job_id, "status": "running"}


def execute_remediation_action(system_id: str, mcp_tool: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Stub for the guarded write/execute path. In the real system this is a
    signed, audited MCP call — the "signed, audited calls" requirement from
    4.6. Never invoked without a human-approved RemediationAction upstream;
    the orchestrator enforces that, not this function, so this stays a dumb
    executor and the safety property lives in the graph, not here.
    """
    return {"system": system_id, "mcp_tool": mcp_tool, "params": params or {}, "result": "SIMULATED_SUCCESS"}

