/**
 * API Client for IncAnalyserAI Backend
 * All API calls made through Next.js rewrite proxy (/api/* -> backend:8000/api/*)
 */

const BASE_URL = '/api';

interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`API ${res.status}: ${errorBody || res.statusText}`);
  }

  return res.json();
}

// ─── Incidents ──────────────────────────────────────────────────────

export interface IncidentStats {
  total: number;
  investigating: number;
  resolved: number;
  open: number;
  high: number;
}

export interface IncidentListItem {
  id: string;
  title: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'open' | 'investigating' | 'resolved';
  flow: string;
  timestamp: string;
  duration: string;
}

export interface IncidentsResponse {
  incidents: IncidentListItem[];
  total: number;
  counts: IncidentStats;
}

export async function getIncidents(): Promise<IncidentsResponse> {
  return fetchApi<IncidentsResponse>('/incidents');
}

export async function getDashboardStats(): Promise<IncidentStats & { system_status: string }> {
  return fetchApi('/stats');
}

// ─── Single Incident ───────────────────────────────────────────────

export interface TimelineEvent {
  time: string;
  event: string;
  type: 'info' | 'warning' | 'error' | 'success';
}

export interface Entity {
  name: string;
  type: string;
  confidence: number;
}

export interface IncidentDetail {
  id: string;
  title: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'open' | 'investigating' | 'resolved';
  flow: string;
  timestamp: string;
  duration: string;
  originalText: string;
  triageSummary: string;
  entities: Entity[];
  timeline: TimelineEvent[];
}

export async function getIncident(incId: string): Promise<IncidentDetail> {
  return fetchApi<IncidentDetail>(`/incidents/${incId}`);
}

// ─── Flow DAG ──────────────────────────────────────────────────────

export interface SubStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'completed' | 'error' | 'skipped';
}

export interface FlowNode {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'completed' | 'error' | 'skipped';
  description: string;
  subSteps: SubStep[];
}

export interface FlowResponse {
  flowId: string;
  flowName: string;
  nodes: FlowNode[];
}

export async function getIncidentFlow(incId: string): Promise<FlowResponse> {
  return fetchApi<FlowResponse>(`/incidents/${incId}/flow`);
}

// ─── RCA ───────────────────────────────────────────────────────────

export interface RCAResult {
  rootCause: string;
  confidence: number;
  causalChain: string[];
}

export async function getIncidentRCA(incId: string): Promise<RCAResult> {
  return fetchApi<RCAResult>(`/incidents/${incId}/rca`);
}

// ─── Best Next Actions ─────────────────────────────────────────────

export interface BestNextAction {
  id: string;
  label: string;
  action: string;
  category: 'rerun' | 'recompute' | 'notify' | 'investigate';
}

export async function getIncidentActions(incId: string): Promise<{ actions: BestNextAction[] }> {
  return fetchApi<{ actions: BestNextAction[] }>(`/incidents/${incId}/actions`);
}

// ─── Evidence ──────────────────────────────────────────────────────

export interface Evidence {
  id: string;
  type: 'tool_call' | 'runbook' | 'similar_incident';
  content: string;
  status: 'success' | 'failed' | 'warning';
  details: string;
  feedback?: 'useful' | 'wrong';
}

export interface EvidenceResponse {
  evidence: Evidence[];
  total: number;
  node_id?: string;
}

export async function getEvidence(
  incId: string,
  nodeId?: string
): Promise<EvidenceResponse> {
  const query = nodeId ? `?node_id=${nodeId}` : '';
  return fetchApi<EvidenceResponse>(`/incidents/${incId}/evidence${query}`);
}

// ─── Live Events ───────────────────────────────────────────────────

export interface LiveEvent {
  timestamp: string;
  message: string;
  type: 'triage' | 'plan' | 'step' | 'rca' | 'info' | 'error';
}

export interface EventsResponse {
  events: LiveEvent[];
  connected: boolean;
  count: number;
  streaming: boolean;
}

export async function getIncidentEvents(incId: string): Promise<EventsResponse> {
  return fetchApi<EventsResponse>(`/incidents/${incId}/events`);
}

// ─── Dashboard (Aggregated) ────────────────────────────────────────

export interface DashboardResponse {
  incident: IncidentDetail;
  flow: FlowResponse | null;
  rca: RCAResult;
  actions: BestNextAction[];
  evidence: (Evidence & { node_id: string })[];
  events: LiveEvent[];
  analysis_id: string;
}

export async function getIncidentDashboard(incId: string): Promise<DashboardResponse> {
  return fetchApi<DashboardResponse>(`/incidents/${incId}/dashboard`);
}

// ─── Feedback / Approval ───────────────────────────────────────────

export async function submitEvidenceFeedback(
  incId: string,
  evidenceId: string,
  feedback: 'useful' | 'wrong'
): Promise<{ status: string; message: string; total_feedback: number }> {
  return fetchApi(`/incidents/${incId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ evidence_id: evidenceId, feedback }),
  });
}

export async function submitRCAFeedback(
  incId: string,
  feedback: 'useful' | 'not_useful',
  comment?: string
): Promise<{ status: string; message: string }> {
  return fetchApi(`/incidents/${incId}/rca-feedback`, {
    method: 'POST',
    body: JSON.stringify({ feedback, comment }),
  });
}

export async function approveRemediation(
  incId: string,
  approved: boolean,
  comment?: string
): Promise<{ status: string; message: string }> {
  return fetchApi(`/incidents/${incId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ approved, comment }),
  });
}

