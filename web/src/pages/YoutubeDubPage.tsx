import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  fetchYoutubeLibrary,
  fetchVoiceInventory,
  generateYoutubeDub,
  synthesizeVoicePreview,
  fetchSubtitleModels
} from '../api/client';
import type {
  YoutubeNasLibraryResponse,
  YoutubeNasVideo,
  YoutubeNasSubtitle,
  VoiceInventoryResponse,
  JobParameterSnapshot
} from '../api/dtos';
import type { MacOSVoice, GTTSLanguage } from '../api/dtos';
import type { JobState } from '../components/JobList';
import { VOICE_OPTIONS } from '../constants/menuOptions';
import { resolveLanguageName } from '../constants/languageCodes';
import styles from './YoutubeDubPage.module.css';

const DEFAULT_VIDEO_DIR = '/Volumes/Data/Video/Youtube';
const DEFAULT_LLM_MODEL = 'kimi-k2:1t-cloud';

type Props = {
  jobs: JobState[];
  onJobCreated: (jobId: string) => void;
  onSelectJob: (jobId: string) => void;
  onOpenJobMedia?: (jobId: string) => void;
  prefillParameters?: JobParameterSnapshot | null;
};

function formatMacOSVoiceIdentifier(voice: MacOSVoice): string {
  const quality = voice.quality ? voice.quality : 'Default';
  const genderSuffix = voice.gender ? ` - ${voice.gender}` : '';
  return `${voice.name} - ${voice.lang} - (${quality})${genderSuffix}`;
}

function formatMacOSVoiceLabel(voice: MacOSVoice): string {
  const descriptors: string[] = [voice.lang];
  if (voice.gender) {
    descriptors.push(voice.gender);
  }
  if (voice.quality) {
    descriptors.push(voice.quality);
  }
  const meta = descriptors.length > 0 ? ` (${descriptors.join(', ')})` : '';
  return `${voice.name}${meta}`;
}

function sampleSentenceFor(languageCode: string, fallbackLabel: string): string {
  const resolvedName = resolveLanguageName(languageCode) ?? fallbackLabel ?? '';
  const display = resolvedName || 'this language';
  return `Sample narration for ${display}.`;
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return '0 B';
  }
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  const precision = size >= 10 || unitIndex === 0 ? 0 : 1;
  return `${size.toFixed(precision)} ${units[unitIndex]}`;
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function subtitleLabel(sub: YoutubeNasSubtitle): string {
  const language = sub.language ? `(${sub.language})` : '';
  return `${sub.format.toUpperCase()} ${language}`.trim();
}

function resolveDefaultSubtitle(video: YoutubeNasVideo | null): YoutubeNasSubtitle | null {
  if (!video) {
    return null;
  }
  const candidates = video.subtitles.filter((sub) => ['ass', 'srt', 'vtt'].includes(sub.format.toLowerCase()));
  if (!candidates.length) {
    return null;
  }
  const english = candidates.find((sub) => (sub.language ?? '').toLowerCase().startsWith('en'));
  return english ?? candidates[0];
}

function resolveOutputPath(job: JobState): string | null {
  const generated = job.status.generated_files;
  if (generated && typeof generated === 'object') {
    const record = generated as Record<string, unknown>;
    const files = record['files'];
    if (Array.isArray(files)) {
      for (const entry of files) {
        if (!entry || typeof entry !== 'object') {
          continue;
        }
        const file = entry as Record<string, unknown>;
        if (typeof file.path === 'string' && file.path.trim()) {
          return file.path.trim();
        }
      }
    }
  }
  const result = job.status.result;
  if (result && typeof result === 'object') {
    const section = (result as Record<string, unknown>)['youtube_dub'];
    if (section && typeof section === 'object' && typeof (section as Record<string, unknown>).output_path === 'string') {
      const pathValue = (section as Record<string, unknown>).output_path as string;
      return pathValue.trim() || null;
    }
  }
  return null;
}

function formatJobLabel(job: JobState): string {
  const parameters = job.status.parameters;
  const languages = parameters?.target_languages ?? [];
  const target = Array.isArray(languages) && languages.length > 0 ? languages[0] : null;
  if (typeof target === 'string' && target.trim()) {
    return target.trim();
  }
  const videoPath = parameters?.video_path ?? parameters?.input_file;
  if (videoPath && typeof videoPath === 'string' && videoPath.trim()) {
    const parts = videoPath.split('/');
    return parts[parts.length - 1] || videoPath;
  }
  return job.jobId;
}

