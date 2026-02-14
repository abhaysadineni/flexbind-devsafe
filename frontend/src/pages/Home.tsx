import NewJobForm from '../components/NewJobForm';

interface Props {
  onJobCreated: () => void;
}

export default function Home({ onJobCreated }: Props) {
  return (
    <div className="mx-auto max-w-3xl">
      {/* Hero */}
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-white">
          Ensemble-Aware Binder Design
        </h1>
        <p className="mt-3 text-base text-slate-400 max-w-xl mx-auto">
          Generate binding-competent conformational ensembles, design robust sequences
          across multiple states, and gate for aggregation and developability risk.
        </p>
        <div className="mt-5 flex items-center justify-center gap-6 text-xs text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500"></span>
            Multi-state robustness
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-cyan-500"></span>
            Developability gating
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-amber-500"></span>
            Self-association screening
          </span>
        </div>
      </div>

      <NewJobForm onCreated={onJobCreated} />
    </div>
  );
}
