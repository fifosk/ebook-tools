import { useCallback } from 'react';
import type { OAuthLoginRequestPayload } from '../api/dtos';
import { useAuth } from '../components/AuthProvider';
import { useUIStore } from '../stores/uiStore';

/**
 * Hook for authentication-related handlers in the App component.
 * Encapsulates login, logout, and password change logic.
 */
export function useAppAuth() {
  const {
    session,
    isLoading: isAuthLoading,
    logoutReason,
    login,
    loginWithOAuth,
    logout,
    updatePassword
  } = useAuth();

  const {
    authError,
    isLoggingIn,
    showChangePassword,
    passwordError,
    passwordMessage,
    isUpdatingPassword,
    setAuthError,
    setIsLoggingIn,
    setShowChangePassword,
    setPasswordError,
    setPasswordMessage,
    setIsUpdatingPassword,
    isAccountExpanded,
    setAccountExpanded
  } = useUIStore();

  const isAuthenticated = Boolean(session);
  const sessionUser = session?.user ?? null;
  const sessionUsername = sessionUser?.username ?? null;

  const handleLogin = useCallback(
    async (username: string, password: string) => {
      setIsLoggingIn(true);
      setAuthError(null);
      try {
        await login(username, password);
      } catch (error) {
        setAuthError(error instanceof Error ? error.message : 'Unable to sign in.');
      } finally {
        setIsLoggingIn(false);
      }
    },
    [login, setAuthError, setIsLoggingIn]
  );

  const handleOAuthLogin = useCallback(
    async (payload: OAuthLoginRequestPayload) => {
      setIsLoggingIn(true);
      setAuthError(null);
      try {
        await loginWithOAuth(payload);
      } catch (error) {
        setAuthError(error instanceof Error ? error.message : 'Unable to sign in.');
      } finally {
        setIsLoggingIn(false);
      }
    },
    [loginWithOAuth, setAuthError, setIsLoggingIn]
  );

  const handleLogout = useCallback(async () => {
    setShowChangePassword(false);
    setPasswordError(null);
    setPasswordMessage(null);
    await logout();
  }, [logout, setPasswordError, setPasswordMessage, setShowChangePassword]);

  const handlePasswordChange = useCallback(
    async (currentPassword: string, newPassword: string) => {
      setPasswordError(null);
      setPasswordMessage(null);
      setIsUpdatingPassword(true);
      try {
        await updatePassword(currentPassword, newPassword);
        setPasswordMessage('Password updated successfully.');
        setShowChangePassword(false);
      } catch (error) {
        setPasswordError(
          error instanceof Error ? error.message : 'Unable to update password. Please try again.'
        );
      } finally {
        setIsUpdatingPassword(false);
      }
    },
    [updatePassword, setIsUpdatingPassword, setPasswordError, setPasswordMessage, setShowChangePassword]
  );

  const toggleChangePassword = useCallback(() => {
    setPasswordError(null);
    setPasswordMessage(null);
    const next = !showChangePassword;
    setShowChangePassword(next);
    if (next) {
      setAccountExpanded(true);
    }
  }, [showChangePassword, setAccountExpanded, setPasswordError, setPasswordMessage, setShowChangePassword]);

  const handlePasswordCancel = useCallback(() => {
    setShowChangePassword(false);
    setPasswordError(null);
  }, [setPasswordError, setShowChangePassword]);

  return {
    // State
    session,
    sessionUser,
    sessionUsername,
    isAuthenticated,
    isAuthLoading,
    logoutReason,
    authError,
    isLoggingIn,
    showChangePassword,
    passwordError,
    passwordMessage,
    isUpdatingPassword,
    isAccountExpanded,

    // Actions
    handleLogin,
    handleOAuthLogin,
    handleLogout,
    handlePasswordChange,
    toggleChangePassword,
    handlePasswordCancel,
    setAccountExpanded,
    setAuthError
  };
}
