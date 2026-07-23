"""
Stand-in for the MCP tool layer described in the architecture:

  "Each [specialist] is a small agent with tools exposed via MCP servers
   (log query, metric query, run diagnostic script, fetch job status)."
  "[Remediation] executes via the same MCP tool layer with signed, audited
   calls."

These are stubs returning synthetic-but-plausible data so the agents that
call them can be exercised end-to-end. Swap the bodies for real MCP client
calls (`mcp_client.call_tool("log_query", {...})` etc.) when wiring in real
per-system MCP servers — the function signatures are the contract.
"""

from __future__ import annotations

from typing import Any, Dict


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

