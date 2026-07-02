import { useCallback, useMemo } from 'react';
import type { LibraryItem } from '../../api/dtos';
import type { LibraryItemPermissions } from '../../components/library-list/libraryListActions';
import { canAccessPolicy, normalizeRole } from '../../utils/accessControl';

export type UseLibraryItemPermissionsInput = {
  selectedItem: LibraryItem | null;
  userId: string | null;
  userRole: string | null;
};

export type UseLibraryItemPermissionsResult = {
  normalizedRole: string | null;
  isAdmin: boolean;
  selectedPermissions: LibraryItemPermissions | null;
  resolveItemPermissions: (item: LibraryItem) => LibraryItemPermissions;
};

export function useLibraryItemPermissions({
  selectedItem,
  userId,
  userRole,
}: UseLibraryItemPermissionsInput): UseLibraryItemPermissionsResult {
  const normalizedRole = useMemo(() => normalizeRole(userRole), [userRole]);
  const isAdmin = normalizedRole === 'admin';

  const resolveItemPermissions = useCallback(
    (item: LibraryItem): LibraryItemPermissions => {
      const ownerId = item.ownerId ?? null;
      const defaultVisibility = 'public';
      const canView = canAccessPolicy(item.access ?? null, {
        ownerId,
        userId,
        userRole: normalizedRole,
        permission: 'view',
        defaultVisibility,
      });
      const canEdit = canAccessPolicy(item.access ?? null, {
        ownerId,
        userId,
        userRole: normalizedRole,
        permission: 'edit',
        defaultVisibility,
      });
      return { canView, canEdit, canExport: canView };
    },
    [normalizedRole, userId],
  );

  const selectedPermissions = useMemo(
    () => (selectedItem ? resolveItemPermissions(selectedItem) : null),
    [resolveItemPermissions, selectedItem],
  );

  return {
    normalizedRole,
    isAdmin,
    selectedPermissions,
    resolveItemPermissions,
  };
}
