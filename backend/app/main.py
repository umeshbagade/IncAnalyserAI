"""
IncAnalyserAI Backend - FastAPI Application
Provides REST APIs for the incident analysis platform.
All data is persisted in MongoDB Atlas (single 'incidents' collection).
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .database import connect_to_mongo, close_mongo_connection, get_incidents_collection
from .seed import seed_database
from .enrich_data import enrich_missing_data
from .models import (
    IncidentSummary,
    IncidentDetail,
    FlowNode,
    FlowDefinition,
    Evidence,
    RootCauseResult,
    BestNextAction,
    LiveEvent,
    InvestigationRequest,
    EvidenceFeedbackRequest,
    RCAFeedbackRequest,
    ApproveRequest,
    CreateIncidentRequest,
)

# ─── App Setup ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="IncAnalyserAI API",
    description="Backend for AI-powered Production Incident Root Cause Analysis",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Startup / Shutdown Events ─────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Connect to MongoDB, seed data, and enrich missing fields on startup."""
    await connect_to_mongo()
    await seed_database()
    await enrich_missing_data()
    print("🚀 IncAnalyserAI Backend ready (MongoDB connected, seeded & enriched)")


@app.on_event("shutdown")
async def shutdown():
    """Close MongoDB connection on shutdown."""
    await close_mongo_connection()


# ─── API Routes ─────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "IncAnalyserAI API",
        "version": "0.2.0",
        "status": "operational",
        "storage": "MongoDB Atlas",
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
            "GET  /api/incidents/{inc_id}/dashboard",
            "POST /api/incidents/{inc_id}/feedback",
            "POST /api/incidents/{inc_id}/rca-feedback",
            "POST /api/incidents/{inc_id}/approve",
            "GET  /api/knowledge/flows",
            "GET  /api/knowledge/flows/{flow_id}",
            "GET  /api/stats",
        ],
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        collection = await get_incidents_collection()
        doc_count = await collection.count_documents({})
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "incident_count": doc_count,
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)},
        )


# ═══════════════════════════════════════════════════════════════════════════
#  INCIDENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents")
async def list_incidents():
    """
    GET /api/incidents
    Returns all incident summaries for the Home Dashboard.
    """
    collection = await get_incidents_collection()
    cursor = collection.find({}, {
        "id": 1, "title": 1, "severity": 1, "status": 1,
        "flowId": 1, "timestamp": 1, "duration": 1, "_id": 0
    }).sort("timestamp", -1)

    incidents = await cursor.to_list(length=100)

    summaries = []
    for inc in incidents:
        summaries.append({
            "id": inc.get("id", ""),
            "title": inc.get("title", ""),
            "severity": inc.get("severity", "LOW"),
            "status": inc.get("status", "open"),
            "flow": inc.get("flowId", "unknown"),
            "timestamp": inc.get("timestamp", ""),
            "duration": inc.get("duration", "00:00:00"),
        })

    return {
        "incidents": summaries,
        "total": len(summaries),
        "counts": {
            "total": len(summaries),
            "investigating": sum(1 for i in summaries if i["status"] == "investigating"),
            "resolved": sum(1 for i in summaries if i["status"] == "resolved"),
            "open": sum(1 for i in summaries if i["status"] == "open"),
            "high": sum(1 for i in summaries if i["severity"] == "HIGH"),
        },
    }


@app.post("/api/incidents")
async def create_incident(req: CreateIncidentRequest):
    """
    POST /api/incidents
    Dummy placeholder — creates a structured mock response without database interaction.
    Returns a fake incident summary as if the incident was created.
    """
    import uuid
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    inc_id = f"INC-{today}-{uuid.uuid4().hex[:4].upper()}"

    return {
        "status": "created",
        "incident": {
            "id": inc_id,
            "title": req.title,
            "severity": req.severity,
            "status": "open",
            "flow": req.flowId,
            "timestamp": today,
            "duration": "00:00:00",
        },
    }


