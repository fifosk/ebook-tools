import { useMemo } from 'react';
import { PipelineStatusResponse, ProgressEventPayload } from '../api/dtos';
import { JobProgress } from './JobProgress';

export interface JobState {
  jobId: string;
  status: PipelineStatusResponse;
  latestEvent?: ProgressEventPayload;
  isReloading: boolean;
  isMutating: boolean;
  canManage: boolean;
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
        <h2 className="visually-hidden">Tracked jobs</h2>
        <details className="job-list-collapsible" open>
          <summary>Tracked jobs</summary>
          <p>No persisted jobs yet. Submit a pipeline request to get started.</p>
        </details>
      </section>
    );
  }

  return (
    <section>
      <h2 className="visually-hidden">Tracked jobs</h2>
      <details className="job-list-collapsible" open>
        <summary>Tracked jobs</summary>
        <div className="job-grid">
          {sortedJobs.map((job) => {
            const statusValue = job.status?.status ?? 'pending';
            return (
              <details key={job.jobId} className="job-collapsible" open>
                <summary>
                  <span>Job {job.jobId}</span>
                  <span className="job-status" data-state={statusValue}>
                    {statusValue}
                  </span>
                </summary>
                <JobProgress
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
                  canManage={job.canManage}
                />
              </details>
            );
          })}
        </div>
      </details>
    </section>
  );
}

export default JobList;
