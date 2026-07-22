"""
IncAnalyserAI Backend - FastAPI Application
Fully in sync with frontend UI (Next.js + TypeScript types).
All mock data matches frontend/mockData.ts exactly.

API Endpoints (10 total):
  1. GET  /                           - Service info
  2. GET  /health                     - Health check
  3. GET  /api/incidents              - List incident summaries (for Home Dashboard)
  4. GET  /api/incidents/{inc_id}     - Full incident details (for Incident Page)
  5. GET  /api/incidents/{inc_id}/flow       - Flow DAG definition
  6. GET  /api/incidents/{inc_id}/rca        - RCA result
  7. GET  /api/incidents/{inc_id}/actions    - Best next actions
  8. GET  /api/incidents/{inc_id}/evidence   - Evidence for a specific flow node
  9. GET  /api/incidents/{inc_id}/events     - Live events
  10. POST /api/incidents/{inc_id}/feedback   - Submit evidence feedback
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import (
    IncidentSummary,
    Incident,
    FlowNode,
    FlowDefinition,
    Evidence,
    RCAResult,
    BestNextAction,
    LiveEvent,
    InvestigationRequest,
    EvidenceFeedbackRequest,
    RCAFeedbackRequest,
    ApproveRequest,
)
from .data import (
    INCIDENT_SUMMARIES,
    INCIDENTS,
    FLOW_DEFINITIONS,
    EVIDENCE_BY_FLOW,
    RCA_RESULTS,
    BEST_NEXT_ACTIONS,
    LIVE_EVENTS,
    get_flow_for_incident,
    get_default_rca,
    get_default_actions,
)

# ─── App Setup ──────────────────────────────────────────────────────────────

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

# In-memory store for feedback
FEEDBACK_STORE: dict[str, list] = {}
APPROVAL_STORE: dict[str, dict] = {}

# ─── API Routes ─────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "IncAnalyserAI API",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": [
            "GET  /",
            "GET  /health",
            "GET  /api/incidents",
            "GET  /api/incidents/{inc_id}",
            "GET  /api/incidents/{inc_id}/flow",
            "GET  /api/incidents/{inc_id}/rca",
            "GET  /api/incidents/{inc_id}/actions",
            "GET  /api/incidents/{inc_id}/evidence",
            "GET  /api/incidents/{inc_id}/events",
            "POST /api/incidents/{inc_id}/feedback",
        ],
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  INCIDENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents", response_model=dict)
async def list_incidents():
    """
    GET /api/incidents
    Returns all incident summaries for the Home Dashboard page.
    Matches mockIncidentSummaries in frontend/src/data/mockData.ts
    """
    return {
        "incidents": INCIDENT_SUMMARIES,
        "total": len(INCIDENT_SUMMARIES),
        "counts": {
            "total": len(INCIDENT_SUMMARIES),
            "investigating": sum(1 for i in INCIDENT_SUMMARIES if i["status"] == "investigating"),
            "resolved": sum(1 for i in INCIDENT_SUMMARIES if i["status"] == "resolved"),
            "open": sum(1 for i in INCIDENT_SUMMARIES if i["status"] == "open"),
            "high": sum(1 for i in INCIDENT_SUMMARIES if i["severity"] == "HIGH"),
        },
    }


@app.get("/api/incidents/{inc_id}", response_model=dict)
async def get_incident(inc_id: str):
    """
    GET /api/incidents/{inc_id}
    Returns full incident details for the Incident Detail page.
    Matches mockIncident in frontend/src/data/mockData.ts
    Returns:
      - id, title, severity, status, flow, timestamp, duration
      - originalText, triageSummary
      - entities: [{name, type, confidence}]
      - timeline: [{time, event, type}]
    """
    incident = INCIDENTS.get(inc_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{inc_id}' not found")

    return incident


# ═══════════════════════════════════════════════════════════════════════════
#  FLOW DAG ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents/{inc_id}/flow", response_model=dict)
async def get_incident_flow(inc_id: str):
    """
    GET /api/incidents/{inc_id}/flow
    Returns the Flow DAG definition for the incident.
    Used by FlowDAG component.
    Matches flowDefinitions in frontend/src/data/mockData.ts
    Returns: { flowId, flowName, nodes: [FlowNode] }
    """
    flow_id = get_flow_for_incident(inc_id)
    flow_def = FLOW_DEFINITIONS.get(flow_id)

    if not flow_def:
        raise HTTPException(status_code=404, detail=f"Flow definition not found for incident '{inc_id}'")

    return {
        "flowId": flow_def["id"],
        "flowName": flow_def["name"],
        "nodes": flow_def["nodes"],
    }


# ═══════════════════════════════════════════════════════════════════════════
#  RCA ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents/{inc_id}/rca", response_model=dict)
async def get_incident_rca(inc_id: str):
    """
    GET /api/incidents/{inc_id}/rca
    Returns Root Cause Analysis result.
    Used by RCAPanel component.
    Matches mockRCAResult in frontend/src/data/mockData.ts
    Returns: { rootCause, confidence, causalChain: [string] }
    """
    flow_id = get_flow_for_incident(inc_id)
    rca = RCA_RESULTS.get(flow_id, get_default_rca())
    return {
        "rootCause": rca["rootCause"],
        "confidence": rca["confidence"],
        "causalChain": rca["causalChain"],
    }


# ═══════════════════════════════════════════════════════════════════════════
#  BEST NEXT ACTIONS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents/{inc_id}/actions", response_model=dict)
async def get_incident_actions(inc_id: str):
    """
    GET /api/incidents/{inc_id}/actions
    Returns Best Next Actions for the incident.
    Used by RCAPanel component.
    Matches mockBestNextActions in frontend/src/data/mockData.ts
    Returns: { actions: [{id, label, action, category}] }
    """
    flow_id = get_flow_for_incident(inc_id)
    actions = BEST_NEXT_ACTIONS.get(flow_id, get_default_actions())
    return {"actions": actions}


# ═══════════════════════════════════════════════════════════════════════════
#  EVIDENCE ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents/{inc_id}/evidence", response_model=dict)
async def get_incident_evidence(
    inc_id: str,
    node_id: Optional[str] = Query(None, description="Filter evidence by flow node ID"),
):
    """
    GET /api/incidents/{inc_id}/evidence?node_id=saturn
    Returns evidence/citations for the incident, optionally filtered by node.
    Used by EvidencePanel component.
    Matches mockEvidence in frontend/src/data/mockData.ts
    Returns: { evidence: [{id, type, content, status, details, feedback?}] }
    """
    flow_id = get_flow_for_incident(inc_id)
    flow_evidence = EVIDENCE_BY_FLOW.get(flow_id, {})

    if node_id:
        # Return evidence for a specific flow node
        node_evidence = flow_evidence.get(node_id, [])
        return {"node_id": node_id, "evidence": node_evidence, "total": len(node_evidence)}
    else:
        # Return all evidence grouped by node
        all_evidence = []
        for nid, ev_list in flow_evidence.items():
            for ev in ev_list:
                all_evidence.append({**ev, "node_id": nid})
        return {"evidence": all_evidence, "total": len(all_evidence)}


# ═══════════════════════════════════════════════════════════════════════════
#  LIVE EVENTS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents/{inc_id}/events", response_model=dict)
async def get_incident_events(inc_id: str):
    """
    GET /api/incidents/{inc_id}/events
    Returns live investigation events for the incident.
    Used by LiveEventStream component.
    Matches mockLiveEvents in frontend/src/data/mockData.ts
    Returns: { events: [{timestamp, message, type}], connected: bool, count: int }
    """
    flow_id = get_flow_for_incident(inc_id)
    events = LIVE_EVENTS.get(flow_id, [])
    return {
        "events": events,
        "connected": True,
        "count": len(events),
        "streaming": True,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  FEEDBACK ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/incidents/{inc_id}/feedback", response_model=dict)
async def submit_evidence_feedback(inc_id: str, feedback_req: EvidenceFeedbackRequest):
    """
    POST /api/incidents/{inc_id}/feedback
    Submit feedback for an evidence item (thumbs up/down).
    Used by EvidencePanel component (onFeedback callback).
    Body: { evidence_id: string, feedback: "useful" | "wrong" }
    """
    if inc_id not in FEEDBACK_STORE:
        FEEDBACK_STORE[inc_id] = []

    FEEDBACK_STORE[inc_id].append({
        "evidence_id": feedback_req.evidence_id,
        "feedback": feedback_req.feedback,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "status": "ok",
        "message": f"Feedback '{feedback_req.feedback}' recorded for evidence '{feedback_req.evidence_id}'",
        "total_feedback": len(FEEDBACK_STORE[inc_id]),
    }


@app.post("/api/incidents/{inc_id}/rca-feedback", response_model=dict)
async def submit_rca_feedback(inc_id: str, feedback_req: RCAFeedbackRequest):
    """
    POST /api/incidents/{inc_id}/rca-feedback
    Submit feedback for the RCA result (Was this helpful?).
    Used by RCAPanel component.
    Body: { feedback: "useful" | "not_useful", comment?: string }
    """
    key = f"{inc_id}_rca"
    if key not in FEEDBACK_STORE:
        FEEDBACK_STORE[key] = []

    FEEDBACK_STORE[key].append({
        "feedback": feedback_req.feedback,
        "comment": feedback_req.comment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "status": "ok",
        "message": f"RCA feedback '{feedback_req.feedback}' recorded",
        "total_feedback": len(FEEDBACK_STORE[key]),
    }


@app.post("/api/incidents/{inc_id}/approve", response_model=dict)
async def approve_remediation(inc_id: str, approval_req: ApproveRequest):
    """
    POST /api/incidents/{inc_id}/approve
    Approve or reject a proposed remediation action.
    Body: { approved: bool, comment?: string }
    """
    APPROVAL_STORE[inc_id] = {
        "approved": approval_req.approved,
        "comment": approval_req.comment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    status = "approved" if approval_req.approved else "rejected"
    return {
        "status": status,
        "message": f"Remediation {status} for incident '{inc_id}'",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  KNOWLEDGE / FLOW DEFINITIONS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/knowledge/flows", response_model=dict)
async def list_flow_definitions():
    """List all available flow definitions."""
    return {
        "flows": [
            {"id": fid, "name": fdef["name"]}
            for fid, fdef in FLOW_DEFINITIONS.items()
        ],
        "total": len(FLOW_DEFINITIONS),
    }


@app.get("/api/knowledge/flows/{flow_id}", response_model=dict)
async def get_flow_definition(flow_id: str):
    """
    GET /api/knowledge/flows/{flow_id}
    Get a specific flow diagram definition.
    Used for Knowledge Base / flow browsing.
    """
    flow = FLOW_DEFINITIONS.get(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")
    return flow


# ═══════════════════════════════════════════════════════════════════════════
#  QUICK ACTIONS ENDPOINT (for Home Dashboard quick-action cards)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents/{inc_id}/dashboard", response_model=dict)
async def get_incident_dashboard(inc_id: str):
    """
    GET /api/incidents/{inc_id}/dashboard
    Aggregated endpoint returning all data needed for the Incident Detail page
    in a single call (flow, rca, actions, evidence, events).
    """
    flow_id = get_flow_for_incident(inc_id)

    # Get incident
    incident = INCIDENTS.get(inc_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{inc_id}' not found")

    # Get flow definition
    flow_def = FLOW_DEFINITIONS.get(flow_id)
    flow_data = {"flowId": flow_def["id"], "flowName": flow_def["name"], "nodes": flow_def["nodes"]} if flow_def else None

    # Get RCA
    rca = RCA_RESULTS.get(flow_id, get_default_rca())

    # Get actions
    actions = BEST_NEXT_ACTIONS.get(flow_id, get_default_actions())

    # Get evidence (all nodes)
    all_evidence = []
    flow_evidence = EVIDENCE_BY_FLOW.get(flow_id, {})
    for nid, ev_list in flow_evidence.items():
        for ev in ev_list:
            all_evidence.append({**ev, "node_id": nid})

    # Get events
    events = LIVE_EVENTS.get(flow_id, [])

    return {
        "incident": incident,
        "flow": flow_data,
        "rca": rca,
        "actions": actions,
        "evidence": all_evidence,
        "events": events,
        "analysis_id": f"{inc_id}-{uuid.uuid4().hex[:8]}",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  STATS ENDPOINT (for Home Dashboard stats bar)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/stats", response_model=dict)
async def get_dashboard_stats():
    """
    GET /api/stats
    Returns aggregated statistics for the Home Dashboard.
    Used by HomePage stats bar and filters.
    """
    total = len(INCIDENT_SUMMARIES)
    investigating = sum(1 for i in INCIDENT_SUMMARIES if i["status"] == "investigating")
    resolved = sum(1 for i in INCIDENT_SUMMARIES if i["status"] == "resolved")
    open_inc = sum(1 for i in INCIDENT_SUMMARIES if i["status"] == "open")
    high = sum(1 for i in INCIDENT_SUMMARIES if i["severity"] == "HIGH")

    return {
        "total": total,
        "investigating": investigating,
        "resolved": resolved,
        "open": open_inc,
        "high": high,
        "system_status": "operational",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  RUN COMMAND
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("🚀 IncAnalyserAI Backend starting on http://0.0.0.0:8000")
    print("📡 API Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)

