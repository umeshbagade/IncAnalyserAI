"""
LLM Client — wraps Azure OpenAI for structured LLM calls.

Environment variables (loaded from .env):
    AZURE_OPENAI_ENDPOINT      e.g. https://<resource>.openai.azure.com/
    AZURE_OPENAI_API_KEY       your API key
    AZURE_OPENAI_API_VERSION   e.g. 2024-08-01-preview
    AZURE_OPENAI_DEPLOYMENT    the deployed model name (e.g. gpt-4o)

If any of these are missing, falls back to a deterministic mock so the
system can still run for demonstration / testing without Azure access.
"""

from __future__ import annotations

import json
import os
import traceback
from typing import Any, Type, TypeVar

from openai import AzureOpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

_client: AzureOpenAI | None = None
_fallback_mode: bool = False


def _sanitize_endpoint(endpoint: str) -> str:
    """
    Strip any path suffix after the base Azure OpenAI endpoint.
    The SDK constructs the full path internally (e.g. /openai/deployments/...).
    If the user provided something like:
      https://foo.openai.azure.com/openai/deployments/gpt-4/...
    we strip back to just the base: https://foo.openai.azure.com/
    """
    endpoint = endpoint.rstrip("/")
    # Remove known path suffixes
    for suffix in ["/openai", "/chat/completions", "/completions"]:
        if endpoint.endswith(suffix):
            endpoint = endpoint[: -len(suffix)]
    # Also handle the "responses" API style
    if "/responses" in endpoint:
        endpoint = endpoint.split("/responses")[0]
    if "/chat" in endpoint:
        endpoint = endpoint.split("/chat")[0]
    if "/deployments" in endpoint:
        endpoint = endpoint.split("/deployments")[0]
    if "/openai" in endpoint and not endpoint.endswith(".com"):
        # Keep the openai part if it's the base path
        pass
    return endpoint.rstrip("/")


def _get_client() -> AzureOpenAI:
    global _client, _fallback_mode
    if _client is not None:
        return _client

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    if not endpoint or not api_key:
        print("⚠️  AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY not set — running in FALLBACK mock mode.")
        _fallback_mode = True
        _client = None  # type: ignore
        return None  # type: ignore

    # Sanitize the endpoint to strip any path suffix the SDK would duplicate
    clean_endpoint = _sanitize_endpoint(endpoint)

    _client = AzureOpenAI(
        azure_endpoint=clean_endpoint,
        api_key=api_key,
        api_version=api_version,
    )
    print(f"✅ Azure OpenAI client initialized (deployment={deployment}, endpoint={clean_endpoint})")
    return _client


def call_llm_structured(
    system_prompt: str,
    user_prompt: str,
    response_model: Type[T],
    temperature: float = 0.1,
) -> T:
    """
    Call Azure OpenAI with structured output parsing.

    Args:
        system_prompt: The system-level instruction prompt.
        user_prompt: The specific user/context prompt.
        response_model: A Pydantic model class — the LLM response is parsed into this.
        temperature: Sampling temperature (low = more deterministic).

    Returns:
        An instance of `response_model` populated from the LLM response.
    """
    _get_client()

    if _fallback_mode:
        return _fallback_call_llm_structured(system_prompt, user_prompt, response_model, temperature)

    try:
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        response = _client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM returned empty response content")

        # Attempt to parse as JSON into the response model
        parsed = json.loads(content)
        return response_model.model_validate(parsed)

    except Exception as e:
        print(f"⚠️  LLM call failed: {e}")
        traceback.print_exc()
        print("⚠️  Falling back to mock LLM response.")
        return _fallback_call_llm_structured(system_prompt, user_prompt, response_model, temperature)


# ---------------------------------------------------------------------------
# Fallback mock — deterministic responses for demo / testing
# ---------------------------------------------------------------------------

