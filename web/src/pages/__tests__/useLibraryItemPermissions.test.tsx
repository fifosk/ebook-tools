import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { AccessPolicy, LibraryItem } from '../../api/dtos';
import { useLibraryItemPermissions } from '../library/useLibraryItemPermissions';

function makeItem(overrides: Partial<LibraryItem> = {}): LibraryItem {
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

function policy(overrides: Partial<AccessPolicy> = {}): AccessPolicy {
  return {
    visibility: 'private',
    grants: [],
    updatedAt: null,
    updatedBy: null,
    ...overrides,
  };
}

describe('useLibraryItemPermissions', () => {
  it('normalizes role and grants admins full selected-item permissions', () => {
    const selectedItem = makeItem({
      access: policy({ visibility: 'private' }),
      ownerId: 'other-user',
    });

    const { result } = renderHook(() =>
      useLibraryItemPermissions({
        selectedItem,
        userId: 'admin-user',
        userRole: ' ADMIN ',
      }),
    );

    expect(result.current.normalizedRole).toBe('admin');
    expect(result.current.isAdmin).toBe(true);
    expect(result.current.selectedPermissions).toEqual({
      canView: true,
      canEdit: true,
      canExport: true,
    });
  });

  it('lets owners edit private entries and keeps export tied to view permission', () => {
    const selectedItem = makeItem({
      access: policy({ visibility: 'private' }),
      ownerId: 'owner-1',
    });

    const { result } = renderHook(() =>
      useLibraryItemPermissions({
        selectedItem,
        userId: 'owner-1',
        userRole: 'member',
      }),
    );

    expect(result.current.isAdmin).toBe(false);
    expect(result.current.selectedPermissions).toEqual({
      canView: true,
      canEdit: true,
      canExport: true,
    });
  });

  it('allows public viewing for viewers while denying edit', () => {
    const item = makeItem({
      access: policy({ visibility: 'public' }),
      ownerId: 'other-user',
    });

    const { result } = renderHook(() =>
      useLibraryItemPermissions({
        selectedItem: null,
        userId: 'viewer-1',
        userRole: 'standard_user',
      }),
    );

    expect(result.current.normalizedRole).toBe('viewer');
    expect(result.current.selectedPermissions).toBeNull();
    expect(result.current.resolveItemPermissions(item)).toEqual({
      canView: true,
      canEdit: false,
      canExport: true,
    });
  });

  it('respects explicit user and role grants on private entries', () => {
    const item = makeItem({
      access: policy({
        visibility: 'private',
        grants: [
          {
            subjectType: 'role',
            subjectId: 'editor',
            permissions: ['view'],
            grantedAt: null,
            grantedBy: null,
          },
          {
            subjectType: 'user',
            subjectId: 'user-2',
            permissions: ['edit'],
            grantedAt: null,
            grantedBy: null,
          },
        ],
      }),
      ownerId: 'owner-1',
    });

    const roleGrant = renderHook(() =>
      useLibraryItemPermissions({
        selectedItem: item,
        userId: 'user-1',
        userRole: 'editor',
      }),
    );
    expect(roleGrant.result.current.selectedPermissions).toEqual({
      canView: true,
      canEdit: false,
      canExport: true,
    });

    const userGrant = renderHook(() =>
      useLibraryItemPermissions({
        selectedItem: item,
        userId: 'user-2',
        userRole: 'member',
      }),
    );
    expect(userGrant.result.current.selectedPermissions).toEqual({
      canView: true,
      canEdit: true,
      canExport: true,
    });
  });

  it('denies private entries without owner or grant evidence', () => {
    const item = makeItem({
      access: policy({ visibility: 'private' }),
      ownerId: 'owner-1',
    });

    const { result } = renderHook(() =>
      useLibraryItemPermissions({
        selectedItem: item,
        userId: 'user-1',
        userRole: null,
      }),
    );

    expect(result.current.selectedPermissions).toEqual({
      canView: false,
      canEdit: false,
      canExport: false,
    });
  });
});
