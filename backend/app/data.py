"""Comprehensive mock data fully in sync with frontend mockData.ts and types.ts."""

# ─── Incident Summaries (for Home Page Dashboard) ─────────────────────

INCIDENT_SUMMARIES = [
    {
        "id": "INC-2026-07-20-001",
        "title": "EOD Reporting Failure - Feed Load Timeout",
        "severity": "HIGH",
        "status": "investigating",
        "flow": "eod_reporting",
        "timestamp": "2026-07-20 21:01:00",
        "duration": "00:14:23",
    },
    {
        "id": "INC-2026-07-19-003",
        "title": "Risk Calculation Pipeline Failure",
        "severity": "HIGH",
        "status": "investigating",
        "flow": "risk_calc_pipeline",
        "timestamp": "2026-07-19 14:30:00",
        "duration": "00:42:10",
    },
    {
        "id": "INC-2026-07-18-007",
        "title": "Market Data Feed Stale",
        "severity": "MEDIUM",
        "status": "resolved",
        "flow": "market_data_ingest",
        "timestamp": "2026-07-18 09:15:00",
        "duration": "01:23:45",
    },
    {
        "id": "INC-2026-07-17-002",
        "title": "Report Generation Timeout",
        "severity": "LOW",
        "status": "resolved",
        "flow": "report_gen_service",
        "timestamp": "2026-07-17 16:45:00",
        "duration": "00:35:20",
    },
    {
        "id": "INC-2026-07-16-005",
        "title": "Database Connection Pool Exhausted",
        "severity": "HIGH",
        "status": "resolved",
        "flow": "db_conn_pool",
        "timestamp": "2026-07-16 11:20:00",
        "duration": "00:28:15",
    },
]


# ─── Full Incident Details ────────────────────────────────────────────

INCIDENTS = {
    "INC-2026-07-20-001": {
        "id": "INC-2026-07-20-001",
        "title": "EOD Reporting Failure - Feed Load Timeout",
        "severity": "HIGH",
        "status": "investigating",
        "flow": "eod_reporting",
        "timestamp": "2026-07-20 21:01:00",
        "duration": "00:14:23",
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
    },
    "INC-2026-07-19-003": {
        "id": "INC-2026-07-19-003",
        "title": "Risk Calculation Pipeline Failure",
        "severity": "HIGH",
        "status": "investigating",
        "flow": "risk_calc_pipeline",
        "timestamp": "2026-07-19 14:30:00",
        "duration": "00:42:10",
        "originalText": "Risk calculation pipeline failed at 14:30 UTC.\nVaR computation returned NaN for 3 portfolios.\nLimit check triggered incorrectly.\nAffected: risk_summary, var_calc, limit_check.",
        "triageSummary": "Risk calculation pipeline halted at Saturn stage.\nSuspected stale market data causing incorrect risk calculations.\nPosition data feed may be delayed. Priority: P1 - High Business Impact.",
        "entities": [
            {"name": "risk_calc_pipeline", "type": "workflow", "confidence": 0.97},
            {"name": "var_calc", "type": "report", "confidence": 0.93},
            {"name": "limit_check", "type": "task", "confidence": 0.90},
            {"name": "saturn", "type": "system", "confidence": 0.85},
            {"name": "market_data", "type": "system", "confidence": 0.82},
        ],
        "timeline": [
            {"time": "14:30:00", "event": "Risk pipeline triggered", "type": "info"},
            {"time": "14:31:20", "event": "Saturn: VaR calculation started", "type": "info"},
            {"time": "14:33:45", "event": "Saturn: VaR NaN for portfolio P1, P2, P3", "type": "error"},
            {"time": "14:35:00", "event": "Saturn: Limit check breach detected", "type": "warning"},
            {"time": "14:36:30", "event": "DataHub: Market data staleness detected (45min delay)", "type": "error"},
            {"time": "14:38:00", "event": "RCA: Identified stale market data feed", "type": "success"},
        ],
    },
    "INC-2026-07-18-007": {
        "id": "INC-2026-07-18-007",
        "title": "Market Data Feed Stale",
        "severity": "MEDIUM",
        "status": "resolved",
        "flow": "market_data_ingest",
        "timestamp": "2026-07-18 09:15:00",
        "duration": "01:23:45",
        "originalText": "Market data feed stale detected at 09:15 UTC.\nPrimary Bloomberg feed unresponsive for 15 minutes.\nBackup feed activated automatically.",
        "triageSummary": "Market data feed stale for 45 minutes.\nPrimary feed had connectivity issues. Failed over to backup.\nAll downstream systems recovered.",
        "entities": [
            {"name": "market_data_ingest", "type": "workflow", "confidence": 0.96},
            {"name": "bloomberg", "type": "system", "confidence": 0.94},
            {"name": "backup_feed", "type": "system", "confidence": 0.88},
        ],
        "timeline": [
            {"time": "09:15:00", "event": "Stale data alert triggered", "type": "warning"},
            {"time": "09:16:30", "event": "Saturn: Data freshness check - FAILED", "type": "error"},
            {"time": "09:18:00", "event": "DataHub: Feed connectivity test - timeout", "type": "error"},
            {"time": "09:20:00", "event": "Ingestion: Failover to backup feed", "type": "info"},
            {"time": "09:25:00", "event": "Backup feed operational - data flowing", "type": "success"},
            {"time": "09:30:00", "event": "RCA: Primary Bloomberg network partition", "type": "success"},
        ],
    },
}


