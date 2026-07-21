import { Incident, FlowNode, LiveEvent, Evidence, RCAResult, BestNextAction, IncidentSummary } from '@/types';

export const mockIncidentSummaries: IncidentSummary[] = [
  {
    id: 'INC-2026-07-20-001',
    title: 'EOD Reporting Failure - Feed Load Timeout',
    severity: 'HIGH',
    status: 'investigating',
    flow: 'eod_reporting',
    timestamp: '2026-07-20 21:01:00',
    duration: '00:14:23',
  },
  {
    id: 'INC-2026-07-19-003',
    title: 'Risk Calculation Pipeline Failure',
    severity: 'HIGH',
    status: 'investigating',
    flow: 'risk_calc_pipeline',
    timestamp: '2026-07-19 14:30:00',
    duration: '00:42:10',
  },
  {
    id: 'INC-2026-07-18-007',
    title: 'Market Data Feed Stale',
    severity: 'MEDIUM',
    status: 'resolved',
    flow: 'market_data_ingest',
    timestamp: '2026-07-18 09:15:00',
    duration: '01:23:45',
  },
  {
    id: 'INC-2026-07-17-002',
    title: 'Report Generation Timeout',
    severity: 'LOW',
    status: 'resolved',
    flow: 'report_gen_service',
    timestamp: '2026-07-17 16:45:00',
    duration: '00:35:20',
  },
  {
    id: 'INC-2026-07-16-005',
    title: 'Database Connection Pool Exhausted',
    severity: 'HIGH',
    status: 'resolved',
    flow: 'db_conn_pool',
    timestamp: '2026-07-16 11:20:00',
    duration: '00:28:15',
  },
];

export const mockIncident: Incident = {
  id: 'INC-2026-07-20-001',
  title: 'EOD Reporting Failure - Feed Load Timeout',
  severity: 'HIGH',
  status: 'investigating',
  flow: 'eod_reporting',
  timestamp: '2026-07-20 21:01:00',
  duration: '00:14:23',
  originalText: `EOD batch job failed at 21:01 UTC. 
Feed "load_feed_alpha" timed out after 900 seconds. 
Affected reports: daily_pnl, risk_summary, exposure_report.
SLA breach imminent. Manual intervention required.`,
  triageSummary: `EOD reporting pipeline halted at Saturn stage. 
Feed load timeout in DataHub ingestion layer. 
Suspected SFTP connectivity issue with vendor data source. 
3 downstream reports blocked. Priority: P1 - High Business Impact.`,
  entities: [
    { name: 'eod_reporting', type: 'workflow', confidence: 0.98 },
    { name: 'load_feed_alpha', type: 'task', confidence: 0.95 },
    { name: 'daily_pnl', type: 'report', confidence: 0.92 },
    { name: 'risk_summary', type: 'report', confidence: 0.90 },
    { name: 'saturn', type: 'system', confidence: 0.88 },
    { name: 'datahub', type: 'system', confidence: 0.85 },
    { name: 'sftp', type: 'integration', confidence: 0.78 },
  ],
  timeline: [
    { time: '21:01:00', event: 'EOD batch triggered', type: 'info' },
    { time: '21:01:15', event: 'Saturn: Checking report count (expected: 47)', type: 'info' },
    { time: '21:03:22', event: 'Saturn: Report count mismatch - found 42/47', type: 'warning' },
    { time: '21:05:00', event: 'DataHub: Querying feed status for missing reports', type: 'info' },
    { time: '21:06:30', event: 'DataHub: Feed "load_feed_alpha" timed out', type: 'error' },
    { time: '21:08:15', event: 'Ingestion: SFTP connection check initiated', type: 'info' },
    { time: '21:09:00', event: 'Ingestion: Connection failed - timeout after 30s', type: 'error' },
    { time: '21:10:00', event: 'RCA: Identified SFTP vendor outage as root cause', type: 'success' },
  ],
};

export const mockFlowNodes: FlowNode[] = [
  {
    id: 'saturn',
    label: 'Saturn',
    status: 'completed',
    description: 'Report Level - Check report count & status',
    subSteps: [
      { id: 's1', label: 'Report Count Check', status: 'completed' },
      { id: 's2', label: 'Status Verification', status: 'completed' },
      { id: 's3', label: 'Anomaly Detection', status: 'completed' },
    ],
  },
  {
    id: 'datahub',
    label: 'Data Hub',
    status: 'active',
    description: 'Data Layer - Query feeds & data sources',
    subSteps: [
      { id: 'd1', label: 'Feed Status Query', status: 'completed' },
      { id: 'd2', label: 'Data Source Verification', status: 'active' },
      { id: 'd3', label: 'Data Quality Check', status: 'pending' },
    ],
  },
  {
    id: 'ingestion',
    label: 'Ingestion',
    status: 'pending',
    description: 'Ingestion Layer - Check connectivity & pipelines',
    subSteps: [
      { id: 'i1', label: 'SFTP Connection Test', status: 'pending' },
      { id: 'i2', label: 'Pipeline Status', status: 'pending' },
      { id: 'i3', label: 'Retry Mechanism', status: 'pending' },
    ],
  },
];

export const mockLiveEvents: LiveEvent[] = [
  { timestamp: '21:15:02', message: 'triage.done', type: 'triage' },
  { timestamp: '21:15:05', message: 'plan.ready (3 steps)', type: 'plan' },
  { timestamp: '21:15:09', message: 'step.done s1 - Report count verified', type: 'step' },
  { timestamp: '21:15:14', message: 'step.done s2 - Anomaly detected', type: 'step' },
  { timestamp: '21:15:18', message: 'step.done s3 - Escalated to DataHub', type: 'step' },
  { timestamp: '21:15:22', message: 'rca.ready - SFTP timeout identified', type: 'rca' },
];

