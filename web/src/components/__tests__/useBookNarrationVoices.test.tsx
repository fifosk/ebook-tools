import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchVoiceInventory, synthesizeVoicePreview } from '../../api/client';
import { useBookNarrationVoices } from '../book-narration/useBookNarrationVoices';

vi.mock('../../api/client', () => ({
  fetchVoiceInventory: vi.fn(),
  synthesizeVoicePreview: vi.fn(),
}));

const mockFetchVoiceInventory = vi.mocked(fetchVoiceInventory);
const mockSynthesizeVoicePreview = vi.mocked(synthesizeVoicePreview);

class MockAudio {
  onended: (() => void) | null = null;
  onerror: (() => void) | null = null;
  src = '';

  constructor(src: string) {
    this.src = src;
  }

  load = vi.fn();
  pause = vi.fn();
  play = vi.fn().mockResolvedValue(undefined);
}

describe('useBookNarrationVoices', () => {
  beforeEach(() => {
    mockFetchVoiceInventory.mockResolvedValue({
      gtts: [
        { code: 'zh-cn', name: 'Chinese' },
        { code: 'es', name: 'Spanish' },
      ],
      macos: [
        { name: 'Tingting', lang: 'zh-CN', quality: 'premium', gender: 'female' },
        { name: 'Monica', lang: 'es_ES', quality: 'premium', gender: 'female' },
      ],
      piper: [
        { name: 'zh_CN-huayan-medium', lang: 'zh_CN', quality: 'medium' },
        { name: 'es_ES-sharvard-medium', lang: 'es_ES', quality: 'medium' },
      ],
    });
    mockSynthesizeVoicePreview.mockResolvedValue(new Blob(['preview'], { type: 'audio/mpeg' }));
    Object.defineProperty(globalThis, 'Audio', {
      configurable: true,
      value: MockAudio,
    });
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn(() => 'blob:preview'),
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('builds language-specific voice options from backend inventory', async () => {
    const { result } = renderHook(() =>
      useBookNarrationVoices({
        selectedVoice: 'gTTS',
        voiceOverrides: {},
      }),
    );

    await waitFor(() => expect(result.current.isLoadingVoiceInventory).toBe(false));
    const options = result.current.buildVoiceOptions('Chinese', 'zh-CN');

    expect(mockFetchVoiceInventory).toHaveBeenCalledTimes(1);
    expect(options.map((option) => option.value)).toEqual(
      expect.arrayContaining(['gTTS-zh', 'Tingting - zh-CN - (premium) - Female', 'zh_CN-huayan-medium']),
    );
    expect(options.find((option) => option.value === 'gTTS-zh')?.label).toBe('gTTS (Chinese)');
    expect(options.find((option) => option.value === 'zh_CN-huayan-medium')?.label).toBe(
      'Piper: zh_CN-huayan-medium',
    );
  });

  it('uses per-language voice overrides for preview synthesis', async () => {
    const { result } = renderHook(() =>
      useBookNarrationVoices({
        selectedVoice: 'gTTS',
        voiceOverrides: {
          es: 'macOS:Monica:es_ES',
        },
      }),
    );

    await waitFor(() => expect(result.current.isLoadingVoiceInventory).toBe(false));
    await act(async () => {
      await result.current.playVoicePreview('es', 'Spanish');
    });

    expect(mockSynthesizeVoicePreview).toHaveBeenCalledWith({
      text: expect.stringContaining('Hola'),
      language: 'es',
      voice: 'macOS:Monica:es_ES',
    });
    expect(result.current.voicePreviewStatus.es).toBe('playing');
  });

  it('reports backend inventory load failures without dropping base options', async () => {
    mockFetchVoiceInventory.mockRejectedValueOnce(new Error('inventory unavailable'));
    const { result } = renderHook(() =>
      useBookNarrationVoices({
        selectedVoice: 'gTTS',
        voiceOverrides: {},
      }),
    );

    await waitFor(() => expect(result.current.isLoadingVoiceInventory).toBe(false));

    expect(result.current.voiceInventory).toBeNull();
    expect(result.current.voiceInventoryError).toBe('inventory unavailable');
    expect(result.current.buildVoiceOptions('Spanish', 'es').map((option) => option.value)).toContain('gTTS');
  });
});
