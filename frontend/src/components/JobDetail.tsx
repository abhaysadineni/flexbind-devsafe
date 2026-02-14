import { useState, useEffect, useRef } from 'react';
import { getJobStatus, getJobReport, getDownloadUrl, getLogsUrl } from '../api';
import { PerStateChart, DevRadarChart } from './ScoreChart';
import type { JobReport, DesignResult } from '../types';

interface Props {
  jobId: string;
  onBack: () => void;
}

export default function JobDetail({ jobId, onBack }: Props) {
  const [report, setReport] = useState<JobReport | null>(null);
  const [status, setStatus] = useState<string>('queued');
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [selectedDesign, setSelectedDesign] = useState<DesignResult | null>(null);
  const [error, setError] = useState('');
  const logsEndRef = useRef<HTMLDivElement>(null);

  // SSE log streaming
  useEffect(() => {
    const evtSource = new EventSource(getLogsUrl(jobId));

    evtSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.log) {
          setLogs((prev) => [...prev.slice(-200), data.log]);
        }
        if (data.status) setStatus(data.status);
        if (data.progress !== undefined) setProgress(data.progress);
      } catch {
        /* ignore parse errors */
      }
    };

    evtSource.onerror = () => {
      evtSource.close();
    };

    return () => evtSource.close();
  }, [jobId]);

  // Scroll logs to bottom
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Fetch report when done
  useEffect(() => {
    if (status === 'done') {
      getJobReport(jobId)
        .then(setReport)
        .catch((e) => setError(e.message));
    }
  }, [status, jobId]);

  const FLAG_STYLES: Record<string, string> = {
    PASS: 'bg-emerald-900/40 text-emerald-300 border-emerald-800/50',
    WARN: 'bg-amber-900/40 text-amber-300 border-amber-800/50',
    FAIL: 'bg-rose-900/40 text-rose-300 border-rose-800/50',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 bg-slate-800/60 text-slate-400 transition hover:text-white"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-mono text-lg font-semibold text-white">{jobId}</h2>
          <div className="flex items-center gap-3 mt-1">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider ${
                status === 'running'
                  ? 'bg-cyan-900/40 text-cyan-300 status-running'
                  : status === 'done'
                  ? 'bg-emerald-900/40 text-emerald-300'
                  : status === 'failed'
                  ? 'bg-rose-900/40 text-rose-300'
                  : 'bg-slate-700/50 text-slate-300'
              }`}
            >
              {status}
            </span>
            {status === 'running' && (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <div className="h-1.5 w-32 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-teal-500 transition-all duration-500"
                    style={{ width: `${Math.round(progress * 100)}%` }}
                  />
                </div>
                {Math.round(progress * 100)}%
              </div>
            )}
          </div>
        </div>
        {status === 'done' && (
          <a
            href={getDownloadUrl(jobId)}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-600/20 transition hover:brightness-110"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17v2a2 2 0 002 2h14a2 2 0 002-2v-2" />
            </svg>
            Download ZIP
          </a>
        )}
      </div>

      {/* Logs */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/70">
        <div className="border-b border-slate-800 px-5 py-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Pipeline Logs</h3>
        </div>
        <div className="h-48 overflow-y-auto px-5 py-3 font-mono text-xs text-slate-400">
          {logs.length === 0 ? (
            <p className="text-slate-600">Waiting for logs…</p>
          ) : (
            logs.map((line, i) => (
              <div key={i} className="py-0.5 hover:text-slate-200 transition-colors">
                {line}
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800/50 bg-rose-950/30 px-4 py-3 text-sm text-rose-300">
          {error}
        </div>
      )}

      {/* Results */}
      {report && (
        <>
          {/* Developability summary */}
          {report.developability && (
            <div className="grid gap-6 md:grid-cols-2">
              <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
                <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Developability Assessment
                </h3>
                <div className="flex items-center gap-4 mb-4">
                  <div className="text-4xl font-bold text-white">
                    {report.developability.composite}
                  </div>
                  <div>
                    <div className="text-sm text-slate-400">/ 100</div>
                    <span
                      className={`mt-1 inline-block rounded-md border px-2 py-0.5 text-xs font-bold ${
                        FLAG_STYLES[report.developability.flag] || ''
                      }`}
                    >
                      {report.developability.flag}
                    </span>
                  </div>
                </div>
                <div className="space-y-2 text-xs text-slate-400">
                  <MetricRow label="Hydrophobic Patch" value={report.developability.hydrophobic_patch} />
                  <MetricRow label="Net Charge (pH 7.4)" value={report.developability.net_charge} />
                  <MetricRow label="Isoelectric Point" value={report.developability.pI} />
                  <MetricRow label="β-sheet Propensity" value={report.developability.beta_propensity} />
                  <MetricRow label="Self-Dock Risk" value={report.developability.self_dock_risk} />
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
                <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Developability Radar
                </h3>
                <DevRadarChart dev={report.developability} />
              </div>
            </div>
          )}

          {/* Designs table */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/70">
            <div className="border-b border-slate-800 px-5 py-3 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Ranked Designs ({report.designs.length})
              </h3>
              <span className="text-xs text-slate-600">
                Ensemble: {report.ensemble_size} states · Seed: {report.seed}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-500">
                    <th className="px-5 py-3 text-left">#</th>
                    <th className="px-5 py-3 text-left">Mutations</th>
                    <th className="px-5 py-3 text-right">Mean</th>
                    <th className="px-5 py-3 text-right">Worst</th>
                    <th className="px-5 py-3 text-right">Robustness</th>
                    <th className="px-5 py-3 text-right">Dev.</th>
                    <th className="px-5 py-3 text-center">Flag</th>
                    <th className="px-5 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {report.designs.map((d) => (
                    <tr
                      key={d.rank}
                      className={`border-b border-slate-800/50 transition-colors cursor-pointer ${
                        selectedDesign?.rank === d.rank
                          ? 'bg-cyan-950/20'
                          : 'hover:bg-slate-800/30'
                      }`}
                      onClick={() => setSelectedDesign(d)}
                    >
                      <td className="px-5 py-3 font-mono text-slate-400">{d.rank}</td>
                      <td className="px-5 py-3 font-mono text-xs text-slate-300 max-w-xs truncate">
                        {d.mutations}
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-slate-300">
                        {d.mean_score.toFixed(2)}
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-slate-300">
                        {d.worst_score.toFixed(2)}
                      </td>
                      <td className="px-5 py-3 text-right font-mono font-semibold text-cyan-300">
                        {d.robustness.toFixed(2)}
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-slate-300">
                        {d.developability_score.toFixed(0)}
                      </td>
                      <td className="px-5 py-3 text-center">
                        <span
                          className={`rounded-md border px-2 py-0.5 text-xs font-bold ${
                            FLAG_STYLES[d.developability_flag] || ''
                          }`}
                        >
                          {d.developability_flag}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <svg
                          className="h-4 w-4 text-slate-600"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={2}
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                        </svg>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Selected design detail */}
          {selectedDesign && (
            <div className="rounded-xl border border-cyan-800/30 bg-cyan-950/10 p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Design #{selectedDesign.rank} — Per-State Scores
                </h3>
                <button
                  onClick={() => setSelectedDesign(null)}
                  className="text-xs text-slate-500 hover:text-slate-300"
                >
                  Close
                </button>
              </div>
              <div className="mb-4 font-mono text-xs text-slate-400 break-all">
                <span className="text-slate-600">Sequence: </span>
                {selectedDesign.sequence}
              </div>
              <PerStateChart scores={selectedDesign.per_state_scores} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between">
      <span>{label}</span>
      <span className="font-mono text-slate-300">{value}</span>
    </div>
  );
}
