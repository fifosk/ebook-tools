import { useMemo } from 'react';
import {
  AccessPolicyUpdatePayload,
  PipelineResponsePayload,
  PipelineStatusResponse,
  ProgressEventPayload
} from '../api/dtos';
import { getStatusGlyph } from '../utils/status';
import { formatModelLabel } from '../utils/modelInfo';
import { JobProgress } from './JobProgress';

export interface JobState {
  jobId: string;
  status: PipelineStatusResponse;
  latestEvent?: ProgressEventPayload;
  isReloading: boolean;
  isMutating: boolean;
  canManage: boolean;
  canView?: boolean;
}

type Props = {
  jobs: JobState[];
  onProgressEvent: (jobId: string, event: ProgressEventPayload) => void;
  onPauseJob: (jobId: string) => void;
  onResumeJob: (jobId: string) => void;
  onCancelJob: (jobId: string) => void;
  onDeleteJob: (jobId: string) => void;
  onReloadJob: (jobId: string) => void;
  onRestartJob?: (jobId: string) => void;
  onUpdateAccess?: (jobId: string, payload: AccessPolicyUpdatePayload) => Promise<void>;
};

export function JobList({
  jobs,
  onProgressEvent,
  onPauseJob,
  onResumeJob,
  onCancelJob,
  onDeleteJob,
  onReloadJob,
  onRestartJob,
  onUpdateAccess
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
        <h2 className="visually-hidden">Active jobs</h2>
        <details className="job-list-collapsible" open>
          <summary>Active jobs</summary>
          <p>No persisted jobs yet. Submit a pipeline request to get started.</p>
        </details>
      </section>
    );
  }

  return (
    <section>
      <h2 className="visually-hidden">Active jobs</h2>
      <details className="job-list-collapsible" open>
        <summary>Active jobs</summary>
        <div className="job-grid">
          {sortedJobs.map((job) => {
            const statusValue = job.status?.status ?? 'pending';
            const statusGlyph = getStatusGlyph(statusValue);
            const parameters = job.status?.parameters ?? null;
            const pipelineResult =
              job.status?.result && typeof job.status.result === 'object'
                ? (job.status.result as PipelineResponsePayload)
                : null;
            const pipelineConfig =
              pipelineResult &&
              pipelineResult.pipeline_config &&
              typeof pipelineResult.pipeline_config === 'object'
                ? (pipelineResult.pipeline_config as Record<string, unknown>)
                : null;
            const llmModelRaw =
              (parameters && typeof parameters.llm_model === 'string' ? parameters.llm_model : null) ??
              (pipelineConfig && typeof pipelineConfig['ollama_model'] === 'string'
                ? (pipelineConfig['ollama_model'] as string)
                : null);
            const llmModel = formatModelLabel(llmModelRaw);
            return (
              <details key={job.jobId} className="job-collapsible" open>
                <summary>
                  <span>Job {job.jobId}</span>
                  <span className="job-type">{job.status.job_type}</span>
                  {llmModel ? (
                    <span className="job-model" title="LLM model">
                      {llmModel}
                    </span>
                  ) : null}
                  <span className="job-status" data-state={statusValue} title={statusGlyph.label} aria-label={statusGlyph.label}>
                    {statusGlyph.icon}
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
                  onRestart={onRestartJob ? () => onRestartJob(job.jobId) : () => {}}
                  onReload={() => onReloadJob(job.jobId)}
                  isReloading={job.isReloading}
                  isMutating={job.isMutating}
                  canManage={job.canManage}
                  onUpdateAccess={
                    onUpdateAccess ? (payload) => onUpdateAccess(job.jobId, payload) : undefined
                  }
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
