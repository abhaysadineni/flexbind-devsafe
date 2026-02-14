import { useState, useRef } from 'react';
import { createJob } from '../api';

interface Props {
  onCreated: () => void;
}

export default function NewJobForm({ onCreated }: Props) {
  const [targetFile, setTargetFile] = useState<File | null>(null);
  const [binderFile, setBinderFile] = useState<File | null>(null);
  const [binderType, setBinderType] = useState<'antibody_fv' | 'other'>('other');
  const [flexResidues, setFlexResidues] = useState('');
  const [interfaceDist, setInterfaceDist] = useState(8.0);
  const [mode, setMode] = useState<'fast' | 'deep'>('fast');
  const [seed, setSeed] = useState(42);
  const [noGlyco, setNoGlyco] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const targetRef = useRef<HTMLInputElement>(null);
  const binderRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async () => {
    if (!targetFile || !binderFile) {
      setError('Please upload both target and binder PDB files.');
      return;
    }
    setError('');
    setSubmitting(true);

    try {
      const form = new FormData();
      form.append('target_pdb', targetFile);
      form.append('binder_pdb', binderFile);
      form.append('binder_type', binderType);
      form.append('flexible_residues', flexResidues);
      form.append('interface_distance', interfaceDist.toString());
      form.append('mode', mode);
      form.append('seed', seed.toString());
      form.append('no_glycosylation', noGlyco.toString());

      await createJob(form);
      onCreated();
    } catch (e: any) {
      setError(e.message || 'Failed to create job');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card-glow rounded-2xl border border-slate-800 bg-slate-900/70 p-8 backdrop-blur">
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-white">New Design Job</h2>
        <p className="mt-2 text-sm text-slate-400">
          Upload your target and binder PDB files to generate ensemble-robust, developable sequence designs.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Target PDB */}
        <FileUploadBox
          label="Target / Receptor PDB"
          file={targetFile}
          inputRef={targetRef}
          onSelect={setTargetFile}
          accept=".pdb"
        />

        {/* Binder PDB */}
        <FileUploadBox
          label="Binder Template PDB"
          file={binderFile}
          inputRef={binderRef}
          onSelect={setBinderFile}
          accept=".pdb"
        />
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Binder Type */}
        <FieldGroup label="Binder Type">
          <select
            value={binderType}
            onChange={(e) => setBinderType(e.target.value as any)}
            className="input-field"
          >
            <option value="antibody_fv">Antibody Fv</option>
            <option value="other">Other binder</option>
          </select>
        </FieldGroup>

        {/* Mode */}
        <FieldGroup label="Compute Mode">
          <div className="flex gap-2">
            <ModeButton
              active={mode === 'fast'}
              onClick={() => setMode('fast')}
              label="Fast"
              sub="~minutes"
            />
            <ModeButton
              active={mode === 'deep'}
              onClick={() => setMode('deep')}
              label="Deep"
              sub="~hours"
            />
          </div>
        </FieldGroup>

        {/* Seed */}
        <FieldGroup label="Random Seed">
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(parseInt(e.target.value) || 0)}
            className="input-field"
            min={0}
          />
        </FieldGroup>

        {/* Flexible residues */}
        <FieldGroup label="Flexible Residues (optional)">
          <input
            type="text"
            value={flexResidues}
            onChange={(e) => setFlexResidues(e.target.value)}
            placeholder="e.g. B:30, B:31, B:52"
            className="input-field"
          />
        </FieldGroup>

        {/* Interface distance */}
        <FieldGroup label={`Interface Cutoff: ${interfaceDist} Å`}>
          <input
            type="range"
            min={3}
            max={20}
            step={0.5}
            value={interfaceDist}
            onChange={(e) => setInterfaceDist(parseFloat(e.target.value))}
            className="w-full accent-cyan-500"
          />
        </FieldGroup>

        {/* No glycosylation */}
        <FieldGroup label="Constraints">
          <label className="flex items-center gap-3 cursor-pointer text-sm text-slate-300">
            <input
              type="checkbox"
              checked={noGlyco}
              onChange={(e) => setNoGlyco(e.target.checked)}
              className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/30"
            />
            Block N-X-S/T glycosylation motifs
          </label>
        </FieldGroup>
      </div>

      {error && (
        <div className="mt-6 rounded-lg border border-rose-800/50 bg-rose-950/30 px-4 py-3 text-sm text-rose-300">
          {error}
        </div>
      )}

      <div className="mt-8">
        <button
          onClick={handleSubmit}
          disabled={submitting || !targetFile || !binderFile}
          className="w-full rounded-xl bg-gradient-to-r from-cyan-600 to-teal-600 px-8 py-3.5 text-sm font-semibold text-white shadow-lg shadow-cyan-600/20 transition-all hover:shadow-cyan-500/30 hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-none disabled:hover:brightness-100"
        >
          {submitting ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
              </svg>
              Submitting…
            </span>
          ) : (
            'Run Design Pipeline'
          )}
        </button>
      </div>
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────────────────── */

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-slate-500">
        {label}
      </label>
      {children}
    </div>
  );
}

function FileUploadBox({
  label,
  file,
  inputRef,
  onSelect,
  accept,
}: {
  label: string;
  file: File | null;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onSelect: (f: File) => void;
  accept: string;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-slate-500">
        {label}
      </label>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className={`flex w-full items-center gap-3 rounded-xl border-2 border-dashed px-5 py-4 text-left transition-all ${
          file
            ? 'border-cyan-700/40 bg-cyan-950/20'
            : 'border-slate-700 bg-slate-800/40 hover:border-slate-600 hover:bg-slate-800/60'
        }`}
      >
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
            file ? 'bg-cyan-900/40 text-cyan-400' : 'bg-slate-800 text-slate-500'
          }`}
        >
          {file ? (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
          )}
        </div>
        <div className="min-w-0">
          <p className={`truncate text-sm font-medium ${file ? 'text-cyan-300' : 'text-slate-300'}`}>
            {file ? file.name : 'Click to upload'}
          </p>
          <p className="text-xs text-slate-500">
            {file ? `${(file.size / 1024).toFixed(1)} KB` : 'PDB format, max 50 MB'}
          </p>
        </div>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onSelect(f);
        }}
      />
    </div>
  );
}

function ModeButton({
  active,
  onClick,
  label,
  sub,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  sub: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 rounded-lg border px-4 py-2.5 text-center transition-all ${
        active
          ? 'border-cyan-700/50 bg-cyan-950/30 text-cyan-300 shadow-inner'
          : 'border-slate-700 bg-slate-800/40 text-slate-400 hover:text-slate-300'
      }`}
    >
      <div className="text-sm font-semibold">{label}</div>
      <div className="text-xs opacity-60">{sub}</div>
    </button>
  );
}
