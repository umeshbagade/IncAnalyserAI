"""
IncAnalyserAI Backend - FastAPI Application
Provides REST APIs + SSE streaming for the incident analysis platform.
All data is static/mocked for hackathon purposes.
"""

import asyncio
import json
import uuid
import random
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# ─── App Setup ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="IncAnalyserAI API",
    description="Backend for AI-powered Production Incident Root Cause Analysis",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ──────────────────────────────────────────────────────────────────

class InvestigationRequest(BaseModel):
    incident_id: str
    description: Optional[str] = None

class InvestigationState(BaseModel):
    run_id: str
    incident_id: str
    status: str = "running"  # running | completed | failed
    current_phase: str = "saturn"
    progress: float = 0.0
    phases: dict = {}

class FeedbackRequest(BaseModel):
    step_id: str
    feedback: str  # "useful" | "wrong"
    comment: Optional[str] = None

class ApproveRequest(BaseModel):
    approved: bool = True
    comment: Optional[str] = None

class FlowNode(BaseModel):
    id: str
    label: str
    status: str  # pending | active | completed | error | skipped
    description: str
    sub_steps: list[dict] = []

class PhaseInfo(BaseModel):
    node_id: str
    label: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

# ─── Mock Data ──────────────────────────────────────────────────────────────

INVESTIGATIONS: dict[str, dict] = {}

FLOW_DEFINITIONS = {
    "eod_reporting": {
        "id": "eod_reporting",
        "name": "EOD Reporting Pipeline",
        "nodes": [
            {
                "id": "saturn",
                "label": "Saturn",
                "status": "completed",
                "description": "Report Level - Check report count & status",
                "sub_steps": [
                    {"id": "s1", "label": "Report Count Check", "status": "completed"},
                    {"id": "s2", "label": "Status Verification", "status": "completed"},
                    {"id": "s3", "label": "Anomaly Detection", "status": "completed"},
                ],
            },
            {
                "id": "datahub",
                "label": "Data Hub",
                "status": "active",
                "description": "Data Layer - Query feeds & data sources",
                "sub_steps": [
                    {"id": "d1", "label": "Feed Status Query", "status": "completed"},
                    {"id": "d2", "label": "Data Source Verification", "status": "active"},
                    {"id": "d3", "label": "Data Quality Check", "status": "pending"},
                ],
            },
            {
                "id": "ingestion",
                "label": "Ingestion",
                "status": "pending",
                "description": "Ingestion Layer - Check connectivity & pipelines",
                "sub_steps": [
                    {"id": "i1", "label": "SFTP Connection Test", "status": "pending"},
                    {"id": "i2", "label": "Pipeline Status", "status": "pending"},
                    {"id": "i3", "label": "Retry Mechanism", "status": "pending"},
                ],
            },
        ],
        "fallback_phases": ["saturn", "datahub", "ingestion"],
        "rca": {
            "root_cause": "Vendor SFTP server timeout - upstream data source unavailable due to network partition",
            "confidence": 0.87,
            "causal_chain": [
                "Vendor SFTP server unresponsive (timeout after 900s)",
                'Feed "load_feed_alpha" failed to ingest data',
                "5 reports missing in Saturn: daily_pnl, risk_summary, exposure_report, var_calc, limit_check",
                "EOD batch reporting pipeline halted at DataHub stage",
                "SLA breach probability: 0.92 - escalation triggered",
            ],
        },
        "evidence": [
            {
                "id": "e1",
                "type": "tool_call",
                "content": "airflow_get_dag_run",
                "status": "failed",
                "details": "status: FAILED\nfailed_tasks: [load_feed_alpha]",
            },
            {
                "id": "e2",
                "type": "runbook",
                "content": "rb_ingest_sftp_timeout.md",
                "status": "success",
                "details": "Runbook: SFTP timeout recovery procedure\nSteps: 1-5 applicable",
            },
            {
                "id": "e3",
                "type": "similar_incident",
                "content": "INC-2026-05-10",
                "status": "success",
                "details": "Similar SFTP timeout incident\nResolution: Vendor failover triggered",
            },
        ],
        "next_actions": [
            {"id": "b1", "label": "Rerun Airflow", "action": "airflow_rerun", "category": "rerun"},
            {"id": "b2", "label": "Recompute snapshot", "action": "recompute_snapshot", "category": "recompute"},
            {"id": "b3", "label": "Notify vendor", "action": "notify_vendor", "category": "notify"},
            {"id": "b4", "label": "Check backup feed", "action": "check_backup_feed", "category": "investigate"},
        ],
    },
    "risk_calc_pipeline": {
        "id": "risk_calc_pipeline",
        "name": "Risk Calculation Pipeline",
        "nodes": [
            {
                "id": "saturn",
                "label": "Saturn",
                "status": "error",
                "description": "Report Level - Check calculations",
                "sub_steps": [
                    {"id": "s1", "label": "VaR Calculation Check", "status": "completed"},
                    {"id": "s2", "label": "Limit Check", "status": "error"},
                    {"id": "s3", "label": "Exposure Report", "status": "pending"},
                ],
            },
            {
                "id": "datahub",
                "label": "Data Hub",
                "status": "pending",
                "description": "Data Layer - Risk data sources",
                "sub_steps": [
                    {"id": "d1", "label": "Market Data Query", "status": "pending"},
                    {"id": "d2", "label": "Position Data", "status": "pending"},
                    {"id": "d3", "label": "Risk Factors", "status": "pending"},
                ],
            },
            {
                "id": "ingestion",
                "label": "Ingestion",
                "status": "pending",
                "description": "Ingestion Layer - Pipeline check",
                "sub_steps": [
                    {"id": "i1", "label": "Pipeline Health", "status": "pending"},
                    {"id": "i2", "label": "Data Quality", "status": "pending"},
                    {"id": "i3", "label": "Retry", "status": "pending"},
                ],
            },
        ],
        "rca": {
            "root_cause": "Position data feed stale - market data provider delayed by 45 minutes",
            "confidence": 0.82,
            "causal_chain": [
                "Market data provider experienced latency spike",
                "Position data feed 45 minutes stale",
                "VaR calculation using outdated positions",
                "Limit check triggered breach incorrectly",
                "Risk report generation halted",
            ],
        },
        "evidence": [],
        "next_actions": [],
    },
}

