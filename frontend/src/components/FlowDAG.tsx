'use client';

import { useState } from 'react';
import { FlowNode } from '@/types';
import {
  CircleCheckBig,
  LoaderCircle,
  Clock,
  AlertCircle,
  SkipForward,
  ChevronRight,
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

  const getArrowColor = (index: number) => {
    const prevNode = nodes[index];
    if (prevNode?.status === 'completed') return 'stroke-[var(--success)]';
    if (prevNode?.status === 'active') return 'stroke-[var(--accent)]';
    if (prevNode?.status === 'error') return 'stroke-[var(--danger)]';
    return 'stroke-[var(--border)]';
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="relative max-w-lg mx-auto">
        {/* SVG Arrow Connectors */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
          {nodes.map((node, idx) => {
            if (idx === nodes.length - 1) return null;
            const y1 = 90 + idx * 140;
            const y2 = y1 + 140 - 30;
            const arrowColor = getArrowColor(idx);
            return (
              <g key={`connector-${idx}`}>
                <defs>
                  <marker id={`arrowhead-${idx}`} markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                    <polygon points="0 0, 8 3, 0 6" fill={arrowColor.includes('success') ? '#22c55e' : arrowColor.includes('accent') ? '#3b82f6' : '#334155'} />
                  </marker>
                </defs>
                <line
                  x1="50%" y1={y1} x2="50%" y2={y2}
                  stroke={arrowColor.includes('success') ? '#22c55e' : arrowColor.includes('accent') ? '#3b82f6' : '#334155'}
                  strokeWidth="2"
                  strokeDasharray={node.status === 'pending' ? '6,4' : 'none'}
                  className={node.status === 'active' ? 'animate-flow-pulse' : ''}
                  markerEnd={`url(#arrowhead-${idx})`}
                />
              </g>
            );
          })}
        </svg>

        {/* Flow Nodes */}
        {nodes.map((node, idx) => (
          <div key={node.id} className="relative" style={{ zIndex: 1 }}>
            <div className="text-center mb-3">
              <span className="text-[10px] text-[var(--muted)] uppercase tracking-wider">
                Phase {idx + 1} of {nodes.length}
              </span>
            </div>
            <button
              onClick={() => onNodeSelect(selectedNodeId === node.id ? null : node)}
              className={`w-full p-4 rounded-lg border transition-all duration-300 cursor-pointer text-left
                ${statusColors[node.status]}
                ${selectedNodeId === node.id ? 'ring-1 ring-[var(--accent)]/50' : ''}
                hover:brightness-110
              `}
            >
              <div className="flex items-center gap-3">
                {statusIcons[node.status]}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-semibold ${statusTextColors[node.status]}`}>
                      {node.label}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded uppercase ${statusTextColors[node.status]} bg-current/10`}>
                      {node.status}
                    </span>
                  </div>
                  <p className="text-[10px] text-[var(--muted)] mt-0.5">{node.description}</p>
                </div>
                <ChevronRight size={14} className="text-[var(--muted)] shrink-0" />
              </div>
              {node.subSteps.length > 0 && (
                <div className="mt-3 space-y-1.5">
                  {node.subSteps.map((step) => (
                    <div key={step.id} className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${subStepStatusColors[step.status]}`} />
                      <span className={`text-[10px] ${step.status === 'completed' ? 'text-[var(--success)] line-through opacity-60' : step.status === 'active' ? 'text-[var(--accent)]' : 'text-[var(--muted)]'}`}>
                        {step.label}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </button>
            {idx < nodes.length - 1 && <div className="h-8" />}
          </div>
        ))}
      </div>
    </div>
  );
}

