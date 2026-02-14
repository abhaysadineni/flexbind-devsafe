import type { JobListItem, JobStatusResponse, JobReport } from './types';

const BASE = 'https://flexbind-api.onrender.com';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export async function createJob(form: FormData): Promise<JobStatusResponse> {
  return request<JobStatusResponse>('/api/jobs', {
    method: 'POST',
    body: form,
  });
}

export async function listJobs(): Promise<JobListItem[]> {
  return request<JobListItem[]>('/api/jobs');
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/api/jobs/${jobId}`);
}

export async function getJobReport(jobId: string): Promise<JobReport> {
  return request<JobReport>(`/api/jobs/${jobId}/report`);
}

export function getDownloadUrl(jobId: string): string {
  return `${BASE}/api/jobs/${jobId}/download`;
}

export function getLogsUrl(jobId: string): string {
  return `${BASE}/api/jobs/${jobId}/logs`;
}
