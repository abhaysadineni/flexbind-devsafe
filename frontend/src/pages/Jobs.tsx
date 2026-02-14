import { useState } from 'react';
import JobsList from '../components/JobsList';
import JobDetail from '../components/JobDetail';

export default function Jobs() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  if (selectedJobId) {
    return (
      <JobDetail
        jobId={selectedJobId}
        onBack={() => setSelectedJobId(null)}
      />
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-white">Design Jobs</h2>
        <p className="mt-1 text-sm text-slate-400">
          Click a job to view results, logs, and per-state score breakdowns.
        </p>
      </div>
      <JobsList onSelect={setSelectedJobId} />
    </div>
  );
}
