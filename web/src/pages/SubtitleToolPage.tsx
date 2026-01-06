import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { JobState } from '../components/JobList';
import { useLanguagePreferences } from '../context/LanguageProvider';
import {
  fetchPipelineDefaults,
  fetchSubtitleSources,
  fetchSubtitleResult,
  lookupSubtitleTvMetadataPreview,
  fetchLlmModels,
  submitSubtitleJob,
  deleteSubtitleSource
} from '../api/client';
import type { SubtitleJobResultPayload, SubtitleSourceEntry, SubtitleTvMetadataPreviewResponse } from '../api/dtos';
import type { JobParameterSnapshot } from '../api/dtos';
import {
  buildLanguageOptions,
  normalizeLanguageLabel,
  sortLanguageLabelsByName
} from '../utils/languages';
import { subtitleFormatFromPath } from '../utils/subtitles';
import SubtitleJobsPanel from './subtitle-tool/SubtitleJobsPanel';
import SubtitleMetadataPanel from './subtitle-tool/SubtitleMetadataPanel';
import SubtitleOptionsPanel from './subtitle-tool/SubtitleOptionsPanel';
import SubtitleSourcePanel from './subtitle-tool/SubtitleSourcePanel';
import SubtitleToolTabs from './subtitle-tool/SubtitleToolTabs';
import {
  DEFAULT_ASS_EMPHASIS,
  DEFAULT_ASS_FONT_SIZE,
  DEFAULT_BATCH_SIZE,
  DEFAULT_LLM_MODEL,
  DEFAULT_START_TIME,
  DEFAULT_SUBTITLE_SOURCE_DIRECTORY,
  DEFAULT_WORKER_COUNT,
  MAX_ASS_EMPHASIS,
  MAX_ASS_FONT_SIZE,
  MIN_ASS_EMPHASIS,
  MIN_ASS_FONT_SIZE,
  SHOW_ORIGINAL_STORAGE_KEY
} from './subtitle-tool/subtitleToolConfig';
import type {
  SubtitleOutputFormat,
  SubtitleSourceMode,
  SubtitleToolTab
} from './subtitle-tool/subtitleToolTypes';
import {
  basenameFromPath,
  coerceRecord,
  formatTimecodeFromSeconds,
  normalizeLanguageInput,
  normalizeSubtitleTimecodeInput
} from './subtitle-tool/subtitleToolUtils';
import styles from './SubtitleToolPage.module.css';

type Props = {
  subtitleJobs: JobState[];
  onJobCreated: (jobId: string) => void;
  onSelectJob: (jobId: string) => void;
  onMoveToLibrary?: (jobId: string) => void;
  prefillParameters?: JobParameterSnapshot | null;
  refreshSignal?: number;
};

