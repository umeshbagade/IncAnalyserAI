"""
Correlator Agent (4.5).

Merges findings across specialists onto a common timeline + causal graph.
Highlights temporal/causal ordering (what failed first) — critical for
distributed RCA: the system where an anomaly was found isn't necessarily
the root cause if an upstream dependency also showed anomalies.
"""

from __future__ import annotations

from . import llm_client
from .models import ActorType, AuditEvent, CausalEvent, CorrelationResult, IncidentGraphState, IncidentStatus
from .knowledge import incident_kb
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
    incident = state["incident"]

    # ── Data-driven path: root cause = deepest (source) layer per runbook ──
    flow_hint = incident.suspected_systems[0] if incident.suspected_systems else ""
    case = incident_kb.match_case(incident.title, incident.description, flow_hint)
    if case is not None:
        ordered = case.ordered_layers
        root_layer = case.root_cause_layer
        root_doc = incident_kb.get_layer_doc(case, root_layer) if root_layer else None
        timeline = []
        for idx, layer in enumerate(ordered):
            label = incident_kb.LAYER_LABELS.get(layer, layer.title())
            doc = incident_kb.get_layer_doc(case, layer)
            is_root = layer == root_layer
            timeline.append(
                CausalEvent(
                    system=layer,
                    description=(
                        doc.symptom if doc and doc.symptom else "discrepancy observed"
                    ),
                    # 0 = most upstream cause (the source layer, checked last)
                    sequence_order=len(ordered) - 1 - idx,
                    likely_root_cause=is_root,
                )
            )
        causes = root_doc.common_causes if root_doc else []
        chain = " → ".join(incident_kb.LAYER_LABELS.get(l, l) for l in ordered)
        root_label = incident_kb.LAYER_LABELS.get(root_layer, root_layer or "unknown")
        summary = (
            f"The discrepancy was traced along {chain}. The upstream layers reflect the "
            f"same symptom, so they are downstream effects; the root cause is at the "
            f"{root_label} (source) layer. "
            + (f"Most likely cause: {causes[0]}" if causes else "")
        )
        result = CorrelationResult(
            timeline=timeline,
            root_cause_system=root_layer,
            root_cause_summary=summary,
            remediation_needed=True,
        )
        audit_entry = AuditEvent(
            actor=ActorType.CORRELATOR_AGENT,
            event_type="CORRELATION_COMPLETE",
            detail=f"root_cause={root_layer} remediation_needed=True. {summary}",
        )
        return {
            "correlation": result,
            "status": IncidentStatus.CORRELATING,
            "audit_trail": state.get("audit_trail", []) + [audit_entry],
        }

    # ── Fallback: LLM correlation for non-catalogued incidents ─────────
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
