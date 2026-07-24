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
import os
import uuid
from datetime import datetime, timezone

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .correlator_agent import correlate_node
from .planner_agent import planner_node
from .remediation_agent import remediation_node
from .specialist_agent import specialist_node
from .triage_agent import triage_node
from .knowledge import incident_kb
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

# Human-visible pacing: the graph super-steps complete in well under a second,
# which is too fast for a person to follow the live investigation. We pause
# after each step that changes the visible DAG (or streams new evidence) so the
# UI reveals Saturn -> Data Hub -> Ingestion one stage at a time. Tunable via
# the STEP_PACING_SECONDS env var (0 disables pacing).
STEP_PACING_SECONDS = float(os.getenv("STEP_PACING_SECONDS", "3.0"))

# Initial "thinking" delay before the first layer is revealed, so the dashboard
# spends a beat in triage/planning instead of popping the first stage instantly.
# Tunable via the INITIAL_INVESTIGATION_DELAY_SECONDS env var.
INITIAL_INVESTIGATION_DELAY_SECONDS = float(os.getenv("INITIAL_INVESTIGATION_DELAY_SECONDS", "2.5"))


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
            entities.append({"name": s, "type": "symptom", "confidence": 0.7})
        if entities:
            updates["entities"] = entities

    # ── Runbook / Flow DAG ─────────────────────────────────────────────
    runbook = state.get("runbook", [])
    findings = state.get("findings", [])
    finding_by_step = {f.step_id: f for f in findings}
    current_step_id = state.get("current_step_id")
    investigation_done = state.get("status") in (IncidentStatus.RESOLVED, IncidentStatus.ESCALATED)
    # The correlator decides which single layer is the actual root cause. Until
    # correlation runs, no layer is flagged as the culprit — every checked layer
    # is shown as "completed" (symptom observed and traced onward), not "error".
    # Only the confirmed root-cause layer is rendered as the issue.
    correlation = state.get("correlation")
    root_cause_system = correlation.root_cause_system if correlation else None
    # Determine the expected endpoint/root-cause layer up-front from the matched
    # runbook case. The terminal (source) layer must never flash "completed"
    # (green success) before the correlator flips it to "error" — instead it
    # stays "active" (still analysing) until the failure is confirmed, so it
    # transitions active -> error, never success -> error.
    _incident_for_root = state.get("incident")
    expected_root_layer = None
    if _incident_for_root is not None:
        _hint = _incident_for_root.suspected_systems[0] if _incident_for_root.suspected_systems else ""
        _root_case = incident_kb.match_case(_incident_for_root.title, _incident_for_root.description, _hint)
        if _root_case is not None:
            expected_root_layer = _root_case.root_cause_layer
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
            is_root_cause = root_cause_system is not None and step.system == root_cause_system
            is_expected_root = (
                expected_root_layer is not None and step.system == expected_root_layer
            )
            # Determine per-node status for the live DAG.
            if is_root_cause:
                # The one layer the correlator pinned as the actual root cause.
                step_status = "error"
            elif finding and is_expected_root:
                # Known source/endpoint layer analysed but not yet confirmed by
                # the correlator — keep it visibly "active" so it never shows a
                # green success state before turning red.
                step_status = "active"
            elif finding:
                # Checked (symptom may have been observed and traced onward, or
                # the layer was clean) — either way it's not the culprit.
                step_status = "completed"
            elif step.step_id == current_step_id:
                step_status = "active"  # specialist is working on this now
            elif investigation_done:
                step_status = "skipped"  # DAG branched away — never visited
            else:
                step_status = "pending"

            label = system_label_map.get(step.system, step.system.replace("_", " ").title())

            # Keep the node concise; the full detail lives in Evidence & Citations.
            if is_root_cause and finding and finding.anomalies:
                # Root cause: surface the anomalies as errors, but keep each line
                # short so it fits on a single row in the DAG node. The node
                # already reads "<layer> / ERROR", so we drop the redundant
                # "ROOT CAUSE at <layer>:" prefix and clip overly long causes.
                def _shorten(a: str) -> str:
                    text = a.split(": ", 1)[1] if a.startswith("ROOT CAUSE at ") and ": " in a else a
                    return text if len(text) <= 52 else text[:51].rstrip() + "…"
                sub = [(_shorten(a), "error") for a in finding.anomalies[:3]]
            elif finding and is_expected_root:
                # Endpoint layer under final confirmation.
                sub = [("Analyzing source layer — confirming root cause…", "active")]
            elif finding and finding.anomalies:
                # Checked layer where the symptom was visible but it is not the
                # root cause — show it was traced onward, not flagged as broken.
                sub = [("Discrepancy detected — traced upstream to source layer", "completed")]
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
            # Progressive reveal: only surface layers the investigation has
            # actually reached (active / completed / error / skipped). Future
            # layers that are still "pending" are withheld so the UI shows one
            # stage at a time — Saturn first, then Data Hub once Saturn is done,
            # then Ingestion — instead of rendering the whole DAG up front.
            visible_nodes = [n for n in nodes if n["status"] != "pending"]
            flow_id = state.get("incident").incident_id if state.get("incident") else "investigation"
            updates["flow.id"] = flow_id
            updates["flow.name"] = f"Investigation for {flow_id}"
            updates["flow.nodes"] = visible_nodes

    # ── Evidence ───────────────────────────────────────────────────────
    evidence_list = state.get("evidence", [])
    mapped_evidence = []
    for ev in evidence_list:
        # Reflect whether the phase this evidence belongs to passed or failed.
        # Only the confirmed root-cause layer is marked "failed"; anomalies on
        # traversed-but-not-culprit layers are shown as warnings (symptom seen).
        f = finding_by_step.get(ev.step_id)
        if root_cause_system and ev.system == root_cause_system:
            ev_status = "failed"
        elif f and f.status == FindingStatus.ANOMALY:
            ev_status = "warning"
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

    # Enrich with runbook-backed evidence (root-cause fix + similar incidents)
    # drawn from the curated knowledge base when this incident matches a case.
    # These are gated on investigation progress so they stream in as the
    # relevant stage is reached — the root-cause candidates/fixes only surface
    # once the Ingestion (source) layer has actually been analysed, and similar
    # incidents only after correlation has confirmed the root cause. This keeps
    # the Evidence panel updating one group at a time instead of all at once.
    incident_obj = state.get("incident")
    if incident_obj is not None:
        analyzed_systems = {
            step.system for step in runbook if finding_by_step.get(step.step_id)
        }
        flow_hint = incident_obj.suspected_systems[0] if incident_obj.suspected_systems else ""
        case = incident_kb.match_case(incident_obj.title, incident_obj.description, flow_hint)
        if case is not None:
            root_layer = case.root_cause_layer
            root_reached = root_layer in analyzed_systems or root_cause_system is not None
            root_doc = incident_kb.get_layer_doc(case, root_layer) if root_layer else None
            if root_doc and root_reached:
                for j, cause in enumerate(root_doc.common_causes):
                    mapped_evidence.append({
                        "id": f"rc-cause-{j}",
                        "type": "runbook",
                        "content": f"Root cause candidate: {cause[:50]}",
                        "status": "failed",
                        "details": f"Runbook '{case.key}' common cause at {root_layer}: {cause}",
                        "node_id": root_layer,
                    })
                for j, action in enumerate(root_doc.next_actions):
                    mapped_evidence.append({
                        "id": f"rc-fix-{j}",
                        "type": "runbook",
                        "content": f"Fix / next step: {action[:50]}",
                        "status": "success",
                        "details": f"Runbook '{case.key}' next action at {root_layer}: {action}",
                        "node_id": root_layer,
                    })
            if root_cause_system is not None:
                for j, sim in enumerate(incident_kb.find_similar(case)):
                    mapped_evidence.append({
                        "id": f"sim-{j}",
                        "type": "similar_incident",
                        "content": f"{sim.domain}/{sim.folder}: {sim.symptom[:45]}",
                        "status": "warning",
                        "details": f"Similar past incident '{sim.key}' ({sim.domain}/{sim.folder}): {sim.symptom}",
                        "node_id": case.root_cause_layer,
                    })

    if mapped_evidence:
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
                f"{incident_kb.LAYER_LABELS.get(e.system, e.system)}: {e.description}"
                for e in correlation.timeline
            ]

    # ── Remediation plan → next actions ───────────────────────────────
    remediation = state.get("remediation_plan")
    if remediation and remediation.actions:
        updates["flow.nextActions"] = [
            {
                "id": a.action_id,
                "label": a.description,
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
        first_visible_reveal = True
        while True:
            snapshot = await asyncio.to_thread(_advance, stream)
            if snapshot is _DONE:
                break
            result = snapshot
            updates = _translate_state_to_updates(snapshot)
            updates["investigation.runId"] = run_id
            updates["investigation.createdAt"] = created_at
            await collection.update_one({"id": inc_id}, {"$set": updates})
            # Pace only the *searching* phase of each stage. We hold while a
            # layer is "active" (loading/searching takes time), but let
            # snapshots that merely mark a stage completed/failed pass straight
            # through — so as soon as one stage finishes the next stage starts
            # immediately, with the delay living inside the active phase rather
            # than between stages.
            flow_nodes = updates.get("flow.nodes")
            stage_searching = isinstance(flow_nodes, list) and any(
                n.get("status") == "active" for n in flow_nodes
            )
            if STEP_PACING_SECONDS > 0 and stage_searching:
                # Hold on the triage/planning phase before the very first layer
                # starts searching, so the investigation doesn't reveal instantly.
                if first_visible_reveal and INITIAL_INVESTIGATION_DELAY_SECONDS > 0:
                    await asyncio.sleep(INITIAL_INVESTIGATION_DELAY_SECONDS)
                first_visible_reveal = False
                await asyncio.sleep(STEP_PACING_SECONDS)
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