export default function SubtitleToolPage({
  subtitleJobs,
  onJobCreated,
  onSelectJob,
  onMoveToLibrary,
  prefillParameters = null,
  refreshSignal = 0
}: Props) {
  const [activeTab, setActiveTab] = useState<SubtitleToolTab>('subtitles');
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
  const sortedLanguageOptions = useMemo(() => sortLanguageLabelsByName(languageOptions), [languageOptions]);
  const [sourceMode, setSourceMode] = useState<SubtitleSourceMode>('existing');
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
  const sourceDirectory = DEFAULT_SUBTITLE_SOURCE_DIRECTORY;
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const metadataSourceName = useMemo(() => {
    if (sourceMode === 'upload') {
      return uploadFile?.name ?? '';
    }
    return selectedSourceEntry?.name ?? (selectedSource ? basenameFromPath(selectedSource) : '');
  }, [selectedSource, selectedSourceEntry, sourceMode, uploadFile]);
  const [metadataLookupSourceName, setMetadataLookupSourceName] = useState<string>('');
  const [metadataPreview, setMetadataPreview] = useState<SubtitleTvMetadataPreviewResponse | null>(null);
  const [mediaMetadataDraft, setMediaMetadataDraft] = useState<Record<string, unknown> | null>(null);
  const [metadataLoading, setMetadataLoading] = useState<boolean>(false);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const metadataLookupIdRef = useRef<number>(0);
  const updateMediaMetadataDraft = useCallback((updater: (draft: Record<string, unknown>) => void) => {
    setMediaMetadataDraft((current) => {
      const next: Record<string, unknown> = current ? { ...current } : {};
      updater(next);
      return next;
    });
  }, []);
  const updateMediaMetadataSection = useCallback(
    (sectionKey: string, updater: (section: Record<string, unknown>) => void) => {
      updateMediaMetadataDraft((draft) => {
        const currentSection = coerceRecord(draft[sectionKey]);
        const nextSection: Record<string, unknown> = currentSection ? { ...currentSection } : {};
        updater(nextSection);
        draft[sectionKey] = nextSection;
      });
    },
    [updateMediaMetadataDraft]
  );
  const [enableTransliteration, setEnableTransliteration] = useState<boolean>(true);
  const [enableHighlight, setEnableHighlight] = useState<boolean>(true);
  const [generateAudioBook, setGenerateAudioBook] = useState<boolean>(true);
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
  const [translationProvider, setTranslationProvider] = useState<string>('llm');
  const [transliterationMode, setTransliterationMode] = useState<string>('default');
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
      setStartTime(formatTimecodeFromSeconds(prefillParameters.start_time_offset_seconds));
    }
    if (typeof prefillParameters.end_time_offset_seconds === 'number') {
      setEndTime(formatTimecodeFromSeconds(prefillParameters.end_time_offset_seconds));
    }
    if (prefillParameters.llm_model && typeof prefillParameters.llm_model === 'string') {
      setSelectedModel(prefillParameters.llm_model.trim());
    }
    if (prefillParameters.translation_provider && typeof prefillParameters.translation_provider === 'string') {
      setTranslationProvider(prefillParameters.translation_provider.trim());
    }
    if (prefillParameters.transliteration_mode && typeof prefillParameters.transliteration_mode === 'string') {
      setTransliterationMode(prefillParameters.transliteration_mode.trim());
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

  const performMetadataLookup = useCallback(
    async (sourceName: string, force: boolean) => {
      const normalized = sourceName.trim();
      if (!normalized) {
        setMetadataPreview(null);
        setMediaMetadataDraft(null);
        setMetadataError(null);
        setMetadataLoading(false);
        return;
      }
      const requestId = metadataLookupIdRef.current + 1;
      metadataLookupIdRef.current = requestId;
      setMetadataLoading(true);
      setMetadataError(null);
      try {
        const payload = await lookupSubtitleTvMetadataPreview({ source_name: normalized, force });
        if (metadataLookupIdRef.current !== requestId) {
          return;
        }
        setMetadataPreview(payload);
        setMediaMetadataDraft(payload.media_metadata ? { ...payload.media_metadata } : null);
      } catch (error) {
        if (metadataLookupIdRef.current !== requestId) {
          return;
        }
        const message = error instanceof Error ? error.message : 'Unable to lookup TV metadata.';
        setMetadataError(message);
        setMetadataPreview(null);
        setMediaMetadataDraft(null);
      } finally {
        if (metadataLookupIdRef.current === requestId) {
          setMetadataLoading(false);
        }
      }
    },
    []
  );

  const handleMetadataClear = useCallback(() => {
    setMetadataPreview(null);
    setMediaMetadataDraft(null);
    setMetadataError(null);
  }, []);

  useEffect(() => {
    const normalized = metadataSourceName.trim();
    setMetadataLookupSourceName(normalized);
    if (!normalized) {
      setMetadataPreview(null);
      setMediaMetadataDraft(null);
      setMetadataError(null);
      setMetadataLoading(false);
      return;
    }
    void performMetadataLookup(normalized, false);
  }, [metadataSourceName, performMetadataLookup]);

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

  const handleSourceModeChange = useCallback((mode: SubtitleSourceMode) => {
    setSourceMode(mode);
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

  const handleUploadFileChange = useCallback((file: File | null) => {
    setUploadFile(file);
  }, []);

  const handleTargetLanguageChange = useCallback((next: string) => {
    const value = normalizeLanguageInput(next);
    setTargetLanguage(value);
    if (value) {
      setPrimaryTargetLanguage(value);
    }
  }, [setPrimaryTargetLanguage]);

  const handleInputLanguageChange = useCallback((next: string) => {
    const value = normalizeLanguageInput(next);
    setInputLanguage(value || 'English');
  }, [setInputLanguage]);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setSubmitError(null);

      const trimmedOriginal = normalizeLanguageInput(inputLanguage);
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
      const trimmedTarget = normalizeLanguageInput(targetLanguage);
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

      const normalisedStartTime = normalizeSubtitleTimecodeInput(startTime, {
        emptyValue: DEFAULT_START_TIME
      });
      if (normalisedStartTime === null) {
        setSubmitError('Enter a valid start time in MM:SS or HH:MM:SS format.');
        return;
      }

      const normalisedEndTime = normalizeSubtitleTimecodeInput(endTime, {
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
      formData.append('generate_audio_book', String(generateAudioBook));
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
      if (translationProvider.trim()) {
        formData.append('translation_provider', translationProvider.trim());
      }
      if (transliterationMode.trim()) {
        formData.append('transliteration_mode', transliterationMode.trim());
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
      if (mediaMetadataDraft) {
        formData.append('media_metadata_json', JSON.stringify(mediaMetadataDraft));
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
        setActiveTab('jobs');
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
      generateAudioBook,
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
      setActiveTab,
      selectedModel,
      outputFormat,
      assFontSize,
      assEmphasis,
      mediaMetadataDraft,
      translationProvider,
      transliterationMode
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
    <div className={styles.container}>
      <SubtitleToolTabs
        activeTab={activeTab}
        sourceCount={sources.length}
        jobCount={sortedSubtitleJobs.length}
        isSubmitting={isSubmitting}
        isAssSelection={isAssSelection}
        onTabChange={setActiveTab}
      />

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
              return ' using auto-detected concurrency. Live status appears in the Jobs tab.';
            }
            const detailText =
              details.length === 1
                ? details[0]
                : `${details.slice(0, -1).join(', ')} and ${details[details.length - 1]}`;
            return ` using ${detailText}. Live status appears in the Jobs tab.`;
          })()}
        </div>
      ) : null}

      <form id="subtitle-submit-form" onSubmit={handleSubmit} className="subtitle-form">
        {activeTab === 'subtitles' ? (
          <SubtitleSourcePanel
            sourceMode={sourceMode}
            sourceDirectory={sourceDirectory}
            sourceCount={sources.length}
            sortedSources={sortedSources}
            selectedSource={selectedSource}
            isLoadingSources={isLoadingSources}
            sourceError={sourceError}
            sourceMessage={sourceMessage}
            deletingSourcePath={deletingSourcePath}
            isAssSelection={isAssSelection}
            onSourceModeChange={handleSourceModeChange}
            onSelectSource={setSelectedSource}
            onRefreshSources={() => void refreshSources()}
            onDeleteSource={handleDeleteSource}
            onUploadFileChange={handleUploadFileChange}
          />
        ) : null}

        {activeTab === 'options' ? (
          <SubtitleOptionsPanel
            inputLanguage={inputLanguage}
            targetLanguage={targetLanguage}
            sortedLanguageOptions={sortedLanguageOptions}
            selectedModel={selectedModel}
            availableModels={availableModels}
            modelsLoading={modelsLoading}
            modelsError={modelsError}
            translationProvider={translationProvider}
            transliterationMode={transliterationMode}
            enableTransliteration={enableTransliteration}
            enableHighlight={enableHighlight}
            generateAudioBook={generateAudioBook}
            showOriginal={showOriginal}
            mirrorToSourceDir={mirrorToSourceDir}
            outputFormat={outputFormat}
            assFontSize={assFontSize}
            assEmphasis={assEmphasis}
            workerCount={workerCount}
            batchSize={batchSize}
            startTime={startTime}
            endTime={endTime}
            sourceDirectory={sourceDirectory}
            onInputLanguageChange={handleInputLanguageChange}
            onTargetLanguageChange={handleTargetLanguageChange}
            onModelChange={setSelectedModel}
            onTranslationProviderChange={setTranslationProvider}
            onTransliterationModeChange={setTransliterationMode}
            onEnableTransliterationChange={setEnableTransliteration}
            onEnableHighlightChange={setEnableHighlight}
            onGenerateAudioBookChange={setGenerateAudioBook}
            onShowOriginalChange={setShowOriginal}
            onMirrorToSourceDirChange={setMirrorToSourceDir}
            onOutputFormatChange={setOutputFormat}
            onAssFontSizeChange={setAssFontSize}
            onAssEmphasisChange={setAssEmphasis}
            onWorkerCountChange={setWorkerCount}
            onBatchSizeChange={setBatchSize}
            onStartTimeChange={setStartTime}
            onEndTimeChange={setEndTime}
          />
        ) : null}

        {activeTab === 'metadata' ? (
          <SubtitleMetadataPanel
            metadataSourceName={metadataSourceName}
            metadataLookupSourceName={metadataLookupSourceName}
            metadataPreview={metadataPreview}
            metadataLoading={metadataLoading}
            metadataError={metadataError}
            mediaMetadataDraft={mediaMetadataDraft}
            onLookupSourceNameChange={setMetadataLookupSourceName}
            onLookupMetadata={performMetadataLookup}
            onClearMetadata={handleMetadataClear}
            onUpdateMediaMetadataDraft={updateMediaMetadataDraft}
            onUpdateMediaMetadataSection={updateMediaMetadataSection}
          />
        ) : null}
      </form>

      {activeTab === 'jobs' ? (
        <SubtitleJobsPanel
          jobs={sortedSubtitleJobs}
          jobResults={jobResults}
          onSelectJob={onSelectJob}
          onMoveToLibrary={onMoveToLibrary}
        />
      ) : null}
    </div>
  );
}
