import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { AcquisitionCandidate } from '../../api/dtos';
import { useBookNarrationDiscoverySelection } from '../book-narration/useBookNarrationDiscoverySelection';

function candidate(overrides: Partial<AcquisitionCandidate> = {}): AcquisitionCandidate {
  return {
    candidate_id: 'local_epub:demo',
    provider: 'local_epub',
    media_kind: 'book',
    title: 'Demo Book',
    rights: 'user_provided',
    capabilities: ['metadata', 'import_local'],
    candidate_token: 'token',
    contributors: [],
    local_path: '/books/demo.epub',
    subtitles: [],
    metadata: {},
    requires_confirmation: false,
    policy_notes: [],
    ...overrides,
  };
}

function renderDiscoverySelectionHook({
  inputFile = '',
  sourceMode = 'upload' as const,
}: {
  inputFile?: string;
  sourceMode?: 'upload' | 'generated';
} = {}) {
  const acquireDiscoveryCandidate = vi.fn().mockResolvedValue(null);
  const applyDiscoveryMetadataCandidate = vi.fn().mockReturnValue(false);
  const closeDiscoveryDialog = vi.fn();
  const discoverInternetArchiveCandidatesForCandidate = vi.fn().mockResolvedValue(false);
  const handleInputFileChange = vi.fn();
  const handleSectionChange = vi.fn();
  const selectDiscoveryCandidate = vi.fn().mockResolvedValue(null);

  const hook = renderHook((props: { inputFile: string }) => useBookNarrationDiscoverySelection({
    acquireDiscoveryCandidate,
    applyDiscoveryMetadataCandidate,
    closeDiscoveryDialog,
    discoverInternetArchiveCandidatesForCandidate,
    discoveryProvider: 'local_epub',
    discoveryQuery: ' demo query ',
    handleInputFileChange,
    handleSectionChange,
    inputFile: props.inputFile,
    selectDiscoveryCandidate,
    sourceMode,
    templatePayloadExtras: { handoff_source: 'web' },
  }), {
    initialProps: { inputFile },
  });

  return {
    ...hook,
    acquireDiscoveryCandidate,
    applyDiscoveryMetadataCandidate,
    closeDiscoveryDialog,
    discoverInternetArchiveCandidatesForCandidate,
    handleInputFileChange,
    handleSectionChange,
    selectDiscoveryCandidate,
  };
}

describe('useBookNarrationDiscoverySelection', () => {
  it('selects local EPUB candidates and preserves token-free discovery provenance', async () => {
    const rendered = renderDiscoverySelectionHook();
    rendered.selectDiscoveryCandidate.mockResolvedValue({
      selectedPath: '/books/selected.epub',
      preparedMetadata: {
        source_provider: 'local_epub',
        source_url: 'https://user:secret@example.test/book.epub?token=drop#name=Book',
      },
    });

    act(() => {
      rendered.result.current.handleDiscoveryCandidateSelect(candidate());
    });

    await waitFor(() => {
      expect(rendered.handleInputFileChange).toHaveBeenCalledWith('/books/selected.epub');
    });
    expect(rendered.closeDiscoveryDialog).toHaveBeenCalledTimes(1);
    expect(rendered.result.current.mergedTemplatePayloadExtras).toMatchObject({
      handoff_source: 'web',
      discovery_state: {
        media_kind: 'book',
        selected_provider: 'local_epub',
        selected_path: '/books/selected.epub',
        query: 'demo query',
        source_url: 'https://example.test/book.epub#name=Book',
      },
    });
    expect(JSON.stringify(rendered.result.current.mergedTemplatePayloadExtras)).not.toContain('secret');
    expect(JSON.stringify(rendered.result.current.mergedTemplatePayloadExtras)).not.toContain('token=');
  });

  it('keeps metadata-only candidates on the metadata step when no archive bridge handles them', async () => {
    const rendered = renderDiscoverySelectionHook();
    rendered.applyDiscoveryMetadataCandidate.mockReturnValue(true);
    const metadataCandidate = candidate({
      provider: 'openlibrary',
      candidate_id: 'openlibrary:/works/demo',
      capabilities: ['metadata'],
      local_path: null,
    });

    act(() => {
      rendered.result.current.handleDiscoveryCandidateSelect(metadataCandidate);
    });

    await waitFor(() => {
      expect(rendered.handleSectionChange).toHaveBeenCalledWith('metadata');
    });
    expect(rendered.discoverInternetArchiveCandidatesForCandidate).toHaveBeenCalledWith(metadataCandidate);
    expect(rendered.closeDiscoveryDialog).toHaveBeenCalledTimes(1);
    expect(rendered.result.current.mergedTemplatePayloadExtras).toMatchObject({
      discovery_state: {
        provider: 'openlibrary',
        candidate_id: 'openlibrary:/works/demo',
        selected_provider: 'local_epub',
      },
    });
  });

  it('clears selected discovery provenance when the input changes to another book', async () => {
    const rendered = renderDiscoverySelectionHook({ inputFile: '/books/selected.epub' });
    act(() => {
      rendered.result.current.setSelectedDiscoveryTemplateState({
        media_kind: 'book',
        provider: 'local_epub',
        selected_path: '/books/selected.epub',
      });
    });

    await waitFor(() => {
      expect(rendered.result.current.mergedTemplatePayloadExtras).toMatchObject({
        discovery_state: {
          selected_path: '/books/selected.epub',
        },
      });
    });

    rendered.rerender({ inputFile: '/books/other.epub' });

    await waitFor(() => {
      expect(rendered.result.current.mergedTemplatePayloadExtras).toEqual({
        handoff_source: 'web',
        discovery_state: {
          media_kind: 'book',
          provider: 'local_epub',
          selected_provider: 'local_epub',
          query: 'demo query',
        },
      });
    });
  });
});
