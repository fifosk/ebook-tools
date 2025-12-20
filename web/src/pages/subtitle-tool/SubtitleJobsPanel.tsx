import type { SubtitleJobResultPayload } from '../../api/dtos';
import type { JobState } from '../../components/JobList';
import { resolveSubtitleDownloadUrl } from '../../api/client';
import { formatTimestamp } from '../../utils/mediaFormatters';
import { getStatusGlyph } from '../../utils/status';
import { extractSubtitleFile, formatSubtitleRetryCounts } from './subtitleToolUtils';
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
            const subtitleDetails = jobResults[job.jobId]?.subtitle;
            const subtitleMetadata = (subtitleDetails?.metadata ?? null) as
              | Record<string, unknown>
              | null;
            const statusFile = extractSubtitleFile(job.status);
            const metadataDownloadValue = subtitleMetadata ? subtitleMetadata['download_url'] : null;
            const metadataDownloadUrl =
              typeof metadataDownloadValue === 'string' ? metadataDownloadValue : null;
            const rawRelativePath =
              statusFile?.relativePath ??
              (typeof subtitleDetails?.relative_path === 'string' ? subtitleDetails.relative_path : null);
            let resolvedRelativePath =
              rawRelativePath && rawRelativePath.trim() ? rawRelativePath.trim() : null;
            const rawOutputPath =
              typeof subtitleDetails?.output_path === 'string' ? subtitleDetails.output_path : null;
            const resultOutputPath = rawOutputPath && rawOutputPath.trim() ? rawOutputPath.trim() : null;
            if (!resolvedRelativePath && resultOutputPath) {
              const normalisedOutput = resultOutputPath.replace(/\\\\/g, '/');
              const marker = `/${job.jobId}/`;
              const markerIndex = normalisedOutput.indexOf(marker);
              if (markerIndex >= 0) {
                const candidate = normalisedOutput.slice(markerIndex + marker.length).trim();
                resolvedRelativePath = candidate || null;
              }
            }
            const derivedNameFromRelative = resolvedRelativePath
              ? resolvedRelativePath.split(/[\\\\/]/).filter(Boolean).pop() ?? null
              : null;
            const derivedNameFromOutput = resultOutputPath
              ? resultOutputPath.split(/[\\\\/]/).filter(Boolean).pop() ?? null
              : null;
            const resolvedName = statusFile?.name ?? derivedNameFromRelative ?? derivedNameFromOutput ?? 'subtitle';
            const directUrl =
              statusFile?.url ??
              metadataDownloadUrl ??
              (resolvedRelativePath ? resolveSubtitleDownloadUrl(job.jobId, resolvedRelativePath) : null);
            const event = job.latestEvent ?? job.status.latest_event ?? null;
            const completed = event?.snapshot.completed ?? 0;
            const total = event?.snapshot.total ?? null;
            const workerValue = subtitleMetadata ? subtitleMetadata['workers'] : null;
            const batchValue = subtitleMetadata ? subtitleMetadata['batch_size'] : null;
            const targetLanguageValue = subtitleMetadata ? subtitleMetadata['target_language'] : null;
            const originalLanguageValue = subtitleMetadata ? subtitleMetadata['original_language'] : null;
            const showOriginalValue = subtitleMetadata ? subtitleMetadata['show_original'] : null;
            const startTimeValue = subtitleMetadata ? subtitleMetadata['start_time_offset_label'] : null;
            const endTimeValue = subtitleMetadata ? subtitleMetadata['end_time_offset_label'] : null;
            const outputFormatValue = subtitleMetadata ? subtitleMetadata['output_format'] : null;
            const outputFormatLabel =
              typeof outputFormatValue === 'string' && outputFormatValue.trim()
                ? outputFormatValue.trim().toUpperCase()
                : null;
            const assFontSizeValue = subtitleMetadata ? subtitleMetadata['ass_font_size'] : null;
            let assFontSizeLabel: number | null = null;
            if (typeof assFontSizeValue === 'number' && Number.isFinite(assFontSizeValue)) {
              assFontSizeLabel = assFontSizeValue;
            } else if (typeof assFontSizeValue === 'string' && assFontSizeValue.trim()) {
              const parsed = Number(assFontSizeValue.trim());
              if (!Number.isNaN(parsed)) {
                assFontSizeLabel = parsed;
              }
            }
            const assEmphasisValue = subtitleMetadata ? subtitleMetadata['ass_emphasis_scale'] : null;
            let assEmphasisLabel: number | null = null;
            if (typeof assEmphasisValue === 'number' && Number.isFinite(assEmphasisValue)) {
              assEmphasisLabel = assEmphasisValue;
            } else if (typeof assEmphasisValue === 'string' && assEmphasisValue.trim()) {
              const parsed = Number(assEmphasisValue.trim());
              if (!Number.isNaN(parsed)) {
                assEmphasisLabel = parsed;
              }
            }
            const workerSetting =
              typeof workerValue === 'number' && Number.isFinite(workerValue)
                ? workerValue
                : null;
            const batchSetting =
              typeof batchValue === 'number' && Number.isFinite(batchValue)
                ? batchValue
                : null;
            const startTimeLabel =
              typeof startTimeValue === 'string' && startTimeValue.trim()
                ? startTimeValue.trim()
                : null;
            const endTimeLabel =
              typeof endTimeValue === 'string' && endTimeValue.trim()
                ? endTimeValue.trim()
                : null;
            const translationLanguage =
              typeof targetLanguageValue === 'string' && targetLanguageValue.trim()
                ? targetLanguageValue.trim()
                : null;
            const originalLanguageLabel =
              typeof originalLanguageValue === 'string' && originalLanguageValue.trim()
                ? originalLanguageValue.trim()
                : null;
            const showOriginalSetting =
              typeof showOriginalValue === 'boolean'
                ? showOriginalValue
                : typeof showOriginalValue === 'string'
                  ? !['false', '0', 'no', 'off'].includes(showOriginalValue.trim().toLowerCase())
                  : null;
            const stage = typeof event?.metadata?.stage === 'string' ? event?.metadata?.stage : null;
            const retrySummary =
              job.status.retry_summary && typeof job.status.retry_summary === 'object'
                ? (job.status.retry_summary as Record<string, Record<string, number>>)
                : null;
            const translationRetries = retrySummary
              ? formatSubtitleRetryCounts(retrySummary.translation)
              : null;
            const transliterationRetries = retrySummary
              ? formatSubtitleRetryCounts(retrySummary.transliteration)
              : null;
            const statusGlyph = getStatusGlyph(job.status.status);
            const updatedAt = job.status.completed_at
              || job.status.started_at
              || (event ? new Date(event.timestamp * 1000).toISOString() : null);
            const subtitleMetadataFromStatus = (() => {
              const rawResult = job.status.result;
              if (!rawResult || typeof rawResult !== 'object') {
                return null;
              }
              const subtitleSection = (rawResult as Record<string, unknown>)['subtitle'];
              if (!subtitleSection || typeof subtitleSection !== 'object') {
                return null;
              }
              const metadata = (subtitleSection as Record<string, unknown>)['metadata'];
              return metadata && typeof metadata === 'object'
                ? (metadata as Record<string, unknown>)
                : null;
            })();
            const audiobookToggleValue =
              subtitleMetadataFromStatus?.['generate_audio_book'] ?? subtitleMetadata?.['generate_audio_book'];
            const isNarratedSubtitleJob =
              typeof audiobookToggleValue === 'boolean'
                ? audiobookToggleValue
                : typeof audiobookToggleValue === 'string'
                  ? ['true', '1', 'yes', 'on'].includes(audiobookToggleValue.trim().toLowerCase())
                  : false;
            const isLibraryCandidate =
              job.status.status === 'completed' ||
              (job.status.status === 'paused' && job.status.media_completed === true);
            const canMoveToLibrary = Boolean(onMoveToLibrary) && job.canManage && isNarratedSubtitleJob && isLibraryCandidate;
            return (
              <article key={job.jobId} className="subtitle-job-card">
                <header>
                  <h3>Job {job.jobId}</h3>
                  <span
                    className={`job-status badge-${job.status.status}`}
                    data-state={job.status.status}
                    title={statusGlyph.label}
                    aria-label={statusGlyph.label}
                  >
                    {statusGlyph.icon}
                  </span>
                </header>
                <dl>
                  <div>
                    <dt>Submitted</dt>
                    <dd>{formatTimestamp(job.status.created_at) ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Updated</dt>
                    <dd>{formatTimestamp(updatedAt) ?? '—'}</dd>
                  </div>
                  {originalLanguageLabel ? (
                    <div>
                      <dt>Original language</dt>
                      <dd>{originalLanguageLabel}</dd>
                    </div>
                  ) : null}
                  {translationLanguage ? (
                    <div>
                      <dt>Translation language</dt>
                      <dd>{translationLanguage}</dd>
                    </div>
                  ) : null}
                  {outputFormatLabel ? (
                    <div>
                      <dt>Format</dt>
                      <dd>{outputFormatLabel}</dd>
                    </div>
                  ) : null}
                  {outputFormatLabel === 'ASS' && assFontSizeLabel ? (
                    <div>
                      <dt>ASS font size</dt>
                      <dd>{assFontSizeLabel}</dd>
                    </div>
                  ) : null}
                  {outputFormatLabel === 'ASS' && assEmphasisLabel ? (
                    <div>
                      <dt>ASS emphasis</dt>
                      <dd>{assEmphasisLabel}×</dd>
                    </div>
                  ) : null}
                  {showOriginalSetting !== null ? (
                    <div>
                      <dt>Show original text</dt>
                      <dd>{showOriginalSetting ? 'Yes' : 'No'}</dd>
                    </div>
                  ) : null}
                  {event ? (
                    <div>
                      <dt>Progress</dt>
                      <dd>
                        {completed}
                        {total !== null ? ` / ${total}` : ''}
                      </dd>
                    </div>
                  ) : null}
                  {workerSetting ? (
                    <div>
                      <dt>Worker threads</dt>
                      <dd>{workerSetting}</dd>
                    </div>
                  ) : null}
                  {batchSetting ? (
                    <div>
                      <dt>Batch size</dt>
                      <dd>{batchSetting}</dd>
                    </div>
                  ) : null}
                  {startTimeLabel ? (
                    <div>
                      <dt>Start time</dt>
                      <dd>{startTimeLabel}</dd>
                    </div>
                  ) : null}
                  {endTimeLabel ? (
                    <div>
                      <dt>End time</dt>
                      <dd>{endTimeLabel}</dd>
                    </div>
                  ) : null}
                  {translationRetries ? (
                    <div>
                      <dt>Translation retries</dt>
                      <dd>{translationRetries}</dd>
                    </div>
                  ) : null}
                  {transliterationRetries ? (
                    <div>
                      <dt>Transliteration retries</dt>
                      <dd>{transliterationRetries}</dd>
                    </div>
                  ) : null}
                  {stage ? (
                    <div>
                      <dt>Stage</dt>
                      <dd>{stage}</dd>
                    </div>
                  ) : null}
                </dl>
                {directUrl ? (
                  <p>
                    <a href={directUrl} className="link-button" target="_blank" rel="noopener noreferrer">
                      Download {resolvedName}
                    </a>
                  </p>
                ) : job.status.status === 'completed' ? (
                  <p>Preparing download link…</p>
                ) : null}
                <footer>
                  <button type="button" className="link-button" onClick={() => onSelectJob(job.jobId)}>
                    View job details
                  </button>
                  {canMoveToLibrary ? (
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
