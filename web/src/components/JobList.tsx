import { useMemo } from 'react';
import { PipelineSubmissionResponse, PipelineStatusResponse, ProgressEventPayload } from '../api/dtos';
import { JobProgress } from './JobProgress';

export interface JobState {
  jobId: string;
  submission: PipelineSubmissionResponse;
  status?: PipelineStatusResponse;
  latestEvent?: ProgressEventPayload;
}

type Props = {
  jobs: JobState[];
  onProgressEvent: (jobId: string, event: ProgressEventPayload) => void;
  onRemoveJob: (jobId: string) => void;
};

export function JobList({ jobs, onProgressEvent, onRemoveJob }: Props) {
  const sortedJobs = useMemo(() => {
    return [...jobs].sort((a, b) => {
      const left = new Date(a.submission.created_at).getTime();
      const right = new Date(b.submission.created_at).getTime();
      return right - left;
    });
  }, [jobs]);

  if (sortedJobs.length === 0) {
    return (
      <section>
        <h2>Tracked jobs</h2>
        <p>No jobs yet. Submit a pipeline request to get started.</p>
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
            onRemove={() => onRemoveJob(job.jobId)}
          />
        ))}
      </div>
    </section>
  );
}

export default JobList;
