# ATOP Incident Diagnosis — Six-Agent Prototype

## Architecture

```
START -> triage -> planner -> specialist -> supervisor_update -+
                                    ^                           |
                                    |___________________________|
                                (loop while DAG has a next step)
                                              |
                                              v
                                          correlate
                                       /              \
                          remediation needed      not needed
                                |                        |
                                v                         v
                        propose_remediation           finalize -> END
                                |
                       (proposed actions?) -- no --> finalize -> END
                                | yes
                                v
                        remediation_gate   <-- the ONLY interrupt in the graph
                                |
                                v
                        execute_remediation -> finalize -> END
```

| # | Agent | File | Status |
|---|---|---|---|
| 4.1 | Supervisor/Orchestrator | `orchestrator.py` | **Real** — plan-and-execute state machine, walks the DAG, maintains the typed Investigation State |
| 4.2 | Triage | `agents/triage_agent.py` | **Real** — LLM call, RAG stub over past incidents |
| 4.3 | Planner | `agents/planner_agent.py` | **Real** — LLM call, emits a *branching* DAG (`on_anomaly`/`on_clean`), not a flat list |
| 4.4 | Specialist | `agents/specialist_agent.py` | **Real** (generic, one function serving all systems) — LLM call over MCP tool stub outputs + system-scoped RAG stub |
| 4.5 | Correlator | `agents/correlator_agent.py` | **Real** — LLM call, builds a causal timeline, picks a root cause |
| 4.6 | Remediation | `agents/remediation_agent.py` | **Real** — LLM call, proposes actions, always `requires_approval=True` |

Stubbed, by design, so the control flow is provable before real integrations exist:
- **MCP tool layer** (`knowledge/mcp_tools.py`) — log/metric/diagnostic queries and the remediation executor all return synthetic data. Swap for real MCP client calls.
- **Graph DB / Vector DB** (`knowledge/topology_store.py`) — in-memory topology + empty RAG results. Swap `get_downstream_systems`/`get_upstream_systems` for Neo4j Cypher, and the `search_*`/`get_system_knowledge_base` functions for real Chroma queries.

## Where the human gate lives — and doesn't

Per your spec, human approval is scoped to **remediation only**. Triage,
planning, every specialist check, and correlation all run fully
autonomously in one `.invoke()` call. The graph is compiled with:

```python
compiled = graph.compile(checkpointer=checkpointer, interrupt_before=["remediation_gate"])
```

`remediation_gate` is the only node named there, so it's the only place
LangGraph will pause. If the Correlator decides `remediation_needed=False`,
the graph routes straight past `propose_remediation` to `finalize` and never
even calls the Remediation agent — no gate, no LLM call, no approval needed,
because there's nothing to approve.

## How the Supervisor walks the DAG

The Planner's `RunbookPlan` isn't a flat list — each `PlanStep` has
`on_anomaly` and `on_clean` pointers to the next step_id. After each
Specialist reports a `Finding`, `_supervisor_update_node` in
`orchestrator.py`:

1. Appends `EvidenceItem`s from the finding's `evidence_refs`
2. On `ANOMALY`: adds an open `Hypothesis` for that system, follows `on_anomaly`
3. On `NORMAL`: marks any hypothesis for that system `RULED_OUT`, follows `on_clean`
4. On `INCONCLUSIVE`: logs an `OpenQuestion`, follows `on_clean` as a default
5. If the branch target is `null`, or a safety cap (`MAX_INVESTIGATION_HOPS`)
   is hit, the investigation ends and control passes to the Correlator

This decision logic is currently deterministic (rule-based on
`Finding.status`) rather than an LLM call — kept that way for hackathon
speed/determinism/auditability. The typed Investigation State
(`hypotheses`/`evidence`/`open_questions`) is exactly what you'd hand an LLM
call to make this smarter later (e.g. resolving conflicting hypotheses).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your Azure OpenAI values
```

## Run the API

```bash
uvicorn main:app --reload
```

```bash
# 1. Create an incident -> runs the full autonomous investigation.
#    Halts here ONLY if a remediation is proposed.
curl -X POST localhost:8000/incidents -H "Content-Type: application/json" -d '{
  "title": "Payment failures spiking",
  "description": "Customers report failed payments since 10am",
  "reported_by": "oncall"
}'

# 2. Check current state / timeline anytime
curl localhost:8000/incidents/<incident_id>

# 3. If a remediation was proposed, approve it to execute
curl -X POST localhost:8000/incidents/<incident_id>/approve-remediation
```

## Tests

```bash
pip install -r requirements.txt   # includes pytest + httpx
python3 -m pytest tests/ -v
```

`tests/conftest.py` mocks `llm_client.call_llm_structured` — every agent
call is faked with realistic structured responses, so the suite runs with
zero Azure OpenAI access. `tests/test_full_flow.py` drives the real FastAPI
app through `TestClient` and covers:
- the DAG actually branching (anomaly at step 1 → follows `on_anomaly` to step 2)
- the typed Investigation State getting populated (hypotheses, evidence)
- the remediation gate pausing, then executing only after approval
- the no-remediation-needed path skipping the gate (and the Remediation
  agent entirely) when the Correlator finds nothing to fix

## Known follow-ups

1. **Supervisor decision-making is deterministic, not LLM-driven.** Fine for
   a demo; swap `_supervisor_update_node`'s rule-based branch selection for
   an LLM call once you want it resolving conflicting hypotheses rather than
   just following the DAG's fixed branches.
2. **Specialist agents are one generic function**, not N deployable agents
   with differentiated tool access. Split out once per-system tool
   permissions actually differ.
3. **Cycle safety** is a blunt hop-count cap (`MAX_INVESTIGATION_HOPS = 8`),
   not real cycle detection on the DAG. Fine for hackathon-sized runbooks;
   revisit if the Planner starts producing larger DAGs.
4. **Checkpointer** is in-process `MemorySaver` — swap for a persistent
   backend before this is anything but a demo.
5. **Minor**: LangGraph logs a deprecation warning about serializing custom
   Pydantic/enum types via msgpack. Harmless today.
