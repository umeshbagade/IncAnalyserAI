"""
FastAPI layer for the ATOP incident-diagnosis prototype.

Endpoints:

    POST /incidents                    create an incident; runs the FULL
                                        investigation autonomously (triage ->
                                        planner -> specialists -> correlate).
                                        If a remediation is proposed, halts
                                        there for approval. Otherwise returns
                                        already resolved.
    GET  /incidents/{id}               current state/timeline
    POST /incidents/{id}/approve-remediation
                                        approve the proposed remediation
                                        action(s); executes them and resolves

Run with:
    uvicorn main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .models import Incident
from .orchestrator import build_graph, new_incident_state

app = FastAPI(title="ATOP Incident Diagnosis Orchestrator")

_graph = build_graph()


class CreateIncidentRequest(BaseModel):
    title: str
    description: str
    reported_by: str = "unknown"
    suspected_systems: list[str] = []


def _thread_config(incident_id: str) -> dict:
    return {"configurable": {"thread_id": incident_id}}


def _serialize_state(incident_id: str) -> dict:
    snapshot = _graph.get_state(_thread_config(incident_id))
    if not snapshot.values:
        raise HTTPException(status_code=404, detail=f"No incident found for id {incident_id}")
    values = snapshot.values
    return jsonable_encoder(
        {
            "incident": values.get("incident"),
            "status": values.get("status"),
            "triage": values.get("triage"),
            "runbook": values.get("runbook", []),
            "hypotheses": values.get("hypotheses", []),
            "evidence": values.get("evidence", []),
            "open_questions": values.get("open_questions", []),
            "findings": values.get("findings", []),
            "correlation": values.get("correlation"),
            "remediation_plan": values.get("remediation_plan"),
            "awaiting_remediation_approval": values.get("awaiting_remediation_approval", False),
            "current_action": values.get("current_action"),
            "audit_trail": values.get("audit_trail", []),
            "is_complete": len(snapshot.next) == 0,
        }
    )


@app.post("/incidents")
def create_incident(req: CreateIncidentRequest):
    incident = Incident(
        title=req.title,
        description=req.description,
        reported_by=req.reported_by,
        suspected_systems=req.suspected_systems,
    )
    config = _thread_config(incident.incident_id)
    initial_state = new_incident_state(incident)

    # Runs triage -> planner -> specialists -> correlate -> (maybe propose
    # remediation) autonomously. Only halts if a remediation is proposed.
    _graph.invoke(initial_state, config)

    return JSONResponse(_serialize_state(incident.incident_id))


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    return JSONResponse(_serialize_state(incident_id))


@app.post("/incidents/{incident_id}/approve-remediation")
def approve_remediation(incident_id: str):
    config = _thread_config(incident_id)
    snapshot = _graph.get_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail=f"No incident found for id {incident_id}")
    if not snapshot.next:
        raise HTTPException(status_code=400, detail="No remediation pending approval for this incident.")

    _graph.invoke(None, config)

    return JSONResponse(_serialize_state(incident_id))


@app.get("/health")
def health():
    return {"status": "ok"}
