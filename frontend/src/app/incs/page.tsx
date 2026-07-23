'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Search, ArrowRight, Zap, Filter, ChevronDown, Activity, CheckCircle2, Clock, AlertTriangle } from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';
import { getIncidents, IncidentListItem } from '@/lib/api';

type SortKey = 'timestamp' | 'severity' | 'status' | 'title';
type SortDir = 'asc' | 'desc';
type SeverityFilter = 'ALL' | 'HIGH' | 'MEDIUM' | 'LOW';
type StatusFilter = 'ALL' | 'open' | 'investigating' | 'resolved';

export default function AllIncidentsPage() {
  const router = useRouter();
  const [incidents, setIncidents] = useState<IncidentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('timestamp');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('ALL');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL');

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await getIncidents();
        setIncidents(res.incidents);
      } catch (err) {
        console.error('Failed to fetch incidents:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const filtered = incidents
    .filter(inc => {
      if (severityFilter !== 'ALL' && inc.severity !== severityFilter) return false;
      if (statusFilter !== 'ALL' && inc.status !== statusFilter) return false;
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        return (
          inc.id.toLowerCase().includes(term) ||
          inc.title.toLowerCase().includes(term) ||
          inc.flow.toLowerCase().includes(term)
        );
      }
      return true;
    })
    .sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'timestamp':
          cmp = a.timestamp.localeCompare(b.timestamp);
          break;
        case 'severity': {
          const order = { HIGH: 0, MEDIUM: 1, LOW: 2 };
          cmp = (order[a.severity] ?? 1) - (order[b.severity] ?? 1);
          break;
        }
        case 'status': {
          const order = { investigating: 0, open: 1, resolved: 2 };
          cmp = (order[a.status] ?? 1) - (order[b.status] ?? 1);
          break;
        }
        case 'title':
          cmp = a.title.localeCompare(b.title);
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });

  const severityColors: Record<string, string> = {
    HIGH: 'text-red-400 bg-red-500/10 border-red-500/20',
    MEDIUM: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
    LOW: 'text-green-400 bg-green-500/10 border-green-500/20',
  };

  const statusDots: Record<string, string> = {
    investigating: 'bg-yellow-400',
    resolved: 'bg-green-400',
    open: 'bg-blue-400',
  };

  const statusColors: Record<string, string> = {
    investigating: 'text-yellow-400',
    resolved: 'text-green-400',
    open: 'text-blue-400',
  };

  const SortHeader = ({ label, sortKey: sk }: { label: string; sortKey: SortKey }) => (
    <button
      onClick={() => toggleSort(sk)}
      className="flex items-center gap-1 text-[10px] font-semibold text-[var(--muted)] uppercase tracking-wider hover:text-[var(--foreground)] transition-colors"
    >
      {label}
      {sortKey === sk && (
        <ChevronDown size={10} className={`transition-transform ${sortDir === 'asc' ? 'rotate-180' : ''}`} />
      )}
    </button>
  );

  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Header */}
      <header className="h-14 bg-[var(--surface)] border-b border-[var(--border)] flex items-center justify-between px-6 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/')}
            className="btn btn-ghost text-xs p-1.5"
            title="Back to Dashboard"
          >
            <ArrowLeft size={16} />
          </button>
          <div className="w-8 h-8 rounded-lg bg-[var(--accent)]/20 border border-[var(--accent)]/30 flex items-center justify-center">
            <Activity size={16} className="text-[var(--accent)]" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-[var(--foreground)]">All Incidents</h1>
            <p className="text-[10px] text-[var(--muted)]">{filtered.length} of {incidents.length} incidents</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-[var(--muted)] bg-[var(--surface-light)] px-2 py-1 rounded">
            {loading ? 'Loading...' : `${incidents.length} Total`}
          </span>
          <ThemeToggle />
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6">
        {/* Search & Filters */}
        <div className="card p-4 mb-6">
          <div className="grid grid-cols-4 gap-4">
            {/* Search */}
            <div className="col-span-2 relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
              <input
                type="text"
                placeholder="Search by ID, title, or flow..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-2.5 bg-[var(--background)] border border-[var(--border)] rounded-lg text-xs text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--accent)]"
              />
            </div>

            {/* Severity Filter */}
            <div>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value as SeverityFilter)}
                className="w-full py-2.5 bg-[var(--background)] border border-[var(--border)] rounded-lg text-xs text-[var(--foreground)] focus:outline-none focus:border-[var(--accent)]"
              >
                <option value="ALL">All Severities</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>

            {/* Status Filter */}
            <div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
                className="w-full py-2.5 bg-[var(--background)] border border-[var(--border)] rounded-lg text-xs text-[var(--foreground)] focus:outline-none focus:border-[var(--accent)]"
              >
                <option value="ALL">All Statuses</option>
                <option value="open">Open</option>
                <option value="investigating">Investigating</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="flex items-center gap-4 mb-4">
          <div className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
            <Activity size={12} />
            <span>{filtered.length} Filtered</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-yellow-400">
            <Clock size={12} />
            <span>{filtered.filter(i => i.status === 'investigating').length} Active</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-green-400">
            <CheckCircle2 size={12} />
            <span>{filtered.filter(i => i.status === 'resolved').length} Resolved</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertTriangle size={12} />
            <span>{filtered.filter(i => i.severity === 'HIGH').length} High Severity</span>
          </div>
        </div>

        {/* Incidents Table */}
        <div className="card overflow-hidden">
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-4 px-4 py-3 border-b border-[var(--border)] bg-[var(--surface-light)]/30">
            <div className="col-span-3"><SortHeader label="Incident" sortKey="title" /></div>
            <div className="col-span-2"><SortHeader label="Severity" sortKey="severity" /></div>
            <div className="col-span-2"><SortHeader label="Status" sortKey="status" /></div>
            <div className="col-span-2"><span className="text-[10px] font-semibold text-[var(--muted)] uppercase tracking-wider">Flow</span></div>
            <div className="col-span-2"><SortHeader label="Date" sortKey="timestamp" /></div>
            <div className="col-span-1"></div>
          </div>

          {/* Table Body */}
          {loading ? (
            <div className="p-8 text-center">
              <div className="flex items-center justify-center gap-2 text-xs text-[var(--muted)]">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Loading incidents...</span>
              </div>
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center">
              <Search size={24} className="mx-auto text-[var(--muted)] mb-2 opacity-30" />
              <p className="text-xs text-[var(--muted)]">No incidents found matching your filters</p>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {filtered.map((inc) => (
                <button
                  key={inc.id}
                  onClick={() => router.push(`/inc/${inc.id}`)}
                  className="w-full grid grid-cols-12 gap-4 px-4 py-3 hover:bg-[var(--surface-light)]/50 transition-colors text-left group"
                >
                  <div className="col-span-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--accent)] transition-colors">
                        {inc.id}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--muted)] truncate mt-0.5">{inc.title}</p>
                  </div>
                  <div className="col-span-2 flex items-center">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${severityColors[inc.severity]}`}>
                      {inc.severity}
                    </span>
                  </div>
                  <div className="col-span-2 flex items-center">
                    <div className="flex items-center gap-1.5">
                      <div className={`w-1.5 h-1.5 rounded-full ${statusDots[inc.status]}`} />
                      <span className={`text-[10px] ${statusColors[inc.status]}`}>
                        {inc.status}
                      </span>
                    </div>
                  </div>
                  <div className="col-span-2 flex items-center">
                    <span className="text-xs text-[var(--muted)]">{inc.flow}</span>
                  </div>
                  <div className="col-span-2 flex items-center">
                    <span className="text-xs text-[var(--muted)]">{inc.timestamp}</span>
                  </div>
                  <div className="col-span-1 flex items-center justify-end">
                    <ArrowRight size={14} className="text-[var(--muted)] group-hover:text-[var(--accent)] transition-colors" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

