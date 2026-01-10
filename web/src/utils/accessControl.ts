import type { AccessGrant, AccessPermission, AccessPolicy, AccessVisibility } from '../api/dtos';

const ALLOWED_PERMISSIONS = new Set<AccessPermission>(['view', 'edit']);
const ALLOWED_VISIBILITY = new Set<AccessVisibility>(['private', 'public']);

type ResolveOptions = {
  defaultVisibility?: AccessVisibility;
};

type AccessCheckOptions = {
  ownerId?: string | null;
  userId?: string | null;
  userRole?: string | null;
  permission: AccessPermission;
  defaultVisibility?: AccessVisibility;
};

export function normalizeRole(role?: string | null): string | null {
  if (!role) {
    return null;
  }
  const normalized = role.trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  if (normalized === 'standard_user') {
    return 'viewer';
  }
  return normalized;
}

function normalizePermissions(entries: AccessPermission[] | string[] | null | undefined): AccessPermission[] {
  if (!Array.isArray(entries)) {
    return [];
  }
  const normalized = entries
    .map((entry) => (typeof entry === 'string' ? entry.trim().toLowerCase() : ''))
    .filter((entry): entry is AccessPermission => ALLOWED_PERMISSIONS.has(entry as AccessPermission));
  if (normalized.includes('edit') && !normalized.includes('view')) {
    normalized.push('view');
  }
  return Array.from(new Set(normalized)).sort((left, right) => (left === 'view' ? -1 : right === 'view' ? 1 : 0));
}

function normalizeGrant(grant: AccessGrant): AccessGrant {
  return {
    subjectType: grant.subjectType,
    subjectId: grant.subjectId.trim(),
    permissions: normalizePermissions(grant.permissions),
    grantedBy: grant.grantedBy ?? null,
    grantedAt: grant.grantedAt ?? null
  };
}

export function resolveAccessPolicy(
  policy: AccessPolicy | null | undefined,
  { defaultVisibility = 'private' }: ResolveOptions = {}
): AccessPolicy {
  const visibility =
    policy && ALLOWED_VISIBILITY.has(policy.visibility) ? policy.visibility : defaultVisibility;
  const grants = Array.isArray(policy?.grants)
    ? policy!.grants.map(normalizeGrant).filter((grant) => grant.subjectId && grant.permissions.length > 0)
    : [];
  return {
    visibility,
    grants,
    updatedBy: policy?.updatedBy ?? null,
    updatedAt: policy?.updatedAt ?? null
  };
}

export function canAccessPolicy(policy: AccessPolicy | null | undefined, options: AccessCheckOptions): boolean {
  const normalizedRole = normalizeRole(options.userRole);
  const permission = options.permission;
  if (!ALLOWED_PERMISSIONS.has(permission)) {
    return false;
  }

  if (normalizedRole === 'admin') {
    return true;
  }

  if (permission === 'edit' && normalizedRole === 'viewer') {
    return false;
  }

  const ownerId = options.ownerId ?? null;
  const userId = options.userId ?? null;
  if (ownerId && userId && ownerId === userId) {
    return true;
  }

  const resolvedPolicy = resolveAccessPolicy(policy, {
    defaultVisibility: options.defaultVisibility ?? 'private'
  });

  if (permission === 'view' && resolvedPolicy.visibility === 'public') {
    return true;
  }

  if (!userId && !normalizedRole) {
    return false;
  }

  for (const grant of resolvedPolicy.grants) {
    if (grant.subjectType === 'user' && userId && grant.subjectId === userId) {
      if (grant.permissions.includes(permission)) {
        return true;
      }
    }
    if (grant.subjectType === 'role' && normalizedRole && grant.subjectId === normalizedRole) {
      if (grant.permissions.includes(permission)) {
        return true;
      }
    }
  }

  return false;
}

