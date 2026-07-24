/**
 * API Client for IncAnalyserAI Backend
 * 
 * All API calls to the FastAPI backend go through this module.
 * Uses relative URLs via Next.js proxy rewrites (see next.config.js)
 * to avoid CORS issues.
 */

const API_BASE = '';  // Relative — proxied via Next.js rewrites

// ─── Types ────────────────────────────────────────────────────────────────

export interface ApiIncidentSummary {
  id: string;
  title: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'open' | 'investigating' | 'resolved';
  flow: string;
  timestamp: string;
  duration: string;
}

export interface ApiIncidentDetail {
  id: string;
  title: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'open' | 'investigating' | 'resolved';
  flow: string;
  timestamp: string;
  duration: string;
  createdAt?: string;
  originalText: string;
  triageSummary: string;
  entities: Array<{ name: string; type: string; confidence: number }>;
  timeline: Array<{ time: string; event: string; type: 'info' | 'warning' | 'error' | 'success' }>;
}

export interface ApiFlowData {
  flowId: string;
  flowName: string;
  nodes: ApiFlowNode[];
}

export interface ApiFlowNode {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'completed' | 'error' | 'skipped';
  description: string;
  subSteps: Array<{
    id: string;
    label: string;
    status: 'pending' | 'active' | 'completed' | 'error' | 'skipped';
  }>;
}

export interface ApiRCAResult {
  rootCause: string;
  confidence: number;
  causalChain: string[];
}

export interface ApiAction {
  id: string;
  label: string;
  action: string;
  category: 'rerun' | 'recompute' | 'notify' | 'investigate';
}

export interface ApiEvidence {
  id: string;
  type: 'tool_call' | 'runbook' | 'similar_incident';
  content: string;
  status: 'success' | 'failed' | 'warning';
  details: string;
  feedback?: 'useful' | 'wrong';
  node_id?: string;
}

export interface ApiEvent {
  timestamp: string;
  message: string;
  type: 'triage' | 'plan' | 'step' | 'rca' | 'info' | 'error';
}

export interface ApiInvestigationStatus {
  status: 'idle' | 'running' | 'completed' | 'failed';
  currentPhase: string;
}

export interface ApiDashboard {
  incident: ApiIncidentDetail;
  flow: ApiFlowData | null;
  rca: ApiRCAResult;
  actions: ApiAction[];
  evidence: ApiEvidence[];
  events: ApiEvent[];
  investigation: ApiInvestigationStatus;
  analysis_id: string;
}

export interface ApiStats {
  total: number;
  investigating: number;
  resolved: number;
  open: number;
  high: number;
  system_status: string;
}

// ─── Generic Fetch Helper ─────────────────────────────────────────────────

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`API Error ${res.status}: ${errorBody || res.statusText}`);
  }

  return res.json();
}

// ─── API Functions ────────────────────────────────────────────────────────

/** GET /api/incidents — list all incident summaries */
export async function fetchIncidents(): Promise<{
  incidents: ApiIncidentSummary[];
  total: number;
  counts: Record<string, number>;
}> {
  return fetchApi('/api/incidents');
}

/** GET /api/incidents/{inc_id} — full incident detail */
export async function fetchIncidentDetail(incId: string): Promise<ApiIncidentDetail> {
  return fetchApi(`/api/incidents/${encodeURIComponent(incId)}`);
}

/** GET /api/incidents/{inc_id}/flow — flow DAG definition */
export async function fetchIncidentFlow(incId: string): Promise<ApiFlowData> {
  return fetchApi(`/api/incidents/${encodeURIComponent(incId)}/flow`);
}

/** GET /api/incidents/{inc_id}/rca — root cause analysis */
export async function fetchIncidentRCA(incId: string): Promise<ApiRCAResult> {
  return fetchApi(`/api/incidents/${encodeURIComponent(incId)}/rca`);
}

/** GET /api/incidents/{inc_id}/actions — best next actions */
export async function fetchIncidentActions(incId: string): Promise<{ actions: ApiAction[] }> {
  return fetchApi(`/api/incidents/${encodeURIComponent(incId)}/actions`);
}

