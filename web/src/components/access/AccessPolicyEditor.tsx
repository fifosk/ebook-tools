import { useCallback, useEffect, useId, useMemo, useState } from 'react';
import type {
  AccessGrant,
  AccessPermission,
  AccessPolicy,
  AccessPolicyUpdatePayload,
  AccessSubjectType,
  AccessVisibility
} from '../../api/dtos';
import { resolveAccessPolicy } from '../../utils/accessControl';
import styles from './AccessPolicyEditor.module.css';

type GrantDraft = AccessGrant;

type Props = {
  policy: AccessPolicy | null | undefined;
  ownerId?: string | null;
  defaultVisibility?: AccessVisibility;
  canEdit?: boolean;
  onSave?: (payload: AccessPolicyUpdatePayload) => Promise<void>;
  title?: string;
};

const ROLE_SUGGESTIONS = ['viewer', 'editor', 'admin'];

const sortPermissions = (permissions: AccessPermission[]) =>
  [...permissions].sort((left, right) => (left === 'view' ? -1 : right === 'view' ? 1 : 0));

const normalizePermissions = (permissions: AccessPermission[]) => {
  const unique = Array.from(new Set(permissions));
  if (unique.includes('edit') && !unique.includes('view')) {
    unique.push('view');
  }
  return sortPermissions(unique);
};

const normalizeGrant = (grant: GrantDraft): GrantDraft => ({
  subjectType: grant.subjectType,
  subjectId: grant.subjectId.trim(),
  permissions: normalizePermissions(grant.permissions ?? []),
  grantedBy: grant.grantedBy ?? null,
  grantedAt: grant.grantedAt ?? null
});

const emptyGrant = (): GrantDraft => ({
  subjectType: 'user',
  subjectId: '',
  permissions: ['view']
});

const serializePolicy = (visibility: AccessVisibility, grants: GrantDraft[]) => {
  const cleaned = grants
    .map(normalizeGrant)
    .filter((grant) => grant.subjectId && grant.permissions.length > 0)
    .sort((left, right) => {
      if (left.subjectType !== right.subjectType) {
        return left.subjectType.localeCompare(right.subjectType);
      }
      return left.subjectId.localeCompare(right.subjectId);
    })
    .map((grant) => ({
      subjectType: grant.subjectType,
      subjectId: grant.subjectId,
      permissions: sortPermissions(grant.permissions)
    }));
  return JSON.stringify({ visibility, grants: cleaned });
};

