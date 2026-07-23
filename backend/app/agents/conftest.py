from __future__ import annotations

import pytest

from app.agents import llm_client
from app.agents.models import (
    CorrelationResult,
    CausalEvent,
    Finding,
    FindingStatus,
    PlanStep,
    RemediationAction,
    RemediationPlan,
    RunbookPlan,
    Severity,
    TriageResult,
)


def fake_call_llm_structured(system_prompt, user_prompt, response_model, temperature=0.1):
    if response_model is TriageResult:
        return TriageResult(
            impacted_business_flow="checkout",
            severity=Severity.SEV2,
            entry_point_service="payment-svc",
            symptoms=["elevated payment failure rate", "checkout errors reported by users"],
            confidence=0.8,
            rationale="Payment errors reported across multiple orders in the last hour.",
        )

    if response_model is RunbookPlan:
        return RunbookPlan(
            entry_step_id="s1",
            steps=[
                PlanStep(
                    step_id="s1", system="payment-svc", action="Pull error logs for failed auths, last 2h",
                    rationale="Symptom reported here first", assigned_agent="payment-svc_specialist",
                    on_anomaly="s2", on_clean=None,
                ),
                PlanStep(
                    step_id="s2", system="order-svc", action="Check order state transitions",
                    rationale="Upstream caller of payment-svc", assigned_agent="order-svc_specialist",
                    on_anomaly=None, on_clean=None,
                ),
            ],
            planning_rationale="Start at the reported symptom; if anomalous, check the upstream caller.",
        )

    if response_model is Finding:
        # payment-svc step has "failed auths" in the action text -> anomaly branch
        if "failed auths" in user_prompt:
            return Finding(
                step_id="", system="", status=FindingStatus.ANOMALY,
                anomalies=["auth timeout rate spiked to 40% at 10:03"],
                evidence_refs=["log query: 214 auth timeout errors in window"],
                suggested_next=["check order-svc for retry storms"],
            )
        return Finding(
            step_id="", system="", status=FindingStatus.NORMAL,
            anomalies=[], evidence_refs=["log query: 0 anomalous transitions"], suggested_next=[],
        )

    if response_model is CorrelationResult:
        return CorrelationResult(
            timeline=[
                CausalEvent(system="payment-svc", description="auth timeout rate spiked", sequence_order=0, likely_root_cause=True),
            ],
            root_cause_system="payment-svc",
            root_cause_summary="Payment service auth timeouts are the root cause; order service checked clean.",
            remediation_needed=True,
        )

    if response_model is RemediationPlan:
        return RemediationPlan(
            actions=[
                RemediationAction(
                    action_id="rem-1",
                    description="Restart payment-svc worker pool to clear stuck auth connections",
                    target_system="payment-svc",
                    mcp_tool="restart_service",
                    risk_level="medium",
                )
            ],
            rationale="Auth timeout spike is consistent with a stuck connection pool; a restart is a safe first remediation.",
        )

    raise AssertionError(f"fake_call_llm_structured got an unexpected response_model: {response_model}")


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    monkeypatch.setattr(llm_client, "call_llm_structured", fake_call_llm_structured)