MOCK_INCIDENTS = {
    "INC-2026-07-20-001": {
        "id": "INC-2026-07-20-001",
        "title": "EOD Reporting Failure - Feed Load Timeout",
        "severity": "HIGH",
        "status": "investigating",
        "flow": "eod_reporting",
        "timestamp": "2026-07-20 21:01:00",
        "duration": "00:14:23",
        "description": "EOD batch job failed at 21:01 UTC. Feed 'load_feed_alpha' timed out after 900 seconds.",
        "triage_summary": "EOD reporting pipeline halted at Saturn stage. Feed load timeout in DataHub ingestion layer.",
    },
    "INC-2026-07-19-003": {
        "id": "INC-2026-07-19-003",
        "title": "Risk Calculation Pipeline Failure",
        "severity": "HIGH",
        "status": "investigating",
        "flow": "risk_calc_pipeline",
        "timestamp": "2026-07-19 14:30:00",
        "duration": "00:42:10",
        "description": "Risk calculation pipeline failed during VaR computation.",
        "triage_summary": "Suspected stale market data causing incorrect risk calculations.",
    },
    "INC-2026-07-18-007": {
        "id": "INC-2026-07-18-007",
        "title": "Market Data Feed Stale",
        "severity": "MEDIUM",
        "status": "resolved",
        "flow": "market_data_ingest",
        "timestamp": "2026-07-18 09:15:00",
        "duration": "01:23:45",
        "description": "Market data feed stale for 45 minutes.",
        "triage_summary": "Primary feed had connectivity issues. Failed over to backup.",
    },
}

# ─── SSE Event Generator ─────────────────────────────────────────────────────

