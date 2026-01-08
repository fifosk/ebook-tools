import { useCallback, useEffect, useRef, useState } from 'react';
import type { VoiceInventoryResponse } from '../../api/dtos';
import { fetchVoiceInventory, synthesizeVoicePreview } from '../../api/client';
import { sampleSentenceFor } from '../../utils/sampleSentences';
import { MenuOption, VOICE_OPTIONS } from '../../constants/menuOptions';
import { formatMacOSVoiceIdentifier, formatMacOSVoiceLabel } from './bookNarrationFormUtils';

type VoicePreviewStatus = Record<string, 'idle' | 'loading' | 'playing'>;

type VoicePreviewError = Record<string, string>;

type UseBookNarrationVoicesOptions = {
  selectedVoice: string;
  voiceOverrides: Record<string, string>;
};

export function useBookNarrationVoices({
  selectedVoice,
  voiceOverrides,
}: UseBookNarrationVoicesOptions) {
  const [voiceInventory, setVoiceInventory] = useState<VoiceInventoryResponse | null>(null);
  const [voiceInventoryError, setVoiceInventoryError] = useState<string | null>(null);
  const [isLoadingVoiceInventory, setIsLoadingVoiceInventory] = useState<boolean>(false);
  const [voicePreviewStatus, setVoicePreviewStatus] = useState<VoicePreviewStatus>({});
  const [voicePreviewError, setVoicePreviewError] = useState<VoicePreviewError>({});
  const previewAudioRef = useRef<{ audio: HTMLAudioElement; url: string; code: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoadingVoiceInventory(true);
    fetchVoiceInventory()
      .then((inventory) => {
        if (cancelled) {
          return;
        }
        setVoiceInventory(inventory);
        setVoiceInventoryError(null);
      })
      .catch((inventoryError) => {
        if (cancelled) {
          return;
        }
        const message =
          inventoryError instanceof Error
            ? inventoryError.message
            : 'Unable to load voice inventory.';
        setVoiceInventory(null);
        setVoiceInventoryError(message);
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingVoiceInventory(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

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
      // ignore cleanup errors
    }
    try {
      URL.revokeObjectURL(current.url);
    } catch {
      // ignore URL cleanup
    }
  }, []);

  useEffect(() => {
    return () => {
      cleanupPreviewAudio();
    };
  }, [cleanupPreviewAudio]);

  const playVoicePreview = useCallback(
    async (languageCode: string, languageLabel: string) => {
      const trimmedCode = languageCode.trim();
      if (!trimmedCode) {
        return;
      }

      const effectiveVoice = voiceOverrides[trimmedCode] ?? selectedVoice;
      const sampleText = sampleSentenceFor(trimmedCode, languageLabel);

      setVoicePreviewError((previous) => {
        const next = { ...previous };
        delete next[trimmedCode];
        return next;
      });
      cleanupPreviewAudio();
      setVoicePreviewStatus((previous) => ({ ...previous, [trimmedCode]: 'loading' }));

      try {
        const previewBlob = await synthesizeVoicePreview({
          text: sampleText,
          language: trimmedCode,
          voice: effectiveVoice,
        });
        const previewUrl = URL.createObjectURL(previewBlob);
        const audio = new Audio(previewUrl);
        previewAudioRef.current = { audio, url: previewUrl, code: trimmedCode };
        audio.onended = () => {
          setVoicePreviewStatus((previous) => ({ ...previous, [trimmedCode]: 'idle' }));
          cleanupPreviewAudio();
        };
        audio.onerror = () => {
          setVoicePreviewStatus((previous) => ({ ...previous, [trimmedCode]: 'idle' }));
          setVoicePreviewError((previous) => ({
            ...previous,
            [trimmedCode]: 'Audio playback failed.',
          }));
          cleanupPreviewAudio();
        };
        await audio.play();
        setVoicePreviewStatus((previous) => ({ ...previous, [trimmedCode]: 'playing' }));
      } catch (previewError) {
        cleanupPreviewAudio();
        setVoicePreviewStatus((previous) => ({ ...previous, [trimmedCode]: 'idle' }));
        const message =
          previewError instanceof Error
            ? previewError.message
            : 'Unable to generate voice preview.';
        setVoicePreviewError((previous) => ({ ...previous, [trimmedCode]: message }));
      }
    },
    [cleanupPreviewAudio, selectedVoice, voiceOverrides],
  );

  const buildVoiceOptions = useCallback(
    (languageLabel: string, languageCode: string | null): MenuOption[] => {
      const baseOptions: MenuOption[] = VOICE_OPTIONS.map((option) => ({
        value: option.value,
        label: option.label,
        description: option.description,
      }));

      if (!voiceInventory || !languageCode) {
        return baseOptions;
      }

      const extras: MenuOption[] = [];
      const normalizedCode = languageCode.toLowerCase();

      const gttsMatches = voiceInventory.gtts.filter((entry) => {
        const entryCode = entry.code.toLowerCase();
        if (entryCode === normalizedCode) {
          return true;
        }
        return entryCode.startsWith(`${normalizedCode}-`) || entryCode.startsWith(`${normalizedCode}_`);
      });
      const seenGtts = new Set<string>();
      for (const entry of gttsMatches) {
        const shortCode = entry.code.split(/[-_]/)[0].toLowerCase();
        if (!shortCode || seenGtts.has(shortCode)) {
          continue;
        }
        seenGtts.add(shortCode);
        const identifier = `gTTS-${shortCode}`;
        extras.push({ value: identifier, label: `gTTS (${entry.name})`, description: 'gTTS voice' });
      }

      const macVoices = voiceInventory.macos.filter((voice) => {
        const voiceLang = voice.lang.toLowerCase();
        return (
          voiceLang === normalizedCode ||
          voiceLang.startsWith(`${normalizedCode}-`) ||
          voiceLang.startsWith(`${normalizedCode}_`)
        );
      });
      macVoices
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name))
        .forEach((voice) => {
          extras.push({
            value: formatMacOSVoiceIdentifier(voice),
            label: formatMacOSVoiceLabel(voice),
            description: 'macOS system voice',
          });
        });

      const merged = new Map<string, MenuOption>();
      for (const option of [...baseOptions, ...extras]) {
        if (!option.value) {
          continue;
        }
        if (!merged.has(option.value)) {
          merged.set(option.value, option);
        }
      }
      return Array.from(merged.values());
    },
    [voiceInventory],
  );

  return {
    voiceInventory,
    voiceInventoryError,
    isLoadingVoiceInventory,
    voicePreviewStatus,
    voicePreviewError,
    playVoicePreview,
    buildVoiceOptions,
  };
}
