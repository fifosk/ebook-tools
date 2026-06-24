import { describe, expect, it } from 'vitest';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import {
  buildPlayerPanelDocumentState,
  resolveInteractiveViewerRenderability
} from '../player-panel/playerPanelDocumentState';

function chunk(overrides: Partial<LiveMediaChunk> = {}): LiveMediaChunk {
  return {
    chunkId: 'chunk-1',
    rangeFragment: 'range-1',
    startSentence: 1,
    endSentence: 2,
    files: [],
    ...overrides,
  };
}

function state(overrides: Partial<Parameters<typeof buildPlayerPanelDocumentState>[0]> = {}) {
  return buildPlayerPanelDocumentState({
    textPreview: null,
    fallbackTextContent: '',
    resolvedActiveTextChunk: null,
    isInteractiveFullscreen: false,
    hasTextItems: false,
    hasSelectedItem: false,
    textLoading: false,
    textError: null,
    ...overrides,
  });
}

describe('buildPlayerPanelDocumentState', () => {
  it('resolves viewer renderability from chunk presence, fallback text, or preview text', () => {
    expect(
      resolveInteractiveViewerRenderability({
        previewContent: null,
        fallbackTextContent: '',
        resolvedActiveTextChunk: null,
      }),
    ).toBe(false);
    expect(
      resolveInteractiveViewerRenderability({
        previewContent: '  ',
        fallbackTextContent: 'Fallback',
        resolvedActiveTextChunk: null,
      }),
    ).toBe(true);
    expect(
      resolveInteractiveViewerRenderability({
        previewContent: 'Preview',
        fallbackTextContent: '',
        resolvedActiveTextChunk: null,
      }),
    ).toBe(true);
    expect(
      resolveInteractiveViewerRenderability({
        previewContent: null,
        fallbackTextContent: '',
        resolvedActiveTextChunk: chunk(),
      }),
    ).toBe(true);
  });

  it('uses preview content and raw text before fallback sentence text', () => {
    expect(
      state({
        textPreview: { content: 'Preview text', raw: '<p>Preview text</p>' },
        fallbackTextContent: 'Fallback sentence',
      }),
    ).toMatchObject({
      interactiveViewerContent: 'Preview text',
      interactiveViewerRaw: '<p>Preview text</p>',
      canRenderInteractiveViewer: true,
      shouldShowInteractiveViewer: true,
    });
  });

  it('renders from fallback text or chunk presence when preview content is absent', () => {
    expect(
      state({
        fallbackTextContent: '  Chunk sentence  ',
      }),
    ).toMatchObject({
      interactiveViewerContent: '  Chunk sentence  ',
      interactiveViewerRaw: '  Chunk sentence  ',
      canRenderInteractiveViewer: true,
      shouldShowInteractiveViewer: true,
    });

    expect(
      state({
        resolvedActiveTextChunk: chunk(),
      }),
    ).toMatchObject({
      interactiveViewerContent: '',
      canRenderInteractiveViewer: true,
      shouldShowInteractiveViewer: true,
    });
  });

  it('shows empty, loading, and standalone error placeholders outside fullscreen', () => {
    expect(
      state({
        hasTextItems: true,
        hasSelectedItem: false,
      }).shouldShowEmptySelectionPlaceholder,
    ).toBe(true);

    expect(
      state({
        hasSelectedItem: true,
        textLoading: true,
      }).shouldShowLoadingPlaceholder,
    ).toBe(true);

    expect(
      state({
        textError: 'Failed to load document.',
      }).shouldShowStandaloneError,
    ).toBe(true);
  });

  it('forces the viewer in fullscreen and suppresses standalone placeholders', () => {
    expect(
      state({
        isInteractiveFullscreen: true,
        hasTextItems: true,
        hasSelectedItem: false,
        textLoading: true,
        textError: 'Failed to load document.',
      }),
    ).toMatchObject({
      shouldShowInteractiveViewer: true,
      shouldShowEmptySelectionPlaceholder: false,
      shouldShowLoadingPlaceholder: false,
      shouldShowStandaloneError: false,
    });
  });
});
