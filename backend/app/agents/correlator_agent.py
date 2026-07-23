"""
Correlator Agent (4.5).

Merges findings across specialists onto a common timeline + causal graph.
Highlights temporal/causal ordering (what failed first) — critical for
distributed RCA: the system where an anomaly was found isn't necessarily
the root cause if an upstream dependency also showed anomalies.
"""

from __future__ import annotations

from . import llm_client
from .models import ActorType, AuditEvent, CorrelationResult, IncidentGraphState, IncidentStatus
from .knowledge.topology_store import get_upstream_systems

SYSTEM_PROMPT = """\
You are the Correlator Agent. You're given the full set of structured
Findings collected during an investigation, in the order they were
gathered, along with each finding's system's upstream dependencies. Produce:

- timeline: one CausalEvent per finding that reported an ANOMALY (skip
  NORMAL/INCONCLUSIVE findings), each with:
    - system, description (what was found)
    - sequence_order: your best judgement of causal ordering (0 = happened
      first / most upstream cause), NOT necessarily the order they were
      investigated in — a downstream symptom can be reported before its
      upstream cause is checked.
    - likely_root_cause: true for the ONE event you believe is the actual
      root cause (usually the most upstream anomaly), false for the rest
- root_cause_system: the system_id of the likely root cause, or null if no
  anomalies were found at all
- root_cause_summary: 2-3 sentences explaining the causal chain
- remediation_needed: true only if there's a concrete, actionable root
  cause a remediation could address (not for INCONCLUSIVE-only results,
  which need more investigation, not remediation)
"""


def correlate_node(state: IncidentGraphState) -> dict:
    findings = state.get("findings", [])

    findings_listing = "\n".join(
        f"{i}. system={f.system} step={f.step_id} status={f.status.value} "
        f"anomalies={f.anomalies} evidence={f.evidence_refs} "
        f"(upstream deps: {get_upstream_systems(f.system) or 'none'})"
        for i, f in enumerate(findings)
    )

    user_prompt = f"""\
Findings gathered during this investigation, in the order collected:
{findings_listing if findings_listing else "(no findings collected)"}
"""

    result: CorrelationResult = llm_client.call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=CorrelationResult,
    )

    audit_entry = AuditEvent(
        actor=ActorType.CORRELATOR_AGENT,
        event_type="CORRELATION_COMPLETE",
        detail=f"root_cause={result.root_cause_system} remediation_needed={result.remediation_needed}. "
        f"{result.root_cause_summary}",
    )

    return {
        "correlation": result,
        "status": IncidentStatus.CORRELATING,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
