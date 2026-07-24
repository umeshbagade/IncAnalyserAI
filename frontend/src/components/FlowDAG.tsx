'use client';

import { FlowNode } from '@/types';
import {
  CircleCheckBig,
  LoaderCircle,
  Clock,
  AlertCircle,
  SkipForward,
  ChevronRight,
  ChevronDown,
} from 'lucide-react';

interface FlowDAGProps {
  nodes: FlowNode[];
  onNodeSelect: (node: FlowNode | null) => void;
  selectedNodeId: string | null;
}

export default function FlowDAG({ nodes, onNodeSelect, selectedNodeId }: FlowDAGProps) {
  const statusIcons: Record<string, React.ReactNode> = {
    completed: <CircleCheckBig size={16} className="text-[var(--success)]" />,
    active: <LoaderCircle size={16} className="text-[var(--accent)] animate-spin" />,
    pending: <Clock size={16} className="text-[var(--muted)]" />,
    error: <AlertCircle size={16} className="text-[var(--danger)]" />,
    skipped: <SkipForward size={16} className="text-[var(--muted)]" />,
  };

  const statusColors: Record<string, string> = {
    completed: 'border-[var(--success)] bg-[var(--success)]/10',
    active: 'border-[var(--accent)] bg-[var(--accent)]/10 node-active',
    pending: 'border-[var(--border)] bg-[var(--surface-light)]/30',
    error: 'border-[var(--danger)] bg-[var(--danger)]/10 node-error',
    skipped: 'border-[var(--border)] bg-[var(--surface-light)]/30 opacity-50',
  };

  const statusTextColors: Record<string, string> = {
    completed: 'text-[var(--success)]',
    active: 'text-[var(--accent)]',
    pending: 'text-[var(--muted)]',
    error: 'text-[var(--danger)]',
    skipped: 'text-[var(--muted)]',
  };

  const subStepStatusColors: Record<string, string> = {
    completed: 'bg-[var(--success)]',
    active: 'bg-[var(--accent)] animate-pulse',
    pending: 'bg-[var(--border)]',
    error: 'bg-[var(--danger)]',
    skipped: 'bg-[var(--border)] opacity-50',
  };

  // Connector colour follows the status of the node it flows out of.
  const connectorColor = (status: string) => {
    if (status === 'completed') return 'text-[var(--success)]';
    if (status === 'active') return 'text-[var(--accent)]';
    if (status === 'error') return 'text-[var(--danger)]';
    return 'text-[var(--border)]';
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {nodes.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center text-center gap-3 py-16">
          <LoaderCircle size={28} className="text-[var(--accent)] animate-spin" />
          <div>
            <p className="text-sm font-medium text-[var(--accent-light)]">Initializing investigation…</p>
            <p className="text-[11px] text-[var(--muted)] mt-1">
              Agents are triaging the incident. Analysis stages will appear here one at a time.
            </p>
          </div>
        </div>
      ) : (
        <div className="max-w-lg mx-auto">
          {nodes.map((node, idx) => (
            <div key={node.id} className="animate-node-in">
              <button
                onClick={() => onNodeSelect(selectedNodeId === node.id ? null : node)}
                className={`w-full p-4 rounded-lg border transition-all duration-500 ease-out cursor-pointer text-left
                  ${statusColors[node.status]}
                  ${selectedNodeId === node.id ? 'ring-1 ring-[var(--accent)]/50' : ''}
                  hover:brightness-110
                `}
              >
                <div className="flex items-center gap-3">
                  {statusIcons[node.status]}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-semibold transition-colors duration-500 ${statusTextColors[node.status]}`}>
                        {node.label}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded uppercase transition-colors duration-500 ${statusTextColors[node.status]} bg-current/10`}>
                        {node.status}
                      </span>
                    </div>
                    <p className="text-[10px] text-[var(--muted)] mt-0.5">{node.description}</p>
                  </div>
                  <span className="text-[9px] text-[var(--muted)] uppercase tracking-wider shrink-0">
                    Phase {idx + 1}/{nodes.length}
                  </span>
                  <ChevronRight size={14} className="text-[var(--muted)] shrink-0" />
                </div>
                {node.subSteps.length > 0 && (
                  <div className="mt-3 space-y-1.5">
                    {node.subSteps.map((step) => (
                      <div key={step.id} className="flex items-center gap-2">
                        <div className={`w-1.5 h-1.5 rounded-full transition-colors duration-500 ${subStepStatusColors[step.status]}`} />
                        <span className={`text-[10px] transition-colors duration-500 ${step.status === 'completed' ? 'text-[var(--success)] line-through opacity-60' : step.status === 'active' ? 'text-[var(--accent)]' : step.status === 'error' ? 'text-[var(--danger)]' : 'text-[var(--muted)]'}`}>
                          {step.label}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </button>

              {/* Border-to-border connector: flows from this card's bottom edge
                  straight into the next card's top edge. */}
              {idx < nodes.length - 1 && (
                <div
                  className={`flex justify-center ${connectorColor(node.status)}`}
                  aria-hidden="true"
                >
                  <div className="flex flex-col items-center h-9 w-4">
                    <div
                      className={`w-[2px] flex-1 transition-colors duration-500 ${
                        node.status === 'active' ? 'connector-flow' : 'bg-current'
                      }`}
                    />
                    <ChevronDown size={16} className="-mt-2 shrink-0 transition-colors duration-500" />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

