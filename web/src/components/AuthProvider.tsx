import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  changePassword as changePasswordRequest,
  fetchSessionStatus,
  login as loginRequest,
  loginWithOAuth as loginWithOAuthRequest,
  logout as logoutRequest,
  setAuthContext,
  setAuthToken,
  setUnauthorizedHandler
} from '../api/client';
import type {
  LoginRequestPayload,
  OAuthLoginRequestPayload,
  PasswordChangeRequestPayload,
  SessionStatusResponse
} from '../api/dtos';

interface AuthContextValue {
  session: SessionStatusResponse | null;
  isLoading: boolean;
  logoutReason: string | null;
  login: (username: string, password: string) => Promise<SessionStatusResponse>;
  loginWithOAuth: (payload: OAuthLoginRequestPayload) => Promise<SessionStatusResponse>;
  logout: () => Promise<void>;
  updatePassword: (currentPassword: string, newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY = 'ebook-tools.auth.token';

function persistToken(token: string | null): void {
  if (typeof window === 'undefined') {
    return;
  }
  if (token) {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ token }));
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}

function readPersistedToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as { token?: string | null };
    return parsed.token ?? null;
  } catch (error) {
    console.warn('Unable to parse persisted auth token', error);
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<SessionStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [logoutReason, setLogoutReason] = useState<string | null>(null);

  const clearSession = useCallback(() => {
    setSession(null);
    setAuthToken(null);
    setAuthContext(null);
    persistToken(null);
  }, []);

  const handleUnauthorized = useCallback(() => {
    clearSession();
    setLogoutReason('Your session has expired. Please sign in again.');
  }, [clearSession]);

  useEffect(() => {
    return setUnauthorizedHandler(() => {
      handleUnauthorized();
    });
  }, [handleUnauthorized]);

  useEffect(() => {
    let isMounted = true;
    const token = readPersistedToken();
    if (!token) {
      setIsLoading(false);
      return;
    }
    setAuthToken(token);
    fetchSessionStatus()
      .then((response) => {
        if (!isMounted) {
          return;
        }
        setSession(response);
        setAuthToken(response.token);
        setAuthContext(response.user);
        persistToken(response.token);
        setLogoutReason(null);
      })
      .catch((error) => {
        console.warn('Unable to restore session', error);
        if (isMounted) {
          handleUnauthorized();
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [handleUnauthorized]);

  const applySession = useCallback((response: SessionStatusResponse) => {
    setSession(response);
    setAuthToken(response.token);
    setAuthContext(response.user);
    persistToken(response.token);
    setLogoutReason(null);
  }, []);

  const login = useCallback(
    async (username: string, password: string) => {
      const payload: LoginRequestPayload = { username, password };
      const response = await loginRequest(payload);
      applySession(response);
      return response;
    },
    [applySession]
  );

  const loginWithOAuth = useCallback(
    async (payload: OAuthLoginRequestPayload) => {
      const response = await loginWithOAuthRequest(payload);
      applySession(response);
      return response;
    },
    [applySession]
  );

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch (error) {
      console.warn('Failed to log out cleanly', error);
    } finally {
      clearSession();
      setLogoutReason(null);
    }
  }, [clearSession]);

  const updatePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    const payload: PasswordChangeRequestPayload = {
      current_password: currentPassword,
      new_password: newPassword
    };
    await changePasswordRequest(payload);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ session, isLoading, logoutReason, login, loginWithOAuth, logout, updatePassword }),
    [isLoading, login, loginWithOAuth, logout, logoutReason, session, updatePassword]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
