'use client';

import { Zap, Activity, Clock, TriangleAlert, Settings, ChevronDown } from 'lucide-react';

interface HeaderProps {
  incId: string;
  flow: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  duration: string;
}

export default function Header({ incId, flow, severity, duration }: HeaderProps) {
  const severityColors = {
    HIGH: 'status-high',
    MEDIUM: 'status-medium',
    LOW: 'status-low',
  };

  return (
    <header className="h-14 bg-[var(--surface)] border-b border-[var(--border)] flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-[var(--accent)]/20 border border-[var(--accent)]/30 flex items-center justify-center">
            <Zap size={14} className="text-[var(--accent)]" />
          </div>
          <span className="text-sm font-semibold text-[var(--accent-light)]">{incId}</span>
        </div>
        <div className="h-5 w-px bg-[var(--border)]" />
        <div className="flex items-center gap-2">
          <Activity size={14} className="text-[var(--muted)]" />
          <span className="text-xs text-[var(--foreground)]">
            Flow: <span className="text-[var(--accent)]">{flow}</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`status-badge ${severityColors[severity]}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse-dot mr-1.5" />
            Sev: {severity}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
          <Clock size={12} />
          <span>0 {duration}</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button className="btn btn-ghost text-xs">
          <TriangleAlert size={12} />
          Escalate
        </button>
        <button className="btn btn-ghost text-xs">
          <Settings size={12} />
        </button>
        <button className="btn btn-ghost text-xs">
          <ChevronDown size={12} />
        </button>
      </div>
    </header>
  );
}

