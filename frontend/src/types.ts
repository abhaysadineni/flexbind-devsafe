export type BinderType = 'antibody_fv' | 'other';
export type RunMode = 'fast' | 'deep';
export type JobStatus = 'queued' | 'running' | 'done' | 'failed';

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  message: string;
}

export interface JobListItem {
  job_id: string;
  status: JobStatus;
  binder_type: BinderType;
  mode: RunMode;
  created_at: string;
  progress: number;
}

export interface StateScore {
  state_index: number;
  contact_score: number;
  clash_score: number;
  hbond_proxy: number;
  sasa_burial: number;
  composite: number;
}

export interface DesignResult {
  rank: number;
  sequence: string;
  mutations: string;
  mean_score: number;
  worst_score: number;
  robustness: number;
  developability_score: number;
  developability_flag: string;
  per_state_scores: StateScore[];
}

export interface DevelopabilityBreakdown {
  hydrophobic_patch: number;
  net_charge: number;
  pI: number;
  beta_propensity: number;
  self_dock_risk: number;
  composite: number;
  flag: string;
}

export interface JobReport {
  job_id: string;
  status: JobStatus;
  binder_type: BinderType;
  mode: RunMode;
  seed: number;
  ensemble_size: number;
  designs: DesignResult[];
  developability: DevelopabilityBreakdown | null;
  errors: string[];
}
