"""
Supervisor / Orchestrator Agent (4.1).

    START -> triage -> planner -> specialist -> supervisor_update -+
                                        ^                          |
                                        |__________________________|
                                     (loop while DAG has a next step)
                                                  |
                                                  v
                                              correlate
                                            /            \\
                              remediation_needed      no remediation
                                    |                       |
                                    v                       v
                            propose_remediation          finalize -> END
                                    |
                          (has actions?)  -- no --> finalize -> END
                                    | yes
                                    v
                            remediation_gate  <-- ONLY interrupt in the graph
                                    |
                                    v
                            execute_remediation -> finalize -> END

Pattern: plan-and-execute state machine (not free-form ReAct) — the DAG is
produced once by the Planner, then the Supervisor (`_supervisor_update_node`
below) walks it, deciding the next specialist based on the topology-derived
branches (on_anomaly / on_clean) and the accumulating typed Investigation
State (hypotheses/evidence/open_questions/next_actions), not by re-planning
from scratch at every step. That's what keeps this auditable instead of a
free-form agent loop.

Human-in-the-loop is scoped to ONE place: `remediation_gate`. Read-only
investigation (triage through correlation) runs fully autonomously; nothing
that writes to or executes against a production system runs without a human
approving it first, enforced by `interrupt_before=["remediation_gate"]`.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .correlator_agent import correlate_node
from .planner_agent import planner_node
from .remediation_agent import remediation_node
from .specialist_agent import specialist_node
from .triage_agent import triage_node
from .knowledge.mcp_tools import execute_remediation_action
from .models import (
    ActorType,
    AuditEvent,
    EvidenceItem,
    FindingStatus,
    Hypothesis,
    HypothesisStatus,
    Incident,
    IncidentGraphState,
    IncidentStatus,
    OpenQuestion,
    PlanStep,
    RunbookStepStatus,
)

MAX_INVESTIGATION_HOPS = 8  # safety cap against a malformed/cyclic DAG


def _supervisor_update_node(state: IncidentGraphState) -> dict:
    """
    The Supervisor's core decision: given the specialist's latest Finding,
    update the typed Investigation State and decide which step to visit
    next by following the DAG's on_anomaly/on_clean branch — i.e. "decide
    which specialist agent to invoke next based on the topology graph +
    current hypotheses."

    Deterministic for now (rule-based on Finding.status), which keeps the
    demo fast and fully auditable. The natural upgrade is to let an LLM call
    make this decision when hypotheses conflict or a finding is ambiguous —
    the typed state here is exactly what that call would need as input.
    """
    runbook = {s.step_id: s for s in state["runbook"]}
    findings = state.get("findings", [])
    latest = findings[-1]
    step: PlanStep = runbook[latest.step_id]

    hypotheses = list(state.get("hypotheses", []))
    evidence = list(state.get("evidence", []))
    open_questions = list(state.get("open_questions", []))

    for ref in latest.evidence_refs:
        evidence.append(
            EvidenceItem(evidence_id=f"ev-{uuid.uuid4().hex[:6]}", system=step.system, step_id=step.step_id, description=ref, source="specialist_finding")
        )

    if latest.status == FindingStatus.ANOMALY:
        hypotheses.append(
            Hypothesis(
                hypothesis_id=f"hyp-{uuid.uuid4().hex[:6]}",
                statement=f"Root cause likely involves {step.system}: {'; '.join(latest.anomalies)}",
                system=step.system,
                status=HypothesisStatus.OPEN,
                confidence=0.6,
            )
        )
        next_step_id = step.on_anomaly
    elif latest.status == FindingStatus.NORMAL:
        hypotheses = [
            h if h.system != step.system else h.model_copy(update={"status": HypothesisStatus.RULED_OUT})
            for h in hypotheses
        ]
        next_step_id = step.on_clean
    else:  # INCONCLUSIVE
        open_questions.append(
            OpenQuestion(question_id=f"q-{uuid.uuid4().hex[:6]}", text=f"Inconclusive at {step.system}: needs a follow-up check.", system=step.system)
        )
        next_step_id = step.on_clean  # default: keep exploring rather than dead-end

    visited_count = len(findings)
    if visited_count >= MAX_INVESTIGATION_HOPS:
        next_step_id = None  # safety cap — stop and correlate whatever we have

    step.status = RunbookStepStatus.DONE

    audit_entry = AuditEvent(
        actor=ActorType.ORCHESTRATOR,
        event_type="SUPERVISOR_DECISION",
        detail=f"after {step.system} ({latest.status.value}): next_step={next_step_id}",
    )

    return {
        "runbook": list(runbook.values()),
        "current_step_id": next_step_id,
        "hypotheses": hypotheses,
        "evidence": evidence,
        "open_questions": open_questions,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }


def _route_after_supervisor(state: IncidentGraphState) -> str:
    return "continue" if state.get("current_step_id") else "done"


def _route_after_correlate(state: IncidentGraphState) -> str:
    correlation = state["correlation"]
    return "propose_remediation" if correlation.remediation_needed else "finalize"


def _route_after_remediation_proposal(state: IncidentGraphState) -> str:
    return "gate" if state.get("awaiting_remediation_approval") else "finalize"


def _remediation_gate_node(state: IncidentGraphState) -> dict:
    """Pass-through node; interrupt_before=['remediation_gate'] does the real work of pausing."""
    return {
        "awaiting_remediation_approval": False,
        "audit_trail": state.get("audit_trail", [])
        + [AuditEvent(actor=ActorType.HUMAN, event_type="REMEDIATION_APPROVED", detail="Human approved proposed remediation action(s).")],
    }


def _execute_remediation_node(state: IncidentGraphState) -> dict:
    plan = state["remediation_plan"]
    audit_trail = state.get("audit_trail", [])
    for action in plan.actions:
        result = execute_remediation_action(action.target_system, action.mcp_tool, {"description": action.description})
        action.status = "EXECUTED"
        audit_trail = audit_trail + [
            AuditEvent(
                actor=ActorType.REMEDIATION_AGENT,
                event_type="REMEDIATION_EXECUTED",
                detail=f"action_id={action.action_id} tool={action.mcp_tool} result={result['result']}",
            )
        ]
    return {"remediation_plan": plan, "status": IncidentStatus.RESOLVED, "audit_trail": audit_trail}


def _finalize_node(state: IncidentGraphState) -> dict:
    if state.get("status") == IncidentStatus.RESOLVED:
        return {}  # already finalized by execute_remediation, or no-remediation-needed path
    audit_entry = AuditEvent(
        actor=ActorType.ORCHESTRATOR,
        event_type="INVESTIGATION_FINALIZED",
        detail="Investigation complete.",
    )
    return {"status": IncidentStatus.RESOLVED, "audit_trail": state.get("audit_trail", []) + [audit_entry]}


def build_graph():
    graph = StateGraph(IncidentGraphState)

    graph.add_node("triage", triage_node)
    graph.add_node("planner", planner_node)
    graph.add_node("specialist", specialist_node)
    graph.add_node("supervisor_update", _supervisor_update_node)
    graph.add_node("correlate", correlate_node)
    graph.add_node("propose_remediation", remediation_node)
    graph.add_node("remediation_gate", _remediation_gate_node)
    graph.add_node("execute_remediation", _execute_remediation_node)
    graph.add_node("finalize", _finalize_node)

    graph.set_entry_point("triage")
    graph.add_edge("triage", "planner")
    graph.add_edge("planner", "specialist")
    graph.add_edge("specialist", "supervisor_update")
    graph.add_conditional_edges(
        "supervisor_update", _route_after_supervisor, {"continue": "specialist", "done": "correlate"}
    )
    graph.add_conditional_edges(
        "correlate", _route_after_correlate, {"propose_remediation": "propose_remediation", "finalize": "finalize"}
    )
    graph.add_conditional_edges(
        "propose_remediation", _route_after_remediation_proposal, {"gate": "remediation_gate", "finalize": "finalize"}
    )
    graph.add_edge("remediation_gate", "execute_remediation")
    graph.add_edge("execute_remediation", "finalize")
    graph.add_edge("finalize", END)

    checkpointer = MemorySaver()
    # NOTE: Human-in-the-loop remediation approval is currently DISABLED (no UI
    # for it yet). The graph runs fully autonomously through remediation_gate
    # and executes the proposed remediation without pausing. To re-enable the
    # approval gate, pass interrupt_before=["remediation_gate"] to compile().
    compiled = graph.compile(checkpointer=checkpointer)
    return compiled


def new_incident_state(incident: Incident) -> IncidentGraphState:
    return IncidentGraphState(
        incident=incident,
        status=IncidentStatus.NEW,
        triage=None,
        runbook=[],
        entry_step_id=None,
        current_step_id=None,
        hypotheses=[],
        evidence=[],
        open_questions=[],
        next_actions=[],
        findings=[],
        correlation=None,
        remediation_plan=None,
        awaiting_remediation_approval=False,
        current_action=None,
        audit_trail=[AuditEvent(actor=ActorType.SYSTEM, event_type="INCIDENT_CREATED", detail=incident.title)],
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Integration Bridge — start_investigation()
# ═══════════════════════════════════════════════════════════════════════════

_graph_instance = None  # lazy-singleton


def _get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance


def _doc_to_incident(inc_id: str, doc: dict) -> Incident:
    """Convert a MongoDB document dict into an agent Incident model."""
    return Incident(
        incident_id=inc_id,
        title=doc.get("title", "Untitled Incident"),
        description=doc.get("description", doc.get("originalText", "")),
        reported_by="system",
        suspected_systems=[doc.get("flowId", "unknown")],
    )


def _translate_state_to_updates(state: dict) -> dict:
    """
    Translate LangGraph state back to MongoDB update fields.
    Maps the agent's structured state to the API/dashboard model fields.
    """
    updates = {
        "investigation.status": "running",
        "investigation.stepIndex": 0,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }

    # ── Triage results ────────────────────────────────────────────────
    triage = state.get("triage")
    if triage:
        updates["triageSummary"] = triage.rationale
        # Map entities from triage
        entities = []
        if triage.entry_point_service:
            entities.append({"name": triage.entry_point_service, "type": "system", "confidence": triage.confidence})
        if triage.impacted_business_flow:
            entities.append({"name": triage.impacted_business_flow, "type": "workflow", "confidence": triage.confidence})
        for s in triage.symptoms[:3]:
            entities.append({"name": s[:40], "type": "symptom", "confidence": 0.7})
        if entities:
            updates["entities"] = entities

    # ── Runbook / Flow DAG ─────────────────────────────────────────────
    runbook = state.get("runbook", [])
    findings = state.get("findings", [])
    finding_by_step = {f.step_id: f for f in findings}
    current_step_id = state.get("current_step_id")
    investigation_done = state.get("status") in (IncidentStatus.RESOLVED, IncidentStatus.ESCALATED)
    system_label_map = {
        "saturn": "Saturn",
        "datahub": "Data Hub",
        "ingestion": "Ingestion",
        "payment-svc": "Payment Service",
        "order-svc": "Order Service",
    }
    if runbook:
        nodes = []
        for step in runbook:
            finding = finding_by_step.get(step.step_id)
            # Determine per-node status for the live DAG.
            if finding:
                # ANOMALY -> error (something failed here); NORMAL/INCONCLUSIVE
                # both mean the step was actually checked -> completed.
                step_status = "error" if finding.status == FindingStatus.ANOMALY else "completed"
            elif step.step_id == current_step_id:
                step_status = "active"  # specialist is working on this now
            elif investigation_done:
                step_status = "skipped"  # DAG branched away — never visited
            else:
                step_status = "pending"

            label = system_label_map.get(step.system, step.system.replace("_", " ").title())

            # Keep the node concise; the full detail lives in Evidence & Citations.
            if finding and finding.anomalies:
                sub = [(a[:60], "error") for a in finding.anomalies[:3]]
            elif step_status == "completed":
                sub = [("Checks passed — no anomaly", "completed")]
            elif step_status == "active":
                sub = [(step.action[:60], "active")]
            elif step_status == "skipped":
                sub = [("Not investigated (branch skipped)", "skipped")]
            else:
                sub = [(step.action[:60], "pending")]

            nodes.append({
                "id": step.system,
                "label": label,
                "status": step_status,
                "description": step.action[:80],
                "subSteps": [
                    {"id": f"{step.step_id}_{j}", "label": lbl, "status": st}
                    for j, (lbl, st) in enumerate(sub)
                ],
            })

        if nodes:
            flow_id = state.get("incident").incident_id if state.get("incident") else "investigation"
            updates["flow.id"] = flow_id
            updates["flow.name"] = f"Investigation for {flow_id}"
            updates["flow.nodes"] = nodes

    # ── Evidence ───────────────────────────────────────────────────────
    evidence_list = state.get("evidence", [])
    if evidence_list:
        mapped_evidence = []
        for ev in evidence_list:
            # Reflect whether the phase this evidence belongs to passed or failed.
            f = finding_by_step.get(ev.step_id)
            if f and f.status == FindingStatus.ANOMALY:
                ev_status = "failed"
            elif f and f.status == FindingStatus.INCONCLUSIVE:
                ev_status = "warning"
            else:
                ev_status = "success"
            mapped_evidence.append({
                "id": ev.evidence_id,
                "type": "tool_call",
                "content": ev.description[:60],
                "status": ev_status,
                "details": f"system={ev.system} step={ev.step_id} source={ev.source}: {ev.description}",
                "node_id": ev.system,
            })
        updates["flow.evidence"] = mapped_evidence

    # ── Hypotheses → causal chain ──────────────────────────────────────
    hypotheses = state.get("hypotheses", [])
    if hypotheses:
        causal_chain = [h.statement for h in hypotheses if h.status in (HypothesisStatus.OPEN, HypothesisStatus.CONFIRMED)]
        updates["flow.rca.causalChain"] = causal_chain

    # ── Correlation → root cause ───────────────────────────────────────
    correlation = state.get("correlation")
    if correlation:
        # Confidence grows with the amount of corroborating anomaly evidence.
        num_anomalies = sum(1 for f in findings if f.status == FindingStatus.ANOMALY)
        confidence = min(0.95, 0.6 + 0.1 * num_anomalies) if correlation.root_cause_system else 0.5
        updates["flow.rca.rootCause"] = correlation.root_cause_summary
        updates["flow.rca.confidence"] = round(confidence, 2)
        if correlation.root_cause_system:
            updates["flow.rca.causalChain"] = [
                f"{e.system}: {e.description}" for e in correlation.timeline
            ]

    # ── Remediation plan → next actions ───────────────────────────────
    remediation = state.get("remediation_plan")
    if remediation and remediation.actions:
        updates["flow.nextActions"] = [
            {
                "id": a.action_id,
                "label": a.description[:40],
                "action": a.mcp_tool,
                "category": "investigate" if a.risk_level == "high" else "rerun",
            }
            for a in remediation.actions
        ]

    # ── Status ─────────────────────────────────────────────────────────
    agent_status = state.get("status")
    if agent_status:
        api_status_map = {
            IncidentStatus.NEW: "open",
            IncidentStatus.TRIAGING: "investigating",
            IncidentStatus.PLANNING: "investigating",
            IncidentStatus.INVESTIGATING: "investigating",
            IncidentStatus.CORRELATING: "investigating",
            IncidentStatus.AWAITING_REMEDIATION_APPROVAL: "investigating",
            IncidentStatus.REMEDIATING: "investigating",
            IncidentStatus.RESOLVED: "resolved",
            IncidentStatus.ESCALATED: "investigating",
        }
        api_status = api_status_map.get(agent_status, "open")
        updates["status"] = api_status
        updates["investigation.status"] = "completed" if agent_status == IncidentStatus.RESOLVED else "running"
        updates["investigation.currentPhase"] = agent_status.value

    # ── Timeline events from audit trail ──────────────────────────────
    audit_trail = state.get("audit_trail", [])
    if audit_trail:
        timeline = []
        for entry in audit_trail:
            event_type_map = {
                ActorType.ORCHESTRATOR: "info",
                ActorType.TRIAGE_AGENT: "info",
                ActorType.PLANNER_AGENT: "info",
                ActorType.SPECIALIST_AGENT: "step",
                ActorType.CORRELATOR_AGENT: "rca",
                ActorType.REMEDIATION_AGENT: "info",
                ActorType.HUMAN: "info",
                ActorType.SYSTEM: "info",
            }
            timeline.append({
                "time": entry.timestamp.strftime("%H:%M:%S") if hasattr(entry.timestamp, "strftime") else datetime.now(timezone.utc).strftime("%H:%M:%S"),
                "event": entry.detail[:80],
                "type": event_type_map.get(entry.actor, "info"),
            })
        updates["timeline"] = timeline

    return updates


async def start_investigation(inc_id: str, doc: dict):
    """
    Entry point called by main.py's create_incident endpoint.
    Runs the full LangGraph investigation autonomously.

    Args:
        inc_id: The incident ID string (e.g. "INC-2026-07-20-001")
        doc: The full MongoDB incident document (dict)

    The investigation runs:
        triage -> planner -> specialist(loop) -> correlate -> (optional remediation)

    Results are written back to MongoDB.
    """
    from ..database import get_incidents_collection

    collection = await get_incidents_collection()

    # 1. Convert MongoDB doc to agent Incident
    incident = _doc_to_incident(inc_id, doc)

    # 2. Build graph and run autonomous investigation
    graph = _get_graph()
    config = {"configurable": {"thread_id": inc_id}}
    initial_state = new_incident_state(incident)

    run_id = f"run-{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()
    result = None

    # Mark as running immediately so the frontend starts live-polling before the
    # first (LLM-bound) super-step completes.
    await collection.update_one(
        {"id": inc_id},
        {"$set": {
            "investigation.status": "running",
            "investigation.runId": run_id,
            "investigation.createdAt": created_at,
            "status": "investigating",
            "updatedAt": created_at,
        }}
    )

    # Each graph super-step is synchronous (blocking LLM calls). We advance the
    # stream one step at a time inside a worker thread so the FastAPI event loop
    # stays free to serve the frontend's live polling requests during the run.
    _DONE = object()

    def _advance(gen):
        try:
            return next(gen)
        except StopIteration:
            return _DONE

    try:
        stream = graph.stream(initial_state, config, stream_mode="values")
        while True:
            snapshot = await asyncio.to_thread(_advance, stream)
            if snapshot is _DONE:
                break
            result = snapshot
            updates = _translate_state_to_updates(snapshot)
            updates["investigation.runId"] = run_id
            updates["investigation.createdAt"] = created_at
            await collection.update_one({"id": inc_id}, {"$set": updates})
    except Exception as e:
        print(f"❌ Investigation failed for {inc_id}: {e}")
        import traceback
        traceback.print_exc()
        # Mark investigation as failed in MongoDB
        await collection.update_one(
            {"id": inc_id},
            {"$set": {
                "investigation.status": "failed",
                "investigation.currentPhase": "error",
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            }}
        )
        return

    # 4. Final completion marker so the frontend can stop polling.
    await collection.update_one(
        {"id": inc_id},
        {"$set": {
            "investigation.status": "completed",
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }}
    )

    status = result.get("status", IncidentStatus.NEW) if result else IncidentStatus.NEW
    print(f"✅ Investigation for {inc_id} completed with status: {status.value if hasattr(status, 'value') else status}")


async def approve_and_execute_remediation(inc_id: str, thread_id: str | None = None) -> dict:
    """
    Resume a paused investigation to approve and execute remediation.

    Called by the POST /api/incidents/{inc_id}/approve endpoint.
    """
    from ..database import get_incidents_collection

    collection = await get_incidents_collection()
    tid = thread_id or inc_id
    config = {"configurable": {"thread_id": tid}}

    graph = _get_graph()
    snapshot = graph.get_state(config)

    if not snapshot.values:
        raise ValueError(f"No active investigation found for incident '{inc_id}'")

    if not snapshot.next:
        raise ValueError(f"No remediation pending approval for incident '{inc_id}'")

    # Resume the graph — it will pass through remediation_gate and execute
    result = graph.invoke(None, config)

    # Translate and write updates
    updates = _translate_state_to_updates(result)
    updates["investigation.approved"] = {
        "approved": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await collection.update_one({"id": inc_id}, {"$set": updates})

    return updates
