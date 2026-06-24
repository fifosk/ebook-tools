import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { LibraryItem } from '../../api/dtos';
import { LibraryItemActions } from '../library-list/LibraryItemActions';
import type { LibraryItemActionState } from '../library-list/libraryListActions';

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

function actionState(overrides: Partial<LibraryItemActionState> = {}): LibraryItemActionState {
  return {
    canView: true,
    canEdit: true,
    canExport: true,
    isExportReady: true,
    isMutating: false,
    mediaOpenDisabled: false,
    editDisabled: false,
    exportDisabled: false,
    removeDisabled: false,
    exportTitle: 'Export offline player',
    ...overrides,
  };
}

describe('LibraryItemActions', () => {
  it('invokes enabled item actions without bubbling row clicks', () => {
    const libraryItem = item();
    const onOpen = vi.fn();
    const onEditMetadata = vi.fn();
    const onExport = vi.fn();
    const onRemove = vi.fn();
    const onParentClick = vi.fn();

    render(
      <div onClick={onParentClick}>
        <LibraryItemActions
          item={libraryItem}
          actionState={actionState()}
          onOpen={onOpen}
          onEditMetadata={onEditMetadata}
          onExport={onExport}
          onRemove={onRemove}
        />
      </div>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Play' }));
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    fireEvent.click(screen.getByRole('button', { name: 'Export offline player' }));
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

    expect(onOpen).toHaveBeenCalledWith(libraryItem);
    expect(onEditMetadata).toHaveBeenCalledWith(libraryItem);
    expect(onExport).toHaveBeenCalledWith(libraryItem);
    expect(onRemove).toHaveBeenCalledWith(libraryItem);
    expect(onParentClick).not.toHaveBeenCalled();
  });

  it('honors disabled and missing-export action states', () => {
    const libraryItem = item();
    const onOpen = vi.fn();
    const onEditMetadata = vi.fn();
    const onRemove = vi.fn();

    render(
      <LibraryItemActions
        item={libraryItem}
        actionState={actionState({
          canEdit: false,
          canExport: false,
          editDisabled: true,
          exportDisabled: true,
          removeDisabled: true,
        })}
        onOpen={onOpen}
        onEditMetadata={onEditMetadata}
        onRemove={onRemove}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Play' }));
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

    expect(screen.queryByRole('button', { name: 'Export offline player' })).not.toBeInTheDocument();
    expect(onOpen).toHaveBeenCalledWith(libraryItem);
    expect(onEditMetadata).not.toHaveBeenCalled();
    expect(onRemove).not.toHaveBeenCalled();
  });
});
