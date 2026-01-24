import { useMemo } from 'react';
import ChangePasswordForm from '../ChangePasswordForm';
import ThemeControl from './ThemeControl';
import type { SessionUser } from '../../api/dtos';

interface AccountPanelProps {
  sessionUser: SessionUser | null;
  isExpanded: boolean;
  showChangePassword: boolean;
  passwordError: string | null;
  passwordMessage: string | null;
  isUpdatingPassword: boolean;
  onToggleExpand: () => void;
  onToggleChangePassword: () => void;
  onPasswordChange: (currentPassword: string, newPassword: string) => Promise<void>;
  onPasswordCancel: () => void;
  onLogout: () => void;
}

/**
 * Account panel in the sidebar showing user info, password change form, and theme control.
 */
export function AccountPanel({
  sessionUser,
  isExpanded,
  showChangePassword,
  passwordError,
  passwordMessage,
  isUpdatingPassword,
  onToggleExpand,
  onToggleChangePassword,
  onPasswordChange,
  onPasswordCancel,
  onLogout
}: AccountPanelProps) {
  const displayName = useMemo(() => {
    if (!sessionUser) {
      return { label: '', showUsernameTag: false };
    }
    const parts = [sessionUser.first_name, sessionUser.last_name]
      .map((value) => (typeof value === 'string' ? value.trim() : ''))
      .filter((value) => Boolean(value));
    const fullName = parts.length > 0 ? parts.join(' ') : null;
    const label = fullName ?? sessionUser.username;
    const showUsernameTag = Boolean(
      fullName && sessionUser.username && fullName !== sessionUser.username
    );
    return { label, showUsernameTag };
  }, [sessionUser]);

  const sessionEmail = useMemo(() => {
    if (!sessionUser?.email) {
      return null;
    }
    const trimmed = sessionUser.email.trim();
    return trimmed || null;
  }, [sessionUser]);

  const lastLoginLabel = useMemo(() => {
    if (!sessionUser?.last_login) {
      return null;
    }
    try {
      return new Date(sessionUser.last_login).toLocaleString();
    } catch (error) {
      console.warn('Unable to parse last login timestamp', error);
      return sessionUser.last_login;
    }
  }, [sessionUser]);

  return (
    <div className="sidebar__account">
      {passwordMessage ? (
        <div className="password-message" role="status">
          {passwordMessage}
        </div>
      ) : null}
      <div
        className={`session-info ${isExpanded ? 'session-info--expanded' : 'session-info--collapsed'}`}
      >
        <button
          type="button"
          className="session-info__summary"
          onClick={onToggleExpand}
          aria-expanded={isExpanded}
          aria-controls="session-info-content"
        >
          <span className="session-info__summary-text">
            <span className="session-info__user">
              Signed in as <strong>{displayName.label}</strong>
              {displayName.showUsernameTag ? (
                <span className="session-info__username">({sessionUser?.username})</span>
              ) : null}
            </span>
          </span>
          <span className="session-info__summary-icon" aria-hidden="true">
            ▾
          </span>
        </button>
        <div id="session-info-content" className="session-info__content" hidden={!isExpanded}>
          <div className="session-info__details">
            {sessionEmail ? <span className="session-info__email">{sessionEmail}</span> : null}
            <span className="session-info__meta">
              <span className="session-info__role">Role: {sessionUser?.role}</span>
              {lastLoginLabel ? (
                <span className="session-info__last-login">Last login: {lastLoginLabel}</span>
              ) : null}
            </span>
          </div>
          <div className="session-info__actions">
            <button type="button" className="session-info__button" onClick={onToggleChangePassword}>
              {showChangePassword ? 'Hide password form' : 'Change password'}
            </button>
            <button
              type="button"
              className="session-info__button session-info__button--logout"
              onClick={onLogout}
            >
              Log out
            </button>
          </div>
          {showChangePassword ? (
            <div className="session-info__password-form">
              <ChangePasswordForm
                onSubmit={onPasswordChange}
                onCancel={onPasswordCancel}
                isSubmitting={isUpdatingPassword}
                error={passwordError}
              />
            </div>
          ) : null}
          <div className="session-info__preferences">
            <ThemeControl variant="sidebar" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default AccountPanel;
