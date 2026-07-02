import { fireEvent, render, screen } from '@testing-library/react';
import type { ComponentProps } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { LibraryItem } from '../../api/dtos';
import { getJobTypeGlyph } from '../../utils/jobGlyphs';
import LibraryDetailsPanel from '../library/LibraryDetailsPanel';

const overviewSpy = vi.fn();
const metadataSpy = vi.fn();
const permissionsSpy = vi.fn();

vi.mock('../library/LibraryOverviewTab', () => ({
  default: (props: Record<string, unknown>) => {
    overviewSpy(props);
    return <div data-testid="overview-tab">Overview: {String(props.title)}</div>;
  },
}));

vi.mock('../library/LibraryMetadataTab', () => ({
  default: (props: Record<string, unknown>) => {
    metadataSpy(props);
    return <div data-testid="metadata-tab">Metadata: {(props.item as LibraryItem).jobId}</div>;
  },
}));

vi.mock('../library/LibraryPermissionsTab', () => ({
  default: (props: Record<string, unknown>) => {
    permissionsSpy(props);
    return <div data-testid="permissions-tab">Permissions</div>;
  },
}));

function item(overrides: Partial<LibraryItem> = {}): LibraryItem {
  return {
    jobId: 'job-1',
    author: 'Author',
    bookTitle: 'Book',
    itemType: 'book',
    language: 'en',
    status: 'finished',
    mediaCompleted: true,
    createdAt: '2026-06-23T10:00:00Z',
    updatedAt: '2026-06-23T10:00:00Z',
    libraryPath: '/library/job-1',
    metadata: {},
    ...overrides,
  };
}

function renderPanel(overrides: Partial<ComponentProps<typeof LibraryDetailsPanel>> = {}) {
  const props: ComponentProps<typeof LibraryDetailsPanel> = {
    item: item(),
    itemType: 'book',
    title: 'Book Title',
    author: 'Author',
    genre: 'Mystery',
    jobGlyph: getJobTypeGlyph('book'),
    jobType: 'book',
    detailTab: 'overview',
    onDetailTabChange: vi.fn(),
    displayedCoverUrl: null,
    tvPoster: null,
    tvStill: null,
    youtubeThumbnail: null,
    youtubeMetadata: null,
    permissions: { canView: true, canEdit: true, canExport: true },
    mutating: false,
    isSaving: false,
    isEditing: false,
    isEnriching: false,
    enrichmentError: null,
    enrichmentResult: null,
    editValues: { title: '', author: '', genre: '', language: '', isbn: '' },
    editError: null,
    selectedFile: null,
    isbnPreview: null,
    isbnFetchError: null,
    isFetchingIsbn: false,
    onPlay: vi.fn(),
    onStartEditing: vi.fn(),
    onEnrichMetadata: vi.fn(),
    onEditSubmit: vi.fn(),
    onEditCancel: vi.fn(),
    onEditValueChange: vi.fn(() => vi.fn()),
    onFetchIsbnMetadata: vi.fn(),
    onSourceFileChange: vi.fn(),
    onSavePermissions: vi.fn(),
    ...overrides,
  };
  const view = render(<LibraryDetailsPanel {...props} />);
  return { ...view, props };
}

describe('LibraryDetailsPanel', () => {
  beforeEach(() => {
    overviewSpy.mockClear();
    metadataSpy.mockClear();
    permissionsSpy.mockClear();
  });

  it('renders an empty prompt when no library item is selected', () => {
    renderPanel({ item: null });

    expect(screen.getByText('Select an entry to inspect its metadata snapshot.')).toBeInTheDocument();
    expect(overviewSpy).not.toHaveBeenCalled();
  });

  it('renders overview details and routes tab changes', () => {
    const { props } = renderPanel();

    expect(screen.getByRole('heading', { name: /Book Title/i })).toBeInTheDocument();
    expect(screen.getByTestId('overview-tab')).toHaveTextContent('Overview: Book Title');
    expect(overviewSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        item: props.item,
        itemType: 'book',
        title: 'Book Title',
        permissions: props.permissions,
        onPlay: props.onPlay,
      }),
    );

    fireEvent.click(screen.getByRole('tab', { name: 'Metadata' }));

    expect(props.onDetailTabChange).toHaveBeenCalledWith('metadata');
  });

  it('routes metadata and permissions tabs to their focused tab components', () => {
    const selected = item({ jobId: 'video-1', itemType: 'video' });
    const { props, rerender } = renderPanel({
      item: selected,
      itemType: 'video',
      detailTab: 'metadata',
      youtubeMetadata: { title: 'Video' },
    });

    expect(screen.getByTestId('metadata-tab')).toHaveTextContent('Metadata: video-1');
    expect(metadataSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        item: selected,
        itemType: 'video',
        youtubeMetadata: { title: 'Video' },
      }),
    );

    rerender(<LibraryDetailsPanel {...props} detailTab="permissions" permissions={{ canView: true, canEdit: false, canExport: true }} />);

    expect(screen.getByTestId('permissions-tab')).toBeInTheDocument();
    expect(permissionsSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        policy: null,
        ownerId: null,
        canEdit: false,
        onSave: props.onSavePermissions,
      }),
    );
  });
});
