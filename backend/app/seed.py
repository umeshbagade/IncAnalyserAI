"""
Seed script: populates MongoDB with the existing mock/static data
from the original backend so there's reference data to start with.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from .database import connect_to_mongo, get_incidents_collection, close_mongo_connection

# ─── Mock Incident Data ──────────────────────────────────────────────────────

SEED_INCIDENTS = [
    {
        "id": "INC-2026-07-20-001",
        "title": "EOD Reporting Failure - Feed Load Timeout",
        "severity": "HIGH",
        "status": "investigating",
        "flowId": "eod_reporting",
        "timestamp": "2026-07-20 21:01:00",
        "duration": "00:14:23",
        "description": "EOD batch job failed at 21:01 UTC. Feed 'load_feed_alpha' timed out after 900 seconds.",
        "originalText": "EOD batch job failed at 21:01 UTC. \nFeed \"load_feed_alpha\" timed out after 900 seconds. \nAffected reports: daily_pnl, risk_summary, exposure_report.\nSLA breach imminent. Manual intervention required.",
        "triageSummary": "EOD reporting pipeline halted at Saturn stage. \nFeed load timeout in DataHub ingestion layer. \nSuspected SFTP connectivity issue with vendor data source. \n3 downstream reports blocked. Priority: P1 - High Business Impact.",
        "entities": [
            {"name": "eod_reporting", "type": "workflow", "confidence": 0.98},
            {"name": "load_feed_alpha", "type": "task", "confidence": 0.95},
            {"name": "daily_pnl", "type": "report", "confidence": 0.92},
            {"name": "risk_summary", "type": "report", "confidence": 0.90},
            {"name": "saturn", "type": "system", "confidence": 0.88},
            {"name": "datahub", "type": "system", "confidence": 0.85},
            {"name": "sftp", "type": "integration", "confidence": 0.78},
        ],
        "timeline": [
            {"time": "21:01:00", "event": "EOD batch triggered", "type": "info"},
            {"time": "21:01:15", "event": "Saturn: Checking report count (expected: 47)", "type": "info"},
            {"time": "21:03:22", "event": "Saturn: Report count mismatch - found 42/47", "type": "warning"},
            {"time": "21:05:00", "event": "DataHub: Querying feed status for missing reports", "type": "info"},
            {"time": "21:06:30", "event": "DataHub: Feed \"load_feed_alpha\" timed out", "type": "error"},
            {"time": "21:08:15", "event": "Ingestion: SFTP connection check initiated", "type": "info"},
            {"time": "21:09:00", "event": "Ingestion: Connection failed - timeout after 30s", "type": "error"},
            {"time": "21:10:00", "event": "RCA: Identified SFTP vendor outage as root cause", "type": "success"},
        ],
        "flow": {
            "id": "eod_reporting",
            "name": "EOD Reporting Pipeline",
            "nodes": [
                {
                    "id": "saturn",
                    "label": "Saturn",
                    "status": "completed",
                    "description": "Report Level - Check report count & status",
                    "subSteps": [
                        {"id": "s1", "label": "Report Count Check", "status": "completed"},
                        {"id": "s2", "label": "Status Verification", "status": "completed"},
                        {"id": "s3", "label": "Anomaly Detection", "status": "completed"},
                    ],
                },
                {
                    "id": "datahub",
                    "label": "Data Hub",
                    "status": "active",
                    "description": "Data Layer - Query feeds & data sources",
                    "subSteps": [
                        {"id": "d1", "label": "Feed Status Query", "status": "completed"},
                        {"id": "d2", "label": "Data Source Verification", "status": "active"},
                        {"id": "d3", "label": "Data Quality Check", "status": "pending"},
                    ],
                },
                {
                    "id": "ingestion",
                    "label": "Ingestion",
                    "status": "pending",
                    "description": "Ingestion Layer - Check connectivity & pipelines",
                    "subSteps": [
                        {"id": "i1", "label": "SFTP Connection Test", "status": "pending"},
                        {"id": "i2", "label": "Pipeline Status", "status": "pending"},
                        {"id": "i3", "label": "Retry Mechanism", "status": "pending"},
                    ],
                },
            ],
            "rca": {
                "rootCause": "Vendor SFTP server timeout - upstream data source unavailable due to network partition",
                "confidence": 0.87,
                "causalChain": [
                    "Vendor SFTP server unresponsive (timeout after 900s)",
                    'Feed "load_feed_alpha" failed to ingest data',
                    "5 reports missing in Saturn: daily_pnl, risk_summary, exposure_report, var_calc, limit_check",
                    "EOD batch reporting pipeline halted at DataHub stage",
                    "SLA breach probability: 0.92 - escalation triggered",
                ],
            },
            "evidence": [
                {
                    "id": "e1",
                    "type": "tool_call",
                    "content": "airflow_get_dag_run",
                    "status": "failed",
                    "details": "status: FAILED\nfailed_tasks: [load_feed_alpha]",
                },
                {
                    "id": "e2",
                    "type": "runbook",
                    "content": "rb_ingest_sftp_timeout.md",
                    "status": "success",
                    "details": "Runbook: SFTP timeout recovery procedure\nSteps: 1-5 applicable",
                },
                {
                    "id": "e3",
                    "type": "similar_incident",
                    "content": "INC-2026-05-10",
                    "status": "success",
                    "details": "Similar SFTP timeout incident\nResolution: Vendor failover triggered",
                },
            ],
            "nextActions": [
                {"id": "b1", "label": "Rerun Airflow", "action": "airflow_rerun", "category": "rerun"},
                {"id": "b2", "label": "Recompute snapshot", "action": "recompute_snapshot", "category": "recompute"},
                {"id": "b3", "label": "Notify vendor", "action": "notify_vendor", "category": "notify"},
                {"id": "b4", "label": "Check backup feed", "action": "check_backup_feed", "category": "investigate"},
            ],
        },
        "investigation": {
            "runId": None,
            "status": "idle",
            "stepIndex": 0,
            "currentPhase": None,
            "feedback": [],
            "approved": None,
            "createdAt": None,
        },
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "INC-2026-07-19-003",
        "title": "Risk Calculation Pipeline Failure",
        "severity": "HIGH",
        "status": "investigating",
        "flowId": "risk_calc_pipeline",
        "timestamp": "2026-07-19 14:30:00",
        "duration": "00:42:10",
        "description": "Risk calculation pipeline failed during VaR computation.",
        "originalText": "Risk calculation pipeline failed at 14:30 UTC.\nVaR computation returned unexpected values.\nLimit check triggered for multiple portfolios.\nSuspected stale market data.",
        "triageSummary": "Risk calculation pipeline halted at Saturn stage.\nSuspected stale market data causing incorrect risk calculations.\n3 portfolios affected. Priority: P1 - High Business Impact.",
        "entities": [
            {"name": "risk_calc_pipeline", "type": "workflow", "confidence": 0.97},
            {"name": "var_calculation", "type": "task", "confidence": 0.94},
            {"name": "limit_check", "type": "task", "confidence": 0.91},
            {"name": "saturn", "type": "system", "confidence": 0.88},
            {"name": "datahub", "type": "system", "confidence": 0.85},
        ],
        "timeline": [
            {"time": "14:30:00", "event": "Risk calculation triggered", "type": "info"},
            {"time": "14:31:15", "event": "Saturn: VaR calculation started", "type": "info"},
            {"time": "14:33:22", "event": "VaR values outside expected range", "type": "warning"},
            {"time": "14:35:00", "event": "Limit check flagged 3 portfolios", "type": "error"},
            {"time": "14:36:30", "event": "Pipeline halted - manual review needed", "type": "error"},
        ],
        "flow": {
            "id": "risk_calc_pipeline",
            "name": "Risk Calculation Pipeline",
            "nodes": [
                {
                    "id": "saturn",
                    "label": "Saturn",
                    "status": "error",
                    "description": "Report Level - Check calculations",
                    "subSteps": [
                        {"id": "s1", "label": "VaR Calculation Check", "status": "completed"},
                        {"id": "s2", "label": "Limit Check", "status": "error"},
                        {"id": "s3", "label": "Exposure Report", "status": "pending"},
                    ],
                },
                {
                    "id": "datahub",
                    "label": "Data Hub",
                    "status": "pending",
                    "description": "Data Layer - Risk data sources",
                    "subSteps": [
                        {"id": "d1", "label": "Market Data Query", "status": "pending"},
                        {"id": "d2", "label": "Position Data", "status": "pending"},
                        {"id": "d3", "label": "Risk Factors", "status": "pending"},
                    ],
                },
                {
                    "id": "ingestion",
                    "label": "Ingestion",
                    "status": "pending",
                    "description": "Ingestion Layer - Pipeline check",
                    "subSteps": [
                        {"id": "i1", "label": "Pipeline Health", "status": "pending"},
                        {"id": "i2", "label": "Data Quality", "status": "pending"},
                        {"id": "i3", "label": "Retry", "status": "pending"},
                    ],
                },
            ],
            "rca": {
                "rootCause": "Position data feed stale - market data provider delayed by 45 minutes",
                "confidence": 0.82,
                "causalChain": [
                    "Market data provider experienced latency spike",
                    "Position data feed 45 minutes stale",
                    "VaR calculation using outdated positions",
                    "Limit check triggered breach incorrectly",
                    "Risk report generation halted",
                ],
            },
            "evidence": [],
            "nextActions": [],
        },
        "investigation": {
            "runId": None,
            "status": "idle",
            "stepIndex": 0,
            "currentPhase": None,
            "feedback": [],
            "approved": None,
            "createdAt": None,
        },
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "INC-2026-07-18-007",
        "title": "Market Data Feed Stale",
        "severity": "MEDIUM",
        "status": "resolved",
        "flowId": "market_data_ingest",
        "timestamp": "2026-07-18 09:15:00",
        "duration": "01:23:45",
        "description": "Market data feed stale for 45 minutes.",
        "originalText": "Market data feed stale detected at 09:15 UTC.\nPrimary feed connectivity issues detected.\nFailed over to backup feed at 10:38 UTC.\nIncident resolved.",
        "triageSummary": "Primary feed had connectivity issues. Failed over to backup.\nMarket data received with 45 minute delay.\nNo data loss reported.",
        "entities": [
            {"name": "market_data_ingest", "type": "workflow", "confidence": 0.96},
            {"name": "primary_feed", "type": "system", "confidence": 0.93},
            {"name": "backup_feed", "type": "system", "confidence": 0.90},
        ],
        "timeline": [
            {"time": "09:15:00", "event": "Market data feed stale alert", "type": "error"},
            {"time": "09:20:00", "event": "Saturn: Freshness check failed", "type": "warning"},
            {"time": "09:25:00", "event": "DataHub: Primary feed connectivity issue", "type": "error"},
            {"time": "10:30:00", "event": "Ingestion: Failover to backup initiated", "type": "info"},
            {"time": "10:38:00", "event": "Backup feed active - data flowing", "type": "success"},
            {"time": "10:45:00", "event": "Incident marked resolved", "type": "success"},
        ],
        "flow": {
            "id": "market_data_ingest",
            "name": "Market Data Ingestion",
            "nodes": [
                {
                    "id": "saturn",
                    "label": "Saturn",
                    "status": "completed",
                    "description": "Report Level - Market data freshness",
                    "subSteps": [
                        {"id": "s1", "label": "Freshness Check", "status": "completed"},
                        {"id": "s2", "label": "Staleness Detection", "status": "completed"},
                        {"id": "s3", "label": "Alert Verification", "status": "completed"},
                    ],
                },
                {
                    "id": "datahub",
                    "label": "Data Hub",
                    "status": "completed",
                    "description": "Data Layer - Feed status",
                    "subSteps": [
                        {"id": "d1", "label": "Feed Status", "status": "completed"},
                        {"id": "d2", "label": "Data Quality", "status": "completed"},
                        {"id": "d3", "label": "Pipeline Health", "status": "completed"},
                    ],
                },
                {
                    "id": "ingestion",
                    "label": "Ingestion",
                    "status": "completed",
                    "description": "Ingestion Layer - Resolved by failover",
                    "subSteps": [
                        {"id": "i1", "label": "Failover Check", "status": "completed"},
                        {"id": "i2", "label": "Backup Feed", "status": "completed"},
                        {"id": "i3", "label": "Recovery", "status": "completed"},
                    ],
                },
            ],
            "rca": {
                "rootCause": "Primary market data provider connectivity failure - automatic failover to backup",
                "confidence": 0.95,
                "causalChain": [
                    "Primary feed connection lost at 09:15",
                    "Staleness threshold exceeded (45 min)",
                    "Automatic failover triggered",
                    "Backup feed activated at 10:38",
                    "No data loss - all reports regenerated from backup",
                ],
            },
            "evidence": [],
            "nextActions": [],
        },
        "investigation": {
            "runId": None,
            "status": "idle",
            "stepIndex": 0,
            "currentPhase": None,
            "feedback": [],
            "approved": None,
            "createdAt": None,
        },
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "INC-2026-07-17-002",
        "title": "Report Generation Timeout",
        "severity": "LOW",
        "status": "resolved",
        "flowId": "report_gen_service",
        "timestamp": "2026-07-17 16:45:00",
        "duration": "00:35:20",
        "description": "Report generation service timed out.",
        "originalText": "Report generation service timed out at 16:45 UTC.\nMonthly risk report generation delayed.\nService recovered after restart.\nAll reports generated successfully.",
        "triageSummary": "Report generation service timeout.\nService restarted and recovered.\nAll pending reports generated successfully.\nMinor business impact.",
        "entities": [
            {"name": "report_gen_service", "type": "workflow", "confidence": 0.94},
            {"name": "monthly_risk_report", "type": "report", "confidence": 0.91},
        ],
        "timeline": [
            {"time": "16:45:00", "event": "Report generation timeout", "type": "error"},
            {"time": "16:50:00", "event": "Service restart initiated", "type": "info"},
            {"time": "17:05:00", "event": "Service recovered", "type": "success"},
            {"time": "17:20:00", "event": "All reports generated", "type": "success"},
            {"time": "17:25:00", "event": "Incident resolved", "type": "success"},
        ],
        "flow": {
            "id": "report_gen_service",
            "name": "Report Generation Service",
            "nodes": [
                {
                    "id": "saturn",
                    "label": "Saturn",
                    "status": "completed",
                    "description": "Report Level - Check generation status",
                    "subSteps": [
                        {"id": "s1", "label": "Generation Status", "status": "completed"},
                        {"id": "s2", "label": "Timeout Detection", "status": "completed"},
                        {"id": "s3", "label": "Impact Assessment", "status": "completed"},
                    ],
                },
                {
                    "id": "datahub",
                    "label": "Data Hub",
                    "status": "completed",
                    "description": "Data Layer - Source availability",
                    "subSteps": [
                        {"id": "d1", "label": "Data Source Check", "status": "completed"},
                        {"id": "d2", "label": "Service Health", "status": "completed"},
                    ],
                },
                {
                    "id": "ingestion",
                    "label": "Ingestion",
                    "status": "completed",
                    "description": "Ingestion Layer - Recovery",
                    "subSteps": [
                        {"id": "i1", "label": "Service Restart", "status": "completed"},
                        {"id": "i2", "label": "Recovery Verification", "status": "completed"},
                        {"id": "i3", "label": "Report Regeneration", "status": "completed"},
                    ],
                },
            ],
            "rca": {
                "rootCause": "Report generation service experienced transient timeout due to memory pressure",
                "confidence": 0.78,
                "causalChain": [
                    "Memory usage exceeded threshold",
                    "Report generation process stalled",
                    "Timeout after 60 seconds",
                    "Service restart freed resources",
                    "All reports regenerated successfully",
                ],
            },
            "evidence": [],
            "nextActions": [],
        },
        "investigation": {
            "runId": None,
            "status": "idle",
            "stepIndex": 0,
            "currentPhase": None,
            "feedback": [],
            "approved": None,
            "createdAt": None,
        },
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "INC-2026-07-16-005",
        "title": "Database Connection Pool Exhausted",
        "severity": "HIGH",
        "status": "resolved",
        "flowId": "db_conn_pool",
        "timestamp": "2026-07-16 11:20:00",
        "duration": "00:28:15",
        "description": "Database connection pool exhausted.",
        "originalText": "Database connection pool exhausted at 11:20 UTC.\nAll 100 connections in use.\nQueries queued and timed out.\nPool expanded to 200 connections.",
        "triageSummary": "Connection pool exhaustion.\n100 connections maxed out.\nPool size increased to 200.\nApplication recovered.",
        "entities": [
            {"name": "db_conn_pool", "type": "system", "confidence": 0.97},
            {"name": "postgresql", "type": "database", "confidence": 0.95},
        ],
        "timeline": [
            {"time": "11:20:00", "event": "Connection pool exhausted", "type": "error"},
            {"time": "11:22:00", "event": "Query queuing detected", "type": "warning"},
            {"time": "11:25:00", "event": "Pool size increased to 200", "type": "info"},
            {"time": "11:35:00", "event": "Backlog cleared", "type": "success"},
            {"time": "11:48:00", "event": "Incident resolved", "type": "success"},
        ],
        "flow": {
            "id": "db_conn_pool",
            "name": "Database Connection Pool Analysis",
            "nodes": [
                {
                    "id": "saturn",
                    "label": "Saturn",
                    "status": "completed",
                    "description": "Report Level - Connection metrics",
                    "subSteps": [
                        {"id": "s1", "label": "Connection Count", "status": "completed"},
                        {"id": "s2", "label": "Pool Utilization", "status": "completed"},
                        {"id": "s3", "label": "Error Rate Check", "status": "completed"},
                    ],
                },
                {
                    "id": "datahub",
                    "label": "Data Hub",
                    "status": "completed",
                    "description": "Data Layer - Source analysis",
                    "subSteps": [
                        {"id": "d1", "label": "Query Pattern Analysis", "status": "completed"},
                        {"id": "d2", "label": "Connection Leak Check", "status": "completed"},
                    ],
                },
                {
                    "id": "ingestion",
                    "label": "Ingestion",
                    "status": "completed",
                    "description": "Ingestion Layer - Resolution",
                    "subSteps": [
                        {"id": "i1", "label": "Pool Expansion", "status": "completed"},
                        {"id": "i2", "label": "Connection Reset", "status": "completed"},
                        {"id": "i3", "label": "Recovery Verification", "status": "completed"},
                    ],
                },
            ],
            "rca": {
                "rootCause": "Sudden traffic spike caused database connection pool to max out at 100 connections",
                "confidence": 0.91,
                "causalChain": [
                    "Traffic spike from batch processing",
                    "All 100 connections consumed",
                    "New queries queued and timed out",
                    "Manual intervention to expand pool",
                    "Pool increased to 200, backlog cleared",
                ],
            },
            "evidence": [],
            "nextActions": [],
        },
        "investigation": {
            "runId": None,
            "status": "idle",
            "stepIndex": 0,
            "currentPhase": None,
            "feedback": [],
            "approved": None,
            "createdAt": None,
        },
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    },
]


async def seed_database():
    """Seed MongoDB with incident data. Skips if data already exists.
    NOTE: Does NOT close the connection — the caller (main.py startup) manages lifecycle."""
    collection = await get_incidents_collection()

    # Check if data already exists
    existing_count = await collection.count_documents({})
    if existing_count > 0:
        print(f"⚠️  Database already has {existing_count} incidents. Skipping seed.")
        return

    # Insert seed data
    result = await collection.insert_many(SEED_INCIDENTS)
    print(f"✅ Seeded {len(result.inserted_ids)} incidents into MongoDB")

    # Verify
    verify_count = await collection.count_documents({})
    print(f"📊 Total incidents in database: {verify_count}")


if __name__ == "__main__":
    asyncio.run(seed_database())

