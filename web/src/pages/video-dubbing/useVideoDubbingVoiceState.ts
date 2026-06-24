import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchVoiceInventory, synthesizeVoicePreview } from '../../api/client';
import type { VoiceInventoryResponse } from '../../api/dtos';
import { resolveLanguageName } from '../../constants/languageCodes';
import { sampleSentenceFor } from '../../utils/sampleSentences';
import { preferLanguageLabel, resolveLanguageCode } from '../../utils/languages';
import { buildVoiceOptions } from './videoDubbingUtils';

type VideoDubbingVoiceStateOptions = {
  subtitleLanguageLabel?: string | null;
  targetLanguage: string;
  targetLanguageCode: string;
};

export function useVideoDubbingVoiceState({
  subtitleLanguageLabel,
  targetLanguage,
  targetLanguageCode
}: VideoDubbingVoiceStateOptions) {
  const [voice, setVoice] = useState('gTTS');
  const [voiceInventory, setVoiceInventory] = useState<VoiceInventoryResponse | null>(null);
  const [voiceInventoryError, setVoiceInventoryError] = useState<string | null>(null);
  const [isLoadingVoices, setIsLoadingVoices] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const previewAudioRef = useRef<{ audio: HTMLAudioElement; url: string } | null>(null);

  const cleanupPreviewAudio = useCallback(() => {
    const current = previewAudioRef.current;
    if (!current) {
      return;
    }
    previewAudioRef.current = null;
    try {
      current.audio.pause();
      current.audio.src = '';
      current.audio.load();
    } catch {
      // Ignore browser audio cleanup failures.
    }
    try {
      URL.revokeObjectURL(current.url);
    } catch {
      // Ignore URL cleanup failures.
    }
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

  useEffect(() => {
    return () => cleanupPreviewAudio();
  }, [cleanupPreviewAudio]);

  const previewVoice = useCallback(async () => {
    const languageCode = targetLanguageCode || resolveLanguageCode(subtitleLanguageLabel ?? '') || '';
    if (!languageCode) {
      setPreviewError('Choose a translation language before previewing.');
      return;
    }
    const languageLabel = preferLanguageLabel([
      targetLanguage,
      subtitleLanguageLabel,
      resolveLanguageName(languageCode),
      languageCode
    ]);
    setPreviewError(null);
    setIsPreviewing(true);
    cleanupPreviewAudio();
    try {
      const blob = await synthesizeVoicePreview({
        text: sampleSentenceFor(languageCode, languageLabel || languageCode),
        language: languageCode,
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
  }, [cleanupPreviewAudio, subtitleLanguageLabel, targetLanguage, targetLanguageCode, voice]);

  const availableVoiceOptions = useMemo(
    () => buildVoiceOptions(voiceInventory, targetLanguageCode),
    [targetLanguageCode, voiceInventory]
  );

  return {
    voice,
    setVoice,
    availableVoiceOptions,
    isLoadingVoices,
    voiceInventoryError,
    isPreviewing,
    previewError,
    previewVoice
  };
}
