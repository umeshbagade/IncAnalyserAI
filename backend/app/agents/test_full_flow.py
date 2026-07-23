from fastapi.testclient import TestClient

from app.agents.main import app

client = TestClient(app)


def test_full_investigation_with_remediation_gate():
    # 1. Create -> autonomous: triage -> planner -> specialist(s1, ANOMALY)
    #    -> supervisor follows on_anomaly to s2 -> specialist(s2, NORMAL)
    #    -> correlate -> remediation proposed -> HALTS at remediation_gate
    resp = client.post(
        "/incidents",
        json={
            "title": "Payments down",
            "description": "Checkout failing for all users since 10am",
            "reported_by": "oncall",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    incident_id = body["incident"]["incident_id"]

    # investigation ran fully autonomously, no approval needed for this part
    assert body["triage"]["entry_point_service"] == "payment-svc"
    assert len(body["findings"]) == 2, "should have followed the DAG: s1 (anomaly) -> s2 (clean)"
    assert body["findings"][0]["status"] == "ANOMALY"
    assert body["findings"][1]["status"] == "NORMAL"

    # supervisor's typed investigation state was actually populated
    assert len(body["hypotheses"]) >= 1
    assert body["hypotheses"][0]["system"] == "payment-svc"

    # correlator identified a root cause
    assert body["correlation"]["root_cause_system"] == "payment-svc"

    # remediation proposed -> now AWAITING approval, NOT auto-executed
    assert body["status"] == "AWAITING_REMEDIATION_APPROVAL"
    assert body["awaiting_remediation_approval"] is True
    assert body["is_complete"] is False
    assert len(body["remediation_plan"]["actions"]) == 1
    assert body["remediation_plan"]["actions"][0]["status"] == "PROPOSED"

    # 2. Approve -> executes the remediation action, resolves
    resp = client.post(f"/incidents/{incident_id}/approve-remediation")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "RESOLVED"
    assert body["is_complete"] is True
    assert body["remediation_plan"]["actions"][0]["status"] == "EXECUTED"

    actors = [e["actor"] for e in body["audit_trail"]]
    assert actors.count("HUMAN") == 1  # exactly one approval, and only for remediation
    assert "TRIAGE_AGENT" in actors
    assert "PLANNER_AGENT" in actors
    assert "SPECIALIST_AGENT" in actors
    assert "CORRELATOR_AGENT" in actors
    assert "REMEDIATION_AGENT" in actors


def test_approve_with_nothing_pending_returns_400():
    resp = client.post("/incidents/nonexistent/approve-remediation")
    assert resp.status_code == 404


def test_investigation_resolves_immediately_when_no_remediation_needed(monkeypatch):
    from app.agents import llm_client
    from app.agents.models import CorrelationResult
    from app.agents.conftest import fake_call_llm_structured

    def no_remediation_llm(system_prompt, user_prompt, response_model, temperature=0.1):
        result = fake_call_llm_structured(system_prompt, user_prompt, response_model, temperature)
        if response_model is CorrelationResult:
            return result.model_copy(update={"remediation_needed": False})
        return result

    monkeypatch.setattr(llm_client, "call_llm_structured", no_remediation_llm)

    resp = client.post(
        "/incidents",
        json={"title": "Payments down", "description": "Checkout failing since 10am", "reported_by": "oncall"},
    )
    body = resp.json()

    # correlate routed straight to finalize -> RemediationAgent never even ran
    assert body["status"] == "RESOLVED"
    assert body["is_complete"] is True
    assert body["remediation_plan"] is None
    actors = [e["actor"] for e in body["audit_trail"]]
    assert "REMEDIATION_AGENT" not in actors
    assert "HUMAN" not in actors