export default function AccessPolicyEditor({
  policy,
  ownerId,
  defaultVisibility = 'private',
  canEdit = false,
  onSave,
  title = 'Access control'
}: Props) {
  const roleListId = useId();
  const resolvedPolicy = useMemo(
    () => resolveAccessPolicy(policy, { defaultVisibility }),
    [defaultVisibility, policy]
  );
  const [visibility, setVisibility] = useState<AccessVisibility>(resolvedPolicy.visibility);
  const [grants, setGrants] = useState<GrantDraft[]>(resolvedPolicy.grants.map(normalizeGrant));
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setVisibility(resolvedPolicy.visibility);
    setGrants(resolvedPolicy.grants.map(normalizeGrant));
    setError(null);
    setNotice(null);
  }, [resolvedPolicy]);

  const handleVisibilityChange = useCallback((value: AccessVisibility) => {
    setVisibility(value);
    setNotice(null);
  }, []);

  const handleGrantChange = useCallback(
    (index: number, next: Partial<GrantDraft>) => {
      setGrants((previous) => {
        const updated = [...previous];
        const current = updated[index];
        if (!current) {
          return previous;
        }
        const subjectType = (next.subjectType ?? current.subjectType) as AccessSubjectType;
        const subjectId =
          next.subjectId !== undefined
            ? next.subjectId
            : subjectType === 'role' && !current.subjectId
              ? 'viewer'
              : current.subjectId;
        const permissions = next.permissions ?? current.permissions;
        updated[index] = normalizeGrant({
          ...current,
          ...next,
          subjectType,
          subjectId,
          permissions
        });
        return updated;
      });
      setNotice(null);
    },
    []
  );

  const handlePermissionToggle = useCallback(
    (index: number, permission: AccessPermission, checked: boolean) => {
      const target = grants[index];
      if (!target) {
        return;
      }
      let nextPermissions = [...target.permissions];
      if (checked) {
        nextPermissions.push(permission);
      } else {
        nextPermissions = nextPermissions.filter((entry) => entry !== permission);
        if (permission === 'view') {
          nextPermissions = nextPermissions.filter((entry) => entry !== 'edit');
        }
      }
      handleGrantChange(index, { permissions: nextPermissions });
    },
    [grants, handleGrantChange]
  );

  const handleAddGrant = useCallback(() => {
    setGrants((previous) => [...previous, emptyGrant()]);
    setNotice(null);
  }, []);

  const handleRemoveGrant = useCallback((index: number) => {
    setGrants((previous) => previous.filter((_, currentIndex) => currentIndex !== index));
    setNotice(null);
  }, []);

  const hasChanges = useMemo(() => {
    return (
      serializePolicy(visibility, grants) !==
      serializePolicy(resolvedPolicy.visibility, resolvedPolicy.grants)
    );
  }, [grants, resolvedPolicy, visibility]);

  const handleReset = useCallback(() => {
    setVisibility(resolvedPolicy.visibility);
    setGrants(resolvedPolicy.grants.map(normalizeGrant));
    setError(null);
    setNotice(null);
  }, [resolvedPolicy]);

  const handleSave = useCallback(async () => {
    if (!onSave || !canEdit || isSaving) {
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      const filteredGrants = grants
        .map(normalizeGrant)
        .filter((grant) => grant.subjectId && grant.permissions.length > 0)
        .map((grant) => ({
          subjectType: grant.subjectType,
          subjectId: grant.subjectId,
          permissions: grant.permissions
        }));
      await onSave({ visibility, grants: filteredGrants });
      setNotice('Access updated.');
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : 'Unable to update access.';
      setError(message);
    } finally {
      setIsSaving(false);
    }
  }, [canEdit, grants, isSaving, onSave, visibility]);

  return (
    <section className={styles.editor} aria-live="polite">
      <div className={styles.header}>
        <div>
          <h4 className={styles.title}>{title}</h4>
          <div className={styles.meta}>
            {ownerId ? (
              <span className={styles.metaItem}>
                <span className={styles.metaLabel}>Owner</span>
                <span>{ownerId}</span>
              </span>
            ) : null}
            {resolvedPolicy.updatedAt ? (
              <span className={styles.metaItem}>
                <span className={styles.metaLabel}>Updated</span>
                <span>{resolvedPolicy.updatedAt}</span>
              </span>
            ) : null}
            {resolvedPolicy.updatedBy ? (
              <span className={styles.metaItem}>
                <span className={styles.metaLabel}>By</span>
                <span>{resolvedPolicy.updatedBy}</span>
              </span>
            ) : null}
          </div>
        </div>
        <div className={styles.visibilityGroup}>
          <label className={styles.fieldLabel} htmlFor={`${roleListId}-visibility`}>
            Visibility
          </label>
          <select
            id={`${roleListId}-visibility`}
            className={styles.select}
            value={visibility}
            onChange={(event) => handleVisibilityChange(event.target.value as AccessVisibility)}
            disabled={!canEdit}
          >
            <option value="private">Private</option>
            <option value="public">Public</option>
          </select>
        </div>
      </div>

      <div className={styles.grants}>
        <div className={styles.sectionHeader}>
          <span>Grants</span>
          {canEdit ? (
            <button type="button" className={styles.linkButton} onClick={handleAddGrant}>
              + Add grant
            </button>
          ) : null}
        </div>
        {grants.length === 0 ? (
          <p className={styles.emptyState}>
            No explicit grants. {visibility === 'public' ? 'Anyone can view.' : 'Only the owner can view.'}
          </p>
        ) : (
          <div className={styles.grantList}>
            {grants.map((grant, index) => (
              <div key={`${grant.subjectType}-${grant.subjectId}-${index}`} className={styles.grantRow}>
                <select
                  className={styles.select}
                  value={grant.subjectType}
                  onChange={(event) =>
                    handleGrantChange(index, { subjectType: event.target.value as AccessSubjectType })
                  }
                  disabled={!canEdit}
                >
                  <option value="user">User</option>
                  <option value="role">Role</option>
                </select>
                <div className={styles.subjectField}>
                  <input
                    type="text"
                    className={styles.input}
                    placeholder={grant.subjectType === 'role' ? 'Role (viewer/editor/admin)' : 'Username'}
                    value={grant.subjectId}
                    onChange={(event) => handleGrantChange(index, { subjectId: event.target.value })}
                    list={grant.subjectType === 'role' ? roleListId : undefined}
                    disabled={!canEdit}
                  />
                  {grant.subjectType === 'role' ? (
                    <datalist id={roleListId}>
                      {ROLE_SUGGESTIONS.map((role) => (
                        <option key={role} value={role} />
                      ))}
                    </datalist>
                  ) : null}
                </div>
                <div className={styles.permissions}>
                  <label className={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      checked={grant.permissions.includes('view')}
                      onChange={(event) => handlePermissionToggle(index, 'view', event.target.checked)}
                      disabled={!canEdit}
                    />
                    View
                  </label>
                  <label className={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      checked={grant.permissions.includes('edit')}
                      onChange={(event) => handlePermissionToggle(index, 'edit', event.target.checked)}
                      disabled={!canEdit}
                    />
                    Edit
                  </label>
                </div>
                {canEdit ? (
                  <button
                    type="button"
                    className={styles.removeButton}
                    onClick={() => handleRemoveGrant(index)}
                  >
                    Remove
                  </button>
                ) : null}
                {grant.grantedAt || grant.grantedBy ? (
                  <div className={styles.grantMeta}>
                    {grant.grantedAt ? <span>Granted {grant.grantedAt}</span> : null}
                    {grant.grantedBy ? <span>by {grant.grantedBy}</span> : null}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>

      {error ? <div className={styles.error}>{error}</div> : null}
      {notice ? <div className={styles.notice}>{notice}</div> : null}
      {canEdit && onSave ? (
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={handleReset}
            disabled={!hasChanges || isSaving}
          >
            Reset
          </button>
          <button
            type="button"
            className={styles.primaryButton}
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
          >
            {isSaving ? 'Saving…' : 'Save access'}
          </button>
        </div>
      ) : (
        <div className={styles.noticeMuted}>You have view-only access.</div>
      )}
    </section>
  );
}

