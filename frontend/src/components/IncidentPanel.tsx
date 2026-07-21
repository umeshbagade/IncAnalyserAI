'use client';

import { useState } from 'react';
import { Incident, FlowNode } from '@/types';
import { FileText, ListTree, ChevronDown, ChevronRight } from 'lucide-react';

interface IncidentPanelProps {
  incident: Incident;
  selectedNode: FlowNode | null;
}

export default function IncidentPanel({ incident, selectedNode }: IncidentPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    original: true,
    triage: true,
    entities: true,
    timeline: true,
  });

  const toggleSection = (key: string) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const timelineIcons: Record<string, string> = {
    info: 'bg-blue-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500',
    success: 'bg-green-500',
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--border)] bg-[var(--surface)]">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--accent-light)] flex items-center gap-2">
            <FileText size={14} />
            Incident Details
          </h2>
          <button className="btn btn-ghost text-xs p-1" title="Open in new tab">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--muted)]">
              <path d="M15 3h6v6" /><path d="M10 14 21 3" /><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            </svg>
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {/* Original Text */}
        <div>
          <button
            onClick={() => toggleSection('original')}
            className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider hover:text-[var(--foreground)] transition-colors border-b border-[var(--border)]"
          >
            <div className="flex items-center gap-2">
              <FileText size={12} />
              <span>Original Text</span>
            </div>
            {expandedSections.original ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
          {expandedSections.original && (
            <div className="px-4 py-3 border-b border-[var(--border)]">
              <p className="text-xs text-[var(--foreground)] leading-relaxed whitespace-pre-wrap font-mono">
                {incident.originalText}
              </p>
            </div>
          )}
        </div>

        {/* Triage Summary */}
        <div>
          <button
            onClick={() => toggleSection('triage')}
            className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider hover:text-[var(--foreground)] transition-colors border-b border-[var(--border)]"
          >
            <div className="flex items-center gap-2">
              <ListTree size={12} />
              <span>Triage Summary</span>
            </div>
            {expandedSections.triage ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
          {expandedSections.triage && (
            <div className="px-4 py-3 border-b border-[var(--border)]">
              <p className="text-xs text-[var(--foreground)] leading-relaxed">{incident.triageSummary}</p>
            </div>
          )}
        </div>

        {/* Entities */}
        <div>
          <button
            onClick={() => toggleSection('entities')}
            className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider hover:text-[var(--foreground)] transition-colors border-b border-[var(--border)]"
          >
            <div className="flex items-center gap-2">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" /><path d="M12 2v4" /><path d="M12 18v4" /><path d="M2 12h4" /><path d="M18 12h4" />
              </svg>
              <span>Entities</span>
            </div>
            {expandedSections.entities ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
          {expandedSections.entities && (
            <div className="px-4 py-3 border-b border-[var(--border)]">
              <div className="flex flex-wrap gap-1.5">
                {incident.entities.map((entity, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-[var(--surface-light)] border border-[var(--border)] text-[var(--accent)]"
                    title={`${entity.type} (${(entity.confidence * 100).toFixed(0)}%)`}
                  >
                    {entity.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Timeline */}
        <div>
          <button
            onClick={() => toggleSection('timeline')}
            className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider hover:text-[var(--foreground)] transition-colors border-b border-[var(--border)]"
          >
            <div className="flex items-center gap-2">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3v18h18" /><path d="M7 16l4-8 4 4 4-6" />
              </svg>
              <span>Timeline of Events</span>
            </div>
            {expandedSections.timeline ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
          {expandedSections.timeline && (
            <div className="p-4 space-y-2">
              {incident.timeline.map((event, idx) => (
                <div key={idx} className="flex items-start gap-2 animate-slide-in">
                  <div className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${timelineIcons[event.type]}`} />
                  <div className="flex gap-2 min-w-0">
                    <span className="text-[10px] text-[var(--muted)] font-mono shrink-0 w-14">{event.time}</span>
                    <span className="text-xs text-[var(--foreground)]">{event.event}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

