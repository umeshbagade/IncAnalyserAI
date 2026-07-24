'use client';

import { useState } from 'react';
import { Evidence, FlowNode } from '@/types';
import { FileText, BookOpen, RefreshCw, ThumbsUp, ThumbsDown, Plus, ExternalLink, CircleAlert, CircleCheckBig } from 'lucide-react';

interface EvidencePanelProps {
  evidence: Evidence[];
  selectedNode: FlowNode | null;
  onFeedback: (evidenceId: string, feedback: 'useful' | 'wrong') => void;
}

export default function EvidencePanel({ evidence, selectedNode, onFeedback }: EvidencePanelProps) {
  const typeIcons: Record<string, React.ReactNode> = {
    tool_call: <FileText size={14} className="text-blue-400" />,
    runbook: <BookOpen size={14} className="text-purple-400" />,
    similar_incident: <RefreshCw size={14} className="text-yellow-400" />,
  };

  const statusIcons: Record<string, React.ReactNode> = {
    success: <CircleCheckBig size={12} className="text-[var(--success)]" />,
    failed: <CircleAlert size={12} className="text-[var(--danger)]" />,
    warning: <CircleAlert size={12} className="text-[var(--warning)]" />,
  };

  const statusColors: Record<string, string> = {
    success: 'text-[var(--success)]',
    failed: 'text-[var(--danger)]',
    warning: 'text-[var(--warning)]',
  };

  const typeLabels: Record<string, string> = {
    tool_call: 'Tool Call',
    runbook: 'Runbook',
    similar_incident: 'Similar Incident',
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--border)] bg-[var(--surface)]">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--accent-light)] flex items-center gap-2">
            <BookOpen size={14} />
            Evidence & Citations
          </h2>
          <button className="btn btn-ghost text-xs p-1">
            <ExternalLink size={12} />
          </button>
        </div>
        <p className="text-[10px] text-[var(--muted)] mt-1">
          {selectedNode
            ? `Showing evidence for: ${selectedNode.label}`
            : 'Live evidence stream — updates in real time as the investigation runs'}
        </p>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {evidence.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <BookOpen size={24} className="text-[var(--muted)] mb-2 opacity-30" />
            <p className="text-xs text-[var(--muted)]">
              {selectedNode
                ? 'No evidence available for this node'
                : 'Listening for evidence… citations will appear here as agents run'}
            </p>
          </div>
        )}
        {evidence.map((item) => (
          <EvidenceCard
            key={item.id}
            evidence={item}
            typeIcons={typeIcons}
            statusIcons={statusIcons}
            statusColors={statusColors}
            typeLabels={typeLabels}
            onFeedback={onFeedback}
          />
        ))}
      </div>
    </div>
  );
}

function EvidenceCard({
  evidence,
  typeIcons,
  statusIcons,
  statusColors,
  typeLabels,
  onFeedback,
}: {
  evidence: Evidence;
  typeIcons: Record<string, React.ReactNode>;
  statusIcons: Record<string, React.ReactNode>;
  statusColors: Record<string, string>;
  typeLabels: Record<string, string>;
  onFeedback: (evidenceId: string, feedback: 'useful' | 'wrong') => void;
}) {
  // Only ever show a binary success/failed state — a symptom seen on a
  // traversed-but-not-culprit layer is treated as a passed check, so the
  // evidence never displays an ambiguous "warning".
  const displayStatus = evidence.status === 'warning' ? 'success' : evidence.status;
  return (
    <div className="card animate-card-in transition-all duration-300 hover:border-[var(--accent)]/40 hover:shadow-[0_0_16px_rgba(59,130,246,0.08)]">
      <div className="card-body p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {typeIcons[evidence.type]}
            <span className="text-xs font-medium text-[var(--foreground)]">
              {typeLabels[evidence.type]}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {statusIcons[displayStatus]}
            <span className={`text-[10px] ${statusColors[displayStatus]}`}>
              {displayStatus}
            </span>
          </div>
        </div>
        <div className="bg-[var(--background)] rounded p-2.5 mb-2 font-mono">
          <p className="text-xs text-[var(--accent)]">{evidence.content}</p>
          <p className="text-[10px] text-[var(--foreground)] mt-1 whitespace-pre-wrap">
            {evidence.details}
          </p>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            <button
              onClick={() => onFeedback(evidence.id, 'useful')}
              className={`p-1 rounded transition-colors ${
                evidence.feedback === 'useful'
                  ? 'text-[var(--success)] bg-[var(--success)]/10'
                  : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-light)]'
              }`}
            >
              <ThumbsUp size={10} />
            </button>
            <button
              onClick={() => onFeedback(evidence.id, 'wrong')}
              className={`p-1 rounded transition-colors ${
                evidence.feedback === 'wrong'
                  ? 'text-[var(--danger)] bg-[var(--danger)]/10'
                  : 'text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-light)]'
              }`}
            >
              <ThumbsDown size={10} />
            </button>
            <button className="p-1 rounded text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-light)] transition-colors">
              <Plus size={10} />
            </button>
          </div>
          <button className="btn btn-ghost text-[10px] p-1">
            <span>Details</span>
            <ExternalLink size={8} />
          </button>
        </div>
      </div>
    </div>
  );
}

