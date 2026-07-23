'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Zap, Search, ArrowRight, Activity, CheckCircle2, Clock, AlertTriangle } from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';
import { getIncidents, getDashboardStats, IncidentListItem, IncidentStats } from '@/lib/api';

interface IncidentRowData {
  id: string;
  title: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'open' | 'investigating' | 'resolved';
  flow: string;
  timestamp: string;
  duration: string;
}

export default function HomePage() {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState('');
  const [incidents, setIncidents] = useState<IncidentListItem[]>([]);
  const [statusCounts, setStatusCounts] = useState<IncidentStats>({
    total: 0, investigating: 0, resolved: 0, open: 0, high: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [incRes, stats] = await Promise.all([
          getIncidents(),
          getDashboardStats(),
        ]);
        setIncidents(incRes.incidents);
        setStatusCounts(stats);
      } catch (err) {
        console.error('Failed to fetch incidents:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const filteredIncidents = incidents.filter(inc =>
    inc.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    inc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    inc.flow.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Header */}
      <header className="h-14 bg-[var(--surface)] border-b border-[var(--border)] flex items-center justify-between px-6 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[var(--accent)]/20 border border-[var(--accent)]/30 flex items-center justify-center">
            <Zap size={16} className="text-[var(--accent)]" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-[var(--foreground)]">OpsAssistantAI</h1>
            <p className="text-[10px] text-[var(--muted)]">Incident Analysis Platform</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--success)] animate-pulse" />
            <span>All Systems Operational</span>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Hero Section */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-xl font-bold text-[var(--foreground)]">Incident Analysis Dashboard</h2>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] border border-[var(--accent)]/30">
              BETA
            </span>
          </div>
          <p className="text-xs text-[var(--muted)]">
            AI-powered root cause analysis for production incidents. Search an incident or select from the list below.
          </p>
        </div>

        {/* Search Bar */}
        <div className="card p-4 mb-8">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
            <input
              type="text"
              placeholder="Search incidents by ID, title, or flow..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-[var(--background)] border border-[var(--border)] rounded-lg text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]/20"
            />
          </div>
          <div className="flex items-center gap-4 mt-3 pt-3 border-t border-[var(--border)]">
            <div className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
              <Activity size={12} />
              <span>{statusCounts.total} Total INCs</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-yellow-400">
              <Clock size={12} />
              <span>{statusCounts.investigating} Active</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-green-400">
              <CheckCircle2 size={12} />
              <span>{statusCounts.resolved} Resolved</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-red-400">
              <AlertTriangle size={12} />
              <span>{statusCounts.high} High Severity</span>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {[
            {
              title: 'New Investigation',
              desc: 'Start a new incident analysis',
              icon: <Search size={20} className="text-[var(--accent)]" />,
              onClick: () => router.push('/inc/new'),
            },
            {
              title: 'View All INCs',
              desc: 'Browse all recorded incidents',
              icon: <Activity size={20} className="text-[var(--accent)]" />,
              onClick: () => router.push('/incs'),
            },
            {
              title: 'Knowledge Base',
              desc: 'Browse runbooks & solutions',
              icon: <Zap size={20} className="text-[var(--accent)]" />,
              onClick: () => {},
            },
          ].map((action, idx) => (
            <button
              key={idx}
              onClick={action.onClick}
              className="card p-4 text-left hover:border-[var(--accent)]/30 hover:bg-[var(--surface-light)]/50 transition-all duration-200 group"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-[var(--accent)]/10 border border-[var(--accent)]/20 flex items-center justify-center">
                  {action.icon}
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--accent)] transition-colors">
                    {action.title}
                  </h3>
                  <p className="text-[10px] text-[var(--muted)]">{action.desc}</p>
                </div>
                <ArrowRight size={14} className="text-[var(--muted)] group-hover:text-[var(--accent)] transition-colors" />
              </div>
            </button>
          ))}
        </div>

        {/* Incidents List */}
        <div className="card">
          <div className="card-body p-4 border-b border-[var(--border)]">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-[var(--foreground)]">All Incidents</h2>
              <span className="text-[10px] text-[var(--muted)]">{filteredIncidents.length} incidents</span>
            </div>
          </div>
          <div className="divide-y divide-[var(--border)]">
            {filteredIncidents.length === 0 ? (
              <div className="p-8 text-center">
                <Search size={24} className="mx-auto text-[var(--muted)] mb-2 opacity-30" />
                <p className="text-xs text-[var(--muted)]">No incidents found matching "{searchTerm}"</p>
              </div>
            ) : (
              filteredIncidents.map((inc) => (
                <IncidentRow key={inc.id} incident={inc} onClick={() => router.push(`/inc/${inc.id}`)} />
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function IncidentRow({ incident, onClick }: { incident: IncidentRowData; onClick: () => void }) {
  const severityColors: Record<string, string> = {
    HIGH: 'text-red-400 bg-red-500/10 border-red-500/20',
    MEDIUM: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
    LOW: 'text-green-400 bg-green-500/10 border-green-500/20',
  };

  const statusColors: Record<string, string> = {
    investigating: 'text-yellow-400',
    resolved: 'text-green-400',
    open: 'text-blue-400',
  };

  const statusDots: Record<string, string> = {
    investigating: 'bg-yellow-400',
    resolved: 'bg-green-400',
    open: 'bg-blue-400',
  };

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-4 px-4 py-3 hover:bg-[var(--surface-light)]/50 transition-colors text-left group"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--accent)] transition-colors">
            {incident.id}
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded border ${severityColors[incident.severity]}`}>
            {incident.severity}
          </span>
        </div>
        <p className="text-xs text-[var(--muted)] truncate">{incident.title}</p>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-[10px] text-[var(--muted)]">Flow: {incident.flow}</span>
          <span className="text-[10px] text-[var(--muted)]">{incident.timestamp}</span>
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <div className="flex items-center gap-1.5">
          <div className={`w-1.5 h-1.5 rounded-full ${statusDots[incident.status]}`} />
          <span className={`text-[10px] ${statusColors[incident.status]}`}>
            {incident.status}
          </span>
        </div>
        <ArrowRight size={14} className="text-[var(--muted)] group-hover:text-[var(--accent)] transition-colors" />
      </div>
    </button>
  );
}

