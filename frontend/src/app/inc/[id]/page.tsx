'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { mockIncident, mockFlowNodes, mockLiveEvents, mockEvidence, mockRCAResult, mockBestNextActions, flowDefinitions } from '@/data/mockData';
import { FlowNode, LiveEvent, Evidence } from '@/types';
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
  const [events, setEvents] = useState<LiveEvent[]>(mockLiveEvents);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>(mockEvidence);
  const [isConnected, setIsConnected] = useState(true);
  const [eventCount, setEventCount] = useState(mockLiveEvents.length);
  const [analysisId, setAnalysisId] = useState<string | null>(null);

  useEffect(() => {
    setAnalysisId(incId + '-' + Date.now().toString(36));
  }, [incId]);

  // Get flow nodes based on incident flow or default
  const flowKey = Object.keys(flowDefinitions).find(k => incId.includes(k)) || 'eod_reporting';
  const flowNodes = flowDefinitions[flowKey] || mockFlowNodes;

  // Get incident data
  const incident = incId === 'INC-2026-07-20-001' ? mockIncident : {
    ...mockIncident,
    id: incId,
    flow: flowKey,
  };

  const handleNodeSelect = (node: FlowNode | null) => {
    setSelectedNode(node);
    setSelectedNodeId(node?.id || null);
  };

  const handleEvidenceFeedback = (evidenceId: string, feedback: 'useful' | 'wrong') => {
    setEvidenceList(prev =>
      prev.map(e => e.id === evidenceId ? { ...e, feedback } : e)
    );
  };

  const handleClearEvents = () => {
    setEvents([]);
    setEventCount(0);
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[var(--background)] overflow-hidden">
      {/* Header for Incident Page */}
      <Header
        incId={incId}
        flow={incident.flow}
        severity={incident.severity}
        duration={incident.duration}
        onBack={() => router.push('/')}
      />

      {/* Main Dashboard Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT PANEL (30%) */}
        <div className="w-[30%] min-w-[300px] border-r border-[var(--border)] flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <IncidentPanel incident={incident} selectedNode={selectedNode} />
          </div>
          <div className="overflow-y-auto max-h-[40%]">
            <RCAPanel rcaResult={mockRCAResult} bestNextActions={mockBestNextActions} />
          </div>
        </div>

        {/* CENTER PANEL (45%) */}
        <div className="w-[45%] min-w-[400px] flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <div className="h-full flex flex-col overflow-hidden">
              <div className="px-4 py-3 border-b border-[var(--border)] bg-[var(--surface)]">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-[var(--accent-light)] flex items-center gap-2">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="3" /><path d="M12 2v4" /><path d="M12 18v4" /><path d="M2 12h4" /><path d="M18 12h4" />
                    </svg>
                    Analysis Flow (DAG)
                  </h2>
                  <span className="text-[10px] text-[var(--muted)] bg-[var(--surface-light)] px-2 py-1 rounded">
                    Phase: {flowNodes.find(n => n.status === 'active')?.label || flowNodes[0]?.label || 'SATURN'}
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
            isConnected={isConnected}
            eventCount={eventCount}
            onClear={handleClearEvents}
          />
        </div>

        {/* RIGHT PANEL (25%) */}
        <div className="w-[25%] min-w-[250px] border-l border-[var(--border)] overflow-hidden">
          <EvidencePanel
            evidence={selectedNode ? evidenceList : []}
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

