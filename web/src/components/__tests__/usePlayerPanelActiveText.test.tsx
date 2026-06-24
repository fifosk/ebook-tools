import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import { usePlayerPanelActiveText } from '../player-panel/usePlayerPanelActiveText';

function item(overrides: Partial<LiveMediaItem> = {}): LiveMediaItem {
  return {
    type: 'text',
    url: 'https://example.com/text/chunk-1.html',
    name: 'chunk-1.html',
    source: 'completed',
    ...overrides,
  };
}

function chunk(overrides: Partial<LiveMediaChunk> = {}): LiveMediaChunk {
  return {
    chunkId: 'chunk-1',
    rangeFragment: 'range-1',
    startSentence: 1,
    endSentence: 2,
    files: [item()],
    ...overrides,
  };
}

function renderActiveText(overrides: Partial<Parameters<typeof usePlayerPanelActiveText>[0]> = {}) {
  const textItems = [
    item({ url: 'first.html', name: 'First' }),
    item({ url: 'second.html', name: 'Second', chunk_id: 'chunk-2' }),
  ];
  const chunks = [
    chunk({ chunkId: 'chunk-1', files: [textItems[0]] }),
    chunk({
      chunkId: 'chunk-2',
      files: [textItems[1], item({ type: 'audio', url: 'chunk-2.mp3', name: '', source: 'completed' })],
    }),
  ];
  return renderHook(() =>
    usePlayerPanelActiveText({
      textItems,
      audioItems: [],
      chunks,
      selectedTextId: null,
      selectedAudioId: null,
      inlineAudioSelection: null,
      ...overrides,
    }),
  );
}

describe('usePlayerPanelActiveText', () => {
  it('resolves selected text and chunk with first-item fallback', () => {
    const { result } = renderActiveText();

    expect(result.current.selectedItem?.url).toBe('first.html');
    expect(result.current.selectedChunk?.chunkId).toBe('chunk-1');
    expect(result.current.activeTextChunk?.chunkId).toBe('chunk-1');
    expect(result.current.activeTextChunkIndex).toBe(0);

    const selected = renderActiveText({ selectedTextId: 'second.html' });

    expect(selected.result.current.selectedItem?.url).toBe('second.html');
    expect(selected.result.current.selectedChunk?.chunkId).toBe('chunk-2');
    expect(selected.result.current.activeTextChunk?.chunkId).toBe('chunk-2');
    expect(selected.result.current.activeTextChunkIndex).toBe(1);
  });

  it('maps interactive audio files to chunks and uses inline audio as active chunk fallback', () => {
    const textItems = [item({ url: 'text-1.html', name: 'Text 1' })];
    const chunks = [
      chunk({ chunkId: 'chunk-1', files: [textItems[0]] }),
      chunk({
        chunkId: 'chunk-2',
        rangeFragment: 'range-2',
        files: [item({ type: 'audio', url: 'chunk-2.mp3', name: '', source: 'completed' })],
      }),
    ];

    const { result } = renderHook(() =>
      usePlayerPanelActiveText({
        textItems,
        audioItems: [],
        chunks,
        selectedTextId: 'missing.html',
        selectedAudioId: null,
        inlineAudioSelection: 'chunk-2.mp3',
      }),
    );

    expect(result.current.selectedItem?.url).toBe('text-1.html');
    expect(result.current.selectedChunk?.chunkId).toBe('chunk-1');
    expect(result.current.interactiveAudioPlaylist.map((entry) => entry.url)).toEqual(['chunk-2.mp3']);
    expect(result.current.interactiveAudioNameMap.get('chunk-2.mp3')).toBe('range-2');
    expect(result.current.audioChunkIndexMap.get('chunk-2.mp3')).toBe(1);
    expect(result.current.activeTextChunk?.chunkId).toBe('chunk-1');
  });

  it('falls back to inline audio chunk when no text item is selected', () => {
    const chunks = [
      chunk({ chunkId: 'chunk-1', files: [] }),
      chunk({
        chunkId: 'chunk-2',
        startSentence: 3,
        endSentence: 4,
        files: [item({ type: 'audio', url: 'chunk-2.mp3', name: 'Chunk Two', source: 'completed' })],
      }),
    ];

    const { result } = renderHook(() =>
      usePlayerPanelActiveText({
        textItems: [],
        audioItems: [],
        chunks,
        selectedTextId: null,
        selectedAudioId: null,
        inlineAudioSelection: 'chunk-2.mp3',
      }),
    );

    expect(result.current.selectedItem).toBeNull();
    expect(result.current.selectedChunk).toBeNull();
    expect(result.current.activeTextChunk?.chunkId).toBe('chunk-2');
    expect(result.current.activeTextChunkIndex).toBe(1);
  });
});
