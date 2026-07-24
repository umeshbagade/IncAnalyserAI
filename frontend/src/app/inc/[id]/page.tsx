'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { FlowNode, LiveEvent, Evidence, Incident, RCAResult, BestNextAction } from '@/types';
import {
  getIncidentDashboard,
  submitEvidenceFeedback,
} from '@/lib/api';
import Header from '@/components/Header';
import IncidentPanel from '@/components/IncidentPanel';
import RCAPanel from '@/components/RCAPanel';
import FlowDAG from '@/components/FlowDAG';
import LiveEventStream from '@/components/LiveEventStream';
import EvidencePanel from '@/components/EvidencePanel';

export default function IncidentDashboard() {
  const params = useParams();
  const router = useRouter();
  const incId = params?.id as string || 'INC-2026-07-20-001';

  const [selectedNode, setSelectedNode] = useState<FlowNode | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [allEvidence, setAllEvidence] = useState<Evidence[]>([]);
  const [flowNodes, setFlowNodes] = useState<FlowNode[]>([]);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [rcaResult, setRcaResult] = useState<RCAResult | null>(null);
  const [bestNextActions, setBestNextActions] = useState<BestNextAction[]>([]);
  const [eventCount, setEventCount] = useState(0);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [investigationStatus, setInvestigationStatus] = useState<string>('idle');

  // Adjustable side-panel widths (px). Defaults mirror the original layout
  // (left 35%, right 25%, center 40%); set from the viewport on mount so the
  // starting proportions match what they were before the panels were resizable.
  const [leftWidth, setLeftWidth] = useState(420);
  const [rightWidth, setRightWidth] = useState(300);

  // Adjustable height (px) for the Root Cause Analysis panel in the left column.
  const [rcaHeight, setRcaHeight] = useState(420);

  useEffect(() => {
    setLeftWidth(Math.round(window.innerWidth * 0.35));
    setRightWidth(Math.round(window.innerWidth * 0.25));
  }, []);

  const isRunning = investigationStatus === 'running';

  useEffect(() => {
    setAnalysisId(incId + '-' + Date.now().toString(36));
  }, [incId]);

  // Single loader used for both the initial fetch and live polling.
  const loadDashboard = useCallback(async (isInitial: boolean) => {
    try {
      const dashboard = await getIncidentDashboard(incId);
      setIncident(dashboard.incident as Incident);
      if (dashboard.flow) {
        setFlowNodes(dashboard.flow.nodes as FlowNode[]);
      }
      setRcaResult(dashboard.rca as RCAResult);
      setBestNextActions(dashboard.actions as BestNextAction[]);
      setAllEvidence(dashboard.evidence as Evidence[]);
      setEvents(dashboard.events as LiveEvent[]);
      setEventCount(dashboard.events.length);
      setInvestigationStatus(dashboard.investigation?.status ?? 'idle');
    } catch (err) {
      console.error('Failed to fetch incident dashboard:', err);
    } finally {
      if (isInitial) setLoading(false);
    }
  }, [incId]);

  // Initial load.
  useEffect(() => {
    setLoading(true);
    loadDashboard(true);
  }, [incId, loadDashboard]);

  // Live polling while the investigation is running. Poll quickly so each
  // streamed stage (Saturn -> Data Hub -> Ingestion) and its evidence appear
  // in near real time rather than jumping straight to the final result.
  useEffect(() => {
    if (!isRunning) return;
    const timer = setInterval(() => loadDashboard(false), 700);
    return () => clearInterval(timer);
  }, [isRunning, loadDashboard]);

  const handleNodeSelect = (node: FlowNode | null) => {
    setSelectedNode(node);
    setSelectedNodeId(node?.id || null);
  };

  const handleEvidenceFeedback = async (evidenceId: string, feedback: 'useful' | 'wrong') => {
    try {
      await submitEvidenceFeedback(incId, evidenceId, feedback);
      setAllEvidence(prev =>
        prev.map(e => e.id === evidenceId ? { ...e, feedback } : e)
      );
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };

  const handleClearEvents = () => {
    setEvents([]);
    setEventCount(0);
  };

  // Drag-to-resize for the left/right side panels. On mousedown we track the
  // pointer on the document until release, clamping each panel to a sensible
  // min/max so the center panel always keeps room.
  const startResize = useCallback((side: 'left' | 'right') => (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startLeft = leftWidth;
    const startRight = rightWidth;
    const onMove = (ev: MouseEvent) => {
      if (side === 'left') {
        setLeftWidth(Math.min(Math.max(startLeft + (ev.clientX - startX), 280), 700));
      } else {
        setRightWidth(Math.min(Math.max(startRight - (ev.clientX - startX), 240), 640));
      }
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [leftWidth, rightWidth]);

  // Drag-to-resize the Root Cause Analysis panel height (vertical).
  const startRcaResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startH = rcaHeight;
    const onMove = (ev: MouseEvent) => {
      setRcaHeight(Math.min(Math.max(startH + (startY - ev.clientY), 140), Math.round(window.innerHeight * 0.75)));
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
  }, [rcaHeight]);

  // Evidence shown in the right panel. When a node is selected we scope to that
  // node; otherwise we show the full live stream of evidence as it accumulates,
  // so the user sees citations appear in real time without having to click.
  const nodeEvidence = selectedNode
    ? allEvidence.filter(e => e.node_id === selectedNode.id)
    : allEvidence;

  if (loading || !incident) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-[var(--background)]">
        <div className="flex items-center gap-3 text-[var(--muted)]">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Loading incident {incId}...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-[var(--background)] overflow-hidden">
      {/* Header for Incident Page */}
      <Header
        incId={incId}
        flow={incident.flow}
        severity={incident.severity}
        duration={incident.duration}
        createdAt={incident.createdAt}
        onBack={() => router.push('/')}
      />

      {/* Main Dashboard Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT PANEL (resizable) */}
        <div style={{ width: leftWidth }} className="shrink-0 flex flex-col overflow-hidden">
          <div className="flex-1 min-h-0 overflow-hidden">
            <IncidentPanel incident={incident} selectedNode={selectedNode} isLive={isRunning} />
          </div>
          {rcaResult && (
            <>
              {/* RCA vertical resize handle */}
              <div
                onMouseDown={startRcaResize}
                title="Drag to resize"
                className="h-1.5 shrink-0 cursor-row-resize bg-[var(--border)] hover:bg-[var(--accent)] transition-colors"
              />
              <div style={{ height: rcaHeight }} className="shrink-0 overflow-y-auto">
                <RCAPanel rcaResult={rcaResult} bestNextActions={bestNextActions} />
              </div>
            </>
          )}
        </div>

        {/* LEFT resize handle */}
        <div
          onMouseDown={startResize('left')}
          title="Drag to resize"
          className="w-1.5 shrink-0 cursor-col-resize bg-[var(--border)] hover:bg-[var(--accent)] transition-colors"
        />

        {/* CENTER PANEL (flexes to fill) */}
        <div className="flex-1 min-w-[320px] flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <div className="h-full flex flex-col overflow-hidden">
              <div className="px-4 py-3 border-b border-[var(--border)] bg-[var(--surface)]">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-[var(--accent-light)] flex items-center gap-2">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="3" /><path d="M12 2v4" /><path d="M12 18v4" /><path d="M2 12h4" /><path d="M18 12h4" />
                    </svg>
                    Analysis Flow (DAG)
                    {isRunning && (
                      <span className="flex items-center gap-1 text-[10px] text-[var(--accent)] bg-[var(--accent)]/10 px-2 py-0.5 rounded-full">
                        <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse" />
                        LIVE
                      </span>
                    )}
                  </h2>
                  <span className="text-[10px] text-[var(--muted)] bg-[var(--surface-light)] px-2 py-1 rounded">
                    Phase: {
                      selectedNode?.label
                      || flowNodes.find(n => n.status === 'active')?.label
                      || flowNodes.find(n => n.status === 'error')?.label
                      || flowNodes[flowNodes.length - 1]?.label
                      || 'SATURN'
                    }
                  </span>
                </div>
              </div>
              <FlowDAG
                nodes={flowNodes}
                onNodeSelect={handleNodeSelect}
                selectedNodeId={selectedNodeId}
              />
            </div>
          </div>
          <LiveEventStream
            events={events}
            isConnected={isRunning}
            eventCount={eventCount}
            onClear={handleClearEvents}
          />
        </div>

        {/* RIGHT resize handle */}
        <div
          onMouseDown={startResize('right')}
          title="Drag to resize"
          className="w-1.5 shrink-0 cursor-col-resize bg-[var(--border)] hover:bg-[var(--accent)] transition-colors"
        />

        {/* RIGHT PANEL (resizable) */}
        <div style={{ width: rightWidth }} className="shrink-0 overflow-hidden">
          <EvidencePanel
            evidence={nodeEvidence}
            selectedNode={selectedNode}
            onFeedback={handleEvidenceFeedback}
          />
        </div>
      </div>

      {/* Footer */}
      <footer className="h-8 bg-[var(--surface)] border-t border-[var(--border)] flex items-center justify-between px-4 text-[10px] text-[var(--muted)] shrink-0">
        <span>OpsAssistantAI v0.1.0</span>
        <span>Analysis ID: {analysisId || 'generating...'}</span>
      </footer>
    </div>
  );
}

