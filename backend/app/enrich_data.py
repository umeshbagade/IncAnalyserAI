"""
Migration script: adds missing evidence and best-next-actions
to incident documents that have empty arrays in MongoDB.

Run standalone:  cd backend && python -m app.enrich_data
Or it auto-runs on startup via main.py if the data is missing.
"""

import asyncio
from datetime import datetime, timezone
from .database import connect_to_mongo, get_incidents_collection, close_mongo_connection

# ─── Evidence & Actions data for incidents missing them ────────────────

ENRICHMENTS = {
    "INC-2026-07-19-003": {  # Risk Calculation Pipeline Failure
        "evidence": [
            {
                "id": "e_r1",
                "type": "tool_call",
                "content": "var_calc_get_positions",
                "status": "failed",
                "details": "status: FAILED\nreason: position data timestamp older than 45 minutes\nsource: market_data_provider",
                "node_id": "saturn",
            },
            {
                "id": "e_r2",
                "type": "tool_call",
                "content": "market_data_freshness_check",
                "status": "warning",
                "details": "status: WARNING\nlast_update: 2026-07-19T13:45:00Z\nstale_threshold: 30 minutes",
                "node_id": "datahub",
            },
            {
                "id": "e_r3",
                "type": "runbook",
                "content": "rb_market_data_latency.md",
                "status": "success",
                "details": "Runbook: Market data latency investigation\nSteps: 1. Check provider status 2. Verify backup feed 3. Trigger catch-up",
                "node_id": "datahub",
            },
            {
                "id": "e_r4",
                "type": "similar_incident",
                "content": "INC-2026-06-28-012",
                "status": "success",
                "details": "Similar stale data incident\nRoot cause: Provider batch job delayed\nResolution: Forced catch-up replay",
            },
        ],
        "nextActions": [
            {"id": "b_r1", "label": "Force market data replay", "action": "force_data_replay", "category": "rerun"},
            {"id": "b_r2", "label": "Recompute VaR snapshot", "action": "recompute_var", "category": "recompute"},
            {"id": "b_r3", "label": "Alert data provider", "action": "alert_provider_sla", "category": "notify"},
            {"id": "b_r4", "label": "Check backup feed health", "action": "check_backup_feed", "category": "investigate"},
        ],
    },
    "INC-2026-07-18-007": {  # Market Data Feed Stale
        "evidence": [
            {
                "id": "e_m1",
                "type": "tool_call",
                "content": "feed_connectivity_check",
                "status": "failed",
                "details": "primary: UNREACHABLE (timeout after 10s)\nbackup: STANDBY (ready)\nlatency: 0ms (backup)",
                "node_id": "datahub",
            },
            {
                "id": "e_m2",
                "type": "tool_call",
                "content": "feed_failover_test",
                "status": "success",
                "details": "status: SUCCESS\nfailover_time: 45s (within 60s SLA)\nbackup feed now PRIMARY",
                "node_id": "ingestion",
            },
            {
                "id": "e_m3",
                "type": "runbook",
                "content": "rb_market_data_failover.md",
                "status": "success",
                "details": "Runbook: Market data failover procedure\nSteps: 1-4 executed successfully\nBackup feed took over at 10:38 UTC",
                "node_id": "ingestion",
            },
            {
                "id": "e_m4",
                "type": "similar_incident",
                "content": "INC-2026-06-15-009",
                "status": "success",
                "details": "Similar primary feed failure\nRoot cause: ISP routing issue\nResolution: Automatic failover within 30s",
            },
        ],
        "nextActions": [
            {"id": "b_m1", "label": "Verify backup feed stability", "action": "verify_backup_stability", "category": "investigate"},
            {"id": "b_m2", "label": "Root cause primary failure", "action": "rca_primary_failure", "category": "investigate"},
            {"id": "b_m3", "label": "Schedule primary recovery", "action": "schedule_primary_recovery", "category": "rerun"},
            {"id": "b_m4", "label": "Notify downstream consumers", "action": "notify_downstream", "category": "notify"},
        ],
    },
    "INC-2026-07-17-002": {  # Report Generation Timeout
        "evidence": [
            {
                "id": "e_g1",
                "type": "tool_call",
                "content": "report_gen_memory_check",
                "status": "failed",
                "details": "memory_usage: 98%\nthreshold: 90%\nOOM risk: CRITICAL",
                "node_id": "saturn",
            },
            {
                "id": "e_g2",
                "type": "tool_call",
                "content": "service_restart_log",
                "status": "success",
                "details": "restart_time: 300ms\nexit_code: 0\nmemory_after_restart: 22%",
                "node_id": "ingestion",
            },
            {
                "id": "e_g3",
                "type": "runbook",
                "content": "rb_report_gen_oom.md",
                "status": "success",
                "details": "Runbook: Report generator OOM recovery\nSteps: 1. Restart service 2. Clear temp files 3. Regenerate reports\nAll steps completed in 20 minutes",
                "node_id": "ingestion",
            },
            {
                "id": "e_g4",
                "type": "similar_incident",
                "content": "INC-2026-07-10-004",
                "status": "success",
                "details": "Similar OOM incident in report_gen_service\nRoot cause: Memory leak in PDF renderer\nResolution: Temporary restart + patch deployed",
            },
        ],
        "nextActions": [
            {"id": "b_g1", "label": "Investigate memory leak", "action": "investigate_memory_leak", "category": "investigate"},
            {"id": "b_g2", "label": "Increase memory limit", "action": "increase_memory_limit", "category": "rerun"},
            {"id": "b_g3", "label": "Set up memory alerting", "action": "setup_memory_alerts", "category": "notify"},
            {"id": "b_g4", "label": "Schedule report generation", "action": "schedule_report_gen", "category": "recompute"},
        ],
    },
    "INC-2026-07-16-005": {  # Database Connection Pool Exhausted
        "evidence": [
            {
                "id": "e_d1",
                "type": "tool_call",
                "content": "db_conn_pool_check",
                "status": "failed",
                "details": "active_connections: 100/100\nqueued_queries: 47\ntimeout_rate: 12/min",
                "node_id": "saturn",
            },
            {
                "id": "e_d2",
                "type": "tool_call",
                "content": "db_query_pattern_analysis",
                "status": "warning",
                "details": "top_consumers: batch_reporting (65%), realtime_dashboard (25%)\nunoptimized_queries: 3 identified",
                "node_id": "datahub",
            },
            {
                "id": "e_d3",
                "type": "runbook",
                "content": "rb_conn_pool_exhaustion.md",
                "status": "success",
                "details": "Runbook: Connection pool exhaustion\nSteps: 1. Increase pool size (→200) 2. Kill idle connections 3. Optimize queries\nCompleted in 15 minutes",
                "node_id": "ingestion",
            },
            {
                "id": "e_d4",
                "type": "similar_incident",
                "content": "INC-2026-06-22-008",
                "status": "success",
                "details": "Similar pool exhaustion incident\nRoot cause: Unoptimized batch queries\nResolution: Pool increased + query optimization deployed",
            },
        ],
        "nextActions": [
            {"id": "b_d1", "label": "Optimize top 3 slow queries", "action": "optimize_slow_queries", "category": "recompute"},
            {"id": "b_d2", "label": "Implement connection pooling limits", "action": "implement_pool_limits", "category": "rerun"},
            {"id": "b_d3", "label": "Set up pool utilization alerts", "action": "setup_pool_alerts", "category": "notify"},
            {"id": "b_d4", "label": "Audit batch job scheduling", "action": "audit_batch_jobs", "category": "investigate"},
        ],
    },
}


