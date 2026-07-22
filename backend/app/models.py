"""Pydantic models matching frontend TypeScript types exactly."""

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


class Incident(BaseModel):
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


class RootCause(BaseModel):
    rootCause: str = Field(alias="root_cause")
    confidence: float
    causalChain: list[str] = Field(alias="causal_chain", default_factory=list)

    class Config:
        populate_by_name = True


class BestNextAction(BaseModel):
    id: str
    label: str
    action: str
    category: str  # rerun | recompute | notify | investigate


class RCAResult(BaseModel):
    rootCause: str
    confidence: float
    causalChain: list[str] = Field(default_factory=list)


class FlowDefinition(BaseModel):
    id: str
    name: str
    nodes: list[FlowNode] = Field(default_factory=list)


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

