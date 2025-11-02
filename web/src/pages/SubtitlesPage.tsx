import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import type { ChangeEvent } from 'react';
import type { JobState } from '../components/JobList';
import { useLanguagePreferences } from '../context/LanguageProvider';
import {
  fetchSubtitleSources,
  fetchSubtitleResult,
  resolveSubtitleDownloadUrl,
  submitSubtitleJob
} from '../api/client';
import type { SubtitleJobResultPayload, SubtitleSourceEntry } from '../api/dtos';
import { TOP_LANGUAGES } from '../constants/menuOptions';
import { formatTimestamp } from '../utils/mediaFormatters';

type SourceMode = 'existing' | 'upload';

type Props = {
  subtitleJobs: JobState[];
  onJobCreated: (jobId: string) => void;
  onSelectJob: (jobId: string) => void;
};

const DEFAULT_SOURCE_DIRECTORY = '/Volumes/Data/Download/Subtitles';
const DEFAULT_WORKER_COUNT = 30;
const DEFAULT_BATCH_SIZE = 30;
const DEFAULT_START_TIME = '00:00';

function deriveDirectoryFromPath(value: string | undefined): string {
  if (!value) {
    return DEFAULT_SOURCE_DIRECTORY;
  }
  const normalised = value.trim().replace(/\\+/g, '/');
  if (!normalised) {
    return DEFAULT_SOURCE_DIRECTORY;
  }
  const index = normalised.lastIndexOf('/');
  if (index <= 0) {
    return normalised;
  }
  return normalised.slice(0, index);
}

function extractSubtitleFile(status: JobState['status']): {
  name: string;
  relativePath: string | null;
  url: string | null;
} | null {
  const generated = status.generated_files;
  if (!generated || typeof generated !== 'object') {
    return null;
  }
  const record = generated as Record<string, unknown>;
  const files = record.files;
  if (!Array.isArray(files)) {
    return null;
  }
  for (const entry of files) {
    if (!entry || typeof entry !== 'object') {
      continue;
    }
    const file = entry as Record<string, unknown>;
    const type = typeof file.type === 'string' ? file.type : undefined;
    if ((type ?? '').toLowerCase() !== 'subtitle') {
      continue;
    }
    const name = typeof file.name === 'string' ? file.name : 'subtitle';
    const relativePath = typeof file.relative_path === 'string' ? file.relative_path : null;
    const url = typeof file.url === 'string' ? file.url : null;
    return { name, relativePath, url };
  }
  return null;
}

function normaliseLanguage(value: string): string {
  return value.trim() || '';
}

function normaliseTimecodeInput(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return DEFAULT_START_TIME;
  }

  const match = trimmed.match(/^(\d+):(\d{1,2})(?::(\d{1,2}))?$/);
  if (!match) {
    return null;
  }

  const [, primary, secondary, tertiary] = match;
  const first = Number(primary);
  const second = Number(secondary);
  const third = typeof tertiary === 'string' ? Number(tertiary) : null;

  if ([first, second, third ?? 0].some((component) => !Number.isFinite(component) || component < 0)) {
    return null;
  }
  if (second >= 60 || (third !== null && third >= 60)) {
    return null;
  }

  if (third !== null) {
    const hours = first;
    const minutes = second;
    const seconds = third;
    return [hours, minutes, seconds].map((component) => component.toString().padStart(2, '0')).join(':');
  }

  const minutes = first;
  const seconds = second;
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

