import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchVoiceInventory, synthesizeVoicePreview } from '../../api/client';
import { useVideoDubbingVoiceState } from '../video-dubbing/useVideoDubbingVoiceState';

vi.mock('../../api/client', () => ({
  fetchVoiceInventory: vi.fn(),
  synthesizeVoicePreview: vi.fn()
}));

const mockFetchVoiceInventory = vi.mocked(fetchVoiceInventory);
const mockSynthesizeVoicePreview = vi.mocked(synthesizeVoicePreview);

type FakeAudioInstance = {
  onended: (() => void) | null;
  onerror: (() => void) | null;
  pause: ReturnType<typeof vi.fn>;
  play: ReturnType<typeof vi.fn>;
  load: ReturnType<typeof vi.fn>;
  src: string;
};

let lastAudio: FakeAudioInstance | null = null;
let nextPlayImplementation: (() => Promise<void>) | null = null;
let createObjectURLSpy: ReturnType<typeof vi.fn>;
let revokeObjectURLSpy: ReturnType<typeof vi.fn>;

function installAudioStubs() {
  createObjectURLSpy = vi.fn(() => 'blob:voice-preview');
  revokeObjectURLSpy = vi.fn();
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: createObjectURLSpy
  });
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: revokeObjectURLSpy
  });
  vi.stubGlobal(
    'Audio',
    class {
      onended: (() => void) | null = null;
      onerror: (() => void) | null = null;
      pause = vi.fn();
      play = vi.fn(() => (nextPlayImplementation ? nextPlayImplementation() : Promise.resolve()));
      load = vi.fn();
      src = '';

      constructor(src: string) {
        this.src = src;
        lastAudio = this;
      }
    }
  );
}

describe('useVideoDubbingVoiceState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    lastAudio = null;
    nextPlayImplementation = null;
    installAudioStubs();
    mockFetchVoiceInventory.mockResolvedValue({ macos: [], gtts: [], piper: [] });
    mockSynthesizeVoicePreview.mockResolvedValue(new Blob(['audio']));
  });

  it('loads voice inventory and builds target-language voice options', async () => {
    mockFetchVoiceInventory.mockResolvedValueOnce({
      macos: [{ name: 'Samantha', lang: 'en-US', quality: 'Premium', gender: 'Female' }],
      gtts: [{ code: 'en', name: 'English' }],
      piper: [{ name: 'piper-es', lang: 'es', quality: 'medium' }]
    });

    const { result } = renderHook(() =>
      useVideoDubbingVoiceState({
        subtitleLanguageLabel: 'English',
        targetLanguage: 'English',
        targetLanguageCode: 'en'
      })
    );

    await waitFor(() => expect(result.current.isLoadingVoices).toBe(false));

    expect(mockFetchVoiceInventory).toHaveBeenCalledTimes(1);
    expect(result.current.voiceInventoryError).toBeNull();
    expect(result.current.availableVoiceOptions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: 'Samantha (en-US, Female, Premium)' }),
        expect.objectContaining({ value: 'gTTS-en', label: 'gTTS (English)' })
      ])
    );
    expect(result.current.availableVoiceOptions).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ value: 'piper-es' })])
    );
  });

  it('surfaces voice inventory load failures without breaking base choices', async () => {
    mockFetchVoiceInventory.mockRejectedValueOnce(new Error('voices offline'));

    const { result } = renderHook(() =>
      useVideoDubbingVoiceState({
        subtitleLanguageLabel: null,
        targetLanguage: '',
        targetLanguageCode: ''
      })
    );

    await waitFor(() => expect(result.current.voiceInventoryError).toBe('voices offline'));

    expect(result.current.isLoadingVoices).toBe(false);
    expect(result.current.availableVoiceOptions.length).toBeGreaterThan(0);
  });

  it('requires a target or subtitle language before previewing', async () => {
    const { result } = renderHook(() =>
      useVideoDubbingVoiceState({
        subtitleLanguageLabel: '',
        targetLanguage: '',
        targetLanguageCode: ''
      })
    );

    await act(async () => {
      await result.current.previewVoice();
    });

    expect(result.current.previewError).toBe('Choose a translation language before previewing.');
    expect(mockSynthesizeVoicePreview).not.toHaveBeenCalled();
  });

  it('synthesizes and plays a sample for the selected voice', async () => {
    const { result } = renderHook(() =>
      useVideoDubbingVoiceState({
        subtitleLanguageLabel: 'English',
        targetLanguage: 'Japanese',
        targetLanguageCode: 'ja'
      })
    );

    act(() => {
      result.current.setVoice('Kyoko - ja-JP - (Premium)');
    });
    await act(async () => {
      await result.current.previewVoice();
    });

    expect(mockSynthesizeVoicePreview).toHaveBeenCalledWith(
      expect.objectContaining({
        language: 'ja',
        voice: 'Kyoko - ja-JP - (Premium)'
      })
    );
    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(lastAudio?.play).toHaveBeenCalled();
    expect(result.current.isPreviewing).toBe(true);

    act(() => {
      lastAudio?.onended?.();
    });

    expect(result.current.isPreviewing).toBe(false);
    expect(lastAudio?.pause).toHaveBeenCalled();
    expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:voice-preview');
  });

  it('cleans up audio and reports preview playback failures', async () => {
    nextPlayImplementation = () => Promise.reject(new Error('play blocked'));
    const { result } = renderHook(() =>
      useVideoDubbingVoiceState({
        subtitleLanguageLabel: 'English',
        targetLanguage: 'English',
        targetLanguageCode: 'en'
      })
    );

    await act(async () => {
      await result.current.previewVoice();
    });

    expect(result.current.isPreviewing).toBe(false);
    expect(result.current.previewError).toBe('play blocked');
    expect(lastAudio?.pause).toHaveBeenCalled();
    expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:voice-preview');
  });
});