export default function YoutubeDubPage({
  jobs,
  onJobCreated,
  onSelectJob,
  onOpenJobMedia,
  prefillParameters = null
}: Props) {
  const [baseDir, setBaseDir] = useState(DEFAULT_VIDEO_DIR);
  const [library, setLibrary] = useState<YoutubeNasLibraryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedVideoPath, setSelectedVideoPath] = useState<string | null>(null);
  const [selectedSubtitlePath, setSelectedSubtitlePath] = useState<string | null>(null);

  const [voice, setVoice] = useState('gTTS');
  const [targetLanguage, setTargetLanguage] = useState('');
  const [startOffset, setStartOffset] = useState('');
  const [endOffset, setEndOffset] = useState('');
  const [originalMixPercent, setOriginalMixPercent] = useState(5);
  const [flushSentences, setFlushSentences] = useState(10);
  const [llmModel, setLlmModel] = useState(DEFAULT_LLM_MODEL);
  const [splitBatches, setSplitBatches] = useState(true);
  const [includeTransliteration, setIncludeTransliteration] = useState(true);
  const [voiceInventory, setVoiceInventory] = useState<VoiceInventoryResponse | null>(null);
  const [voiceInventoryError, setVoiceInventoryError] = useState<string | null>(null);
  const [isLoadingVoices, setIsLoadingVoices] = useState(false);
  const [llmModels, setLlmModels] = useState<string[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const previewAudioRef = useRef<{ audio: HTMLAudioElement; url: string } | null>(null);

  const cleanupPreviewAudio = useCallback(() => {
    if (previewAudioRef.current) {
      previewAudioRef.current.audio.pause();
      URL.revokeObjectURL(previewAudioRef.current.url);
      previewAudioRef.current = null;
    }
  }, []);

  const parseOffset = useCallback((value: string): number => {
    const trimmed = value.trim();
    if (!trimmed) {
      return 0;
    }
    const segments = trimmed.split(':');
    const parseNumber = (token: string) => {
      if (!/^\d+(\.\d+)?$/.test(token)) {
        throw new Error('Offsets must be numbers or timecodes like HH:MM:SS');
      }
      return parseFloat(token);
    };
    if (segments.length === 1) {
      const seconds = parseNumber(segments[0]);
      if (seconds < 0) throw new Error('Offsets must be non-negative');
      return seconds;
    }
    if (segments.length > 3) {
      throw new Error('Use MM:SS or HH:MM:SS for timecodes');
    }
    const [hStr, mStr, sStr] =
      segments.length === 3 ? segments : ['0', segments[0], segments[1]];
    const hours = parseNumber(hStr);
    const minutes = parseNumber(mStr);
    const seconds = parseNumber(sStr);
    if (minutes >= 60 || seconds >= 60) {
      throw new Error('Minutes and seconds must be between 0 and 59');
    }
    return hours * 3600 + minutes * 60 + seconds;
  }, []);

  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const formatOffset = useCallback((value: number | null | undefined): string => {
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

  const videos = library?.videos ?? [];
  const selectedVideo = useMemo(
    () => videos.find((video) => video.path === selectedVideoPath) ?? null,
    [videos, selectedVideoPath]
  );
  const languageOptions: GTTSLanguage[] = useMemo(() => {
    if (!voiceInventory) {
      return [];
    }
    return voiceInventory.gtts.slice().sort((a, b) => a.name.localeCompare(b.name));
  }, [voiceInventory]);
  const playableSubtitles = useMemo(() => {
    if (!selectedVideo) {
      return [];
    }
    return selectedVideo.subtitles.filter((sub) => ['ass', 'srt', 'vtt'].includes(sub.format.toLowerCase()));
  }, [selectedVideo]);
  const selectedSubtitle = useMemo(
    () => playableSubtitles.find((sub) => sub.path === selectedSubtitlePath) ?? null,
    [playableSubtitles, selectedSubtitlePath]
  );

  const handleRefresh = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    setStatusMessage(null);
    try {
      const response = await fetchYoutubeLibrary(baseDir.trim() || undefined);
      setLibrary(response);
      setBaseDir(response.base_dir || baseDir);
      if (response.videos.length > 0) {
        const existingSelection = response.videos.find((video) => video.path === selectedVideoPath);
        const nextVideo = existingSelection ?? response.videos[0];
        setSelectedVideoPath(nextVideo.path);
        const defaultSubtitle = resolveDefaultSubtitle(nextVideo);
        setSelectedSubtitlePath(defaultSubtitle?.path ?? null);
        if (defaultSubtitle?.language && !targetLanguage) {
          setTargetLanguage(defaultSubtitle.language);
        }
      } else {
        setSelectedVideoPath(null);
        setSelectedSubtitlePath(null);
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to load YouTube NAS videos.' : 'Unable to load YouTube NAS videos.';
      setLoadError(message);
    } finally {
      setIsLoading(false);
    }
  }, [baseDir, selectedVideoPath]);

  useEffect(() => {
    void handleRefresh();
  }, [handleRefresh]);

  useEffect(() => {
    return () => cleanupPreviewAudio();
  }, [cleanupPreviewAudio]);

  useEffect(() => {
    if (!prefillParameters) {
      return;
    }
    if (prefillParameters.input_file && typeof prefillParameters.input_file === 'string') {
      setSelectedVideoPath(prefillParameters.input_file.trim());
    } else if (prefillParameters.video_path && typeof prefillParameters.video_path === 'string') {
      setSelectedVideoPath(prefillParameters.video_path.trim());
    }
    if (prefillParameters.subtitle_path && typeof prefillParameters.subtitle_path === 'string') {
      setSelectedSubtitlePath(prefillParameters.subtitle_path.trim());
    }
    const targets = Array.isArray(prefillParameters.target_languages)
      ? prefillParameters.target_languages
          .map((entry) => (typeof entry === 'string' ? entry.trim() : ''))
          .filter((entry) => entry.length > 0)
      : [];
    if (targets.length > 0) {
      setTargetLanguage(targets[0]);
    }
    if (prefillParameters.selected_voice && typeof prefillParameters.selected_voice === 'string') {
      setVoice(prefillParameters.selected_voice.trim());
    }
    if (
      typeof prefillParameters.start_time_offset_seconds === 'number' &&
      Number.isFinite(prefillParameters.start_time_offset_seconds)
    ) {
      setStartOffset(formatOffset(prefillParameters.start_time_offset_seconds));
    }
    if (
      typeof prefillParameters.end_time_offset_seconds === 'number' &&
      Number.isFinite(prefillParameters.end_time_offset_seconds)
    ) {
      setEndOffset(formatOffset(prefillParameters.end_time_offset_seconds));
    }
    if (
      typeof prefillParameters.original_mix_percent === 'number' &&
      Number.isFinite(prefillParameters.original_mix_percent)
    ) {
      setOriginalMixPercent(prefillParameters.original_mix_percent);
    } else {
      setOriginalMixPercent(5);
    }
    if (
      typeof prefillParameters.flush_sentences === 'number' &&
      Number.isFinite(prefillParameters.flush_sentences)
    ) {
      setFlushSentences(prefillParameters.flush_sentences);
    }
    if (typeof prefillParameters.split_batches === 'boolean') {
      setSplitBatches(prefillParameters.split_batches);
    } else {
      setSplitBatches(true);
    }
    if (prefillParameters.llm_model && typeof prefillParameters.llm_model === 'string') {
      setLlmModel(prefillParameters.llm_model.trim());
    }
    if (typeof prefillParameters.include_transliteration === 'boolean') {
      setIncludeTransliteration(prefillParameters.include_transliteration);
    } else {
      setIncludeTransliteration(true);
    }
  }, [formatOffset, prefillParameters]);

  useEffect(() => {
    if (playableSubtitles.length === 0) {
      setSelectedSubtitlePath(null);
      return;
    }
    const current = playableSubtitles.find((sub) => sub.path === selectedSubtitlePath);
    if (current) {
      return;
    }
    const defaultSubtitle = resolveDefaultSubtitle(selectedVideo) ?? playableSubtitles[0];
    setSelectedSubtitlePath(defaultSubtitle?.path ?? null);
    if (defaultSubtitle?.language && !targetLanguage) {
      setTargetLanguage(defaultSubtitle.language);
    }
  }, [playableSubtitles, selectedSubtitlePath, selectedVideo, targetLanguage]);

  useEffect(() => {
    let cancelled = false;
    const loadModels = async () => {
      setIsLoadingModels(true);
      setModelError(null);
      try {
        const models = await fetchSubtitleModels();
        if (cancelled) return;
        setLlmModels(models);
        if (!llmModel && models.length > 0) {
          setLlmModel(models.includes(DEFAULT_LLM_MODEL) ? DEFAULT_LLM_MODEL : models[0]);
        }
      } catch (error) {
        if (cancelled) return;
        const message =
          error instanceof Error ? error.message || 'Unable to load translation models.' : 'Unable to load translation models.';
        setModelError(message);
      } finally {
        if (!cancelled) {
          setIsLoadingModels(false);
        }
      }
    };
    void loadModels();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadVoices = async () => {
      setIsLoadingVoices(true);
      setVoiceInventoryError(null);
      try {
        const inventory = await fetchVoiceInventory();
        if (cancelled) {
          return;
        }
        setVoiceInventory(inventory);
      } catch (error) {
        if (cancelled) {
          return;
        }
        const message =
          error instanceof Error ? error.message || 'Unable to load voices.' : 'Unable to load voices.';
        setVoiceInventoryError(message);
      } finally {
        if (!cancelled) {
          setIsLoadingVoices(false);
        }
      }
    };
    void loadVoices();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSelectVideo = useCallback((video: YoutubeNasVideo) => {
    setSelectedVideoPath(video.path);
    const defaultSubtitle = resolveDefaultSubtitle(video);
    setSelectedSubtitlePath(defaultSubtitle?.path ?? null);
    if (defaultSubtitle?.language && !targetLanguage) {
      setTargetLanguage(defaultSubtitle.language);
    }
  }, [targetLanguage]);

  const handleSelectSubtitle = useCallback((path: string) => {
    setSelectedSubtitlePath(path);
    const match = playableSubtitles.find((sub) => sub.path === path);
    if (match?.language && !targetLanguage) {
      setTargetLanguage(match.language);
    }
  }, [playableSubtitles, targetLanguage]);

  const handleGenerate = useCallback(async () => {
    if (!selectedVideo || !selectedSubtitle) {
      setGenerateError('Choose a video and an ASS subtitle before generating audio.');
      return;
    }
    let parsedStart = 0;
    let parsedEnd: number | undefined;
    try {
      parsedStart = parseOffset(startOffset);
      parsedEnd = endOffset.trim() ? parseOffset(endOffset) : undefined;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Offsets must be in seconds or HH:MM:SS format.';
      setGenerateError(message);
      return;
    }
    if (parsedEnd !== undefined && parsedEnd <= parsedStart) {
      setGenerateError('End offset must be greater than start offset.');
      return;
    }
    setIsGenerating(true);
    setGenerateError(null);
    setStatusMessage(null);
    try {
      const response = await generateYoutubeDub({
        video_path: selectedVideo.path,
        subtitle_path: selectedSubtitle.path,
        target_language: targetLanguage || selectedSubtitle.language || undefined,
        voice: voice.trim() || 'gTTS',
        start_time_offset: startOffset.trim() || undefined,
        end_time_offset: endOffset.trim() || undefined,
        original_mix_percent: originalMixPercent,
        flush_sentences: flushSentences,
        llm_model: llmModel || undefined,
        split_batches: splitBatches,
        include_transliteration: includeTransliteration
      });
      setStatusMessage(`Dub job submitted as ${response.job_id}. Track progress below.`);
      onJobCreated(response.job_id);
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to generate dubbed video.' : 'Unable to generate dubbed video.';
      setGenerateError(message);
    } finally {
      setIsGenerating(false);
    }
  }, [
    selectedVideo,
    selectedSubtitle,
    targetLanguage,
    voice,
    startOffset,
    endOffset,
    originalMixPercent,
    flushSentences,
    llmModel,
    splitBatches,
    includeTransliteration,
    onJobCreated,
    parseOffset
  ]);

  const handlePreviewVoice = useCallback(async () => {
    const lang = (targetLanguage || selectedSubtitle?.language || '').trim();
    if (!lang) {
      setPreviewError('Choose a target language code before previewing.');
      return;
    }
    setPreviewError(null);
    setIsPreviewing(true);
    cleanupPreviewAudio();
    try {
      const blob = await synthesizeVoicePreview({
        text: sampleSentenceFor(lang, resolveLanguageName(lang) || lang),
        language: lang,
        voice: voice.trim() || undefined
      });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      previewAudioRef.current = { audio, url };
      audio.onended = () => {
        setIsPreviewing(false);
        cleanupPreviewAudio();
      };
      audio.onerror = () => {
        setIsPreviewing(false);
        setPreviewError('Audio playback failed.');
        cleanupPreviewAudio();
      };
      await audio.play();
    } catch (error) {
      setIsPreviewing(false);
      setPreviewError(error instanceof Error ? error.message : 'Unable to preview voice.');
      cleanupPreviewAudio();
    }
  }, [cleanupPreviewAudio, targetLanguage, selectedSubtitle, voice]);

  const subtitleNotice = useMemo(() => {
    if (!selectedVideo) {
      return 'Select a video to see subtitles.';
    }
    if (playableSubtitles.length === 0) {
      return 'No subtitles were found next to this video.';
    }
    return null;
  }, [playableSubtitles, selectedVideo]);

  const availableVoiceOptions = useMemo(() => {
    const base = VOICE_OPTIONS.map((option) => ({
      value: option.value,
      label: option.label
    }));
    if (!voiceInventory) {
      return base;
    }
    const targetCode = (targetLanguage || selectedSubtitle?.language || '').toLowerCase();
    const macVoices = voiceInventory.macos
      .filter((voice) => {
        if (!targetCode) {
          return true;
        }
        return voice.lang.toLowerCase().startsWith(targetCode);
      })
      .map((voice) => ({
        value: formatMacOSVoiceIdentifier(voice),
        label: formatMacOSVoiceLabel(voice)
      }));
    const merged = new Map<string, { value: string; label: string }>();
    [...base, ...macVoices].forEach((entry) => merged.set(entry.value, entry));
    return Array.from(merged.values()).sort((a, b) => a.label.localeCompare(b.label));
  }, [voiceInventory, targetLanguage, selectedSubtitle]);

  const canGenerate = Boolean(selectedVideo && selectedSubtitle && !isGenerating);

  return (
    <div className={styles.container}>
      <div>
        <p className={styles.kicker}>YouTube → NAS</p>
        <h1 className={styles.title}>Dub downloaded videos from ASS subtitles</h1>
        <p className={styles.subtitle}>
          Pick a downloaded YouTube video from the NAS share, choose an ASS translation next to it, and render a new audio track that follows the subtitle timing.
        </p>
      </div>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Discovered videos</h2>
            <p className={styles.cardHint}>
              Base path: <code>{baseDir}</code>
            </p>
          </div>
          <div className={styles.controlRow}>
            <input
              className={styles.input}
              value={baseDir}
              onChange={(event) => setBaseDir(event.target.value)}
              placeholder="NAS directory"
              aria-label="YouTube NAS directory"
            />
            <button className={styles.secondaryButton} type="button" onClick={() => void handleRefresh()} disabled={isLoading}>
              {isLoading ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
        </div>
        {loadError ? <p className={styles.error}>{loadError}</p> : null}
        {isLoading && videos.length === 0 ? <p className={styles.status}>Loading YouTube videos…</p> : null}
        {!isLoading && videos.length === 0 ? (
          <p className={styles.status}>No downloaded videos found in this directory.</p>
        ) : null}
        <div className={styles.videoList}>
          {videos.map((video) => {
            const isActive = video.path === selectedVideoPath;
            return (
              <label key={video.path} className={`${styles.videoOption} ${isActive ? styles.videoOptionActive : ''}`}>
                <input
                  type="radio"
                  name="video"
                  value={video.path}
                  checked={isActive}
                  onChange={() => handleSelectVideo(video)}
                />
                <div className={styles.videoContent}>
                  <div className={styles.videoTitle}>{video.filename}</div>
                  <div className={styles.videoMeta}>
                    <span>{formatBytes(video.size_bytes)}</span>
                    <span aria-hidden="true">·</span>
                    <span>{formatDate(video.modified_at)}</span>
                  </div>
                  <div className={styles.subtitleRow} aria-label="Available subtitles">
                    {video.subtitles.length === 0 ? (
                      <span className={styles.pillMuted}>No subtitles</span>
                    ) : (
                      video.subtitles.map((sub) => (
                        <span
                          key={sub.path}
                          className={`${styles.pill} ${
                            sub.format.toLowerCase() === 'ass' ? styles.pillAss : styles.pillMuted
                          }`}
                        >
                          {subtitleLabel(sub)}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              </label>
            );
          })}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.formGrid}>
          <div>
            <h3 className={styles.sectionTitle}>Choose subtitle</h3>
            {subtitleNotice ? <p className={styles.status}>{subtitleNotice}</p> : null}
            <div className={styles.subtitleList}>
              {playableSubtitles.map((sub) => (
                <label key={sub.path} className={styles.subtitleOption}>
                  <input
                    type="radio"
                    name="subtitle"
                    value={sub.path}
                    checked={selectedSubtitlePath === sub.path}
                    onChange={() => handleSelectSubtitle(sub.path)}
                  />
                  <div>
                    <div className={styles.subtitleName}>{sub.filename}</div>
                    <div className={styles.subtitleMeta}>
                      <span>{sub.language || 'Unknown language'}</span>
                      <span aria-hidden="true"> · </span>
                      <span>{sub.format.toUpperCase()}</span>
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>
          <div>
            <h3 className={styles.sectionTitle}>Audio options</h3>
            <div className={styles.formFields}>
              <label className={styles.field}>
                <span>Target language code</span>
                <input
                  className={styles.input}
                  list="dub-language-options"
                  value={targetLanguage}
                  onChange={(event) => setTargetLanguage(event.target.value)}
                  placeholder={selectedSubtitle?.language || 'en'}
                />
                <datalist id="dub-language-options">
                  {languageOptions.map((language) => (
                    <option key={language.code} value={language.code}>
                      {language.name}
                    </option>
                  ))}
                </datalist>
                <p className={styles.fieldHint}>Uses language codes supported by the audio API (gTTS/macOS).</p>
              </label>
              <label className={styles.field}>
                <span>Voice / audio mode</span>
                <select
                  className={styles.input}
                  value={voice}
                  onChange={(event) => setVoice(event.target.value)}
                  disabled={availableVoiceOptions.length === 0 && isLoadingVoices}
                >
                  {availableVoiceOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                  {availableVoiceOptions.length === 0 ? <option value={voice}>{voice || 'gTTS'}</option> : null}
                </select>
                <p className={styles.fieldHint}>Switch between macOS voices, gTTS, or other configured modes.</p>
              </label>
              <p className={styles.fieldHint}>
                Audio pacing follows the subtitle timing automatically for each sentence.
              </p>
              <label className={styles.field}>
                <span>Translation model</span>
                <select
                  className={styles.input}
                  value={llmModel}
                  onChange={(event) => setLlmModel(event.target.value)}
                  disabled={isLoadingModels}
                >
                  {[...(llmModels.length ? llmModels : [DEFAULT_LLM_MODEL])].map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
                <p className={styles.fieldHint}>Model used when translating subtitles before TTS (defaults to kimi).</p>
                {isLoadingModels ? <p className={styles.status}>Loading models…</p> : null}
                {modelError ? <p className={styles.error}>{modelError}</p> : null}
              </label>
              <label className={styles.field}>
                <span>Flush interval (sentences)</span>
                <div className={styles.rangeRow}>
                  <input
                    className={styles.input}
                    type="number"
                    min={1}
                    step={1}
                    value={flushSentences}
                    onChange={(event) => setFlushSentences(Math.max(1, Number(event.target.value)))}
                  />
                  <span className={styles.rangeValue}>{flushSentences} sentences</span>
                </div>
                <p className={styles.fieldHint}>Write out/append the video every N sentences (default 10).</p>
              </label>
              <label className={styles.fieldCheckbox}>
                <input
                  type="checkbox"
                  checked={splitBatches}
                  onChange={(event) => setSplitBatches(event.target.checked)}
                />
                <span>Create separate video per batch (adds start-end sentence to filename)</span>
              </label>
              <label className={styles.fieldCheckbox}>
                <input
                  type="checkbox"
                  checked={includeTransliteration}
                  onChange={(event) => setIncludeTransliteration(event.target.checked)}
                />
                <span>Include transliteration subtitle track (default on for non-Latin targets)</span>
              </label>
              <label className={styles.field}>
                <span>Original audio mix</span>
                <div className={styles.rangeRow}>
                  <input
                    className={styles.rangeInput}
                    type="range"
                    min={0}
                    max={100}
                    step={5}
                    value={originalMixPercent}
                    onChange={(event) => setOriginalMixPercent(Number(event.target.value))}
                  />
                  <span className={styles.rangeValue}>{originalMixPercent}% original</span>
                </div>
                <p className={styles.fieldHint}>
                  Amount of the original track to keep under the dub (default 5%).
                </p>
              </label>
              <div className={styles.field}>
                <span>Clip window (seconds)</span>
                <div className={styles.clipInputs}>
                  <input
                    className={styles.input}
                    type="text"
                    value={startOffset}
                    onChange={(event) => setStartOffset(event.target.value)}
                    placeholder="Start (e.g., 45 or 00:45)"
                  />
                  <input
                    className={styles.input}
                    type="text"
                    value={endOffset}
                    onChange={(event) => setEndOffset(event.target.value)}
                    placeholder="End (e.g., 01:30)"
                  />
                </div>
                <p className={styles.fieldHint}>Leave blank to dub the entire video. Use offsets to render a short slice.</p>
              </div>
              <div className={styles.actions}>
                <button
                  className={styles.primaryButton}
                  type="button"
                  onClick={() => void handleGenerate()}
                  disabled={!canGenerate}
                >
                  {isGenerating ? 'Rendering…' : 'Generate dubbed video'}
                </button>
                <button
                  className={styles.secondaryButton}
                  type="button"
                  onClick={() => void handlePreviewVoice()}
                  disabled={isPreviewing}
                >
                  {isPreviewing ? 'Playing…' : 'Play sample'}
                </button>
                {isLoadingVoices ? <p className={styles.status}>Loading voices…</p> : null}
                {voiceInventoryError ? <p className={styles.error}>{voiceInventoryError}</p> : null}
                {previewError ? <p className={styles.error}>{previewError}</p> : null}
                {statusMessage ? <p className={styles.success}>{statusMessage}</p> : null}
                {generateError ? <p className={styles.error}>{generateError}</p> : null}
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Dubbing jobs</h2>
            <p className={styles.cardHint}>Monitor active and recent YouTube dubbing tasks.</p>
          </div>
        </div>
        {jobs.length === 0 ? (
          <p className={styles.status}>No dubbing jobs submitted yet.</p>
        ) : (
          <div className={styles.jobList}>
            {[...jobs]
              .sort((a, b) => new Date(b.status.created_at).getTime() - new Date(a.status.created_at).getTime())
              .map((job) => {
                const statusValue = job.status?.status ?? 'pending';
                const outputPath = resolveOutputPath(job);
                return (
                  <div key={job.jobId} className={styles.jobRow}>
                    <div>
                      <div className={styles.jobTitle}>
                        <span className={styles.jobBadge}>{statusValue}</span>
                        <span>{formatJobLabel(job)}</span>
                      </div>
                      <div className={styles.jobMeta}>
                        <span>Job {job.jobId}</span>
                        {outputPath ? (
                          <>
                            <span aria-hidden="true">•</span>
                            <span className={styles.jobPath}>{outputPath}</span>
                          </>
                        ) : null}
                      </div>
                    </div>
                    <div className={styles.jobActions}>
                      <button
                        type="button"
                        className={styles.primaryButton}
                        onClick={() => (onOpenJobMedia ? onOpenJobMedia(job.jobId) : onSelectJob(job.jobId))}
                      >
                        Play media
                      </button>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={() => onSelectJob(job.jobId)}
                      >
                        View progress
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </section>
    </div>
  );
}
