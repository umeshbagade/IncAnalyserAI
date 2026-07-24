'use client';

import { useState } from 'react';
import { RCAResult, BestNextAction } from '@/types';
import { Search, RotateCcw, TrendingUp, Bell, Plus, CheckCircle2, HelpCircle } from 'lucide-react';

interface RCAPanelProps {
  rcaResult: RCAResult;
  bestNextActions: BestNextAction[];
}

export default function RCAPanel({ rcaResult, bestNextActions }: RCAPanelProps) {
  const [feedback, setFeedback] = useState<'useful' | 'not_useful' | null>(null);

  const actionIcons: Record<string, React.ReactNode> = {
    rerun: <RotateCcw size={12} />,
    recompute: <TrendingUp size={12} />,
    notify: <Bell size={12} />,
    investigate: <Search size={12} />,
  };

  const actionColors: Record<string, string> = {
    rerun: 'text-blue-400 border-blue-500/30 hover:bg-blue-500/10',
    recompute: 'text-yellow-400 border-yellow-500/30 hover:bg-yellow-500/10',
    notify: 'text-purple-400 border-purple-500/30 hover:bg-purple-500/10',
    investigate: 'text-green-400 border-green-500/30 hover:bg-green-500/10',
  };

  return (
    <div className="border-t border-[var(--border)] bg-[var(--surface)]">
      {/* Root Cause Section */}
      <div className="p-4 border-b border-[var(--border)]">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-[var(--muted)] uppercase">Root Cause Analysis</h3>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-[var(--muted)]">Confidence</span>
            <div className="flex items-center gap-1">
              <div className="w-16 h-1.5 rounded-full bg-[var(--surface-light)] overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-yellow-500 to-green-500 transition-all duration-500"
                  style={{ width: `${rcaResult.confidence * 100}%` }}
                />
              </div>
              <span className="text-[10px] font-bold text-[var(--accent)]">
                {(rcaResult.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
        <p className="text-xs text-[var(--foreground)] leading-relaxed mb-3 bg-[var(--surface-light)]/50 rounded p-2.5 border border-[var(--border)]">
          {rcaResult.rootCause}
        </p>

        {/* Causal Chain */}
        <div className="space-y-0">
          {rcaResult.causalChain.map((step, idx) => (
            <div key={idx} className="flex items-start gap-3 pb-3 relative">
              <div className="flex flex-col items-center">
                <div className="w-6 h-6 rounded-full bg-[var(--accent)]/20 border border-[var(--accent)]/30 flex items-center justify-center shrink-0">
                  <span className="text-[10px] font-mono text-[var(--accent)]">{idx + 1}</span>
                </div>
                {idx < rcaResult.causalChain.length - 1 && (
                  <div className="w-px flex-1 bg-gradient-to-b from-[var(--accent)]/50 to-transparent mt-1" />
                )}
              </div>
              <div className="flex-1 pt-0.5">
                <p className="text-xs text-[var(--foreground)]">{step}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Best Next Actions */}
      <div className="p-4 border-b border-[var(--border)]">
        <h3 className="text-xs font-semibold text-[var(--muted)] uppercase mb-3">Best Next Actions</h3>
        <div className="grid grid-cols-1 gap-2">
          {bestNextActions.map((action) => (
            <button
              key={action.id}
              className={`flex items-start gap-2 px-3 py-2 rounded border text-xs transition-all ${actionColors[action.category]}`}
            >
              <span className="shrink-0 mt-0.5">{actionIcons[action.category]}</span>
              <span className="flex-1 min-w-0 text-left whitespace-normal break-words leading-relaxed">{action.label}</span>
              <svg className="shrink-0 mt-0.5" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14" /><path d="m12 5 7 7-7 7" />
              </svg>
            </button>
          ))}
        </div>
        <button className="mt-3 btn btn-ghost w-full text-xs text-[var(--muted)]">
          <Plus size={12} />
          <span>Add custom action</span>
        </button>
      </div>

      {/* Feedback */}
      <div className="p-4">
        <h3 className="text-xs font-semibold text-[var(--muted)] uppercase mb-2">Was this helpful?</h3>
        <div className="flex gap-2">
          <button
            onClick={() => setFeedback('useful')}
            className={`btn btn-secondary text-xs flex-1 ${feedback === 'useful' ? 'bg-green-500/20 text-green-400 border-green-500/30' : ''}`}
          >
            <CheckCircle2 size={12} />
            Yes
          </button>
          <button
            onClick={() => setFeedback('not_useful')}
            className={`btn btn-secondary text-xs flex-1 ${feedback === 'not_useful' ? 'bg-red-500/20 text-red-400 border-red-500/30' : ''}`}
          >
            <HelpCircle size={12} />
            No
          </button>
        </div>
      </div>
    </div>
  );
}