export default function SubtitlesPage({ subtitleJobs, onJobCreated, onSelectJob }: Props) {
  const {
    inputLanguage,
    setInputLanguage,
    primaryTargetLanguage,
    setPrimaryTargetLanguage
  } = useLanguagePreferences();
  const [targetLanguage, setTargetLanguage] = useState<string>(primaryTargetLanguage ?? 'French');
  const [sourceMode, setSourceMode] = useState<SourceMode>('existing');
  const [sources, setSources] = useState<SubtitleSourceEntry[]>([]);
  const [selectedSource, setSelectedSource] = useState<string>('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [enableTransliteration, setEnableTransliteration] = useState<boolean>(true);
  const [enableHighlight, setEnableHighlight] = useState<boolean>(true);
  const [mirrorToSourceDir, setMirrorToSourceDir] = useState<boolean>(true);
  const [workerCount, setWorkerCount] = useState<number | ''>(DEFAULT_WORKER_COUNT);
  const [batchSize, setBatchSize] = useState<number | ''>(DEFAULT_BATCH_SIZE);
  const [startTime, setStartTime] = useState<string>(DEFAULT_START_TIME);
  const [isLoadingSources, setLoadingSources] = useState<boolean>(false);
  const [isSubmitting, setSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [lastSubmittedJobId, setLastSubmittedJobId] = useState<string | null>(null);
  const [lastSubmittedWorkerCount, setLastSubmittedWorkerCount] = useState<number | null>(
    typeof DEFAULT_WORKER_COUNT === 'number' ? DEFAULT_WORKER_COUNT : null
  );
  const [jobResults, setJobResults] = useState<Record<string, SubtitleJobResultPayload>>({});
  const [lastSubmittedBatchSize, setLastSubmittedBatchSize] = useState<number | null>(
    typeof DEFAULT_BATCH_SIZE === 'number' ? DEFAULT_BATCH_SIZE : null
  );
  const [lastSubmittedStartTime, setLastSubmittedStartTime] = useState<string>(DEFAULT_START_TIME);

  useEffect(() => {
    setTargetLanguage(primaryTargetLanguage ?? targetLanguage);
  }, [primaryTargetLanguage]);

  const refreshSources = useCallback(
    async (hint?: string) => {
      setLoadingSources(true);
      try {
        const directory = deriveDirectoryFromPath(hint);
        const entries = await fetchSubtitleSources(directory);
        setSources(entries);
        if (!selectedSource && entries.length > 0) {
          setSelectedSource(entries[0].path);
        }
      } catch (error) {
        console.warn('Unable to list subtitle sources', error);
      } finally {
        setLoadingSources(false);
      }
    },
    [selectedSource]
  );

  useEffect(() => {
    refreshSources();
  }, [refreshSources]);

  useEffect(() => {
    const completedSubtitleJobs = subtitleJobs.filter(
      (job) => job.status.job_type === 'subtitle' && job.status.status === 'completed'
    );
    const missing = completedSubtitleJobs.filter((job) => jobResults[job.jobId] === undefined);
    if (missing.length === 0) {
      return;
    }

    let cancelled = false;
    (async () => {
      const results = await Promise.all(
        missing.map(async (job) => {
          try {
            const payload = await fetchSubtitleResult(job.jobId);
            return { jobId: job.jobId, payload };
          } catch (error) {
            console.warn('Unable to load subtitle result', job.jobId, error);
            return null;
          }
        })
      );
      if (cancelled) {
        return;
      }
      setJobResults((previous) => {
        const next = { ...previous };
        for (const entry of results) {
          if (!entry) {
            continue;
          }
          next[entry.jobId] = entry.payload;
        }
        return next;
      });
    })();

    return () => {
      cancelled = true;
    };
  }, [subtitleJobs, jobResults]);

  const handleSourceModeChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value === 'upload' ? 'upload' : 'existing';
    setSourceMode(value);
    setSubmitError(null);
  }, []);

  const handleSourceChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    setSelectedSource(event.target.value);
  }, []);

  const handleUploadChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files && event.target.files.length > 0 ? event.target.files[0] : null;
    setUploadFile(file);
  }, []);

  const handleTargetLanguageChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const value = normaliseLanguage(event.target.value);
    setTargetLanguage(value);
    if (value) {
      setPrimaryTargetLanguage(value);
    }
  }, [setPrimaryTargetLanguage]);

  const handleInputLanguageChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const value = normaliseLanguage(event.target.value);
    setInputLanguage(value || 'English');
  }, [setInputLanguage]);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setSubmitError(null);

      const trimmedTarget = normaliseLanguage(targetLanguage);
      if (!trimmedTarget) {
        setSubmitError('Choose a target language.');
        return;
      }

      if (sourceMode === 'existing' && !selectedSource.trim()) {
        setSubmitError('Select a subtitle file to process.');
        return;
      }
      if (sourceMode === 'upload' && !uploadFile) {
        setSubmitError('Choose a subtitle file to upload.');
        return;
      }

      const normalisedStartTime = normaliseTimecodeInput(startTime);
      if (normalisedStartTime === null) {
        setSubmitError('Enter a valid start time in MM:SS or HH:MM:SS format.');
        return;
      }

      const formData = new FormData();
      formData.append('input_language', inputLanguage);
      formData.append('target_language', trimmedTarget);
      formData.append('enable_transliteration', String(enableTransliteration));
      formData.append('highlight', String(enableHighlight));
      formData.append('mirror_batches_to_source_dir', String(mirrorToSourceDir));
      formData.append('start_time', normalisedStartTime);
      if (sourceMode === 'existing') {
        formData.append('source_path', selectedSource.trim());
      } else if (uploadFile) {
        formData.append('file', uploadFile, uploadFile.name);
      }
      if (typeof workerCount === 'number' && workerCount > 0) {
        formData.append('worker_count', String(workerCount));
      }
      if (typeof batchSize === 'number' && batchSize > 0) {
        formData.append('batch_size', String(batchSize));
      }

      setSubmitting(true);
      try {
        const response = await submitSubtitleJob(formData);
        setLastSubmittedJobId(response.job_id);
        setLastSubmittedWorkerCount(typeof workerCount === 'number' ? workerCount : null);
        setLastSubmittedBatchSize(typeof batchSize === 'number' ? batchSize : null);
        setLastSubmittedStartTime(normalisedStartTime);
        if (normalisedStartTime !== startTime) {
          setStartTime(normalisedStartTime);
        }
        onJobCreated(response.job_id);
        if (sourceMode === 'upload') {
          setUploadFile(null);
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to submit subtitle job.';
        setSubmitError(message);
      } finally {
        setSubmitting(false);
      }
    },
    [
      enableHighlight,
      enableTransliteration,
      inputLanguage,
      onJobCreated,
      selectedSource,
      sourceMode,
      targetLanguage,
      uploadFile,
      workerCount,
      batchSize,
      mirrorToSourceDir,
      startTime
    ]
  );

  const sortedSubtitleJobs = useMemo(() => {
    return [...subtitleJobs].sort((a, b) => {
      const left = new Date(a.status.created_at).getTime();
      const right = new Date(b.status.created_at).getTime();
      return right - left;
    });
  }, [subtitleJobs]);

  return (
    <div className="subtitles-page">
      <header className="page-header">
        <h1>Subtitle processing</h1>
        <p>Translate or transliterate subtitle files into dynamic highlight (DRT) output.</p>
      </header>

      <section className="card">
        <h2>Submit subtitle job</h2>
        <form onSubmit={handleSubmit} className="subtitle-form">
          <fieldset>
            <legend>Subtitle source</legend>
            <div className="field">
              <label>
                <input
                  type="radio"
                  name="subtitle_source_mode"
                  value="existing"
                  checked={sourceMode === 'existing'}
                  onChange={handleSourceModeChange}
                />
                Use existing file
              </label>
              <label>
                <input
                  type="radio"
                  name="subtitle_source_mode"
                  value="upload"
                  checked={sourceMode === 'upload'}
                  onChange={handleSourceModeChange}
                />
                Upload new file
              </label>
            </div>
            {sourceMode === 'existing' ? (
              <div className="field">
                <label className="field-label" htmlFor="subtitle-source-input">
                  Subtitle path
                </label>
                <input
                  id="subtitle-source-input"
                  type="text"
                  value={selectedSource}
                  onChange={handleSourceChange}
                  list="subtitle-source-list"
                  placeholder={`${DEFAULT_SOURCE_DIRECTORY}/example.srt`}
                  disabled={isLoadingSources}
                />
                <datalist id="subtitle-source-list">
                  {sources.map((entry) => (
                    <option key={entry.path} value={entry.path}>
                      {entry.name}
                    </option>
                  ))}
                </datalist>
                <div className="field-actions">
                  <button type="button" className="link-button" onClick={() => refreshSources(selectedSource)}>
                    Refresh list
                  </button>
                </div>
              </div>
            ) : (
              <div className="field">
                <label className="field-label" htmlFor="subtitle-upload-input">
                  Upload subtitle file
                </label>
                <input
                  id="subtitle-upload-input"
                  type="file"
                  accept=".srt,.vtt"
                  onChange={handleUploadChange}
                />
              </div>
            )}
          </fieldset>

          <fieldset>
            <legend>Languages</legend>
            <div className="field">
              <label className="field-label" htmlFor="subtitle-input-language">Source language</label>
              <input
                id="subtitle-input-language"
                type="text"
                value={inputLanguage}
                onChange={handleInputLanguageChange}
                placeholder="English"
              />
            </div>
            <div className="field">
              <label className="field-label" htmlFor="subtitle-target-language">Target language</label>
              <input
                id="subtitle-target-language"
                type="text"
                value={targetLanguage}
                onChange={handleTargetLanguageChange}
                list="subtitle-language-options"
                placeholder="Arabic"
              />
              <datalist id="subtitle-language-options">
                {TOP_LANGUAGES.map((language) => (
                  <option key={language} value={language} />
                ))}
              </datalist>
            </div>
            <div className="field-inline">
              <label>
                <input
                  type="checkbox"
                  checked={enableTransliteration}
                  onChange={(event) => setEnableTransliteration(event.target.checked)}
                />
                Enable transliteration for non-Latin scripts
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={enableHighlight}
                  onChange={(event) => setEnableHighlight(event.target.checked)}
                />
                Dynamic word highlighting
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={mirrorToSourceDir}
                  onChange={(event) => setMirrorToSourceDir(event.target.checked)}
                />
                Write batches to <code>{DEFAULT_SOURCE_DIRECTORY}</code>
              </label>
              <label>
                Worker threads
                <input
                  type="number"
                  min={1}
                  max={32}
                  value={workerCount}
                  onChange={(event) => {
                    const raw = event.target.value;
                    if (!raw.trim()) {
                      setWorkerCount('');
                      return;
                    }
                    const parsed = Number(raw);
                    if (Number.isNaN(parsed)) {
                      return;
                    }
                    setWorkerCount(Math.min(Math.max(1, parsed), 32));
                  }}
                />
              </label>
              <label>
                Batch size
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={batchSize}
                  onChange={(event) => {
                    const raw = event.target.value;
                    if (!raw.trim()) {
                      setBatchSize('');
                      return;
                    }
                    const parsed = Number(raw);
                    if (Number.isNaN(parsed)) {
                      return;
                    }
                    setBatchSize(Math.min(Math.max(1, parsed), 500));
                  }}
                />
              </label>
              <label>
                Start time (MM:SS or HH:MM:SS)
                <input
                  type="text"
                  value={startTime}
                  onChange={(event) => setStartTime(event.target.value)}
                  placeholder={DEFAULT_START_TIME}
                  inputMode="numeric"
                />
              </label>
            </div>
          </fieldset>

          {submitError ? <div className="alert" role="alert">{submitError}</div> : null}
          {lastSubmittedJobId ? (
            <div className="notice notice--info" role="status">
              Submitted subtitle job {lastSubmittedJobId}
              {(() => {
                const details: string[] = [];
                if (lastSubmittedWorkerCount) {
                  details.push(
                    `${lastSubmittedWorkerCount} thread${lastSubmittedWorkerCount === 1 ? '' : 's'}`
                  );
                }
                if (lastSubmittedBatchSize) {
                  details.push(`batch size ${lastSubmittedBatchSize}`);
                }
                if (lastSubmittedStartTime && lastSubmittedStartTime !== DEFAULT_START_TIME) {
                  details.push(`starting at ${lastSubmittedStartTime}`);
                }
                if (details.length === 0) {
                  return ' using auto-detected concurrency. Live status appears below.';
                }
                const detailText =
                  details.length === 1
                    ? details[0]
                    : `${details.slice(0, -1).join(', ')} and ${details[details.length - 1]}`;
                return ` using ${detailText}. Live status appears below.`;
              })()}
            </div>
          ) : null}

          <div className="form-actions">
            <button type="submit" className="primary" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting…' : 'Create subtitle job'}
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <h2>Subtitle jobs</h2>
        {sortedSubtitleJobs.length === 0 ? (
          <p>No subtitle jobs yet. Submit a job to get started.</p>
        ) : (
          <div className="subtitle-job-grid">
            {sortedSubtitleJobs.map((job) => {
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
                const normalisedOutput = resultOutputPath.replace(/\\/g, '/');
                const marker = `/${job.jobId}/`;
                const markerIndex = normalisedOutput.indexOf(marker);
                if (markerIndex >= 0) {
                  const candidate = normalisedOutput.slice(markerIndex + marker.length).trim();
                  resolvedRelativePath = candidate || null;
                }
              }
              const derivedNameFromRelative = resolvedRelativePath
                ? resolvedRelativePath.split(/[\\/]/).filter(Boolean).pop() ?? null
                : null;
              const derivedNameFromOutput = resultOutputPath
                ? resultOutputPath.split(/[\\/]/).filter(Boolean).pop() ?? null
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
              const startTimeValue = subtitleMetadata ? subtitleMetadata['start_time_offset_label'] : null;
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
              const stage = typeof event?.metadata?.stage === 'string' ? event?.metadata?.stage : null;
              const updatedAt = job.status.completed_at
                || job.status.started_at
                || (event ? new Date(event.timestamp * 1000).toISOString() : null);
              return (
                <article key={job.jobId} className="subtitle-job-card">
                  <header>
                    <h3>Job {job.jobId}</h3>
                    <span className={`job-status badge-${job.status.status}`}>{job.status.status}</span>
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
                  </footer>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
