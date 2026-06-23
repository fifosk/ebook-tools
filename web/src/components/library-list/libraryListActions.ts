import type { LibraryItem } from '../../api/dtos';

export type LibraryItemPermissions = {
  canView: boolean;
  canEdit: boolean;
  canExport: boolean;
};

export type LibraryItemPermissionResolver = (item: LibraryItem) => LibraryItemPermissions;

export type LibraryItemActionState = {
  canView: boolean;
  canEdit: boolean;
  canExport: boolean;
  isMutating: boolean;
  isExportReady: boolean;
  mediaOpenDisabled: boolean;
  editDisabled: boolean;
  exportDisabled: boolean;
  removeDisabled: boolean;
  exportTitle: string;
};

export const DEFAULT_LIBRARY_ITEM_PERMISSIONS: LibraryItemPermissions = {
  canView: true,
  canEdit: true,
  canExport: true
};

export function resolveLibraryItemPermissions(
  item: LibraryItem,
  resolvePermissions?: LibraryItemPermissionResolver,
): LibraryItemPermissions {
  if (!resolvePermissions) {
    return DEFAULT_LIBRARY_ITEM_PERMISSIONS;
  }
  const resolved = resolvePermissions(item);
  return {
    canView: Boolean(resolved.canView),
    canEdit: Boolean(resolved.canEdit),
    canExport: Boolean(resolved.canExport)
  };
}

export function buildLibraryItemActionState(
  item: LibraryItem,
  permissions: LibraryItemPermissions,
  isMutating: boolean,
): LibraryItemActionState {
  const canView = permissions.canView;
  const canEdit = permissions.canEdit;
  const canExport = permissions.canExport && canView;
  const isExportReady = item.mediaCompleted;
  return {
    canView,
    canEdit,
    canExport,
    isMutating,
    isExportReady,
    mediaOpenDisabled: isMutating || !canView,
    editDisabled: isMutating || !canEdit,
    exportDisabled: isMutating || !isExportReady || !canExport,
    removeDisabled: isMutating || !canEdit,
    exportTitle: isExportReady ? 'Export offline player' : 'Export available after media completes'
  };
}
