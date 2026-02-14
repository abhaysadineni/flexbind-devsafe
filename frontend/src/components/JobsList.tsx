import { useState, useEffect } from 'react';
import { listJobs, getJobStatus } from '../api';
import type { JobListItem } from '../types';

interface Props {
  onSelect: (jobId: string) => void;
}

const STATUS_STYLES: Record<string, string> = {
  queued: 'bg-slate-700/50 text-slate-300',
  running: 'bg-cyan-900/40 text-cyan-300 status-running',
  done: 'bg-emerald-900/40 text-emerald-300',
  failed: 'bg-rose-900/40 text-rose-300',
};

export default function JobsList({ onSelect }: Props) {
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchJobs = async () => {
    try {
      const data = await listJobs();
      setJobs(data);
    } catch {
      /* ignore fetch errors during polling */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <svg className="h-6 w-6 animate-spin text-cyan-500" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
          <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
        </svg>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-700 py-16 text-center">
        <div className="text-4xl mb-3 opacity-30">🧬</div>
        <p className="text-slate-500 text-sm">No jobs yet. Create one from the home page.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {jobs.map((job) => (
        <button
          key={job.job_id}
          onClick={() => onSelect(job.job_id)}
          className="group flex w-full items-center gap-4 rounded-xl border border-slate-800 bg-slate-900/50 px-5 py-4 text-left transition-all hover:border-slate-700 hover:bg-slate-800/50"
        >
          {/* Status badge */}
          <span
            className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wider ${
              STATUS_STYLES[job.status] || STATUS_STYLES.queued
            }`}
          >
            {job.status}
          </span>

          {/* Job info */}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-mono font-medium text-slate-200 group-hover:text-white">
              {job.job_id}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">
              {job.binder_type === 'antibody_fv' ? 'Antibody Fv' : 'Other binder'} ·{' '}
              {job.mode === 'fast' ? 'Fast' : 'Deep'} ·{' '}
              {new Date(job.created_at).toLocaleString()}
            </p>
          </div>

          {/* Progress */}
          {job.status === 'running' && (
            <div className="w-24 shrink-0">
              <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-teal-500 transition-all duration-500"
                  style={{ width: `${Math.round(job.progress * 100)}%` }}
                />
              </div>
              <p className="mt-1 text-right text-xs text-slate-500">
                {Math.round(job.progress * 100)}%
              </p>
            </div>
          )}

          {/* Arrow */}
          <svg
            className="h-4 w-4 shrink-0 text-slate-600 group-hover:text-slate-400 transition-colors"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      ))}
    </div>
  );
}
