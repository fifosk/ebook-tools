import LoginForm from '../LoginForm';
import LoginServerStatus from '../LoginServerStatus';
import { API_BASE_URL } from '../../api/client';
import { APP_BRANCH } from '../../constants/appViews';
import type { OAuthLoginRequestPayload } from '../../api/dtos';

interface AuthScreenProps {
  isLoading?: boolean;
  isSubmitting: boolean;
  error: string | null;
  notice?: string | null;
  onSubmit: (username: string, password: string) => Promise<void>;
  onOAuthSubmit: (payload: OAuthLoginRequestPayload) => Promise<void>;
}

/**
 * Authentication screen displayed when the user is not logged in.
 * Shows the login form with server status indicator.
 */
export function AuthScreen({
  isLoading,
  isSubmitting,
  error,
  notice,
  onSubmit,
  onOAuthSubmit
}: AuthScreenProps) {
  if (isLoading) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <p>Checking session…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-card__header">
          <div className="auth-card__logo" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="9" />
              <path d="M3 12h18" />
              <path d="M5 7c2.2 1.4 4.7 2 7 2s4.8-.6 7-2" />
              <path d="M5 17c2.2-1.4 4.7-2 7-2s4.8.6 7 2" />
              <path d="M12 3c2.5 3 2.5 15 0 18c-2.5-3-2.5-15 0-18z" />
            </svg>
          </div>
          <h1>Language tools</h1>
          <span className="app-version" aria-label={`Version ${APP_BRANCH}`}>
            v{APP_BRANCH}
          </span>
        </div>
        <LoginServerStatus apiBaseUrl={API_BASE_URL} />
        <LoginForm
          onSubmit={onSubmit}
          onOAuthSubmit={onOAuthSubmit}
          isSubmitting={isSubmitting}
          error={error}
          notice={notice}
        />
      </div>
    </div>
  );
}

export default AuthScreen;