@app.get("/api/incidents/{inc_id}")
async def get_incident(inc_id: str):
    """
    GET /api/incidents/{inc_id}
    Returns full incident details for the Incident Detail page.
    """
    collection = await get_incidents_collection()
    doc = await collection.find_one({"id": inc_id}, {"_id": 0})

    if not doc:
        raise HTTPException(status_code=404, detail=f"Incident '{inc_id}' not found")

    return {
        "id": doc.get("id", ""),
        "title": doc.get("title", ""),
        "severity": doc.get("severity", "LOW"),
        "status": doc.get("status", "open"),
        "flow": doc.get("flowId", "unknown"),
        "timestamp": doc.get("timestamp", ""),
        "duration": doc.get("duration", "00:00:00"),
        "originalText": doc.get("originalText", ""),
        "triageSummary": doc.get("triageSummary", ""),
        "entities": doc.get("entities", []),
        "timeline": doc.get("timeline", []),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  FLOW DAG ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents/{inc_id}/flow")
async def get_incident_flow(inc_id: str):
    """
    GET /api/incidents/{inc_id}/flow
    Returns the Flow DAG definition for the incident.
    """
    collection = await get_incidents_collection()
    doc = await collection.find_one({"id": inc_id}, {"_id": 0, "flow": 1})

    if not doc:
        raise HTTPException(status_code=404, detail=f"Incident '{inc_id}' not found")

    flow = doc.get("flow", {})
    return {
        "flowId": flow.get("id", ""),
        "flowName": flow.get("name", ""),
        "nodes": flow.get("nodes", []),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  RCA ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents/{inc_id}/rca")
async def get_incident_rca(inc_id: str):
    """
    GET /api/incidents/{inc_id}/rca
    Returns Root Cause Analysis result.
    """
    collection = await get_incidents_collection()
    doc = await collection.find_one({"id": inc_id}, {"_id": 0, "flow.rca": 1})

    if not doc:
        raise HTTPException(status_code=404, detail=f"Incident '{inc_id}' not found")

    rca = doc.get("flow", {}).get("rca", {})
    return {
        "rootCause": rca.get("rootCause", "No root cause identified"),
        "confidence": rca.get("confidence", 0.5),
        "causalChain": rca.get("causalChain", []),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  BEST NEXT ACTIONS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents/{inc_id}/actions")
async def get_incident_actions(inc_id: str):
    """
    GET /api/incidents/{inc_id}/actions
    Returns Best Next Actions for the incident.
    """
    collection = await get_incidents_collection()
    doc = await collection.find_one({"id": inc_id}, {"_id": 0, "flow.nextActions": 1})

    if not doc:
        raise HTTPException(status_code=404, detail=f"Incident '{inc_id}' not found")

    actions = doc.get("flow", {}).get("nextActions", [])
    return {"actions": actions}


# ═══════════════════════════════════════════════════════════════════════════
#  EVIDENCE ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents/{inc_id}/evidence")
async def get_incident_evidence(
    inc_id: str,
    node_id: Optional[str] = Query(None, description="Filter evidence by flow node ID"),
):
    """
    GET /api/incidents/{inc_id}/evidence?node_id=saturn
    Returns evidence/citations for the incident, optionally filtered by node.
    """
    collection = await get_incidents_collection()
    doc = await collection.find_one({"id": inc_id}, {"_id": 0, "flow.evidence": 1})

    if not doc:
        raise HTTPException(status_code=404, detail=f"Incident '{inc_id}' not found")

    all_evidence = doc.get("flow", {}).get("evidence", [])

    if node_id:
        # Filter evidence by node_id (nodes in evidence have node_id field)
        filtered = [e for e in all_evidence if e.get("node_id") == node_id]
        return {"node_id": node_id, "evidence": filtered, "total": len(filtered)}
    else:
        return {"evidence": all_evidence, "total": len(all_evidence)}


# ═══════════════════════════════════════════════════════════════════════════
#  LIVE EVENTS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents/{inc_id}/events")
async def get_incident_events(inc_id: str):
    """
    GET /api/incidents/{inc_id}/events
    Returns live investigation events for the incident.
    """
    # Events are generated dynamically; for now return a default set
    # In future, this will pull from an investigation session
    return {
        "events": [
            {"timestamp": "00:00:00", "message": "Investigation initialized", "type": "info"},
        ],
        "connected": True,
        "count": 1,
        "streaming": True,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  FEEDBACK ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

FEEDBACK_STORE: dict[str, list] = {}
APPROVAL_STORE: dict[str, dict] = {}


@app.post("/api/incidents/{inc_id}/feedback")
async def submit_evidence_feedback(inc_id: str, feedback_req: EvidenceFeedbackRequest):
    """
    POST /api/incidents/{inc_id}/feedback
    Submit feedback for an evidence item (thumbs up/down).
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


@app.post("/api/incidents/{inc_id}/rca-feedback")
async def submit_rca_feedback(inc_id: str, feedback_req: RCAFeedbackRequest):
    """
    POST /api/incidents/{inc_id}/rca-feedback
    Submit feedback for the RCA result.
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


@app.post("/api/incidents/{inc_id}/approve")
async def approve_remediation(inc_id: str, approval_req: ApproveRequest):
    """
    POST /api/incidents/{inc_id}/approve
    Approve or reject a proposed remediation action.
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
#  DASHBOARD AGGREGATED ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/incidents/{inc_id}/dashboard")
async def get_incident_dashboard(inc_id: str):
    """
    GET /api/incidents/{inc_id}/dashboard
    Aggregated endpoint returning all data for the Incident Detail page.
    """
    collection = await get_incidents_collection()
    doc = await collection.find_one({"id": inc_id}, {"_id": 0})

    if not doc:
        raise HTTPException(status_code=404, detail=f"Incident '{inc_id}' not found")

    flow = doc.get("flow", {})

    # Build incident detail
    incident = {
        "id": doc.get("id", ""),
        "title": doc.get("title", ""),
        "severity": doc.get("severity", "LOW"),
        "status": doc.get("status", "open"),
        "flow": doc.get("flowId", "unknown"),
        "timestamp": doc.get("timestamp", ""),
        "duration": doc.get("duration", "00:00:00"),
        "originalText": doc.get("originalText", ""),
        "triageSummary": doc.get("triageSummary", ""),
        "entities": doc.get("entities", []),
        "timeline": doc.get("timeline", []),
    }

    # Flow definition
    flow_data = {
        "flowId": flow.get("id", ""),
        "flowName": flow.get("name", ""),
        "nodes": flow.get("nodes", []),
    } if flow else None

    # RCA
    rca = flow.get("rca", {})
    rca_result = {
        "rootCause": rca.get("rootCause", "No root cause identified"),
        "confidence": rca.get("confidence", 0.5),
        "causalChain": rca.get("causalChain", []),
    }

    # Actions
    actions = flow.get("nextActions", [])

    # Evidence
    evidence = flow.get("evidence", [])

    # Events
    events = [
        {"timestamp": "00:00:00", "message": "Investigation initialized", "type": "info"},
    ]

    return {
        "incident": incident,
        "flow": flow_data,
        "rca": rca_result,
        "actions": actions,
        "evidence": evidence,
        "events": events,
        "analysis_id": f"{inc_id}-{uuid.uuid4().hex[:8]}",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  KNOWLEDGE / FLOW DEFINITIONS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/knowledge/flows")
async def list_flow_definitions():
    """List all available flow definitions by inspecting incidents collection."""
    collection = await get_incidents_collection()
    pipeline = [
        {"$group": {"_id": "$flowId", "name": {"$first": "$flow.name"}}},
        {"$project": {"_id": 0, "flowId": "$_id", "name": 1}},
    ]
    cursor = collection.aggregate(pipeline)
    flows = await cursor.to_list(length=100)

    return {
        "flows": [{"id": f["flowId"], "name": f.get("name", f["flowId"])} for f in flows],
        "total": len(flows),
    }


@app.get("/api/knowledge/flows/{flow_id}")
async def get_flow_definition(flow_id: str):
    """
    GET /api/knowledge/flows/{flow_id}
    Get a specific flow diagram definition.
    """
    collection = await get_incidents_collection()
    doc = await collection.find_one(
        {"flow.id": flow_id},
        {"_id": 0, "flow": 1}
    )

    if not doc:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")

    return doc["flow"]


# ═══════════════════════════════════════════════════════════════════════════
#  STATS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/stats")
async def get_dashboard_stats():
    """
    GET /api/stats
    Returns aggregated statistics for the Home Dashboard.
    """
    collection = await get_incidents_collection()
    all_incidents = await collection.find(
        {},
        {"_id": 0, "status": 1, "severity": 1}
    ).to_list(length=100)

    total = len(all_incidents)
    investigating = sum(1 for i in all_incidents if i.get("status") == "investigating")
    resolved = sum(1 for i in all_incidents if i.get("status") == "resolved")
    open_inc = sum(1 for i in all_incidents if i.get("status") == "open")
    high = sum(1 for i in all_incidents if i.get("severity") == "HIGH")

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
    print("🗄️  Storage: MongoDB Atlas")
    uvicorn.run(app, host="0.0.0.0", port=8000)

