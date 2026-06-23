import { describe, expect, it } from 'vitest';
import type { LibraryItem } from '../../api/dtos';
import {
  DEFAULT_LIBRARY_ITEM_PERMISSIONS,
  buildLibraryItemActionState,
  resolveLibraryItemPermissions
} from '../library-list/libraryListActions';

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
    ...overrides
  };
}

describe('libraryListActions', () => {
  it('returns default permissions when no resolver is provided', () => {
    expect(resolveLibraryItemPermissions(item())).toBe(DEFAULT_LIBRARY_ITEM_PERMISSIONS);
  });

  it('normalizes resolver permissions to booleans', () => {
    const permissions = resolveLibraryItemPermissions(item(), () => ({
      canView: 1 as unknown as boolean,
      canEdit: 0 as unknown as boolean,
      canExport: 'yes' as unknown as boolean
    }));

    expect(permissions).toEqual({ canView: true, canEdit: false, canExport: true });
  });

  it('allows export only when media is complete and the item can be viewed', () => {
    expect(
      buildLibraryItemActionState(
        item({ mediaCompleted: true }),
        { canView: true, canEdit: true, canExport: true },
        false,
      ),
    ).toMatchObject({
      canExport: true,
      exportDisabled: false,
      exportTitle: 'Export offline player'
    });

    expect(
      buildLibraryItemActionState(
        item({ mediaCompleted: false }),
        { canView: true, canEdit: true, canExport: true },
        false,
      ),
    ).toMatchObject({
      canExport: true,
      exportDisabled: true,
      exportTitle: 'Export available after media completes'
    });

    expect(
      buildLibraryItemActionState(
        item({ mediaCompleted: true }),
        { canView: false, canEdit: true, canExport: true },
        false,
      ),
    ).toMatchObject({
      canView: false,
      canExport: false,
      mediaOpenDisabled: true,
      exportDisabled: true
    });
  });

  it('disables every mutating action while preserving capability flags', () => {
    expect(
      buildLibraryItemActionState(
        item(),
        { canView: true, canEdit: true, canExport: true },
        true,
      ),
    ).toMatchObject({
      canView: true,
      canEdit: true,
      canExport: true,
      isMutating: true,
      mediaOpenDisabled: true,
      editDisabled: true,
      exportDisabled: true,
      removeDisabled: true
    });
  });
});
