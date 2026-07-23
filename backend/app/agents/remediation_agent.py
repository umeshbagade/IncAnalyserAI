"""
Remediation Agent (4.6) — guarded.

Proposes actions given the Correlator's root-cause finding. Every proposed
action has requires_approval=True by construction — this agent PROPOSES,
it never executes. Execution (via the MCP tool layer) only happens after a
human approves, enforced by the orchestrator's interrupt_before gate, not by
anything in this file.
"""

from __future__ import annotations

from . import llm_client
from .models import ActorType, AuditEvent, CurrentAction, IncidentGraphState, IncidentStatus, RemediationPlan

SYSTEM_PROMPT = """\
You are the Remediation Agent. You're given a Correlator's root-cause
finding for an incident. Propose a small set of concrete remediation
actions (0-3) that could address the root cause. For each action:

- action_id (short, unique)
- description: what the action does, specific enough that a human reviewer
  can judge whether it's safe (e.g. "restart payment-svc worker pool",
  "clear the stuck message from the dead-letter queue for order #12345",
  NOT vague like "fix the issue")
- target_system
- mcp_tool: a plausible tool name for executing this (e.g.
  "restart_service", "requeue_message", "scale_replicas")
- risk_level: "low" | "medium" | "high" — be honest, err toward higher risk
  when an action is destructive or hard to undo
- requires_approval: always true

If the root cause doesn't have a safe automatable remediation (e.g. it needs
a code fix, or root_cause_system is null), propose zero actions and explain
why in the rationale — do not force a remediation that isn't warranted.
"""


def remediation_node(state: IncidentGraphState) -> dict:
    correlation = state["correlation"]
    assert correlation is not None, "remediation_node requires correlation to have run first"

    user_prompt = f"""\
root_cause_system: {correlation.root_cause_system}
root_cause_summary: {correlation.root_cause_summary}
timeline: {[(e.system, e.description, e.likely_root_cause) for e in correlation.timeline]}
"""

    plan: RemediationPlan = llm_client.call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=RemediationPlan,
    )
    for action in plan.actions:
        action.requires_approval = True  # enforced here too, belt-and-suspenders with the model default

    current_action = CurrentAction(
        summary=(
            f"Proposing {len(plan.actions)} remediation action(s). Approve to execute."
            if plan.actions
            else "No safe automatable remediation identified."
        ),
        action_type="propose_remediation",
        requires_approval=bool(plan.actions),
    )

    audit_entry = AuditEvent(
        actor=ActorType.REMEDIATION_AGENT,
        event_type="REMEDIATION_PROPOSED",
        detail=f"{len(plan.actions)} action(s): {[a.description for a in plan.actions]}. {plan.rationale}",
    )

    return {
        "remediation_plan": plan,
        "status": IncidentStatus.AWAITING_REMEDIATION_APPROVAL if plan.actions else IncidentStatus.RESOLVED,
        "awaiting_remediation_approval": bool(plan.actions),
        "current_action": current_action,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
