import type { SubtitleJobResultPayload } from '../../api/dtos';
import type { JobState } from '../../components/JobList';
import { formatTimestamp } from '../../utils/mediaFormatters';
import { buildSubtitleJobPresentation } from './subtitleJobPresentation';
import styles from '../SubtitleToolPage.module.css';

type SubtitleJobsPanelProps = {
  jobs: JobState[];
  jobResults: Record<string, SubtitleJobResultPayload>;
  onSelectJob: (jobId: string) => void;
  onMoveToLibrary?: (jobId: string) => void;
};

export default function SubtitleJobsPanel({
  jobs,
  jobResults,
  onSelectJob,
  onMoveToLibrary
}: SubtitleJobsPanelProps) {
  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <h2 className={styles.cardTitle}>Subtitle jobs</h2>
          <p className={styles.cardHint}>Track progress and download completed subtitle exports.</p>
        </div>
      </div>
      {jobs.length === 0 ? (
        <p>No subtitle jobs yet. Submit a job to get started.</p>
      ) : (
        <div className="subtitle-job-grid">
          {jobs.map((job) => {
            const presentation = buildSubtitleJobPresentation(
              job,
              jobResults[job.jobId]?.subtitle,
              Boolean(onMoveToLibrary)
            );
            return (
              <article key={job.jobId} className="subtitle-job-card">
                <header>
                  <h3>Job {job.jobId}</h3>
                  <span
                    className={`job-status badge-${job.status.status}`}
                    data-state={job.status.status}
                    title={presentation.statusGlyph.label}
                    aria-label={presentation.statusGlyph.label}
                  >
                    {presentation.statusGlyph.icon}
                  </span>
                </header>
                <dl>
                  <div>
                    <dt>Submitted</dt>
                    <dd>{formatTimestamp(job.status.created_at) ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Updated</dt>
                    <dd>{formatTimestamp(presentation.updatedAt) ?? '—'}</dd>
                  </div>
                  {presentation.originalLanguageLabel ? (
                    <div>
                      <dt>Original language</dt>
                      <dd>{presentation.originalLanguageLabel}</dd>
                    </div>
                  ) : null}
                  {presentation.translationLanguage ? (
                    <div>
                      <dt>Translation language</dt>
                      <dd>{presentation.translationLanguage}</dd>
                    </div>
                  ) : null}
                  {presentation.outputFormatLabel ? (
                    <div>
                      <dt>Format</dt>
                      <dd>{presentation.outputFormatLabel}</dd>
                    </div>
                  ) : null}
                  {presentation.outputFormatLabel === 'ASS' && presentation.assFontSizeLabel ? (
                    <div>
                      <dt>ASS font size</dt>
                      <dd>{presentation.assFontSizeLabel}</dd>
                    </div>
                  ) : null}
                  {presentation.outputFormatLabel === 'ASS' && presentation.assEmphasisLabel ? (
                    <div>
                      <dt>ASS emphasis</dt>
                      <dd>{presentation.assEmphasisLabel}×</dd>
                    </div>
                  ) : null}
                  {presentation.showOriginalSetting !== null ? (
                    <div>
                      <dt>Show original text</dt>
                      <dd>{presentation.showOriginalSetting ? 'Yes' : 'No'}</dd>
                    </div>
                  ) : null}
                  {presentation.event ? (
                    <div>
                      <dt>Progress</dt>
                      <dd>
                        {presentation.completed}
                        {presentation.total !== null ? ` / ${presentation.total}` : ''}
                      </dd>
                    </div>
                  ) : null}
                  {presentation.workerSetting ? (
                    <div>
                      <dt>Worker threads</dt>
                      <dd>{presentation.workerSetting}</dd>
                    </div>
                  ) : null}
                  {presentation.batchSetting ? (
                    <div>
                      <dt>Batch size</dt>
                      <dd>{presentation.batchSetting}</dd>
                    </div>
                  ) : null}
                  {presentation.translationBatchSetting ? (
                    <div>
                      <dt>LLM batch</dt>
                      <dd>{presentation.translationBatchSetting}</dd>
                    </div>
                  ) : null}
                  {presentation.startTimeLabel ? (
                    <div>
                      <dt>Start time</dt>
                      <dd>{presentation.startTimeLabel}</dd>
                    </div>
                  ) : null}
                  {presentation.endTimeLabel ? (
                    <div>
                      <dt>End time</dt>
                      <dd>{presentation.endTimeLabel}</dd>
                    </div>
                  ) : null}
                  {presentation.translationRetries ? (
                    <div>
                      <dt>Translation retries</dt>
                      <dd>{presentation.translationRetries}</dd>
                    </div>
                  ) : null}
                  {presentation.transliterationRetries ? (
                    <div>
                      <dt>Transliteration retries</dt>
                      <dd>{presentation.transliterationRetries}</dd>
                    </div>
                  ) : null}
                  {presentation.stage ? (
                    <div>
                      <dt>Stage</dt>
                      <dd>{presentation.stage}</dd>
                    </div>
                  ) : null}
                </dl>
                {presentation.directUrl ? (
                  <p>
                    <a href={presentation.directUrl} className="link-button" target="_blank" rel="noopener noreferrer">
                      Download {presentation.resolvedName}
                    </a>
                  </p>
                ) : job.status.status === 'completed' ? (
                  <p>Preparing download link…</p>
                ) : null}
                <footer>
                  <button type="button" className="link-button" onClick={() => onSelectJob(job.jobId)}>
                    View job details
                  </button>
                  {presentation.canMoveToLibrary ? (
                    <button
                      type="button"
                      className="link-button"
                      onClick={() => onMoveToLibrary?.(job.jobId)}
                    >
                      Move to library
                    </button>
                  ) : null}
                </footer>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
