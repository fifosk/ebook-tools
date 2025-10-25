import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import {
  activateUserAccount,
  createUser,
  deleteUserAccount,
  listUsers,
  resetUserPassword,
  suspendUserAccount
} from '../../api/client';
import type { ManagedUser, UserAccountStatus } from '../../api/dtos';

interface UserManagementPanelProps {
  currentUser: string;
}

type RoleOption = 'admin' | 'standard_user';

type CreateUserFormState = {
  username: string;
  password: string;
  role: RoleOption;
};

type RefreshMode = 'initial' | 'subsequent';

function resolveAccountStatus(user: ManagedUser): UserAccountStatus {
  if (user.status === 'inactive' || user.status === 'suspended' || user.status === 'active') {
    return user.status;
  }
  if (typeof user.is_suspended === 'boolean') {
    return user.is_suspended ? 'suspended' : 'active';
  }
  if (user.is_active === false) {
    return 'inactive';
  }
  const metadataSuspended = user.metadata?.suspended ?? user.metadata?.is_suspended;
  if (typeof metadataSuspended === 'boolean') {
    return metadataSuspended ? 'suspended' : 'active';
  }
  if (typeof metadataSuspended === 'string') {
    const normalised = metadataSuspended.trim().toLowerCase();
    if (normalised === 'true') {
      return 'suspended';
    }
    if (normalised === 'false') {
      return 'active';
    }
  }
  return 'active';
}

function resolveLastLogin(user: ManagedUser): string | null {
  if (typeof user.last_login === 'string' && user.last_login) {
    return user.last_login;
  }
  const metadataLogin = user.metadata?.last_login;
  if (typeof metadataLogin === 'string' && metadataLogin) {
    return metadataLogin;
  }
  return null;
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return 'Never';
  }
  try {
    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toLocaleString();
    }
  } catch (error) {
    console.warn('Unable to parse timestamp value', value, error);
  }
  return value;
}