# ─── Flow Definitions ─────────────────────────────────────────────────

FLOW_DEFINITIONS = {
    "eod_reporting": {
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
    },
    "risk_calc_pipeline": {
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
    },
    "market_data_ingest": {
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
    },
    "report_gen_service": {
        "id": "report_gen_service",
        "name": "Report Generation Service",
        "nodes": [
            {
                "id": "saturn",
                "label": "Saturn",
                "status": "completed",
                "description": "Report Level - Generation status",
                "subSteps": [
                    {"id": "s1", "label": "Report Queue Check", "status": "completed"},
                    {"id": "s2", "label": "Generation Status", "status": "completed"},
                    {"id": "s3", "label": "Timeout Detection", "status": "completed"},
                ],
            },
            {
                "id": "datahub",
                "label": "Data Hub",
                "status": "completed",
                "description": "Data Layer - Template & data check",
                "subSteps": [
                    {"id": "d1", "label": "Template Availability", "status": "completed"},
                    {"id": "d2", "label": "Data Source Check", "status": "completed"},
                ],
            },
            {
                "id": "ingestion",
                "label": "Ingestion",
                "status": "pending",
                "description": "Ingestion Layer - Concurrency check",
                "subSteps": [
                    {"id": "i1", "label": "Concurrency Limit", "status": "pending"},
                    {"id": "i2", "label": "Resource Allocation", "status": "pending"},
                ],
            },
        ],
    },
    "db_conn_pool": {
        "id": "db_conn_pool",
        "name": "Database Connection Pool",
        "nodes": [
            {
                "id": "saturn",
                "label": "Saturn",
                "status": "completed",
                "description": "Report Level - Connection health",
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
                "description": "Data Layer - Database health",
                "subSteps": [
                    {"id": "d1", "label": "Active Connections", "status": "completed"},
                    {"id": "d2", "label": "Query Performance", "status": "completed"},
                ],
            },
            {
                "id": "ingestion",
                "label": "Ingestion",
                "status": "completed",
                "description": "Ingestion Layer - Pool reset",
                "subSteps": [
                    {"id": "i1", "label": "Connection Drain", "status": "completed"},
                    {"id": "i2", "label": "Pool Reset", "status": "completed"},
                    {"id": "i3", "label": "Verification", "status": "completed"},
                ],
            },
        ],
    },
}


# ─── Evidence Data (per flow, per node) ───────────────────────────────

