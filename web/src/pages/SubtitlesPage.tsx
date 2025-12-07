import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ChangeEvent } from 'react';
import type { JobState } from '../components/JobList';
import { useLanguagePreferences } from '../context/LanguageProvider';
import {
  fetchPipelineDefaults,
  fetchSubtitleSources,
  fetchSubtitleResult,
  fetchLlmModels,
  resolveSubtitleDownloadUrl,
  submitSubtitleJob,
  deleteSubtitleSource
} from '../api/client';
import type { SubtitleJobResultPayload, SubtitleSourceEntry } from '../api/dtos';
import { formatTimestamp } from '../utils/mediaFormatters';
import type { JobParameterSnapshot } from '../api/dtos';
import { buildLanguageOptions, normalizeLanguageLabel } from '../utils/languages';
import { inferSubtitleLanguageFromPath, subtitleFormatFromPath, subtitleLanguageDetail } from '../utils/subtitles';
import styles from './SubtitlesPage.module.css';

type SourceMode = 'existing' | 'upload';
type SubtitleOutputFormat = 'srt' | 'ass';

type Props = {
  subtitleJobs: JobState[];
  onJobCreated: (jobId: string) => void;
  onSelectJob: (jobId: string) => void;
  prefillParameters?: JobParameterSnapshot | null;
  refreshSignal?: number;
};

const DEFAULT_SOURCE_DIRECTORY = '/Volumes/Data/Download/Subtitles';
const DEFAULT_WORKER_COUNT = 10;
const DEFAULT_BATCH_SIZE = 20;
const DEFAULT_START_TIME = '00:00';
const SHOW_ORIGINAL_STORAGE_KEY = 'subtitles:show_original';
const DEFAULT_LLM_MODEL = 'kimi-k2:1t-cloud';
const DEFAULT_ASS_FONT_SIZE = 56;
const MIN_ASS_FONT_SIZE = 12;
const MAX_ASS_FONT_SIZE = 120;
const DEFAULT_ASS_EMPHASIS = 1.3;
const MIN_ASS_EMPHASIS = 1.0;
const MAX_ASS_EMPHASIS = 2.5;

