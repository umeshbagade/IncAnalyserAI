"""
Triage Agent (4.2).

Input: alert / user description.
Output: {impactedBusinessFlow, severity, entryPointService, symptoms[]}.
Uses RAG over past incidents to help classify by similarity.
"""

from __future__ import annotations

from . import llm_client
from .models import ActorType, AuditEvent, IncidentGraphState, IncidentStatus, TriageResult
from .knowledge.topology_store import get_all_systems, search_similar_incidents

SYSTEM_PROMPT = """\
You are the Triage Agent inside an incident-diagnosis system for a
distributed set of applications. Given a raw incident report, the list of
known systems, and any similar past incidents found via retrieval, produce:

- impacted_business_flow: the end-user-facing flow affected (e.g.
  "checkout", "order fulfillment", "account signup") — infer this from the
  description even if not stated explicitly.
- severity (SEV1 = full outage/revenue-impacting, SEV2 = major degradation,
  SEV3 = partial/limited blast radius, SEV4 = cosmetic/low urgency). Be
  conservative — do not downgrade on limited information.
- entry_point_service: the system_id (from the provided list) where the
  symptom was FIRST observed or reported — not necessarily the root cause,
  just where it surfaced.
- symptoms: a list of concrete, observable symptoms from the report (not
  diagnoses).
- confidence: 0.0-1.0
- rationale: 2-4 sentences
- similar_past_incidents: carry through any similar incidents you were
  given verbatim (empty list if none provided)
"""


def triage_node(state: IncidentGraphState) -> dict:
    incident = state["incident"]
    known_systems = get_all_systems()
    systems_listing = "\n".join(f"- {s.system_id}: {s.name} — {s.description}" for s in known_systems)

    similar = search_similar_incidents(f"{incident.title} {incident.description}")
    similar_block = "\n".join(similar) if similar else "(none found)"

    user_prompt = f"""\
Incident title: {incident.title}
Incident description: {incident.description}
Reporter-suspected systems (may be incomplete or wrong): {incident.suspected_systems}

Known systems in the environment:
{systems_listing}

Similar past incidents found via retrieval:
{similar_block}
"""

    result: TriageResult = llm_client.call_llm_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=TriageResult,
    )

    audit_entry = AuditEvent(
        actor=ActorType.TRIAGE_AGENT,
        event_type="TRIAGE_COMPLETE",
        detail=(
            f"flow={result.impacted_business_flow} severity={result.severity.value} "
            f"entry_point={result.entry_point_service} confidence={result.confidence:.2f}"
        ),
    )

    return {
        "triage": result,
        "status": IncidentStatus.PLANNING,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
