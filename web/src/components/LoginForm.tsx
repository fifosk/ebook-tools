import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { OAuthLoginRequestPayload } from '../api/dtos';

interface LoginFormProps {
  onSubmit: (username: string, password: string) => Promise<void>;
  onOAuthSubmit?: (payload: OAuthLoginRequestPayload) => Promise<void>;
  isSubmitting?: boolean;
  error?: string | null;
  notice?: string | null;
}

export default function LoginForm({
  onSubmit,
  onOAuthSubmit,
  isSubmitting = false,
  error,
  notice
}: LoginFormProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [oauthError, setOauthError] = useState<string | null>(null);
  const googleButtonRef = useRef<HTMLDivElement | null>(null);
  const googleInitializedRef = useRef(false);
  const appleInitializedRef = useRef(false);

  const googleClientId = useMemo(() => import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined, []);
  const appleClientId = useMemo(() => import.meta.env.VITE_APPLE_CLIENT_ID as string | undefined, []);
  const appleRedirectUri = useMemo(() => {
    if (typeof window === 'undefined') {
      return '';
    }
    return (import.meta.env.VITE_APPLE_REDIRECT_URI as string | undefined) ?? window.location.origin;
  }, []);
  const hasOAuthProviders = Boolean(googleClientId || appleClientId);

  const handleOAuthSubmit = useCallback(
    async (payload: OAuthLoginRequestPayload) => {
      if (!onOAuthSubmit) {
        setOauthError('OAuth sign-in is not configured.');
        return;
      }
      setOauthError(null);
      await onOAuthSubmit(payload);
    },
    [onOAuthSubmit]
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setOauthError(null);
    await onSubmit(username.trim(), password);
  };

  const handleGoogleCredential = useCallback(
    (response: { credential?: string }) => {
      const credential = response?.credential;
      if (!credential) {
        setOauthError('Google sign-in did not return a credential.');
        return;
      }
      void handleOAuthSubmit({ provider: 'google', id_token: credential });
    },
    [handleOAuthSubmit]
  );

  const setupGoogleButton = useCallback(() => {
    if (!googleClientId || !googleButtonRef.current) {
      return false;
    }
    const googleApi = window.google?.accounts?.id;
    if (!googleApi) {
      return false;
    }
    if (!googleInitializedRef.current) {
      googleApi.initialize({
        client_id: googleClientId,
        callback: handleGoogleCredential,
        context: 'signin',
        ux_mode: 'popup',
        auto_select: false,
        itp_support: true,
        use_fedcm_for_prompt: true
      });
      googleInitializedRef.current = true;
    }
    googleButtonRef.current.innerHTML = '';
    googleApi.renderButton(googleButtonRef.current, {
      theme: 'outline',
      size: 'large',
      text: 'continue_with',
      shape: 'pill',
      width: googleButtonRef.current.clientWidth || 360
    });
    return true;
  }, [googleClientId, handleGoogleCredential]);

  useEffect(() => {
    if (!googleClientId) {
      return;
    }
    if (setupGoogleButton()) {
      return;
    }
    let attempts = 0;
    const timer = window.setInterval(() => {
      attempts += 1;
      if (setupGoogleButton() || attempts > 20) {
        window.clearInterval(timer);
      }
    }, 250);
    return () => window.clearInterval(timer);
  }, [googleClientId, setupGoogleButton]);

  const setupApple = useCallback(() => {
    if (!appleClientId) {
      return false;
    }
    const appleAuth = window.AppleID?.auth;
    if (!appleAuth) {
      return false;
    }
    if (!appleInitializedRef.current) {
      appleAuth.init({
        clientId: appleClientId,
        scope: 'name email',
        redirectURI: appleRedirectUri,
        usePopup: true
      });
      appleInitializedRef.current = true;
    }
    return true;
  }, [appleClientId, appleRedirectUri]);

  useEffect(() => {
    if (!appleClientId) {
      return;
    }
    if (setupApple()) {
      return;
    }
    let attempts = 0;
    const timer = window.setInterval(() => {
      attempts += 1;
      if (setupApple() || attempts > 20) {
        window.clearInterval(timer);
      }
    }, 250);
    return () => window.clearInterval(timer);
  }, [appleClientId, setupApple]);

  const handleAppleClick = useCallback(async () => {
    setOauthError(null);
    if (!setupApple()) {
      setOauthError('Apple sign-in is not available yet.');
      return;
    }
    try {
      const appleAuth = window.AppleID?.auth;
      if (!appleAuth) {
        setOauthError('Apple sign-in is not available yet.');
        return;
      }
      const response = await appleAuth.signIn();
      const idToken = response?.authorization?.id_token;
      if (!idToken) {
        setOauthError('Apple sign-in did not return a token.');
        return;
      }
      const user = response?.user ?? {};
      const name = user?.name ?? {};
      await handleOAuthSubmit({
        provider: 'apple',
        id_token: idToken,
        email: typeof user?.email === 'string' ? user.email : null,
        first_name: typeof name?.firstName === 'string' ? name.firstName : null,
        last_name: typeof name?.lastName === 'string' ? name.lastName : null
      });
    } catch (err) {
      setOauthError(err instanceof Error ? err.message : 'Apple sign-in failed.');
    }
  }, [handleOAuthSubmit, setupApple]);

  const combinedError = error ?? oauthError;

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <div className="auth-form__field">
        <label htmlFor="username">Username</label>
        <input
          id="username"
          name="username"
          type="text"
          autoComplete="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          required
        />
      </div>
      <div className="auth-form__field">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
      </div>
      {combinedError ? (
        <div className="auth-form__alert" role="alert">
          {combinedError}
        </div>
      ) : null}
      {notice ? (
        <div className="auth-form__notice" role="status">
          {notice}
        </div>
      ) : null}
      <button type="submit" className="auth-form__submit" disabled={isSubmitting}>
        {isSubmitting ? 'Signing in…' : 'Sign in'}
      </button>
      {hasOAuthProviders ? (
        <>
          <div className="auth-form__divider">or continue with</div>
          <div className="auth-form__oauth">
            {appleClientId ? (
              <button
                type="button"
                className="auth-form__oauth-button auth-form__oauth-button--apple"
                onClick={handleAppleClick}
                disabled={isSubmitting}
              >
                <span className="auth-form__oauth-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" focusable="false">
                    <path d="M16.7 6.2c-1 .1-2.2.7-2.9 1.6-.7.8-1.2 2-.9 3.1 1.1.1 2.3-.6 3-1.5.6-.8 1.1-2 .8-3.2z" />
                    <path d="M20.1 19c-.5 1.1-1.2 2.1-2 3.1-.7.8-1.4 1.7-2.5 1.7-1.1 0-1.4-.6-2.6-.6-1.2 0-1.6.6-2.6.6-1 0-1.7-.9-2.5-1.8-1.7-2-3-5.5-1.2-7.9.9-1.2 2.4-2 4-2 1.1 0 2.1.7 2.6.7.5 0 1.7-.8 3-.7.5 0 1.9.1 2.9 1.4-.1.1-1.7 1-1.7 3 0 2.4 2.1 3.2 2.1 3.2z" />
                  </svg>
                </span>
                Continue with Apple
              </button>
            ) : null}
            {googleClientId ? <div ref={googleButtonRef} className="auth-form__oauth-google" /> : null}
          </div>
        </>
      ) : null}
    </form>
  );
}
