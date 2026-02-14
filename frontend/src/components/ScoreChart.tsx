import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import type { StateScore, DevelopabilityBreakdown } from '../types';

interface PerStateChartProps {
  scores: StateScore[];
}

export function PerStateChart({ scores }: PerStateChartProps) {
  const data = scores.map((s) => ({
    state: `S${s.state_index}`,
    Contacts: s.contact_score,
    'H-bonds': s.hbond_proxy,
    SASA: s.sasa_burial,
    Composite: s.composite,
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="state" tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            labelStyle={{ color: '#e2e8f0' }}
          />
          <Bar dataKey="Contacts" fill="#22d3ee" radius={[3, 3, 0, 0]} />
          <Bar dataKey="H-bonds" fill="#2dd4bf" radius={[3, 3, 0, 0]} />
          <Bar dataKey="SASA" fill="#a78bfa" radius={[3, 3, 0, 0]} />
          <Bar dataKey="Composite" fill="#f59e0b" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

interface DevRadarProps {
  dev: DevelopabilityBreakdown;
}

export function DevRadarChart({ dev }: DevRadarProps) {
  const data = [
    { metric: 'Low Hydrophobicity', value: Math.max(0, (1 - dev.hydrophobic_patch) * 100) },
    { metric: 'Charge OK', value: Math.max(0, 100 - Math.abs(dev.net_charge) * 5) },
    { metric: 'pI OK', value: dev.pI >= 6 && dev.pI <= 9 ? 90 : 50 },
    { metric: 'Low β-sheet', value: Math.max(0, (2 - dev.beta_propensity) * 50) },
    { metric: 'Low Self-Agg', value: Math.max(0, 100 - dev.self_dock_risk * 10) },
  ];

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="#334155" />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fill: '#94a3b8', fontSize: 10 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: '#64748b', fontSize: 9 }}
          />
          <Radar
            name="Score"
            dataKey="value"
            stroke="#22d3ee"
            fill="#22d3ee"
            fillOpacity={0.2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
