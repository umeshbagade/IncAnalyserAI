"""
Specialist Agent (4.4) — one logical agent per system, generically driven
by the current DAG step's `system` / `assigned_agent`.

Each invocation:
  1. Calls the MCP-exposed tools for its system (log query, metric query,
     diagnostic script) — stubbed for now, see knowledge/mcp_tools.py.
  2. Pulls that system's own scoped knowledge base (its runbooks, config
     docs, known-issues) — also stubbed, see knowledge/topology_store.py.
  3. Returns a structured Finding — status/anomalies/evidence_refs/
     suggested_next — never prose, so the Supervisor and Correlator can
     reason over it programmatically instead of parsing free text.

In a real system this would likely be N separate deployable agents (one per
system, possibly with different tool access/permissions). Kept as one
generic function here since the *pattern* is identical per system and the
tool layer is what's actually system-specific — split it out once real
per-system tool access differs enough to warrant it.
"""

from __future__ import annotations

from . import llm_client
from .models import ActorType, AuditEvent, Finding, FindingStatus, IncidentGraphState, PlanStep
from .knowledge import incident_kb
from .knowledge.mcp_tools import investigate_layer, log_query, metric_query, run_diagnostic
from .knowledge.topology_store import get_system_knowledge_base

SYSTEM_PROMPT = """\
You are a Specialist Agent scoped to ONE system. You've been given the
results of log/metric/diagnostic tool calls against your system, plus
relevant excerpts from your system's own knowledge base. Based ONLY on this
evidence — do not speculate beyond it — return a structured Finding:

- status: "ANOMALY" if the tool outputs show something concrete and
  suspicious, "NORMAL" if everything looks healthy, "INCONCLUSIVE" if the
  available data doesn't give a clear answer (e.g. tool outputs are empty).
- anomalies: specific things you found, if any (empty list if NORMAL or
  INCONCLUSIVE)
- evidence_refs: short references to what supports your finding (e.g. "log
  query: 0 matching error lines in window" — cite what you were given, not
  what you assume)
- suggested_next: brief suggestions for what else could be checked, if
  relevant (empty list is fine)

Do not fabricate log lines, metrics, or KB content you were not given.
"""


def specialist_node(state: IncidentGraphState) -> dict:
    runbook = state["runbook"]
    step_id = state["current_step_id"]
    step: PlanStep = next(s for s in runbook if s.step_id == step_id)
    incident = state["incident"]

    # ── Data-driven path: real MCP sweep against the matched runbook ────
    flow_hint = incident.suspected_systems[0] if incident.suspected_systems else ""
    case = incident_kb.match_case(incident.title, incident.description, flow_hint)
    if case is not None and step.system in case.layers:
        sweep = investigate_layer(case, step.system)
        label = sweep["label"]
        if sweep["is_root_cause"]:
            anomalies = [f"ROOT CAUSE at {label}: {c}" for c in sweep["common_causes"]] or [
                f"ROOT CAUSE at {label}: {sweep['symptom']}"
            ]
        else:
            anomalies = [f"Discrepancy at {label}: {sweep['symptom']}"] + [
                f"Check flagged: {c}" for c in sweep["checks"][:2]
            ]
        evidence_refs = [f"{label} check — {c}" for c in sweep["checks"]] or [f"{label}: {sweep['symptom']}"]
        finding = Finding(
            step_id=step.step_id,
            system=step.system,
            status=FindingStatus.ANOMALY,
            anomalies=anomalies,
            evidence_refs=evidence_refs,
            suggested_next=sweep["next_actions"],
        )
        audit_entry = AuditEvent(
            actor=ActorType.SPECIALIST_AGENT,
            event_type="FINDING_REPORTED",
            detail=(
                f"step_id={step.step_id} system={step.system} status=ANOMALY "
                f"root_cause={sweep['is_root_cause']} anomalies={anomalies[:1]}"
            ),
        )
        return {
            "findings": state.get("findings", []) + [finding],
            "audit_trail": state.get("audit_trail", []) + [audit_entry],
        }

    # ── Fallback: LLM specialist for non-catalogued incidents ──────────
    logs = log_query(step.system, step.action)
    metrics = metric_query(step.system, "error_rate")
    diagnostic = run_diagnostic(step.system, "health_check")
    kb_excerpts = get_system_knowledge_base(step.system, step.action)

    user_prompt = f"""\
System: {step.system}
Step action requested: {step.action}
Step rationale: {step.rationale}

Log query result: {logs}
Metric query result: {metrics}
Diagnostic result: {diagnostic}

System-scoped knowledge base excerpts:
{kb_excerpts if kb_excerpts else "(none found)"}
"""

    finding: Finding = llm_client.call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=Finding,
    )
    finding.step_id = step.step_id
    finding.system = step.system

    audit_entry = AuditEvent(
        actor=ActorType.SPECIALIST_AGENT,
        event_type="FINDING_REPORTED",
        detail=f"step_id={step.step_id} system={step.system} status={finding.status.value} "
        f"anomalies={finding.anomalies}",
    )

    return {
        "findings": state.get("findings", []) + [finding],
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
