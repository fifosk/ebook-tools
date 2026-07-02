import { fireEvent, render, screen, within } from '@testing-library/react';
import type { ComponentProps } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { LibraryItem, ResumePositionEntry } from '../../api/dtos';
import LibraryEntriesPanel from '../library/LibraryEntriesPanel';

const libraryListSpy = vi.fn();

vi.mock('../../components/LibraryList', () => ({
  default: (props: Record<string, unknown>) => {
    libraryListSpy(props);
    const items = props.items as LibraryItem[];
    return <div data-testid="library-list">Rows: {items.map((item) => item.jobId).join(',')}</div>;
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

function renderPanel(overrides: Partial<ComponentProps<typeof LibraryEntriesPanel>> = {}) {
  const props: ComponentProps<typeof LibraryEntriesPanel> = {
    activeTab: 'book',
    onActiveTabChange: vi.fn(),
    bookCount: 2,
    subtitleCount: 1,
    videoCount: 3,
    items: [item()],
    view: 'flat',
    onSelect: vi.fn(),
    onOpen: vi.fn(),
    onExport: vi.fn(),
    onRemove: vi.fn(),
    onEditMetadata: vi.fn(),
    resolvePermissions: () => ({ canView: true, canEdit: true, canExport: true }),
    selectedJobId: 'job-1',
    mutating: { 'job-1': true },
    resumeEntries: [],
    ...overrides,
  };
  const view = render(<LibraryEntriesPanel {...props} />);
  return { ...view, props };
}

describe('LibraryEntriesPanel', () => {
  beforeEach(() => {
    libraryListSpy.mockClear();
  });

  it('renders tab counts and routes tab changes', () => {
    const { props } = renderPanel({ activeTab: 'narrated_subtitle' });
    const tabList = screen.getByRole('tablist', { name: 'Library tabs' });

    expect(within(tabList).getByRole('tab', { name: /Books 2/i })).toHaveAttribute('aria-selected', 'false');
    expect(within(tabList).getByRole('tab', { name: /Subtitles 1/i })).toHaveAttribute('aria-selected', 'true');
    expect(within(tabList).getByRole('tab', { name: /Videos 3/i })).toHaveAttribute('aria-selected', 'false');

    fireEvent.click(within(tabList).getByRole('tab', { name: /Videos 3/i }));

    expect(props.onActiveTabChange).toHaveBeenCalledWith('video');
  });

  it('passes active rows and library actions to LibraryList', () => {
    const rows = [item({ jobId: 'book-a' }), item({ jobId: 'book-b' })];
    const resumeEntries: ResumePositionEntry[] = [
      {
        job_id: 'book-a',
        kind: 'time',
        position: 42,
        updated_at: 1,
        media_type: 'audio',
        base_id: null,
      },
    ];
    const { props } = renderPanel({ items: rows, resumeEntries });

    expect(screen.getByTestId('library-list')).toHaveTextContent('Rows: book-a,book-b');
    expect(libraryListSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        items: rows,
        view: 'flat',
        variant: 'embedded',
        onSelect: props.onSelect,
        onOpen: props.onOpen,
        onExport: props.onExport,
        onRemove: props.onRemove,
        onEditMetadata: props.onEditMetadata,
        resolvePermissions: props.resolvePermissions,
        selectedJobId: 'job-1',
        mutating: props.mutating,
        resumeEntries,
      }),
    );
  });
});