export default function UserManagementPanel({ currentUser }: UserManagementPanelProps) {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [pendingUser, setPendingUser] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [formState, setFormState] = useState<CreateUserFormState>({
    username: '',
    password: '',
    role: 'standard_user'
  });

  const refreshUsers = useCallback(async (mode: RefreshMode = 'subsequent') => {
    if (mode === 'initial') {
      setIsLoading(true);
    } else {
      setIsRefreshing(true);
    }
    setError(null);
    try {
      const payload = await listUsers();
      const sorted = [...payload].sort((left, right) =>
        left.username.localeCompare(right.username, undefined, { sensitivity: 'base' })
      );
      setUsers(sorted);
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load users. Please try again.';
      setError(message);
    } finally {
      if (mode === 'initial') {
        setIsLoading(false);
      } else {
        setIsRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    void refreshUsers('initial');
  }, [refreshUsers]);

  const sortedUsers = useMemo(() => {
    return [...users].sort((left, right) =>
      left.username.localeCompare(right.username, undefined, { sensitivity: 'base' })
    );
  }, [users]);

  const resetForm = useCallback(() => {
    setFormState({ username: '', password: '', role: 'standard_user' });
  }, []);

  const handleCreateUser = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const username = formState.username.trim();
      const password = formState.password;
      if (!username || !password) {
        setError('Username and password are required to create a user.');
        return;
      }
      setIsCreating(true);
      setError(null);
      setFeedback(null);
      try {
        await createUser({ username, password, roles: [formState.role] });
        setFeedback(`Created user '${username}'.`);
        resetForm();
        await refreshUsers();
      } catch (requestError) {
        const message =
          requestError instanceof Error
            ? requestError.message
            : 'Unable to create user. Please try again.';
        setError(message);
      } finally {
        setIsCreating(false);
      }
    },
    [formState, refreshUsers, resetForm]
  );

  const runUserAction = useCallback(
    async (username: string, action: () => Promise<string>) => {
      setPendingUser(username);
      setError(null);
      setFeedback(null);
      try {
        const message = await action();
        setFeedback(message);
        await refreshUsers();
      } catch (requestError) {
        const message =
          requestError instanceof Error
            ? requestError.message
            : 'Unable to complete the requested action.';
        setError(message);
      } finally {
        setPendingUser(null);
      }
    },
    [refreshUsers]
  );

  const handleToggleSuspension = useCallback(
    async (user: ManagedUser) => {
      const status = resolveAccountStatus(user);
      const shouldActivate = status === 'suspended';
      const confirmationMessage = shouldActivate
        ? `Activate ${user.username}? They will regain access immediately.`
        : `Suspend ${user.username}? They will be prevented from logging in.`;
      const confirmed = window.confirm(confirmationMessage);
      if (!confirmed) {
        return;
      }
      await runUserAction(user.username, async () => {
        if (shouldActivate) {
          await activateUserAccount(user.username);
          return `Reactivated '${user.username}'.`;
        }
        await suspendUserAccount(user.username);
        return `Suspended '${user.username}'.`;
      });
    },
    [runUserAction]
  );

  const handleDeleteUser = useCallback(
    async (user: ManagedUser) => {
      const confirmed = window.confirm(
        `Delete ${user.username}? This action cannot be undone and will remove their stored sessions.`
      );
      if (!confirmed) {
        return;
      }
      await runUserAction(user.username, async () => {
        await deleteUserAccount(user.username);
        return `Deleted '${user.username}'.`;
      });
    },
    [runUserAction]
  );

  const handlePasswordReset = useCallback(
    async (user: ManagedUser) => {
      const nextPassword = window.prompt(
        `Enter a new password for ${user.username}. They will be asked to use this on their next login.`
      );
      if (!nextPassword) {
        return;
      }
      await runUserAction(user.username, async () => {
        await resetUserPassword(user.username, { password: nextPassword });
        return `Password reset for '${user.username}'.`;
      });
    },
    [runUserAction]
  );

  const isBusy = isCreating || isRefreshing;

  return (
    <div className="user-management">
      <section className="user-management__card">
        <h2>Create a new user</h2>
        <p className="user-management__description">
          Provide a username, a temporary password, and assign the initial role. Users can update their
          password after signing in.
        </p>
        <form className="user-management__form" onSubmit={handleCreateUser}>
          <label className="user-management__field">
            <span className="user-management__label">Username</span>
            <input
              type="text"
              name="username"
              autoComplete="off"
              value={formState.username}
              onChange={(event) =>
                setFormState((previous) => ({ ...previous, username: event.target.value }))
              }
              disabled={isCreating}
              required
            />
          </label>
          <label className="user-management__field">
            <span className="user-management__label">Temporary password</span>
            <input
              type="password"
              name="password"
              autoComplete="new-password"
              value={formState.password}
              onChange={(event) =>
                setFormState((previous) => ({ ...previous, password: event.target.value }))
              }
              disabled={isCreating}
              required
            />
          </label>
          <label className="user-management__field">
            <span className="user-management__label">Role</span>
            <select
              name="role"
              value={formState.role}
              onChange={(event) =>
                setFormState((previous) => ({ ...previous, role: event.target.value as RoleOption }))
              }
              disabled={isCreating}
            >
              <option value="standard_user">Standard user</option>
              <option value="admin">Administrator</option>
            </select>
          </label>
          <div className="user-management__actions">
            <button type="submit" className="user-management__primary" disabled={isCreating}>
              {isCreating ? 'Creating…' : 'Create user'}
            </button>
            <button
              type="button"
              className="user-management__secondary"
              onClick={resetForm}
              disabled={isCreating}
            >
              Clear form
            </button>
          </div>
        </form>
      </section>

      <section className="user-management__card">
        <div className="user-management__header">
          <div>
            <h2>User accounts</h2>
            <p className="user-management__description">
              Manage account access, reset passwords, and control who can use the dashboard.
            </p>
          </div>
          <button
            type="button"
            className="user-management__secondary"
            onClick={() => {
              void refreshUsers();
            }}
            disabled={isRefreshing}
          >
            {isRefreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
        {error ? (
          <div className="user-management__alert" role="alert">
            {error}
          </div>
        ) : null}
        {feedback ? (
          <div className="user-management__notice" role="status">
            {feedback}
          </div>
        ) : null}
        {isLoading ? (
          <div className="user-management__empty">Loading users…</div>
        ) : sortedUsers.length === 0 ? (
          <div className="user-management__empty">No users registered yet.</div>
        ) : (
          <div className="user-management__table-wrapper">
            <table className="user-management__table">
              <thead>
                <tr>
                  <th scope="col">Username</th>
                  <th scope="col">Role</th>
                  <th scope="col">Status</th>
                  <th scope="col">Last login</th>
                  <th scope="col" className="user-management__actions-column">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedUsers.map((user) => {
                  const status = resolveAccountStatus(user);
                  const lastLogin = formatTimestamp(resolveLastLogin(user));
                  const isCurrentUser = user.username === currentUser;
                  const disableDangerous = pendingUser === user.username || isBusy;
                  const disableSelfManagement = disableDangerous || isCurrentUser;
                  return (
                    <tr key={user.username}>
                      <th scope="row">{user.username}</th>
                      <td>{user.roles.join(', ') || '—'}</td>
                      <td>
                        <span
                          className={`user-management__status user-management__status--${status}`}
                        >
                          {status === 'suspended'
                            ? 'Suspended'
                            : status === 'inactive'
                            ? 'Inactive'
                            : 'Active'}
                        </span>
                      </td>
                      <td>{lastLogin}</td>
                      <td>
                        <div className="user-management__row-actions">
                          <button
                            type="button"
                            className="user-management__secondary"
                            onClick={() => {
                              void handlePasswordReset(user);
                            }}
                            disabled={pendingUser === user.username || isBusy}
                          >
                            Reset password
                          </button>
                          <button
                            type="button"
                            className="user-management__secondary"
                            onClick={() => {
                              void handleToggleSuspension(user);
                            }}
                            disabled={disableSelfManagement}
                          >
                            {status === 'suspended' ? 'Activate' : 'Suspend'}
                          </button>
                          <button
                            type="button"
                            className="user-management__danger"
                            onClick={() => {
                              void handleDeleteUser(user);
                            }}
                            disabled={disableSelfManagement}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