export const mockEvidence: Evidence[] = [
  {
    id: 'e1',
    type: 'tool_call',
    content: 'airflow_get_dag_run',
    status: 'failed',
    details: 'status: FAILED\nfailed_tasks: [load_feed_alpha]',
  },
  {
    id: 'e2',
    type: 'runbook',
    content: 'rb_ingest_sftp_timeout.md',
    status: 'success',
    details: 'Runbook: SFTP timeout recovery procedure\nSteps: 1-5 applicable',
  },
  {
    id: 'e3',
    type: 'similar_incident',
    content: 'INC-2026-05-10',
    status: 'success',
    details: 'Similar SFTP timeout incident\nResolution: Vendor failover triggered',
    feedback: 'useful',
  },
];

export const mockRCAResult: RCAResult = {
  rootCause: 'Vendor SFTP server timeout - upstream data source unavailable due to network partition',
  confidence: 0.87,
  causalChain: [
    'Vendor SFTP server unresponsive (timeout after 900s)',
    'Feed "load_feed_alpha" failed to ingest data',
    '5 reports missing in Saturn: daily_pnl, risk_summary, exposure_report, var_calc, limit_check',
    'EOD batch reporting pipeline halted at DataHub stage',
    'SLA breach probability: 0.92 - escalation triggered',
  ],
};

export const mockBestNextActions: BestNextAction[] = [
  {
    id: 'b1',
    label: 'Rerun Airflow',
    action: 'airflow_rerun',
    category: 'rerun',
  },
  {
    id: 'b2',
    label: 'Recompute snapshot',
    action: 'recompute_snapshot',
    category: 'recompute',
  },
  {
    id: 'b3',
    label: 'Notify vendor',
    action: 'notify_vendor',
    category: 'notify',
  },
  {
    id: 'b4',
    label: 'Check backup feed',
    action: 'check_backup_feed',
    category: 'investigate',
  },
];

export const flowDefinitions: Record<string, FlowNode[]> = {
  eod_reporting: [
    {
      id: 'saturn',
      label: 'Saturn',
      status: 'completed',
      description: 'Report Level - Check report count & status',
      subSteps: [
        { id: 's1', label: 'Report Count Check', status: 'completed' },
        { id: 's2', label: 'Status Verification', status: 'completed' },
        { id: 's3', label: 'Anomaly Detection', status: 'completed' },
      ],
    },
    {
      id: 'datahub',
      label: 'Data Hub',
      status: 'active',
      description: 'Data Layer - Query feeds & data sources',
      subSteps: [
        { id: 'd1', label: 'Feed Status Query', status: 'completed' },
        { id: 'd2', label: 'Data Source Verification', status: 'active' },
        { id: 'd3', label: 'Data Quality Check', status: 'pending' },
      ],
    },
    {
      id: 'ingestion',
      label: 'Ingestion',
      status: 'pending',
      description: 'Ingestion Layer - Check connectivity & pipelines',
      subSteps: [
        { id: 'i1', label: 'SFTP Connection Test', status: 'pending' },
        { id: 'i2', label: 'Pipeline Status', status: 'pending' },
        { id: 'i3', label: 'Retry Mechanism', status: 'pending' },
      ],
    },
  ],
  risk_calc_pipeline: [
    {
      id: 'saturn',
      label: 'Saturn',
      status: 'error',
      description: 'Report Level - Check calculations',
      subSteps: [
        { id: 's1', label: 'VaR Calculation Check', status: 'completed' },
        { id: 's2', label: 'Limit Check', status: 'error' },
        { id: 's3', label: 'Exposure Report', status: 'pending' },
      ],
    },
    {
      id: 'datahub',
      label: 'Data Hub',
      status: 'pending',
      description: 'Data Layer - Risk data sources',
      subSteps: [
        { id: 'd1', label: 'Market Data Query', status: 'pending' },
        { id: 'd2', label: 'Position Data', status: 'pending' },
        { id: 'd3', label: 'Risk Factors', status: 'pending' },
      ],
    },
    {
      id: 'ingestion',
      label: 'Ingestion',
      status: 'pending',
      description: 'Ingestion Layer - Pipeline check',
      subSteps: [
        { id: 'i1', label: 'Pipeline Health', status: 'pending' },
        { id: 'i2', label: 'Data Quality', status: 'pending' },
        { id: 'i3', label: 'Retry', status: 'pending' },
      ],
    },
  ],
  market_data_ingest: [
    {
      id: 'saturn',
      label: 'Saturn',
      status: 'completed',
      description: 'Report Level - Market data freshness',
      subSteps: [
        { id: 's1', label: 'Freshness Check', status: 'completed' },
        { id: 's2', label: 'Staleness Detection', status: 'completed' },
        { id: 's3', label: 'Alert Verification', status: 'completed' },
      ],
    },
    {
      id: 'datahub',
      label: 'Data Hub',
      status: 'completed',
      description: 'Data Layer - Feed status',
      subSteps: [
        { id: 'd1', label: 'Feed Status', status: 'completed' },
        { id: 'd2', label: 'Data Quality', status: 'completed' },
        { id: 'd3', label: 'Pipeline Health', status: 'completed' },
      ],
    },
    {
      id: 'ingestion',
      label: 'Ingestion',
      status: 'completed',
      description: 'Ingestion Layer - Resolved by failover',
      subSteps: [
        { id: 'i1', label: 'Failover Check', status: 'completed' },
        { id: 'i2', label: 'Backup Feed', status: 'completed' },
        { id: 'i3', label: 'Recovery', status: 'completed' },
      ],
    },
  ],
};