/** GET /api/incidents/{inc_id}/evidence — evidence list */
export async function fetchIncidentEvidence(
  incId: string,
  nodeId?: string
): Promise<{ evidence: ApiEvidence[]; total: number }> {
  const query = nodeId ? `?node_id=${encodeURIComponent(nodeId)}` : '';
  return fetchApi(`/api/incidents/${encodeURIComponent(incId)}/evidence${query}`);
}

/** GET /api/incidents/{inc_id}/events — live events */
export async function fetchIncidentEvents(incId: string): Promise<{
  events: ApiEvent[];
  connected: boolean;
  count: number;
}> {
  return fetchApi(`/api/incidents/${encodeURIComponent(incId)}/events`);
}

/** GET /api/incidents/{inc_id}/dashboard — all data in one call */
export async function fetchIncidentDashboard(incId: string): Promise<ApiDashboard> {
  return fetchApi(`/api/incidents/${encodeURIComponent(incId)}/dashboard`);
}

/** POST /api/incidents/{inc_id}/feedback — submit evidence feedback */
export async function submitEvidenceFeedback(
  incId: string,
  evidenceId: string,
  feedback: 'useful' | 'wrong'
): Promise<{ status: string; message: string }> {
  return fetchApi(`/api/incidents/${encodeURIComponent(incId)}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ evidence_id: evidenceId, feedback }),
  });
}

/** POST /api/incidents/{inc_id}/rca-feedback — submit RCA feedback */
export async function submitRCAFeedback(
  incId: string,
  feedback: 'useful' | 'not_useful',
  comment?: string
): Promise<{ status: string; message: string }> {
  return fetchApi(`/api/incidents/${encodeURIComponent(incId)}/rca-feedback`, {
    method: 'POST',
    body: JSON.stringify({ feedback, comment }),
  });
}

/** POST /api/incidents/{inc_id}/approve — approve/reject remediation */
export async function approveRemediation(
  incId: string,
  approved: boolean,
  comment?: string
): Promise<{ status: string; message: string }> {
  return fetchApi(`/api/incidents/${encodeURIComponent(incId)}/approve`, {
    method: 'POST',
    body: JSON.stringify({ approved, comment }),
  });
}

/** GET /api/stats — dashboard statistics */
export async function fetchStats(): Promise<ApiStats> {
  return fetchApi('/api/stats');
}

/** GET /api/knowledge/flows — list all flow definitions */
export async function fetchFlowDefinitions(): Promise<{ flows: Array<{ id: string; name: string }>; total: number }> {
  return fetchApi('/api/knowledge/flows');
}

/** GET /api/knowledge/flows/{flow_id} — get specific flow definition */
export async function fetchFlowDefinition(flowId: string): Promise<ApiFlowData & { rca?: any; evidence?: any[]; nextActions?: any[] }> {
  return fetchApi(`/api/knowledge/flows/${encodeURIComponent(flowId)}`);
}


/** POST /api/incidents — create a new incident */
export async function createIncident(data: {
  title: string;
  description?: string;
  severity?: 'HIGH' | 'MEDIUM' | 'LOW';
  flowId?: string;
}): Promise<{ status: string; incident: ApiIncidentSummary }> {
  return fetchApi('/api/incidents', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}


// ═══════════════════════════════════════════════════════════════════════════
//  COMPATIBILITY EXPORTS (aliases used by existing page.tsx imports)
// ═══════════════════════════════════════════════════════════════════════════

export type IncidentListItem = ApiIncidentSummary;
export type IncidentStats = ApiStats;
export type DashboardResponse = ApiDashboard;

// Aliases used by existing page.tsx imports
export const getIncidents = fetchIncidents;
export const getDashboardStats = fetchStats;
export const getIncidentDashboard = fetchIncidentDashboard;
export const getEvidence = fetchIncidentEvidence;
export const getIncidentEvents = fetchIncidentEvents;

