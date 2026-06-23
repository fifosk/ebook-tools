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
import SubtitleJobsPanel from './subtitle-tool/SubtitleJobsPanel';
import SubtitleMetadataPanel from './subtitle-tool/SubtitleMetadataPanel';
import SubtitleOptionsPanel from './subtitle-tool/SubtitleOptionsPanel';
import SubtitleSourcePanel from './subtitle-tool/SubtitleSourcePanel';
import SubtitleTuningPanel from './subtitle-tool/SubtitleTuningPanel';
import SubtitleToolTabs from './subtitle-tool/SubtitleToolTabs';
import {
  DEFAULT_ASS_EMPHASIS,
  DEFAULT_ASS_FONT_SIZE,
  DEFAULT_BATCH_SIZE,
  DEFAULT_LLM_MODEL,
  DEFAULT_START_TIME,
  DEFAULT_SUBTITLE_SOURCE_DIRECTORY,
  DEFAULT_TRANSLATION_BATCH_SIZE,
  DEFAULT_WORKER_COUNT,
  SHOW_ORIGINAL_STORAGE_KEY
} from './subtitle-tool/subtitleToolConfig';
import type {
  SubtitleOutputFormat,
  SubtitleSourceMode,
  SubtitleToolTab
} from './subtitle-tool/subtitleToolTypes';
import {
  coerceRecord,
  formatSubmittedSubtitleSummary,
  isAssSubtitleSelection,
  normalizeLanguageInput,
  pickLatestSubtitleSource,
  resolveSubtitleMetadataSourceName,
  resolveSubtitlePrefillValues,
  resolveSubtitleSubmitValues,
  selectMissingCompletedSubtitleJobs,
  sortSubtitleJobsNewestFirst,
  sortSubtitleSourcesForSelection
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
  const isAssSelection = useMemo(
    () => isAssSubtitleSelection(sourceMode, selectedSourceEntry),
    [sourceMode, selectedSourceEntry]
  );
  const sortedSources = useMemo(() => sortSubtitleSourcesForSelection(sources), [sources]);
  const sourceDirectory = DEFAULT_SUBTITLE_SOURCE_DIRECTORY;
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const metadataSourceName = useMemo(
    () =>
      resolveSubtitleMetadataSourceName({
        sourceMode,
        uploadFileName: uploadFile?.name,
        selectedSourceName: selectedSourceEntry?.name,
        selectedSourcePath: selectedSource
      }),
    [selectedSource, selectedSourceEntry, sourceMode, uploadFile]
  );
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
  const [translationBatchSize, setTranslationBatchSize] = useState<number | ''>(
    DEFAULT_TRANSLATION_BATCH_SIZE
  );
  const [startTime, setStartTime] = useState<string>(DEFAULT_START_TIME);
  const [endTime, setEndTime] = useState<string>('');
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>(DEFAULT_LLM_MODEL);
  const [transliterationModel, setTransliterationModel] = useState<string>('');
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
  const [lastSubmittedTranslationBatchSize, setLastSubmittedTranslationBatchSize] = useState<
    number | null
  >(typeof DEFAULT_TRANSLATION_BATCH_SIZE === 'number' ? DEFAULT_TRANSLATION_BATCH_SIZE : null);
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
    const prefill = resolveSubtitlePrefillValues(prefillParameters);
    if (prefill.targetLanguage) {
      setTargetLanguage(prefill.targetLanguage);
      setPrimaryTargetLanguage(prefill.targetLanguage);
    }
    if (prefill.inputLanguage) {
      setInputLanguage(prefill.inputLanguage);
    }
    if (prefill.enableTransliteration !== null) {
      setEnableTransliteration(prefill.enableTransliteration);
    }
    if (prefill.showOriginal !== null) {
      setShowOriginal(prefill.showOriginal);
    }
    if (prefill.workerCount !== null) {
      setWorkerCount(prefill.workerCount);
    }
    if (prefill.batchSize !== null) {
      setBatchSize(prefill.batchSize);
    }
    if (prefill.translationBatchSize !== null) {
      setTranslationBatchSize(prefill.translationBatchSize);
    }
    if (prefill.startTime !== null) {
      setStartTime(prefill.startTime);
    }
    if (prefill.endTime !== null) {
      setEndTime(prefill.endTime);
    }
    if (prefill.selectedModel) {
      setSelectedModel(prefill.selectedModel);
    }
    if (prefill.translationProvider) {
      setTranslationProvider(prefill.translationProvider);
    }
    if (prefill.transliterationMode) {
      setTransliterationMode(prefill.transliterationMode);
    }
    if (prefill.transliterationModel) {
      setTransliterationModel(prefill.transliterationModel);
    }
    if (prefill.sourcePath) {
      setSelectedSource(prefill.sourcePath);
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
          const nextSelection = pickLatestSubtitleSource(entries);
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
    const missing = selectMissingCompletedSubtitleJobs(subtitleJobs, jobResults);
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

      const submitResolution = resolveSubtitleSubmitValues({
        inputLanguage,
        targetLanguage,
        isAssSelection,
        sourceMode,
        selectedSource,
        hasUploadFile: Boolean(uploadFile),
        startTime,
        endTime,
        outputFormat,
        assFontSize,
        assEmphasis,
        selectedModel,
        translationProvider,
        transliterationMode,
        transliterationModel,
        workerCount,
        batchSize,
        translationBatchSize
      });
      if (!submitResolution.ok) {
        setSubmitError(submitResolution.error);
        return;
      }
      const {
        originalLanguage,
        targetLanguage: resolvedTargetLanguage,
        normalizedStartTime,
        normalizedEndTime,
        resolvedAssFontSize,
        resolvedAssEmphasis
      } = submitResolution.values;

      const formData = new FormData();
      formData.append('input_language', originalLanguage);
      formData.append('original_language', originalLanguage);
      formData.append('target_language', resolvedTargetLanguage);
      formData.append('enable_transliteration', String(enableTransliteration));
      formData.append('highlight', String(enableHighlight));
      formData.append('show_original', String(showOriginal));
      formData.append('generate_audio_book', String(generateAudioBook));
      formData.append('output_format', outputFormat);
      formData.append('mirror_batches_to_source_dir', String(mirrorToSourceDir));
      formData.append('start_time', normalizedStartTime);
      if (resolvedAssFontSize !== null) {
        formData.append('ass_font_size', String(resolvedAssFontSize));
      }
      if (resolvedAssEmphasis !== null) {
        formData.append('ass_emphasis_scale', String(resolvedAssEmphasis));
      }
      if (submitResolution.values.selectedModel) {
        formData.append('llm_model', submitResolution.values.selectedModel);
      }
      if (submitResolution.values.translationProvider) {
        formData.append('translation_provider', submitResolution.values.translationProvider);
      }
      if (submitResolution.values.transliterationMode) {
        formData.append('transliteration_mode', submitResolution.values.transliterationMode);
      }
      if (submitResolution.values.transliterationModel) {
        formData.append('transliteration_model', submitResolution.values.transliterationModel);
      }
      if (normalizedEndTime) {
        formData.append('end_time', normalizedEndTime);
      }
      if (submitResolution.values.sourcePath) {
        formData.append('source_path', submitResolution.values.sourcePath);
      } else if (uploadFile) {
        formData.append('file', uploadFile, uploadFile.name);
      }
      if (submitResolution.values.workerCount !== null) {
        formData.append('worker_count', String(submitResolution.values.workerCount));
      }
      if (submitResolution.values.batchSize !== null) {
        formData.append('batch_size', String(submitResolution.values.batchSize));
      }
      if (submitResolution.values.translationBatchSize !== null) {
        formData.append('translation_batch_size', String(submitResolution.values.translationBatchSize));
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
        setLastSubmittedTranslationBatchSize(
          typeof translationBatchSize === 'number' ? translationBatchSize : null
        );
        setLastSubmittedStartTime(normalizedStartTime);
        setLastSubmittedEndTime(normalizedEndTime || null);
        setLastSubmittedModel(submitResolution.values.selectedModel);
        setLastSubmittedFormat(outputFormat);
        setLastSubmittedAssFontSize(resolvedAssFontSize);
        setLastSubmittedAssEmphasis(resolvedAssEmphasis);
        if (normalizedStartTime !== startTime) {
          setStartTime(normalizedStartTime);
        }
        if (normalizedEndTime !== endTime) {
          setEndTime(normalizedEndTime);
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
      translationBatchSize,
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
      transliterationMode,
      transliterationModel
    ]
  );

  const sortedSubtitleJobs = useMemo(() => sortSubtitleJobsNewestFirst(subtitleJobs), [subtitleJobs]);

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
          {formatSubmittedSubtitleSummary({
            jobId: lastSubmittedJobId,
            workerCount: lastSubmittedWorkerCount,
            batchSize: lastSubmittedBatchSize,
            translationBatchSize: lastSubmittedTranslationBatchSize,
            startTime: lastSubmittedStartTime,
            defaultStartTime: DEFAULT_START_TIME,
            endTime: lastSubmittedEndTime,
            model: lastSubmittedModel,
            format: lastSubmittedFormat,
            assFontSize: lastSubmittedAssFontSize,
            assEmphasis: lastSubmittedAssEmphasis
          })}
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
            transliterationModel={transliterationModel}
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
            startTime={startTime}
            endTime={endTime}
            sourceDirectory={sourceDirectory}
            onInputLanguageChange={handleInputLanguageChange}
            onTargetLanguageChange={handleTargetLanguageChange}
            onModelChange={setSelectedModel}
            onTranslationProviderChange={setTranslationProvider}
            onTransliterationModeChange={setTransliterationMode}
            onTransliterationModelChange={setTransliterationModel}
            onEnableTransliterationChange={setEnableTransliteration}
            onEnableHighlightChange={setEnableHighlight}
            onGenerateAudioBookChange={setGenerateAudioBook}
            onShowOriginalChange={setShowOriginal}
            onMirrorToSourceDirChange={setMirrorToSourceDir}
            onOutputFormatChange={setOutputFormat}
            onAssFontSizeChange={setAssFontSize}
            onAssEmphasisChange={setAssEmphasis}
            onStartTimeChange={setStartTime}
            onEndTimeChange={setEndTime}
          />
        ) : null}

        {activeTab === 'tuning' ? (
          <SubtitleTuningPanel
            workerCount={workerCount}
            batchSize={batchSize}
            translationBatchSize={translationBatchSize}
            onWorkerCountChange={setWorkerCount}
            onBatchSizeChange={setBatchSize}
            onTranslationBatchSizeChange={setTranslationBatchSize}
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