EVIDENCE_BY_FLOW = {
    "eod_reporting": {
        "saturn": [
            {
                "id": "e1",
                "type": "tool_call",
                "content": "airflow_get_dag_run",
                "status": "success",
                "details": "status: SUCCESS\ndag_id: eod_reporting\nrun_count: 47 expected, 42 found",
            },
            {
                "id": "e2",
                "type": "tool_call",
                "content": "saturn_check_report_count",
                "status": "warning",
                "details": "report_count: 42/47\nmissing: [daily_pnl, risk_summary, exposure_report, var_calc, limit_check]",
            },
        ],
        "datahub": [
            {
                "id": "e3",
                "type": "tool_call",
                "content": "airflow_get_dag_run",
                "status": "failed",
                "details": "status: FAILED\nfailed_tasks: [load_feed_alpha]\nerror: Timeout after 900s",
            },
            {
                "id": "e4",
                "type": "runbook",
                "content": "rb_ingest_sftp_timeout.md",
                "status": "success",
                "details": "Runbook: SFTP timeout recovery procedure\nSteps: 1-5 applicable\nEstimated resolution time: 15min",
            },
            {
                "id": "e5",
                "type": "similar_incident",
                "content": "INC-2026-05-10",
                "status": "success",
                "details": "Similar SFTP timeout incident\nResolution: Vendor failover triggered\nRecovery time: 12min",
                "feedback": "useful",
            },
        ],
        "ingestion": [
            {
                "id": "e6",
                "type": "tool_call",
                "content": "sftp_connectivity_test",
                "status": "failed",
                "details": "host: vendor-sftp.example.com\ntimeout: 30s\nresult: CONNECTION_FAILED",
            },
            {
                "id": "e7",
                "type": "tool_call",
                "content": "vendor_status_api",
                "status": "warning",
                "details": "vendor: AcmeData Inc.\nstatus: DEGRADED\nincident: Network partition in us-east-1",
            },
            {
                "id": "e8",
                "type": "runbook",
                "content": "rb_vendor_failover.md",
                "status": "success",
                "details": "Runbook: Vendor failover procedure\nBackup vendor: AcmeData Backup (eu-west-1)\nSteps: 1-3 applicable",
            },
        ],
    },
    "risk_calc_pipeline": {
        "saturn": [
            {
                "id": "r1",
                "type": "tool_call",
                "content": "var_calculation_check",
                "status": "failed",
                "details": "portfolios: P1, P2, P3\nresult: NaN\nreason: Zero/negative weights detected",
            },
            {
                "id": "r2",
                "type": "tool_call",
                "content": "limit_check_query",
                "status": "warning",
                "details": "limits: 3 breached\nbreaches: P1_Market, P2_Credit, P3_Concentration",
            },
        ],
        "datahub": [
            {
                "id": "r3",
                "type": "tool_call",
                "content": "market_data_freshness",
                "status": "failed",
                "details": "feeds: bloomberg, reuters\nstaleness: 45min\nthreshold: 15min",
            },
            {
                "id": "r4",
                "type": "similar_incident",
                "content": "INC-2026-04-22",
                "status": "success",
                "details": "Similar stale market data incident\nResolution: Restart market data gateway\nRecovery time: 20min",
            },
        ],
        "ingestion": [
            {
                "id": "r5",
                "type": "tool_call",
                "content": "md_gateway_health",
                "status": "failed",
                "details": "gateway: md-gateway-01\nstatus: UNHEALTHY\nconnections: 0/8",
            },
        ],
    },
    "market_data_ingest": {
        "saturn": [
            {
                "id": "m1",
                "type": "tool_call",
                "content": "freshness_check_query",
                "status": "failed",
                "details": "feed: bloomberg (primary)\nlast_update: 09:00 UTC\nthreshold: 09:15 UTC → STALE",
            },
        ],
        "datahub": [
            {
                "id": "m2",
                "type": "tool_call",
                "content": "feed_connectivity_test",
                "status": "failed",
                "details": "endpoint: bloomberg-src.example.com\nresult: CONNECTION_TIMEOUT\ntimeout: 10s",
            },
        ],
        "ingestion": [
            {
                "id": "m3",
                "type": "runbook",
                "content": "rb_feed_failover.md",
                "status": "success",
                "details": "Runbook: Feed failover procedure\nBackup: reuters backup feed activated\nStatus: OPERATIONAL",
            },
            {
                "id": "m4",
                "type": "tool_call",
                "content": "backup_feed_status",
                "status": "success",
                "details": "feed: reuters_backup\nstatus: OPERATIONAL\nlatency: 200ms (normal)",
            },
        ],
    },
}


# ─── RCA Results (per flow) ───────────────────────────────────────────