def _fallback_call_llm_structured(
    system_prompt: str,
    user_prompt: str,
    response_model: Type[T],
    temperature: float = 0.1,
) -> T:
    """Deterministic mock that returns realistic structured responses."""

    from .models import (
        TriageResult,
        RunbookPlan,
        PlanStep,
        Finding,
        FindingStatus,
        CorrelationResult,
        CausalEvent,
        RemediationPlan,
        RemediationAction,
        Severity,
    )

    model_name = response_model.__name__

    # ── TriageResult ──────────────────────────────────────────────────
    if response_model is TriageResult:
        desc_lower = user_prompt.lower()
        if "sftp" in desc_lower or "timeout" in desc_lower or "feed" in desc_lower:
            return TriageResult(
                impacted_business_flow="eod_reporting",
                severity=Severity.SEV1,
                entry_point_service="saturn",
                symptoms=["EOD batch job failed", "Feed load timeout after 900s", "5 reports missing"],
                confidence=0.85,
                rationale="EOD reporting pipeline halted at Saturn stage. Feed load timeout in DataHub ingestion layer. Suspected SFTP connectivity issue with vendor data source.",
                similar_past_incidents=["INC-2026-05-10: SFTP vendor timeout during EOD batch"],
            )
        elif "payment" in desc_lower or "checkout" in desc_lower:
            return TriageResult(
                impacted_business_flow="checkout",
                severity=Severity.SEV2,
                entry_point_service="payment-svc",
                symptoms=["elevated payment failure rate", "checkout errors reported by users"],
                confidence=0.8,
                rationale="Payment errors reported across multiple orders in the last hour.",
                similar_past_incidents=["INC-2026-06-15: Payment gateway timeout"],
            )
        elif "risk" in desc_lower or "var" in desc_lower:
            return TriageResult(
                impacted_business_flow="risk_calc_pipeline",
                severity=Severity.SEV1,
                entry_point_service="saturn",
                symptoms=["VaR computation returned NaN", "Limit check triggered incorrectly"],
                confidence=0.82,
                rationale="Risk calculation pipeline halted. Stale market data causing incorrect risk calculations.",
                similar_past_incidents=["INC-2026-04-22: Stale market data incident"],
            )
        else:
            return TriageResult(
                impacted_business_flow="general",
                severity=Severity.SEV3,
                entry_point_service="saturn",
                symptoms=["Investigation requested for reported issue"],
                confidence=0.6,
                rationale="No specific symptoms matched known patterns. Default triage applied.",
                similar_past_incidents=[],
            )

    # ── RunbookPlan ───────────────────────────────────────────────────
    if response_model is RunbookPlan:
        desc_lower = user_prompt.lower()
        if "saturn" in desc_lower:
            return RunbookPlan(
                entry_step_id="s1",
                steps=[
                    PlanStep(
                        step_id="s1", system="saturn", action="Pull error logs and check report count for last 2 hours",
                        rationale="Symptom reported at Saturn layer first", assigned_agent="saturn_specialist",
                        on_anomaly="s2", on_clean=None,
                    ),
                    PlanStep(
                        step_id="s2", system="datahub", action="Query feed status and check for timeouts in data ingestion",
                        rationale="Downstream data layer could explain Saturn anomalies", assigned_agent="datahub_specialist",
                        on_anomaly="s3", on_clean=None,
                    ),
                    PlanStep(
                        step_id="s3", system="ingestion", action="Check SFTP connectivity and vendor status",
                        rationale="If DataHub shows feed issues, check ingestion layer", assigned_agent="ingestion_specialist",
                        on_anomaly=None, on_clean=None,
                    ),
                ],
                planning_rationale="Start at reported symptom (Saturn), if anomalous check downstream data layer, then ingestion.",
            )
        elif "payment" in desc_lower:
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
        else:
            return RunbookPlan(
                entry_step_id="s1",
                steps=[
                    PlanStep(
                        step_id="s1", system="saturn", action="Check system health and error logs",
                        rationale="Default starting point for investigation",
                        assigned_agent="saturn_specialist",
                        on_anomaly="s2", on_clean=None,
                    ),
                ],
                planning_rationale="Simple default investigation plan.",
            )

    # ── Finding ──────────────────────────────────────────────────────
    if response_model is Finding:
        action_lower = user_prompt.lower()
        if "error" in action_lower or "fail" in action_lower or "timeout" in action_lower or "anomal" in action_lower:
            return Finding(
                step_id="", system="", status=FindingStatus.ANOMALY,
                anomalies=["Error rate spike detected", "Timeout errors in recent log window"],
                evidence_refs=["log query: 214 error entries in 2 hour window", "metric query: error_rate > 5%"],
                suggested_next=["Check upstream dependencies for root cause"],
            )
        return Finding(
            step_id="", system="", status=FindingStatus.NORMAL,
            anomalies=[], evidence_refs=["log query: 0 anomalous entries in window"], suggested_next=[],
        )

    # ── CorrelationResult ─────────────────────────────────────────────
    if response_model is CorrelationResult:
        desc_lower = user_prompt.lower()
        if "sftp" in desc_lower or "vendor" in desc_lower:
            return CorrelationResult(
                timeline=[
                    CausalEvent(system="ingestion", description="SFTP vendor connection timeout", sequence_order=0, likely_root_cause=True),
                    CausalEvent(system="datahub", description="Feed load timeout due to upstream failure", sequence_order=1, likely_root_cause=False),
                    CausalEvent(system="saturn", description="Report count mismatch from missing feed data", sequence_order=2, likely_root_cause=False),
                ],
                root_cause_system="ingestion",
                root_cause_summary="SFTP vendor outage at the ingestion layer caused cascading failures upstream. DataHub feed timeouts and Saturn report mismatches are downstream symptoms.",
                remediation_needed=True,
            )
        elif "payment" in desc_lower:
            return CorrelationResult(
                timeline=[
                    CausalEvent(system="payment-svc", description="Auth timeout rate spiked", sequence_order=0, likely_root_cause=True),
                ],
                root_cause_system="payment-svc",
                root_cause_summary="Payment service auth timeouts are the root cause.",
                remediation_needed=True,
            )
        else:
            return CorrelationResult(
                timeline=[],
                root_cause_system=None,
                root_cause_summary="No clear root cause identified from available findings.",
                remediation_needed=False,
            )

    # ── RemediationPlan ───────────────────────────────────────────────
    if response_model is RemediationPlan:
        desc_lower = user_prompt.lower()
        if "ingestion" in desc_lower:
            return RemediationPlan(
                actions=[
                    RemediationAction(
                        action_id="rem-1",
                        description="Failover SFTP traffic to backup vendor endpoint",
                        target_system="ingestion",
                        mcp_tool="failover_sftp",
                        risk_level="medium",
                    ),
                    RemediationAction(
                        action_id="rem-2",
                        description="Rerun EOD batch job to reprocess missing reports",
                        target_system="saturn",
                        mcp_tool="rerun_airflow_dag",
                        risk_level="low",
                    ),
                ],
                rationale="SFTP vendor primary endpoint is down. Failover to backup and reprocess.",
            )
        elif "payment" in desc_lower:
            return RemediationPlan(
                actions=[
                    RemediationAction(
                        action_id="rem-1",
                        description="Restart payment-svc worker pool to clear stuck auth connections",
                        target_system="payment-svc",
                        mcp_tool="restart_service",
                        risk_level="medium",
                    ),
                ],
                rationale="Auth timeout spike is consistent with a stuck connection pool; a restart is a safe first remediation.",
            )
        else:
            return RemediationPlan(
                actions=[],
                rationale="No safe automatable remediation identified for the current root cause.",
            )

    # ── Fallback ──────────────────────────────────────────────────────
    raise ValueError(f"Unsupported response_model: {model_name}")
