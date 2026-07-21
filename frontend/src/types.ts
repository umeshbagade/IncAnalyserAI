export interface Incident {
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

export interface Entity {
  name: string;
  type: string;
  confidence: number;
}

export interface TimelineEvent {
  time: string;
  event: string;
  type: 'info' | 'warning' | 'error' | 'success';
}

export interface FlowNode {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'completed' | 'error' | 'skipped';
  description: string;
  subSteps: SubStep[];
}

export interface SubStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'completed' | 'error' | 'skipped';
}

export interface LiveEvent {
  timestamp: string;
  message: string;
  type: 'triage' | 'plan' | 'step' | 'rca' | 'info' | 'error';
}

export interface Evidence {
  id: string;
  type: 'tool_call' | 'runbook' | 'similar_incident';
  content: string;
  status: 'success' | 'failed' | 'warning';
  details: string;
  feedback?: 'useful' | 'wrong';
}

export interface RCAResult {
  rootCause: string;
  confidence: number;
  causalChain: string[];
}

export interface BestNextAction {
  id: string;
  label: string;
  action: string;
  category: 'rerun' | 'recompute' | 'notify' | 'investigate';
}

export interface IncidentSummary {
  id: string;
  title: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'open' | 'investigating' | 'resolved';
  flow: string;
  timestamp: string;
  duration: string;
}

