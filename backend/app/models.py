"""Pydantic models matching frontend TypeScript types exactly.
Includes MongoDB document model for the single 'incidents' collection."""

from typing import Optional
from pydantic import BaseModel, Field


class Entity(BaseModel):
    name: str
    type: str
    confidence: float


class TimelineEvent(BaseModel):
    time: str
    event: str
    type: str  # info | warning | error | success


class SubStep(BaseModel):
    id: str
    label: str
    status: str  # pending | active | completed | error | skipped


class FlowNode(BaseModel):
    id: str
    label: str
    status: str  # pending | active | completed | error | skipped
    description: str
    subSteps: list[SubStep] = Field(default_factory=list)


class IncidentSummary(BaseModel):
    id: str
    title: str
    severity: str  # HIGH | MEDIUM | LOW
    status: str    # open | investigating | resolved
    flow: str
    timestamp: str
    duration: str


class IncidentDetail(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    flow: str
    timestamp: str
    duration: str
    originalText: str
    triageSummary: str
    entities: list[Entity] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)


class LiveEvent(BaseModel):
    timestamp: str
    message: str
    type: str  # triage | plan | step | rca | info | error


class Evidence(BaseModel):
    id: str
    type: str   # tool_call | runbook | similar_incident
    content: str
    status: str  # success | failed | warning
    details: str
    feedback: Optional[str] = None  # useful | wrong


class RootCauseResult(BaseModel):
    rootCause: str
    confidence: float
    causalChain: list[str] = Field(default_factory=list)


class BestNextAction(BaseModel):
    id: str
    label: str
    action: str
    category: str  # rerun | recompute | notify | investigate


class FlowDefinition(BaseModel):
    id: str
    name: str
    nodes: list[FlowNode] = Field(default_factory=list)


class FlowEmbedded(BaseModel):
    """Embedded flow definition inside an incident document."""
    id: str
    name: str
    nodes: list[FlowNode] = Field(default_factory=list)
    rca: RootCauseResult = Field(default_factory=lambda: RootCauseResult(rootCause="", confidence=0.0, causalChain=[]))
    evidence: list[Evidence] = Field(default_factory=list)
    nextActions: list[BestNextAction] = Field(default_factory=list)


class InvestigationState(BaseModel):
    """Investigation session state embedded inside incident document."""
    runId: Optional[str] = None
    status: str = "idle"  # idle | running | completed | failed
    stepIndex: int = 0
    currentPhase: Optional[str] = None
    feedback: list[dict] = Field(default_factory=list)
    approved: Optional[dict] = None
    createdAt: Optional[str] = None


class IncidentDocument(BaseModel):
    """
    Full MongoDB document schema for the single 'incidents' collection.
    Combines incident details + embedded flow + investigation state.
    """
    id: str
    title: str
    severity: str
    status: str
    flowId: str
    timestamp: str
    duration: str
    description: str = ""
    originalText: str = ""
    triageSummary: str = ""
    entities: list[Entity] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    flow: FlowEmbedded = Field(default_factory=FlowEmbedded)
    investigation: InvestigationState = Field(default_factory=InvestigationState)
    createdAt: str = ""
    updatedAt: str = ""


# ─── Request Models ─────────────────────────────────────────────────────

class InvestigationRequest(BaseModel):
    incident_id: str
    description: Optional[str] = None


class EvidenceFeedbackRequest(BaseModel):
    evidence_id: str
    feedback: str  # useful | wrong


class RCAFeedbackRequest(BaseModel):
    feedback: str  # useful | not_useful
    comment: Optional[str] = None


class ApproveRequest(BaseModel):
    approved: bool = True
    comment: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """Request body for the /api/analyze endpoint."""
    description: str
    top_k: int = Field(default=5, ge=1, le=20, description="Number of vector DB results")

