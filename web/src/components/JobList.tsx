import { useMemo } from 'react';
import { PipelineStatusResponse, ProgressEventPayload } from '../api/dtos';
import { JobProgress } from './JobProgress';

export interface JobState {
  jobId: string;
  status: PipelineStatusResponse;
  latestEvent?: ProgressEventPayload;
  isReloading: boolean;
  isMutating: boolean;
}

type Props = {
  jobs: JobState[];
  onProgressEvent: (jobId: string, event: ProgressEventPayload) => void;
  onPauseJob: (jobId: string) => void;
  onResumeJob: (jobId: string) => void;
  onCancelJob: (jobId: string) => void;
  onDeleteJob: (jobId: string) => void;
  onReloadJob: (jobId: string) => void;
};

export function JobList({
  jobs,
  onProgressEvent,
  onPauseJob,
  onResumeJob,
  onCancelJob,
  onDeleteJob,
  onReloadJob
}: Props) {
  const sortedJobs = useMemo(() => {
    return [...jobs].sort((a, b) => {
      const left = new Date(a.status.created_at).getTime();
      const right = new Date(b.status.created_at).getTime();
      return right - left;
    });
  }, [jobs]);

  if (sortedJobs.length === 0) {
    return (
      <section>
        <h2>Tracked jobs</h2>
        <p>No persisted jobs yet. Submit a pipeline request to get started.</p>
      </section>
    );
  }

  return (
    <section>
      <h2>Tracked jobs</h2>
      <div className="job-grid">
        {sortedJobs.map((job) => (
          <JobProgress
            key={job.jobId}
            jobId={job.jobId}
            status={job.status}
            latestEvent={job.latestEvent}
            onEvent={(event) => onProgressEvent(job.jobId, event)}
            onPause={() => onPauseJob(job.jobId)}
            onResume={() => onResumeJob(job.jobId)}
            onCancel={() => onCancelJob(job.jobId)}
            onDelete={() => onDeleteJob(job.jobId)}
            onReload={() => onReloadJob(job.jobId)}
            isReloading={job.isReloading}
            isMutating={job.isMutating}
          />
        ))}
      </div>
    </section>
  );
}

export default JobList;