RCA_RESULTS = {
    "eod_reporting": {
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
    "risk_calc_pipeline": {
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
    "market_data_ingest": {
        "rootCause": "Primary Bloomberg data feed network partition - automatic failover to backup feed successful",
        "confidence": 0.95,
        "causalChain": [
            "Bloomberg feed connection timeout after 10s",
            "Primary feed declared unhealthy",
            "Automatic failover to Reuters backup feed triggered",
            "Backup feed operational within 5 minutes",
            "All downstream systems recovered - incident resolved",
        ],
    },
    "report_gen_service": {
        "rootCause": "Concurrent report generation limit exceeded - 15 concurrent requests blocked queue",
        "confidence": 0.89,
        "causalChain": [
            "15 simultaneous report requests at 16:45 UTC",
            "Maximum concurrency limit (10) exceeded",
            "Queue backup of 5 reports",
            "Oldest request timed out after 300s",
            "Report generation service halted",
        ],
    },
    "db_conn_pool": {
        "rootCause": "Database connection pool exhausted due to unclosed connections from application pods",
        "confidence": 0.91,
        "causalChain": [
            "Application deployment caused connection leak",
            "Active connections increased from 50 to 200",
            "Connection pool max (100) exceeded",
            "New connections blocked - pool exhausted",
            "Database query failures cascaded to all dependent services",
        ],
    },
}


# ─── Best Next Actions (per flow) ─────────────────────────────────────

BEST_NEXT_ACTIONS = {
    "eod_reporting": [
        {"id": "b1", "label": "Rerun Airflow", "action": "airflow_rerun", "category": "rerun"},
        {"id": "b2", "label": "Recompute snapshot", "action": "recompute_snapshot", "category": "recompute"},
        {"id": "b3", "label": "Notify vendor", "action": "notify_vendor", "category": "notify"},
        {"id": "b4", "label": "Check backup feed", "action": "check_backup_feed", "category": "investigate"},
    ],
    "risk_calc_pipeline": [
        {"id": "r1", "label": "Rerun VaR calculation", "action": "rerun_var", "category": "rerun"},
        {"id": "r2", "label": "Restart MD gateway", "action": "restart_md_gateway", "category": "recompute"},
        {"id": "r3", "label": "Notify risk team", "action": "notify_risk_team", "category": "notify"},
        {"id": "r4", "label": "Check backup data feed", "action": "check_backup_feed", "category": "investigate"},
    ],
    "market_data_ingest": [
        {"id": "m1", "label": "Verify backup feed", "action": "verify_backup", "category": "investigate"},
        {"id": "m2", "label": "Investigate primary", "action": "investigate_bloomberg", "category": "investigate"},
        {"id": "m3", "label": "Notify trading desk", "action": "notify_trading", "category": "notify"},
    ],
    "report_gen_service": [
        {"id": "g1", "label": "Clear report queue", "action": "clear_queue", "category": "rerun"},
        {"id": "g2", "label": "Increase concurrency limit", "action": "increase_concurrency", "category": "recompute"},
        {"id": "g3", "label": "Notify report consumers", "action": "notify_consumers", "category": "notify"},
    ],
    "db_conn_pool": [
        {"id": "d1", "label": "Kill idle connections", "action": "kill_idle", "category": "rerun"},
        {"id": "d2", "label": "Increase pool size", "action": "increase_pool", "category": "recompute"},
        {"id": "d3", "label": "Rollback app deployment", "action": "rollback_deploy", "category": "investigate"},
    ],
}


# ─── Live Events (SSE simulation) ─────────────────────────────────────

LIVE_EVENTS = {
    "eod_reporting": [
        {"timestamp": "21:15:02", "message": "triage.done", "type": "triage"},
        {"timestamp": "21:15:05", "message": "plan.ready (3 steps)", "type": "plan"},
        {"timestamp": "21:15:09", "message": "step.done s1 - Report count verified", "type": "step"},
        {"timestamp": "21:15:14", "message": "step.done s2 - Anomaly detected", "type": "step"},
        {"timestamp": "21:15:18", "message": "step.done s3 - Escalated to DataHub", "type": "step"},
        {"timestamp": "21:15:22", "message": "rca.ready - SFTP timeout identified", "type": "rca"},
    ],
    "risk_calc_pipeline": [
        {"timestamp": "14:35:01", "message": "triage.done", "type": "triage"},
        {"timestamp": "14:35:04", "message": "plan.ready (3 steps)", "type": "plan"},
        {"timestamp": "14:35:08", "message": "step.done s1 - VaR check completed", "type": "step"},
        {"timestamp": "14:35:13", "message": "step.error s2 - Limit check failed", "type": "error"},
        {"timestamp": "14:35:18", "message": "rca.ready - Stale market data", "type": "rca"},
    ],
    "market_data_ingest": [
        {"timestamp": "09:20:01", "message": "triage.done", "type": "triage"},
        {"timestamp": "09:20:05", "message": "plan.ready - Failover initiated", "type": "plan"},
        {"timestamp": "09:20:10", "message": "step.done - Backup feed activated", "type": "step"},
        {"timestamp": "09:25:00", "message": "step.done - Data flowing on backup", "type": "step"},
        {"timestamp": "09:25:30", "message": "rca.ready - Primary network issue", "type": "rca"},
    ],
}


# ─── Helper to get flow ID from incident ID ──────────────────────────

def get_flow_for_incident(incident_id: str) -> str:
    """Map incident ID to flow key. Matches frontend logic in inc/[id]/page.tsx."""
    incident = INCIDENTS.get(incident_id)
    if incident:
        return incident["flow"]
    for key in FLOW_DEFINITIONS:
        if key in incident_id.lower():
            return key
    return "eod_reporting"


def get_default_rca() -> dict:
    return {
        "rootCause": "No root cause identified",
        "confidence": 0.5,
        "causalChain": ["Investigation in progress..."],
    }


def get_default_actions() -> list:
    return [
        {"id": "default_1", "label": "Review logs", "action": "review_logs", "category": "investigate"},
        {"id": "default_2", "label": "Escalate to on-call", "action": "escalate", "category": "notify"},
    ]