async def enrich_missing_data():
    """Update MongoDB documents that have empty evidence or nextActions."""
    collection = await get_incidents_collection()
    total_updated = 0

    for inc_id, data in ENRICHMENTS.items():
        # Check if enrichment is needed — only update if evidence is empty
        doc = await collection.find_one(
            {"id": inc_id},
            {"_id": 0, "flow.evidence": 1, "flow.nextActions": 1}
        )

        if not doc:
            print(f"⚠️  Incident '{inc_id}' not found in database. Skipping.")
            continue

        current_evidence = doc.get("flow", {}).get("evidence", [])
        current_actions = doc.get("flow", {}).get("nextActions", [])

        updates = {}
        if len(current_evidence) == 0:
            updates["flow.evidence"] = data["evidence"]
        if len(current_actions) == 0:
            updates["flow.nextActions"] = data["nextActions"]

        if updates:
            updates["updatedAt"] = datetime.now(timezone.utc).isoformat()
            result = await collection.update_one(
                {"id": inc_id},
                {"$set": updates}
            )
            if result.modified_count > 0:
                total_updated += 1
                ev_count = len(data["evidence"])
                ac_count = len(data["nextActions"])
                print(f"✅ Updated '{inc_id}' — added {ev_count} evidence + {ac_count} actions")
            else:
                print(f"ℹ️  '{inc_id}' — update skipped (unchanged)")
        else:
            ev_count = len(current_evidence)
            ac_count = len(current_actions)
            print(f"✅ '{inc_id}' — already has {ev_count} evidence + {ac_count} actions")

    print(f"\n📊 Enrichment complete. {total_updated} incidents updated.")
    return total_updated


async def main():
    """Run enrichment as standalone script."""
    print("🔧 IncAnalyserAI Data Enrichment Tool")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    await connect_to_mongo()
    await enrich_missing_data()
    await close_mongo_connection()
    print("\n✅ Done.")


if __name__ == "__main__":
    asyncio.run(main())