function formatRetryCounts(counts?: Record<string, number> | null): string | null {
  if (!counts) {
    return null;
  }
  const parts = Object.entries(counts)
    .filter(([, count]) => typeof count === 'number' && count > 0)
    .sort((a, b) => {
      const delta = (b[1] || 0) - (a[1] || 0);
      return delta !== 0 ? delta : a[0].localeCompare(b[0]);
    })
    .map(([reason, count]) => `${reason} (${count})`);
  return parts.length ? parts.join(', ') : null;
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

type ParsedTimecode = {
  seconds: number;
  normalized: string;
};

function parseAbsoluteTimecode(value: string): ParsedTimecode | null {
  const trimmed = value.trim();
  const match = trimmed.match(/^(\d+):(\d{1,2})(?::(\d{1,2}))?$/);
  if (!match) {
    return null;
  }
  const [, primary, secondary, tertiary] = match;
  const first = Number(primary);
  const second = Number(secondary);
  const third = typeof tertiary === 'string' ? Number(tertiary) : null;

  if ([first, second, third ?? 0].some((component) => !Number.isInteger(component) || component < 0)) {
    return null;
  }
  if (third !== null) {
    if (second >= 60 || third >= 60) {
      return null;
    }
    const hours = first;
    const minutes = second;
    const seconds = third;
    const normalized = [hours, minutes, seconds]
      .map((component, index) => (index === 0 ? component.toString().padStart(2, '0') : component.toString().padStart(2, '0')))
      .join(':');
    return {
      seconds: hours * 3600 + minutes * 60 + seconds,
      normalized
    };
  }

  if (second >= 60) {
    return null;
  }
  const minutes = first;
  const seconds = second;
  return {
    seconds: minutes * 60 + seconds,
    normalized: `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  };
}

function formatRelativeDuration(totalSeconds: number): string {
  const clamped = Math.max(0, Math.floor(totalSeconds));
  if (clamped >= 3600) {
    const hours = Math.floor(clamped / 3600);
    const remainder = clamped % 3600;
    const minutes = Math.floor(remainder / 60);
    const seconds = remainder % 60;
    return [hours, minutes, seconds].map((component) => component.toString().padStart(2, '0')).join(':');
  }
  const minutes = Math.floor(clamped / 60);
  const seconds = clamped % 60;
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function parseRelativeTimecode(value: string): ParsedTimecode | null {
  const trimmed = value.trim();
  if (/^\d+$/.test(trimmed)) {
    const minutes = Number(trimmed);
    if (!Number.isInteger(minutes) || minutes < 0) {
      return null;
    }
    const totalSeconds = minutes * 60;
    return {
      seconds: totalSeconds,
      normalized: formatRelativeDuration(totalSeconds)
    };
  }
  const absolute = parseAbsoluteTimecode(trimmed);
  if (!absolute) {
    return null;
  }
  return {
    seconds: absolute.seconds,
    normalized: formatRelativeDuration(absolute.seconds)
  };
}

function normaliseTimecodeInput(
  value: string,
  options: { allowRelative?: boolean; emptyValue?: string } = {}
): string | null {
  const { allowRelative = false, emptyValue = '' } = options;
  const trimmed = value.trim();
  if (!trimmed) {
    return emptyValue;
  }
  if (allowRelative && trimmed.startsWith('+')) {
    const relative = parseRelativeTimecode(trimmed.slice(1));
    if (!relative) {
      return null;
    }
    return `+${relative.normalized}`;
  }
  const absolute = parseAbsoluteTimecode(trimmed);
  if (!absolute) {
    return null;
  }
  return absolute.normalized;
}

export default function SubtitlesPage({
  subtitleJobs,
  onJobCreated,
  onSelectJob,
  prefillParameters = null,
  refreshSignal = 0
}: Props) {
  const {
    inputLanguage,
    setInputLanguage,
    primaryTargetLanguage,
    setPrimaryTargetLanguage
  } = useLanguagePreferences();
  const [targetLanguage, setTargetLanguage] = useState<string>(
    normalizeLanguageLabel(primaryTargetLanguage ?? 'French')
  );
  const [fetchedLanguages, setFetchedLanguages] = useState<string[]>([]);
  const languageOptions = useMemo(
    () =>
      buildLanguageOptions({
        fetchedLanguages,
        preferredLanguages: [inputLanguage, primaryTargetLanguage, targetLanguage]
      }),
    [fetchedLanguages, inputLanguage, primaryTargetLanguage, targetLanguage]
  );
  const [sourceMode, setSourceMode] = useState<SourceMode>('existing');
  const [sources, setSources] = useState<SubtitleSourceEntry[]>([]);
  const [selectedSource, setSelectedSource] = useState<string>('');
  const selectedSourceRef = useRef<string>('');
  useEffect(() => {
    selectedSourceRef.current = selectedSource;
  }, [selectedSource]);
  const selectedSourceEntry = useMemo(
    () => sources.find((entry) => entry.path === selectedSource) ?? null,
    [selectedSource, sources]
  );
  const selectedSourceFormat = useMemo(() => {
    if (!selectedSourceEntry) {
      return '';
    }
    return (selectedSourceEntry.format || subtitleFormatFromPath(selectedSourceEntry.path) || '').toLowerCase();
  }, [selectedSourceEntry]);
  const isAssSelection = useMemo(
    () => sourceMode === 'existing' && selectedSourceFormat === 'ass',
    [sourceMode, selectedSourceFormat]
  );
  const sortedSources = useMemo(() => {
    return [...sources]
      .map((entry, index) => ({ entry, index }))
      .sort((left, right) => {
        const leftFormat = (left.entry.format || subtitleFormatFromPath(left.entry.path) || '').toLowerCase();
        const rightFormat = (right.entry.format || subtitleFormatFromPath(right.entry.path) || '').toLowerCase();
        const leftWeight = leftFormat === 'ass' ? 1 : 0;
        const rightWeight = rightFormat === 'ass' ? 1 : 0;
        if (leftWeight !== rightWeight) {
          return leftWeight - rightWeight;
        }
        return left.index - right.index;
      })
      .map(({ entry }) => entry);
  }, [sources]);
  const sourceDirectory = DEFAULT_SOURCE_DIRECTORY;
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [enableTransliteration, setEnableTransliteration] = useState<boolean>(true);
  const [enableHighlight, setEnableHighlight] = useState<boolean>(true);
  const [outputFormat, setOutputFormat] = useState<SubtitleOutputFormat>('ass');
  const [assFontSize, setAssFontSize] = useState<number | ''>(DEFAULT_ASS_FONT_SIZE);
  const [assEmphasis, setAssEmphasis] = useState<number | ''>(DEFAULT_ASS_EMPHASIS);
  const [showOriginal, setShowOriginal] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    try {
      const persisted = window.localStorage.getItem(SHOW_ORIGINAL_STORAGE_KEY);
      if (persisted === null) {
        return true;
      }
      return persisted === 'true';
    } catch {
      return true;
    }
  });
  const [mirrorToSourceDir, setMirrorToSourceDir] = useState<boolean>(true);
  const [workerCount, setWorkerCount] = useState<number | ''>(DEFAULT_WORKER_COUNT);
  const [batchSize, setBatchSize] = useState<number | ''>(DEFAULT_BATCH_SIZE);
  const [startTime, setStartTime] = useState<string>(DEFAULT_START_TIME);
  const [endTime, setEndTime] = useState<string>('');
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>(DEFAULT_LLM_MODEL);
  const [modelsLoading, setModelsLoading] = useState<boolean>(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [isLoadingSources, setLoadingSources] = useState<boolean>(false);
  const [deletingSourcePath, setDeletingSourcePath] = useState<string | null>(null);
  const [sourceMessage, setSourceMessage] = useState<string | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);
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
  const [lastSubmittedEndTime, setLastSubmittedEndTime] = useState<string | null>(null);
  const [lastSubmittedModel, setLastSubmittedModel] = useState<string | null>(null);
  const [lastSubmittedFormat, setLastSubmittedFormat] = useState<SubtitleOutputFormat | null>(
    null
  );
  const [lastSubmittedAssFontSize, setLastSubmittedAssFontSize] = useState<number | null>(null);
  const [lastSubmittedAssEmphasis, setLastSubmittedAssEmphasis] = useState<number | null>(null);
  const secondsToTimecode = useCallback((value: number | null | undefined): string => {
    if (value === null || value === undefined || !Number.isFinite(value) || value < 0) {
      return '';
    }
    const totalSeconds = Math.floor(value);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours > 0) {
      return [hours, minutes, seconds].map((component) => component.toString().padStart(2, '0')).join(':');
    }
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }, []);

  useEffect(() => {
    setTargetLanguage(primaryTargetLanguage ?? targetLanguage);
  }, [primaryTargetLanguage]);

  useEffect(() => {
    if (!prefillParameters) {
      return;
    }
    const targetLanguages = Array.isArray(prefillParameters.target_languages)
      ? prefillParameters.target_languages
          .map((entry) => (typeof entry === 'string' ? entry.trim() : ''))
          .filter((entry) => entry.length > 0)
      : [];
    if (targetLanguages.length > 0) {
      setTargetLanguage(targetLanguages[0]);
      setPrimaryTargetLanguage(targetLanguages[0]);
    }
    if (prefillParameters.input_language && typeof prefillParameters.input_language === 'string') {
      setInputLanguage(prefillParameters.input_language.trim());
    }
    if (typeof prefillParameters.enable_transliteration === 'boolean') {
      setEnableTransliteration(prefillParameters.enable_transliteration);
    }
    if (typeof prefillParameters.show_original === 'boolean') {
      setShowOriginal(prefillParameters.show_original);
    }
    if (typeof prefillParameters.worker_count === 'number' && Number.isFinite(prefillParameters.worker_count)) {
      setWorkerCount(prefillParameters.worker_count);
    }
    if (typeof prefillParameters.batch_size === 'number' && Number.isFinite(prefillParameters.batch_size)) {
      setBatchSize(prefillParameters.batch_size);
    }
    if (typeof prefillParameters.start_time_offset_seconds === 'number') {
      setStartTime(secondsToTimecode(prefillParameters.start_time_offset_seconds));
    }
    if (typeof prefillParameters.end_time_offset_seconds === 'number') {
      setEndTime(secondsToTimecode(prefillParameters.end_time_offset_seconds));
    }
    if (prefillParameters.llm_model && typeof prefillParameters.llm_model === 'string') {
      setSelectedModel(prefillParameters.llm_model.trim());
    }
    const sourcePath =
      typeof prefillParameters.subtitle_path === 'string'
        ? prefillParameters.subtitle_path.trim()
        : typeof prefillParameters.input_file === 'string' && prefillParameters.input_file
          ? prefillParameters.input_file.trim()
          : '';
    if (sourcePath) {
      setSelectedSource(sourcePath);
    }
  }, [
    prefillParameters,
    secondsToTimecode,
    setInputLanguage,
    setPrimaryTargetLanguage
  ]);

  useEffect(() => {
    let cancelled = false;
    fetchPipelineDefaults()
      .then((defaults) => {
        if (cancelled) {
          return;
        }
        const config = defaults?.config ?? {};
        const targetLanguages = Array.isArray(config['target_languages'])
          ? (config['target_languages'] as unknown[])
          : [];
        const normalised = targetLanguages
          .map((language) => (typeof language === 'string' ? normalizeLanguageLabel(language) : ''))
          .filter((language) => language.length > 0);
        if (normalised.length > 0) {
          setFetchedLanguages(normalised);
        }
        const defaultInput = normalizeLanguageLabel(
          typeof config['input_language'] === 'string' ? config['input_language'] : ''
        );
        if (defaultInput && !inputLanguage) {
          setInputLanguage(defaultInput);
        }
      })
      .catch((error) => {
        console.warn('Unable to load pipeline defaults for language list', error);
      });
    return () => {
      cancelled = true;
    };
  }, [inputLanguage, setInputLanguage]);

  useEffect(() => {
    let cancelled = false;
    setModelsLoading(true);
    setModelsError(null);
    fetchLlmModels()
      .then((models) => {
        if (!cancelled) {
          setAvailableModels(models ?? []);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn('Unable to load available subtitle models', error);
          const message = error instanceof Error ? error.message : 'Request failed';
          setModelsError(message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setModelsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(SHOW_ORIGINAL_STORAGE_KEY, showOriginal ? 'true' : 'false');
    } catch {
      // Ignore persistence failures; preference resets next session.
    }
  }, [showOriginal]);

  useEffect(() => {
    if (!targetLanguage && languageOptions.length > 0) {
      const preferred = languageOptions[0];
      setTargetLanguage(preferred);
      if (preferred) {
        setPrimaryTargetLanguage(preferred);
      }
    }
  }, [languageOptions, setPrimaryTargetLanguage, targetLanguage]);

  const refreshSources = useCallback(
    async (resetSelection: boolean = false) => {
      const directory = sourceDirectory;
      setLoadingSources(true);
      setSourceError(null);
      setSourceMessage(null);
      try {
        const entries = await fetchSubtitleSources(directory);
        setSources(entries);
        const currentSelection = resetSelection ? '' : selectedSourceRef.current;
        if (!currentSelection) {
          const pickLatest = (items: SubtitleSourceEntry[]): string => {
            const parseTimestamp = (value: string | null | undefined): number => {
              if (!value) {
                return 0;
              }
              const parsed = Date.parse(value);
              return Number.isNaN(parsed) ? 0 : parsed;
            };
            const preferred = items.filter((item) => {
              const format = (item.format || subtitleFormatFromPath(item.path) || '').toLowerCase();
              return format !== 'ass';
            });
            const pool = preferred.length > 0 ? preferred : items;
            if (pool.length === 0) {
              return '';
            }
            return pool.reduce<string>((latest, candidate) => {
              if (!latest) {
                return candidate.path;
              }
              const latestEntry = pool.find((item) => item.path === latest) ?? candidate;
              const latestTs = parseTimestamp(latestEntry.modified_at);
              const candidateTs = parseTimestamp(candidate.modified_at);
              if (candidateTs > latestTs) {
                return candidate.path;
              }
              if (candidateTs === latestTs && candidate.path.localeCompare(latest) < 0) {
                return candidate.path;
              }
              return latest;
            }, '');
          };
          const nextSelection = pickLatest(entries);
          if (nextSelection) {
            setSelectedSource(nextSelection);
          }
        } else if (resetSelection && entries.length === 0) {
          setSelectedSource('');
        }
        if (entries.length === 0) {
          setSourceMessage(`No subtitles found in ${directory}`);
        }
      } catch (error) {
        console.warn('Unable to list subtitle sources', error);
        const message = error instanceof Error ? error.message : 'Unable to list subtitle sources.';
        setSourceError(message);
      } finally {
        setLoadingSources(false);
      }
    },
    [sourceDirectory]
  );

  useEffect(() => {
    refreshSources();
  }, [refreshSignal, refreshSources]);

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

  const handleDeleteSource = useCallback(
    async (entry: SubtitleSourceEntry) => {
      const confirmed =
        typeof window === 'undefined' ||
        window.confirm(
          `Delete ${entry.name}? This removes the subtitle and any mirrored HTML transcript copies.`,
        );
      if (!confirmed) {
        return;
      }
      setSourceError(null);
      setSourceMessage(null);
      setDeletingSourcePath(entry.path);
      try {
        await deleteSubtitleSource(entry.path);
        const resetSelection = selectedSource === entry.path;
        await refreshSources(resetSelection);
        setSourceMessage(`Deleted ${entry.name}`);
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to delete subtitle.';
        setSourceError(message);
      } finally {
        setDeletingSourcePath(null);
      }
    },
    [refreshSources, selectedSource]
  );

  const handleUploadChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files && event.target.files.length > 0 ? event.target.files[0] : null;
    setUploadFile(file);
  }, []);

  const handleTargetLanguageChange = useCallback((event: ChangeEvent<HTMLSelectElement>) => {
    const value = normaliseLanguage(event.target.value);
    setTargetLanguage(value);
    if (value) {
      setPrimaryTargetLanguage(value);
    }
  }, [setPrimaryTargetLanguage]);

  const handleInputLanguageChange = useCallback((event: ChangeEvent<HTMLSelectElement>) => {
    const value = normaliseLanguage(event.target.value);
    setInputLanguage(value || 'English');
  }, [setInputLanguage]);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setSubmitError(null);

      const trimmedOriginal = normaliseLanguage(inputLanguage);
      if (!trimmedOriginal) {
        setSubmitError('Choose an original language.');
        return;
      }
      if (isAssSelection) {
        setSubmitError(
          'Generated ASS files cannot be used as sources. Choose the original SRT/VTT or upload a new subtitle.'
        );
        return;
      }
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

      const normalisedStartTime = normaliseTimecodeInput(startTime, {
        emptyValue: DEFAULT_START_TIME
      });
      if (normalisedStartTime === null) {
        setSubmitError('Enter a valid start time in MM:SS or HH:MM:SS format.');
        return;
      }

      const normalisedEndTime = normaliseTimecodeInput(endTime, {
        allowRelative: true,
        emptyValue: ''
      });
      if (normalisedEndTime === null) {
        setSubmitError('Enter a valid end time in MM:SS, HH:MM:SS, or +offset format.');
        return;
      }

      let resolvedAssFontSize: number | null = null;
      let resolvedAssEmphasis: number | null = null;
      if (outputFormat === 'ass') {
        if (typeof assFontSize !== 'number' || Number.isNaN(assFontSize)) {
          setSubmitError('Enter a numeric ASS base font size.');
          return;
        }
        const clamped = Math.max(MIN_ASS_FONT_SIZE, Math.min(MAX_ASS_FONT_SIZE, Math.round(assFontSize)));
        resolvedAssFontSize = clamped;

        if (typeof assEmphasis !== 'number' || Number.isNaN(assEmphasis)) {
          setSubmitError('Enter a numeric ASS emphasis scale.');
          return;
        }
        const normalized = Math.max(
          MIN_ASS_EMPHASIS,
          Math.min(MAX_ASS_EMPHASIS, Math.round(assEmphasis * 100) / 100)
        );
        resolvedAssEmphasis = normalized;
      }

      const formData = new FormData();
      formData.append('input_language', trimmedOriginal);
      formData.append('original_language', trimmedOriginal);
      formData.append('target_language', trimmedTarget);
      formData.append('enable_transliteration', String(enableTransliteration));
      formData.append('highlight', String(enableHighlight));
      formData.append('show_original', String(showOriginal));
      formData.append('output_format', outputFormat);
      formData.append('mirror_batches_to_source_dir', String(mirrorToSourceDir));
      formData.append('start_time', normalisedStartTime);
      if (resolvedAssFontSize !== null) {
        formData.append('ass_font_size', String(resolvedAssFontSize));
      }
      if (resolvedAssEmphasis !== null) {
        formData.append('ass_emphasis_scale', String(resolvedAssEmphasis));
      }
      if (selectedModel.trim()) {
        formData.append('llm_model', selectedModel.trim());
      }
      if (normalisedEndTime) {
        formData.append('end_time', normalisedEndTime);
      }
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
        setLastSubmittedEndTime(normalisedEndTime || null);
        setLastSubmittedModel(selectedModel.trim() ? selectedModel.trim() : null);
        setLastSubmittedFormat(outputFormat);
        setLastSubmittedAssFontSize(resolvedAssFontSize);
        setLastSubmittedAssEmphasis(resolvedAssEmphasis);
        if (normalisedStartTime !== startTime) {
          setStartTime(normalisedStartTime);
        }
        if (normalisedEndTime !== endTime) {
          setEndTime(normalisedEndTime);
        }
        if (resolvedAssFontSize !== null && assFontSize !== resolvedAssFontSize) {
          setAssFontSize(resolvedAssFontSize);
        }
        if (resolvedAssEmphasis !== null && assEmphasis !== resolvedAssEmphasis) {
          setAssEmphasis(resolvedAssEmphasis);
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
      showOriginal,
      inputLanguage,
      onJobCreated,
      selectedSource,
      sourceMode,
      targetLanguage,
      uploadFile,
      workerCount,
      batchSize,
      mirrorToSourceDir,
      startTime,
      endTime,
      selectedModel,
      outputFormat,
      assFontSize,
      assEmphasis
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
                <div className={styles.cardHeader}>
                  <div>
                    <div className="field-label">Subtitle directory</div>
                    <p className={styles.cardHint}>
                      Using the default NAS Subtitles folder; scans for .srt/.vtt files plus generated .ass outputs and mirrors deletions alongside HTML transcripts.
                    </p>
                    <p className={styles.sourcePath}>{sourceDirectory}</p>
                  </div>
                  <div className={styles.controlRow}>
                    <button
                      type="button"
                      className={styles.secondaryButton}
                      onClick={() => void refreshSources()}
                      disabled={isLoadingSources || Boolean(deletingSourcePath)}
                    >
                      {isLoadingSources ? 'Refreshing…' : 'Refresh list'}
                    </button>
                  </div>
                </div>
                {sourceError ? <div className="alert" role="alert">{sourceError}</div> : null}
                {sourceMessage && !sourceError ? <p className={styles.status}>{sourceMessage}</p> : null}
                <div className={styles.sourceList}>
                  {isLoadingSources && sources.length === 0 ? (
                    <p className={styles.status}>Scanning directory…</p>
                  ) : null}
                  {!isLoadingSources && sources.length === 0 ? (
                    <p className={styles.status}>No subtitles found in {sourceDirectory}.</p>
                  ) : null}
                  {isAssSelection ? (
                    <p className={styles.status}>
                      Generated ASS files are read-only—pick the original SRT/VTT or upload a new subtitle to process.
                    </p>
                  ) : null}
                  {sortedSources.map((entry) => {
                    const isActive = selectedSource === entry.path;
                    const isDeleting = deletingSourcePath === entry.path;
                    const language = entry.language || inferSubtitleLanguageFromPath(entry.path);
                    const languageLabel = subtitleLanguageDetail(language);
                    const languageCode = (language || 'UNK').toUpperCase();
                    const format = (entry.format || subtitleFormatFromPath(entry.path) || 'srt').toUpperCase();
                    return (
                      <div
                        key={entry.path}
                        className={`${styles.sourceCard} ${isActive ? styles.sourceCardActive : ''}`}
                      >
                        <label className={styles.sourceChoice}>
                          <input
                            type="radio"
                            name="subtitle_source"
                            value={entry.path}
                            checked={isActive}
                            disabled={Boolean(deletingSourcePath)}
                            onChange={() => setSelectedSource(entry.path)}
                          />
                          <div className={styles.sourceBody}>
                            <div className={styles.sourceHeaderRow}>
                              <div className={styles.sourceName}>{entry.name}</div>
                              <div className={styles.sourceBadges} aria-label="Subtitle details">
                                <span className={`${styles.pill} ${styles.pillFormat}`}>{format}</span>
                                <span
                                  className={`${styles.pill} ${styles.pillMuted}`}
                                  title={languageLabel}
                                >
                                  {languageCode}
                                </span>
                              </div>
                            </div>
                          </div>
                        </label>
                        <div className={styles.sourceActions}>
                          <button
                            type="button"
                            className={styles.dangerButton}
                            onClick={() => void handleDeleteSource(entry)}
                            disabled={Boolean(deletingSourcePath) || isLoadingSources}
                            title={`Delete ${entry.name}`}
                            aria-label={`Delete ${entry.name}`}
                          >
                            {isDeleting ? '…' : '🗑'}
                          </button>
                        </div>
                      </div>
                    );
                  })}
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
              <label className="field-label" htmlFor="subtitle-input-language">Original language</label>
              <select
                id="subtitle-input-language"
                value={inputLanguage}
                onChange={handleInputLanguageChange}
              >
                {languageOptions.map((language) => (
                  <option key={language} value={language}>
                    {language}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field-label" htmlFor="subtitle-target-language">Translation language</label>
              <select
                id="subtitle-target-language"
                value={targetLanguage}
                onChange={handleTargetLanguageChange}
              >
                {languageOptions.map((language) => (
                  <option key={language} value={language}>
                    {language}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field-label" htmlFor="subtitle-llm-model">LLM model (optional)</label>
              <input
                id="subtitle-llm-model"
                type="text"
                list="subtitle-llm-models"
                placeholder="Use server default"
                value={selectedModel}
                onChange={(event) => setSelectedModel(event.target.value)}
                disabled={modelsLoading && availableModels.length === 0}
              />
              <datalist id="subtitle-llm-models">
                {availableModels.map((model) => (
                  <option key={model} value={model} />
                ))}
              </datalist>
              <small className="field-note">
                {modelsLoading
                  ? 'Loading models from Ollama…'
                  : modelsError
                  ? `Unable to load models (${modelsError}).`
                  : 'Leave blank to use the default server model.'}
              </small>
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
                  checked={showOriginal}
                  onChange={(event) => setShowOriginal(event.target.checked)}
                />
                Show original language part
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
                Subtitle format
                <select
                  value={outputFormat}
                  onChange={(event) => setOutputFormat(event.target.value === 'ass' ? 'ass' : 'srt')}
                >
                  <option value="srt">SRT (SubRip)</option>
                  <option value="ass">ASS (Advanced SubStation Alpha)</option>
                </select>
              </label>
              <label>
                ASS base font size
                <input
                  type="number"
                  min={MIN_ASS_FONT_SIZE}
                  max={MAX_ASS_FONT_SIZE}
                  value={typeof assFontSize === 'number' ? assFontSize : ''}
                  onChange={(event) => {
                    const raw = event.target.value;
                    if (!raw.trim()) {
                      setAssFontSize('');
                      return;
                    }
                    const parsed = Number(raw);
                    if (Number.isNaN(parsed)) {
                      return;
                    }
                    const clamped = Math.max(
                      MIN_ASS_FONT_SIZE,
                      Math.min(MAX_ASS_FONT_SIZE, Math.round(parsed))
                    );
                    setAssFontSize(clamped);
                  }}
                  disabled={outputFormat !== 'ass'}
                />
                <small>Used only for ASS exports ({MIN_ASS_FONT_SIZE}-{MAX_ASS_FONT_SIZE}).</small>
              </label>
              <label>
                ASS emphasis scale
                <input
                  type="number"
                  step={0.1}
                  min={MIN_ASS_EMPHASIS}
                  max={MAX_ASS_EMPHASIS}
                  value={typeof assEmphasis === 'number' ? assEmphasis : ''}
                  onChange={(event) => {
                    const raw = event.target.value;
                    if (!raw.trim()) {
                      setAssEmphasis('');
                      return;
                    }
                    const parsed = Number(raw);
                    if (Number.isNaN(parsed)) {
                      return;
                    }
                    const clamped = Math.max(
                      MIN_ASS_EMPHASIS,
                      Math.min(MAX_ASS_EMPHASIS, Math.round(parsed * 100) / 100)
                    );
                    setAssEmphasis(clamped);
                  }}
                  disabled={outputFormat !== 'ass'}
                />
                <small>Translation scale (default {DEFAULT_ASS_EMPHASIS.toFixed(2)}×).</small>
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
              <label>
                End time (leave blank for full file)
                <input
                  type="text"
                  value={endTime}
                  onChange={(event) => setEndTime(event.target.value)}
                  placeholder="+05:00"
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
                if (lastSubmittedEndTime) {
                  const display =
                    lastSubmittedEndTime.startsWith('+')
                      ? `ending after ${lastSubmittedEndTime.slice(1)}`
                      : `ending at ${lastSubmittedEndTime}`;
                  details.push(display);
                }
                if (lastSubmittedModel) {
                  details.push(`LLM ${lastSubmittedModel}`);
                }
                if (lastSubmittedFormat) {
                  const label = lastSubmittedFormat === 'ass' ? 'ASS subtitles' : 'SRT subtitles';
                  details.push(label);
                  if (lastSubmittedFormat === 'ass' && lastSubmittedAssFontSize) {
                    details.push(`font size ${lastSubmittedAssFontSize}`);
                  }
                  if (lastSubmittedFormat === 'ass' && lastSubmittedAssEmphasis) {
                    details.push(`scale ${lastSubmittedAssEmphasis}×`);
                  }
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
            <button type="submit" className="primary" disabled={isSubmitting || isAssSelection}>
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
                ? formatRetryCounts(retrySummary.translation)
                : null;
              const transliterationRetries = retrySummary
                ? formatRetryCounts(retrySummary.transliteration)
                : null;
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
