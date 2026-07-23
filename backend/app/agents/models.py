"""
Shared data models for the ATOP incident-diagnosis agent system.

Six agents, one shared contract:
  Supervisor -> Triage -> Planner -> Specialist(s) -> Correlator -> Remediation

The `IncidentGraphState` TypedDict IS the "typed Investigation State" the
Supervisor maintains: hypotheses[], evidence[], open_questions[],
next_actions[], plus everything else every agent reads/writes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, TypedDict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


class IncidentStatus(str, Enum):
    NEW = "NEW"
    TRIAGING = "TRIAGING"
    PLANNING = "PLANNING"
    INVESTIGATING = "INVESTIGATING"
    CORRELATING = "CORRELATING"
    AWAITING_REMEDIATION_APPROVAL = "AWAITING_REMEDIATION_APPROVAL"
    REMEDIATING = "REMEDIATING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class RunbookStepStatus(str, Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    SKIPPED = "SKIPPED"


class FindingStatus(str, Enum):
    NORMAL = "NORMAL"          # nothing anomalous found at this system
    ANOMALY = "ANOMALY"        # something concrete and suspicious found
    INCONCLUSIVE = "INCONCLUSIVE"  # tool/data didn't give a clear answer


class HypothesisStatus(str, Enum):
    OPEN = "OPEN"
    CONFIRMED = "CONFIRMED"
    RULED_OUT = "RULED_OUT"


class ActorType(str, Enum):
    ORCHESTRATOR = "ORCHESTRATOR"
    TRIAGE_AGENT = "TRIAGE_AGENT"
    PLANNER_AGENT = "PLANNER_AGENT"
    SPECIALIST_AGENT = "SPECIALIST_AGENT"
    CORRELATOR_AGENT = "CORRELATOR_AGENT"
    REMEDIATION_AGENT = "REMEDIATION_AGENT"
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"


# ---------------------------------------------------------------------------
# Core domain objects
# ---------------------------------------------------------------------------

class SystemRef(BaseModel):
    system_id: str
    name: str
    description: str = ""


class Incident(BaseModel):
    incident_id: str = Field(default_factory=lambda: f"INC-{uuid.uuid4().hex[:8].upper()}")
    title: str
    description: str
    reported_by: str = "unknown"
    reported_at: datetime = Field(default_factory=datetime.utcnow)
    suspected_systems: List[str] = Field(default_factory=list)


# --- 4.2 Triage --------------------------------------------------------

class TriageResult(BaseModel):
    """Structured output the Triage agent must produce."""
    impacted_business_flow: str = Field(..., description="e.g. 'checkout', 'order fulfillment'")
    severity: Severity
    entry_point_service: str = Field(..., description="system_id where the symptom was first observed/reported")
    symptoms: List[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    similar_past_incidents: List[str] = Field(
        default_factory=list, description="ids/summaries of similar incidents found via RAG, if any"
    )


# --- 4.3 Planner (DAG runbook) ------------------------------------------

class PlanStep(BaseModel):
    """
    One node in the investigation DAG. Branching is explicit: after this
    step's specialist reports a Finding, the Supervisor follows on_anomaly
    or on_clean to pick the next node — this is the "check X -> if Y then
    check Z, else check W" structure, not just a flat ordered list.
    """
    step_id: str
    system: str  # system_id
    action: str
    rationale: str
    assigned_agent: str  # f"{system}_specialist"
    on_anomaly: Optional[str] = None  # next step_id if FindingStatus.ANOMALY
    on_clean: Optional[str] = None    # next step_id if FindingStatus.NORMAL
    status: RunbookStepStatus = RunbookStepStatus.PENDING


class RunbookPlan(BaseModel):
    """Structured output the Planner agent must produce."""
    entry_step_id: str
    steps: List[PlanStep]
    planning_rationale: str


# --- 4.4 Specialist findings --------------------------------------------

class Finding(BaseModel):
    """Structured output every Specialist agent must produce — no prose."""
    step_id: str = ""
    system: str = ""
    status: FindingStatus
    anomalies: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    suggested_next: List[str] = Field(default_factory=list)


# --- Supervisor's typed Investigation State pieces ----------------------

class Hypothesis(BaseModel):
    hypothesis_id: str
    statement: str
    system: str
    status: HypothesisStatus = HypothesisStatus.OPEN
    confidence: float = 0.5


class EvidenceItem(BaseModel):
    evidence_id: str
    system: str
    step_id: str
    description: str
    source: str  # e.g. "log_query", "metric_query", "diagnostic_script"


class OpenQuestion(BaseModel):
    question_id: str
    text: str
    system: Optional[str] = None


class NextActionItem(BaseModel):
    action_id: str
    description: str
    target_agent: str


# --- 4.5 Correlator ------------------------------------------------------

class CausalEvent(BaseModel):
    system: str
    description: str
    sequence_order: int  # lower = happened earlier in the causal chain
    likely_root_cause: bool = False


class CorrelationResult(BaseModel):
    """Structured output the Correlator agent must produce."""
    timeline: List[CausalEvent]
    root_cause_system: Optional[str]
    root_cause_summary: str
    remediation_needed: bool


# --- 4.6 Remediation (guarded) -------------------------------------------

class RemediationAction(BaseModel):
    action_id: str
    description: str
    target_system: str
    mcp_tool: str  # which MCP-exposed tool would execute this
    risk_level: str  # "low" | "medium" | "high"
    requires_approval: bool = True
    status: str = "PROPOSED"  # PROPOSED -> APPROVED -> EXECUTED / REJECTED


class RemediationPlan(BaseModel):
    """Structured output the Remediation agent must produce."""
    actions: List[RemediationAction]
    rationale: str


class AuditEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: ActorType
    event_type: str
    detail: str


class CurrentAction(BaseModel):
    """What the dashboard shows as 'what's happening now'."""
    summary: str
    action_type: str
    target_step_id: Optional[str] = None
    requires_approval: bool = False


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------

class IncidentGraphState(TypedDict, total=False):
    incident: Incident
    status: IncidentStatus

    triage: Optional[TriageResult]

    runbook: List[PlanStep]
    entry_step_id: Optional[str]
    current_step_id: Optional[str]

    # Supervisor's typed Investigation State
    hypotheses: List[Hypothesis]
    evidence: List[EvidenceItem]
    open_questions: List[OpenQuestion]
    next_actions: List[NextActionItem]

    findings: List[Finding]

    correlation: Optional[CorrelationResult]
    remediation_plan: Optional[RemediationPlan]
    awaiting_remediation_approval: bool

    current_action: Optional[CurrentAction]
    audit_trail: List[AuditEvent]
