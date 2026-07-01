import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type {
  AcquisitionCandidate,
  AcquisitionDiscoveryResponse,
  PipelineFileBrowserResponse,
} from '../../api/dtos';
import { BookNarrationFormDialogs } from '../book-narration/BookNarrationFormDialogs';

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

const fileOptions: PipelineFileBrowserResponse = {
  ebooks: [
    {
      name: 'Demo.epub',
      path: '/books/Demo.epub',
      type: 'file',
    },
  ],
  outputs: [
    {
      name: 'Output',
      path: '/output/book',
      type: 'directory',
    },
  ],
  books_root: '/books',
  output_root: '/output',
};

const discoveryResponse: AcquisitionDiscoveryResponse = {
  candidates: [candidate()],
  providers_queried: ['local_epub'],
  policy_notes: ['Review source rights before narrating.'],
};

function renderDialogs(overrides: Partial<Parameters<typeof BookNarrationFormDialogs>[0]> = {}) {
  const props: Parameters<typeof BookNarrationFormDialogs>[0] = {
    activeFileDialog: null,
    fileOptions,
    onInputFileSelect: vi.fn(),
    onOutputPathSelect: vi.fn(),
    onCloseFileDialog: vi.fn(),
    onDeleteEbook: vi.fn(),
    activeDiscoveryDialog: false,
    discoveryProvider: 'local_epub',
    discoveryQuery: 'demo',
    discoveryCandidates: [candidate()],
    discoveryResponse,
    discoveryError: null,
    isDiscovering: false,
    isLoadingProviders: false,
    acquiringCandidateId: null,
    providerOptions: [
      {
        id: 'local_epub',
        label: 'Local EPUBs',
        unavailableMessage: null,
      },
    ],
    providerError: null,
    selectedProviderUnavailableMessage: null,
    onDiscoveryProviderChange: vi.fn(),
    onDiscoveryQueryChange: vi.fn(),
    onDiscoverySearch: vi.fn(),
    onDiscoverySelect: vi.fn(),
    onCloseDiscoveryDialog: vi.fn(),
    ...overrides,
  };
  render(<BookNarrationFormDialogs {...props} />);
  return props;
}

describe('BookNarrationFormDialogs', () => {
  it('routes input file selection and deletion through the shared file dialog', () => {
    const props = renderDialogs({ activeFileDialog: 'input' });

    fireEvent.click(screen.getByLabelText('Select Demo.epub'));
    expect(props.onInputFileSelect).toHaveBeenCalledWith('/books/Demo.epub');
    expect(props.onCloseFileDialog).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByLabelText('Delete Demo.epub'));
    expect(props.onDeleteEbook).toHaveBeenCalledWith(fileOptions.ebooks[0]);
  });

  it('routes discovery search and candidate selection through the discovery dialog', () => {
    const props = renderDialogs({ activeDiscoveryDialog: true });

    expect(screen.getByText('Review source rights before narrating.')).toBeInTheDocument();
    expect(screen.getByText('Checked local epub.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Search' }));
    expect(props.onDiscoverySearch).toHaveBeenCalledWith('demo');

    fireEvent.click(screen.getByLabelText('Use Demo Book'));
    expect(props.onDiscoverySelect).toHaveBeenCalledWith(props.discoveryCandidates[0]);
  });
});
