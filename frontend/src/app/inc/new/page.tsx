'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Zap, Send, AlertCircle, Loader2 } from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';
import { createIncident } from '@/lib/api';

export default function NewInvestigationPage() {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState<'HIGH' | 'MEDIUM' | 'LOW'>('MEDIUM');
  const [flowId, setFlowId] = useState('SATURN');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Incident title is required');
      return;
    }
    setSubmitting(true);
    setError(null);

    try {
      const res = await createIncident({
        title: title.trim(),
        description: description.trim(),
        severity,
        flowId,
      });
      router.push(`/inc/${res.incident.id}`);
    } catch (err) {
      console.error('Failed to create incident:', err);
      setError(err instanceof Error ? err.message : 'Failed to create incident. Please try again.');
      setSubmitting(false);
    }
  };

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
            <Zap size={16} className="text-[var(--accent)]" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-[var(--foreground)]">New Investigation</h1>
            <p className="text-[10px] text-[var(--muted)]">Create a new incident for AI-powered analysis</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Error Banner */}
          {error && (
            <div className="flex items-center gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
              <AlertCircle size={16} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Title */}
          <div className="card p-5">
            <label className="block text-sm font-semibold text-[var(--foreground)] mb-2">
              Incident Title <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Database Connection Timeout in Production"
              className="w-full bg-[var(--background)] border border-[var(--border)] rounded-lg text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--accent)] px-4 py-3"
              disabled={submitting}
            />
          </div>

          {/* Description */}
          <div className="card p-5">
            <label className="block text-sm font-semibold text-[var(--foreground)] mb-2">
              Description / Incident Details
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what happened, error messages, affected services, etc. This text will be used for AI triage and analysis."
              rows={6}
              className="w-full bg-[var(--background)] border border-[var(--border)] rounded-lg text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--accent)] px-4 py-3 resize-y min-h-[120px]"
              disabled={submitting}
            />
          </div>

          {/* Severity & Flow */}
          <div className="grid grid-cols-2 gap-6">
            {/* Severity */}
            <div className="card p-5">
              <label className="block text-sm font-semibold text-[var(--foreground)] mb-2">
                Severity
              </label>
              <div className="flex gap-2">
                {(['HIGH', 'MEDIUM', 'LOW'] as const).map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setSeverity(s)}
                    disabled={submitting}
                    className={`flex-1 py-2.5 px-3 rounded-lg text-xs font-semibold border transition-all ${
                      severity === s
                        ? s === 'HIGH'
                          ? 'bg-red-500/15 border-red-500/30 text-red-400'
                          : s === 'MEDIUM'
                          ? 'bg-yellow-500/15 border-yellow-500/30 text-yellow-400'
                          : 'bg-green-500/15 border-green-500/30 text-green-400'
                        : 'bg-[var(--background)] border-[var(--border)] text-[var(--muted)] hover:border-[var(--accent)]/30'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* Flow */}
            <div className="card p-5">
              <label className="block text-sm font-semibold text-[var(--foreground)] mb-2">
                Analysis Flow
              </label>
              <select
                value={flowId}
                onChange={(e) => setFlowId(e.target.value)}
                disabled={submitting}
                className="w-full bg-[var(--background)] border border-[var(--border)] rounded-lg text-sm text-[var(--foreground)] focus:outline-none focus:border-[var(--accent)] px-4 py-2.5"
              >
                <option value="SATURN">SATURN (Report Layer)</option>
                <option value="DATAHUB">DATA HUB (Snapshot Layer)</option>
                <option value="INGESTION">INGESTION (Source Layer)</option>
              </select>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={() => router.push('/')}
              className="btn btn-ghost text-sm"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !title.trim()}
              className="btn btn-primary text-sm px-6 py-2.5 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Creating Incident...
                </>
              ) : (
                <>
                  <Send size={16} />
                  Create & Start Investigation
                </>
              )}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

