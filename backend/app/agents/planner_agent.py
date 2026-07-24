"""
Planner Agent (4.3) — Runbook Generator.

Consumes triage output + service topology graph + flow definitions.
Emits a DAG: "check X -> if Y then check Z, else check W".

This is deliberately NOT a flat ordered list — each PlanStep has on_anomaly
and on_clean pointers to the next step_id, so the Supervisor (in
orchestrator.py) walks a real branching investigation instead of a fixed
sequence. That's what lets the system skip irrelevant downstream systems
when an upstream check comes back clean, and drill deeper only where an
anomaly was actually found.
"""

from __future__ import annotations

from . import llm_client
from .models import ActorType, AuditEvent, IncidentGraphState, IncidentStatus, PlanStep, RunbookPlan
from .knowledge import incident_kb
from .knowledge.topology_store import get_downstream_systems, get_system, search_similar_runbooks

SYSTEM_PROMPT = """\
You are the Planner Agent inside an incident-diagnosis system. You receive
the triage classification and a topology of candidate systems (with their
downstream dependents). Produce a branching investigation DAG, not a flat
list:

- entry_step_id: which step to run first — should be the triage entry_point
  system.
- steps: each PlanStep needs:
    - step_id (short, unique, e.g. "s1", "s2")
    - system: system_id to check
    - action: a concrete, checkable action (e.g. "pull error logs for
      correlation_id in the last 2 hours", "check queue depth / consumer
      lag") — not vague guidance
    - rationale: why this step, given the hypothesis so far
    - assigned_agent: f"{system_id}_specialist"
    - on_anomaly: step_id to go to IF this check finds an anomaly (usually
      an UPSTREAM system — a problem here suggests looking at what THIS
      system depends on) — null if this should be treated as a likely root
      cause with nothing further upstream to check
    - on_clean: step_id to go to IF this check comes back normal (usually a
      DOWNSTREAM or sibling system — ruling this one out means look
      elsewhere) — null if there's nowhere else sensible to check

Keep the DAG small and purposeful: 3-6 steps for a first pass. Every step_id
referenced by on_anomaly/on_clean must exist in the steps list, or be null.
planning_rationale: 2-4 sentences on the overall branching strategy.
"""


def planner_node(state: IncidentGraphState) -> dict:
    incident = state["incident"]
    triage = state["triage"]
    assert triage is not None, "planner_node requires triage to have run first"

    # ── Data-driven path: build the DAG straight from the matched runbook ──
    flow_hint = incident.suspected_systems[0] if incident.suspected_systems else ""
    case = incident_kb.match_case(incident.title, incident.description, flow_hint)
    if case is not None:
        ordered = case.ordered_layers  # e.g. ["saturn", "datahub", "ingestion"]
        steps: list[PlanStep] = []
        for idx, layer in enumerate(ordered):
            doc = incident_kb.get_layer_doc(case, layer)
            step_id = f"s{idx + 1}"
            next_id = f"s{idx + 2}" if idx + 1 < len(ordered) else None
            label = incident_kb.LAYER_LABELS.get(layer, layer.title())
            action = (doc.checks[0] if doc and doc.checks else f"Verify {label} for the reported discrepancy")
            steps.append(
                PlanStep(
                    step_id=step_id,
                    system=layer,
                    action=action,
                    rationale=(
                        f"Trace the discrepancy at {label}; if confirmed, escalate to the "
                        f"upstream source layer as the runbook's Next Actions instruct."
                    ),
                    assigned_agent=f"{layer}_specialist",
                    on_anomaly=next_id,   # discrepancy here -> drill to the upstream source
                    on_clean=None,        # clean here -> nothing further to check
                )
            )
        plan = RunbookPlan(
            entry_step_id="s1",
            steps=steps,
            planning_rationale=(
                f"Runbook '{case.key}' drives a straight upstream drill: "
                f"{' → '.join(incident_kb.LAYER_LABELS.get(l, l) for l in ordered)}. "
                f"Each layer is checked in turn; a confirmed discrepancy escalates to the "
                f"next-deeper source layer, ending at the root-cause layer."
            ),
        )
        audit_entry = AuditEvent(
            actor=ActorType.PLANNER_AGENT,
            event_type="RUNBOOK_DRAFTED",
            detail=(
                f"entry=s1 steps={[(s.step_id, s.system) for s in steps]}. {plan.planning_rationale}"
            ),
        )
        return {
            "runbook": plan.steps,
            "entry_step_id": plan.entry_step_id,
            "current_step_id": plan.entry_step_id,
            "status": IncidentStatus.INVESTIGATING,
            "audit_trail": state.get("audit_trail", []) + [audit_entry],
        }

    # ── Fallback: LLM planner for non-catalogued incidents ─────────────
    candidate_ids = {triage.entry_point_service}
    candidate_ids.update(get_downstream_systems(triage.entry_point_service))

    candidates_listing = "\n".join(
        f"- {sid}: {(get_system(sid).description if get_system(sid) else 'unknown system')} "
        f"(downstream of this: {get_downstream_systems(sid) or 'none'})"
        for sid in candidate_ids
    )

    similar = search_similar_runbooks(f"{triage.impacted_business_flow} {triage.severity.value}")
    similar_block = "\n".join(similar) if similar else "(none found)"

    user_prompt = f"""\
Incident: {incident.title}
Description: {incident.description}

Triage classification:
- impacted_business_flow: {triage.impacted_business_flow}
- severity: {triage.severity.value}
- entry_point_service: {triage.entry_point_service}
- symptoms: {triage.symptoms}
- rationale: {triage.rationale}

Candidate systems (entry point + its downstream dependents):
{candidates_listing}

Similar past runbooks (reference only, adapt don't copy blindly):
{similar_block}
"""

    plan: RunbookPlan = llm_client.call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=RunbookPlan,
    )

    audit_entry = AuditEvent(
        actor=ActorType.PLANNER_AGENT,
        event_type="RUNBOOK_DRAFTED",
        detail=(
            f"entry={plan.entry_step_id} steps={[(s.step_id, s.system) for s in plan.steps]}. "
            f"{plan.planning_rationale}"
        ),
    )

    return {
        "runbook": plan.steps,
        "entry_step_id": plan.entry_step_id,
        "current_step_id": plan.entry_step_id,
        "status": IncidentStatus.INVESTIGATING,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
