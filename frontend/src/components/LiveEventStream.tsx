'use client';

import { useState, useEffect, useRef } from 'react';
import { LiveEvent } from '@/types';
import { Radio, LoaderCircle, ArrowRight } from 'lucide-react';

interface LiveEventStreamProps {
  events: LiveEvent[];
  isConnected: boolean;
  eventCount: number;
  onClear?: () => void;
}

export default function LiveEventStream({ events, isConnected, eventCount, onClear }: LiveEventStreamProps) {
  const streamEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    streamEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const eventColors: Record<string, string> = {
    triage: 'text-blue-400',
    plan: 'text-yellow-400',
    step: 'text-green-400',
    rca: 'text-purple-400',
    info: 'text-[var(--muted)]',
    error: 'text-red-400',
  };

  const eventDots: Record<string, string> = {
    triage: 'bg-blue-400',
    plan: 'bg-yellow-400',
    step: 'bg-green-400',
    rca: 'bg-purple-400',
    info: 'bg-[var(--muted)]',
    error: 'bg-red-400',
  };

  return (
    <div className="border-t border-[var(--border)] bg-[var(--surface)]">
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border)]">
        <div className="flex items-center gap-2">
          <Radio size={12} className="text-[var(--muted)]" />
          <span className="text-xs font-semibold text-[var(--foreground)]">Live Event Stream</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--muted)]">{eventCount} events</span>
          {onClear && (
            <button onClick={onClear} className="text-[10px] text-[var(--muted)] hover:text-[var(--foreground)]">
              Clear
            </button>
          )}
        </div>
      </div>
      <div className="h-56 min-h-[6rem] max-h-[70vh] resize-y overflow-y-auto px-4 py-2 space-y-1">
        {events.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center gap-2 text-[var(--muted)]">
              <LoaderCircle size={12} className="animate-spin" />
              <span className="text-xs">Waiting for events...</span>
            </div>
          </div>
        ) : (
          events.map((event, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 animate-slide-in"
            >
              <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${eventDots[event.type]}`} />
              <span className="text-[10px] text-[var(--muted)] font-mono shrink-0 w-14">
                {event.timestamp}
              </span>
              <span className={`text-xs ${eventColors[event.type]}`}>
                {event.message}
              </span>
            </div>
          ))
        )}
        <div ref={streamEndRef} />
      </div>
      <div className="flex items-center gap-3 px-4 py-1.5 border-t border-[var(--border)] bg-[var(--surface-light)]/30">
        <div className="flex items-center gap-1.5">
          <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-[var(--success)]' : 'bg-[var(--muted)]'} ${isConnected ? 'animate-pulse' : ''}`} />
          <span className="text-[10px] text-[var(--muted)]">{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
        <ArrowRight size={10} className="text-[var(--muted)]" />
        <span className="text-[10px] text-[var(--muted)]">
          {isConnected ? `Streaming ${eventCount} events` : 'No events'}
        </span>
      </div>
    </div>
  );
}

