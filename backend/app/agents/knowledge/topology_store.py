"""
Topology Store — in-memory system/service topology with RAG stubs.

Provides:
    - get_all_systems()            : list[SystemRef]
    - get_system(system_id)        : SystemRef | None
    - get_downstream_systems(id)   : list[str]
    - get_upstream_systems(id)     : list[str]
    - search_similar_incidents(q)  : list[str]
    - search_similar_runbooks(q)   : list[str]
    - get_system_knowledge_base(id): str

In production, swap the in-memory topology for Neo4j Cypher queries,
and the RAG stubs for real Chroma/vector-db queries.
"""

from __future__ import annotations

from ..models import SystemRef


# ---------------------------------------------------------------------------
# In-memory service topology
# ---------------------------------------------------------------------------

_SYSTEMS: dict[str, SystemRef] = {
    "saturn": SystemRef(system_id="saturn", name="Saturn", description="Report generation & orchestration layer"),
    "datahub": SystemRef(system_id="datahub", name="Data Hub", description="Data feed aggregation & transformation layer"),
    "ingestion": SystemRef(system_id="ingestion", name="Ingestion", description="SFTP / file ingestion pipeline"),
    "payment-svc": SystemRef(system_id="payment-svc", name="Payment Service", description="Payment processing and auth"),
    "order-svc": SystemRef(system_id="order-svc", name="Order Service", description="Order management and fulfillment"),
    "kafka": SystemRef(system_id="kafka", name="Kafka", description="Event streaming backbone"),
    "scheduler": SystemRef(system_id="scheduler", name="Scheduler", description="Batch job scheduling (Airflow)"),
    "bloomberg": SystemRef(system_id="bloomberg", name="Bloomberg Feed", description="Primary market data provider"),
    "reuters": SystemRef(system_id="reuters", name="Reuters Feed", description="Backup market data provider"),
}

# Downstream dependencies (parent -> [children])
# A depends on B means B is downstream from A
_DOWNSTREAM: dict[str, list[str]] = {
    "saturn": ["datahub", "scheduler"],
    "datahub": ["ingestion", "kafka"],
    "ingestion": ["sftp_gateway"],
    "payment-svc": ["order-svc"],
    "order-svc": ["kafka"],
    "bloomberg": ["datahub"],
    "reuters": ["datahub"],
}

_UPSTREAM: dict[str, list[str]] = {}
for parent, children in _DOWNSTREAM.items():
    for child in children:
        _UPSTREAM.setdefault(child, []).append(parent)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_all_systems() -> list[SystemRef]:
    return list(_SYSTEMS.values())


def get_system(system_id: str) -> SystemRef | None:
    return _SYSTEMS.get(system_id)


def get_downstream_systems(system_id: str) -> list[str]:
    return _DOWNSTREAM.get(system_id, [])


def get_upstream_systems(system_id: str) -> list[str]:
    return _UPSTREAM.get(system_id, [])


def search_similar_incidents(query: str, top_k: int = 3) -> list[str]:
    """
    Stub: search past incidents via RAG / vector similarity.
    In production, query Chroma DB with the vectorized query string.
    Returns list of short incident summaries.
    """
    # Return some plausible similar incidents for known keywords
    query_lower = query.lower()
    if "sftp" in query_lower or "timeout" in query_lower or "feed" in query_lower:
        return [
            "INC-2026-05-10: SFTP vendor timeout during EOD batch — resolved via vendor failover",
            "INC-2026-04-22: Market data feed stale — resolved by restarting gateway",
        ]
    if "payment" in query_lower or "checkout" in query_lower:
        return [
            "INC-2026-06-15: Payment gateway timeout — auth service connection pool exhausted",
        ]
    if "risk" in query_lower or "var" in query_lower:
        return [
            "INC-2026-04-22: Market data feed stale — resolved by restarting market data gateway",
        ]
    return []


def search_similar_runbooks(query: str, top_k: int = 3) -> list[str]:
    """
    Stub: search past runbooks / investigation plans via RAG / vector similarity.
    In production, query Chroma DB.
    """
    query_lower = query.lower()
    if "sftp" in query_lower or "eod" in query_lower:
        return [
            "Runbook: EOD_SFTP_TIMEOUT — check vendor status, failover to backup, rerun batch",
        ]
    if "payment" in query_lower:
        return [
            "Runbook: PAYMENT_AUTH_FAILURE — check conn pool, restart worker, verify upstream",
        ]
    return []


def get_system_knowledge_base(system_id: str, query: str = "") -> str:
    """
    Stub: retrieve system-specific knowledge (runbooks, config docs, known issues).
    In production, query a system-scoped vector DB.
    """
    kb = {
        "saturn": (
            "Saturn runbooks:\n"
            "- RB_SATURN_REPORT_CHECK.md: verify report count, match expected vs actual\n"
            "- RB_SATURN_ANOMALY.md: investigate mismatched reports, escalate to DataHub\n"
        ),
        "datahub": (
            "DataHub runbooks:\n"
            "- RB_DATAHUB_FEED_STATUS.md: query feed load status, check for timeouts\n"
            "- RB_DATAHUB_DATA_QUALITY.md: validate data freshness, check for staleness\n"
        ),
        "ingestion": (
            "Ingestion runbooks:\n"
            "- RB_SFTP_CONNECTIVITY.md: test SFTP connection, verify credentials\n"
            "- RB_VENDOR_FAILOVER.md: failover to backup vendor if primary is down\n"
        ),
        "payment-svc": (
            "Payment Service runbooks:\n"
            "- RB_PAYMENT_AUTH.md: check auth service health, connection pool status\n"
            "- RB_PAYMENT_TIMEOUT.md: investigate timeout patterns, upstream dependencies\n"
        ),
        "order-svc": (
            "Order Service runbooks:\n"
            "- RB_ORDER_STATE.md: verify order state transitions, check for stuck orders\n"
        ),
    }
    return kb.get(system_id, f"No knowledge base entries for system '{system_id}'")