async def generate_investigation_events(run_id: str):
    """Generate SSE events simulating the investigation workflow with 2s per step."""
    investigation = INVESTIGATIONS.get(run_id)
    if not investigation:
        yield f"event: error\ndata: {json.dumps({'error': 'Investigation not found'})}\n\n"
        return

    flow_id = investigation.get("flow", "eod_reporting")
    flow_def = FLOW_DEFINITIONS.get(flow_id, FLOW_DEFINITIONS["eod_reporting"])
    nodes = flow_def["nodes"]
    all_steps = []
    for node in nodes:
        for step in node["sub_steps"]:
            all_steps.append({"node_id": node["id"], "node_label": node["label"], **step})

    step_index = investigation.get("step_index", 0)
    all_steps = all_steps[step_index:]

    event_id = 1
    phase_order = ["saturn", "datahub", "ingestion"]

    for phase_idx, phase_id in enumerate(phase_order):
        phase_node = next((n for n in nodes if n["id"] == phase_id), None)
        if not phase_node:
            continue

        # Phase start event
        phase_event = {
            "type": "phase.start",
            "phase": phase_id,
            "phase_label": phase_node["label"],
            "phase_index": phase_idx + 1,
            "total_phases": len(phase_order),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        yield f"id: {event_id}\nevent: phase.start\ndata: {json.dumps(phase_event)}\n\n"
        event_id += 1
        await asyncio.sleep(2)

        # Execute sub-steps for this phase
        phase_steps = [s for s in all_steps if s["node_id"] == phase_id]
        for step in phase_steps:
            # Simulate step execution
            step_status = "completed" if random.random() > 0.15 else "error"
            step_event = {
                "type": "step.done",
                "step_id": step["id"],
                "step_label": step["label"],
                "phase": phase_id,
                "phase_label": phase_node["label"],
                "status": step_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"id: {event_id}\nevent: step.done\ndata: {json.dumps(step_event)}\n\n"
            event_id += 1
            investigation["step_index"] = investigation.get("step_index", 0) + 1
            await asyncio.sleep(2)

            # If step failed, mark entire phase as error and break flow
            if step_status == "error":
                fail_event = {
                    "type": "phase.failed",
                    "phase": phase_id,
                    "phase_label": phase_node["label"],
                    "failed_step": step["label"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"id: {event_id}\nevent: phase.failed\ndata: {json.dumps(fail_event)}\n\n"
                event_id += 1

                # Mark investigation as failed
                investigation["status"] = "failed"
                investigation["failed_at"] = phase_id
                investigation["failed_step"] = step["id"]

                # Send RCA ready with limited info
                rca_event = {
                    "type": "rca.ready",
                    "status": "partial",
                    "root_cause": f"Investigation halted at {phase_node['label']} - step '{step['label']}' failed",
                    "confidence": 0.65,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"id: {event_id}\nevent: rca.ready\ndata: {json.dumps(rca_event)}\n\n"
                event_id += 1
                return

        # Phase completed
        phase_done_event = {
            "type": "phase.completed",
            "phase": phase_id,
            "phase_label": phase_node["label"],
            "phase_index": phase_idx + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        yield f"id: {event_id}\nevent: phase.completed\ndata: {json.dumps(phase_done_event)}\n\n"
        event_id += 1

        # If there's a next phase, send transition
        if phase_idx < len(phase_order) - 1:
            next_phase = phase_order[phase_idx + 1]
            next_node = next((n for n in nodes if n["id"] == next_phase), None)
            transition_event = {
                "type": "phase.transition",
                "from": phase_id,
                "to": next_phase,
                "to_label": next_node["label"] if next_node else next_phase,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"id: {event_id}\nevent: phase.transition\ndata: {json.dumps(transition_event)}\n\n"
            event_id += 1

    # All phases completed successfully
    investigation["status"] = "completed"

    # Send plan ready
    plan_event = {
        "type": "plan.ready",
        "steps": len(all_steps),
        "phases": len(phase_order),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    yield f"id: {event_id}\nevent: plan.ready\ndata: {json.dumps(plan_event)}\n\n"
    event_id += 1

    # Send triage done
    triage_event = {
        "type": "triage.done",
        "incident_id": investigation["incident_id"],
        "summary": f"Investigation complete for {investigation['incident_id']}. All phases analyzed.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    yield f"id: {event_id}\nevent: triage.done\ndata: {json.dumps(triage_event)}\n\n"
    event_id += 1

    # Send RCA ready
    rca = flow_def.get("rca", {})
    rca_event = {
        "type": "rca.ready",
        "status": "complete",
        "root_cause": rca.get("root_cause", "No root cause identified"),
        "confidence": rca.get("confidence", 0.5),
        "causal_chain": rca.get("causal_chain", []),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    yield f"id: {event_id}\nevent: rca.ready\ndata: {json.dumps(rca_event)}\n\n"
    event_id += 1

    # Completion event
    complete_event = {
        "type": "investigation.complete",
        "run_id": run_id,
        "status": "completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    yield f"id: {event_id}\nevent: investigation.complete\ndata: {json.dumps(complete_event)}\n\n"


# ─── API Routes ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"service": "IncAnalyserAI API", "version": "0.1.0", "status": "operational"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/incidents")
async def start_investigation(request: InvestigationRequest):
    """Start a new incident investigation. Returns a run_id."""
    run_id = f"run-{uuid.uuid4().hex[:12]}"

    # Find matching flow
    flow_id = "eod_reporting"
    for key in FLOW_DEFINITIONS:
        if key in request.incident_id.lower() or key in (request.description or "").lower():
            flow_id = key
            break

    INVESTIGATIONS[run_id] = {
        "run_id": run_id,
        "incident_id": request.incident_id,
        "flow": flow_id,
        "status": "running",
        "step_index": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "run_id": run_id,
        "incident_id": request.incident_id,
        "flow": flow_id,
        "status": "running",
        "message": f"Investigation started for {request.incident_id}",
    }


@app.get("/incidents/{run_id}")
async def get_investigation_state(run_id: str):
    """Get the current state of an investigation (polling fallback)."""
    investigation = INVESTIGATIONS.get(run_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    flow_def = FLOW_DEFINITIONS.get(investigation.get("flow", "eod_reporting"), FLOW_DEFINITIONS["eod_reporting"])

    return {
        "run_id": run_id,
        "incident_id": investigation["incident_id"],
        "status": investigation["status"],
        "flow": investigation["flow"],
        "flow_definition": flow_def,
        "progress": calculate_progress(investigation, flow_def),
        "created_at": investigation["created_at"],
    }


@app.get("/incidents/{run_id}/stream")
async def stream_investigation(run_id: str):
    """SSE endpoint: streams live events as the investigation graph executes."""
    investigation = INVESTIGATIONS.get(run_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    return StreamingResponse(
        generate_investigation_events(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/incidents/{run_id}/feedback")
async def submit_feedback(run_id: str, feedback: FeedbackRequest):
    """Submit feedback for a specific step in the investigation."""
    investigation = INVESTIGATIONS.get(run_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    if "feedback" not in investigation:
        investigation["feedback"] = []

    investigation["feedback"].append({
        "step_id": feedback.step_id,
        "feedback": feedback.feedback,
        "comment": feedback.comment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "status": "ok",
        "message": f"Feedback recorded for step {feedback.step_id}",
        "total_feedback": len(investigation["feedback"]),
    }


@app.post("/incidents/{run_id}/approve")
async def approve_remediation(run_id: str, approval: ApproveRequest):
    """Approve the proposed remediation action."""
    investigation = INVESTIGATIONS.get(run_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    investigation["approved"] = {
        "approved": approval.approved,
        "comment": approval.comment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    status = "approved" if approval.approved else "rejected"
    return {
        "status": status,
        "message": f"Remediation {status} for investigation {run_id}",
    }


@app.get("/knowledge/flows/{flow_id}")
async def get_flow_definition(flow_id: str):
    """Get the flow diagram definition for a specific flow."""
    flow = FLOW_DEFINITIONS.get(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")

    return flow


@app.get("/incidents")
async def list_incidents():
    """List all known incidents (static mock data)."""
    return {
        "incidents": list(MOCK_INCIDENTS.values()),
        "total": len(MOCK_INCIDENTS),
    }


@app.get("/incidents/{run_id}/results")
async def get_investigation_results(run_id: str):
    """Get the full results of a completed investigation."""
    investigation = INVESTIGATIONS.get(run_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    flow_def = FLOW_DEFINITIONS.get(investigation.get("flow", "eod_reporting"), FLOW_DEFINITIONS["eod_reporting"])

    return {
        "run_id": run_id,
        "incident_id": investigation["incident_id"],
        "status": investigation["status"],
        "flow": flow_def,
        "rca": flow_def.get("rca", {}),
        "evidence": flow_def.get("evidence", []),
        "next_actions": flow_def.get("next_actions", []),
        "feedback": investigation.get("feedback", []),
        "approved": investigation.get("approved"),
    }


# ─── Helper Functions ────────────────────────────────────────────────────────

def calculate_progress(investigation: dict, flow_def: dict) -> dict:
    """Calculate the progress of an investigation."""
    total_steps = sum(len(n["sub_steps"]) for n in flow_def.get("nodes", []))
    completed_steps = investigation.get("step_index", 0)

    progress_pct = min(100.0, (completed_steps / max(total_steps, 1)) * 100)

    # Determine current phase
    current_phase = "saturn"
    for node in flow_def.get("nodes", []):
        if node["status"] == "active":
            current_phase = node["id"]
            break

    return {
        "percentage": round(progress_pct, 1),
        "completed_steps": completed_steps,
        "total_steps": total_steps,
        "current_phase": current_phase,
        "status": investigation.get("status", "running"),
    }


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

