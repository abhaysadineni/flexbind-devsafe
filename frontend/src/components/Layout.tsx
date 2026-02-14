import type { ReactNode } from 'react';

interface LayoutProps {
  children: ReactNode;
  page: 'home' | 'jobs';
  onNavigate: (p: 'home' | 'jobs') => void;
}

export default function Layout({ children, page, onNavigate }: LayoutProps) {
  return (
    <div className="min-h-screen bg-grid">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <button
            onClick={() => onNavigate('home')}
            className="flex items-center gap-3 group"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-teal-600 text-sm font-bold text-white shadow-lg shadow-cyan-500/20">
              Fb
            </div>
            <div>
              <span className="text-lg font-semibold tracking-tight text-white group-hover:text-cyan-400 transition-colors">
                FlexBind
              </span>
              <span className="ml-1 text-xs font-medium text-cyan-400/70">DevSafe</span>
            </div>
          </button>

          <nav className="flex items-center gap-1">
            <NavButton
              active={page === 'home'}
              onClick={() => onNavigate('home')}
            >
              New Job
            </NavButton>
            <NavButton
              active={page === 'jobs'}
              onClick={() => onNavigate('jobs')}
            >
              Jobs
            </NavButton>
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-6xl px-6 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/40 py-6 text-center text-xs text-slate-600">
        FlexBind-DevSafe v1.0 — Ensemble-aware binder design with developability gating
      </footer>
    </div>
  );
}

function NavButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${
        active
          ? 'bg-slate-800 text-cyan-400 shadow-inner'
          : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
      }`}
    >
      {children}
    </button>
  );
}
