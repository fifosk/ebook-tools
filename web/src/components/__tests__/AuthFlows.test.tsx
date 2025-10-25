import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../../App';
import { ThemeProvider } from '../ThemeProvider';
import { AuthProvider } from '../AuthProvider';

const AUTH_STORAGE_KEY = 'ebook-tools.auth.token';

function createJsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init
  });
}

function createEmptyResponse(status = 204): Response {
  return new Response(null, { status });
}

function resolvePath(input: RequestInfo | URL): string {
  const url =
    typeof input === 'string'
      ? input
      : input instanceof URL
      ? input.toString()
      : input.url;
  return new URL(url, 'http://localhost').pathname;
}

function renderWithProviders() {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <App />
      </AuthProvider>
    </ThemeProvider>
  );
}

describe('authentication flows', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('signs a user in and renders the dashboard', async () => {
    const user = userEvent.setup();
    const sessionResponse = {
      token: 'test-token',
      user: { username: 'alice', role: 'admin', last_login: '2024-03-01T12:00:00Z' }
    };

    vi.spyOn(global, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const path = resolvePath(input);
      if (path === '/auth/login') {
        return Promise.resolve(createJsonResponse(sessionResponse));
      }
      if (path === '/pipelines/jobs') {
        expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer test-token');
        return Promise.resolve(createJsonResponse({ jobs: [] }));
      }
      if (path === '/pipelines/defaults') {
        expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer test-token');
        return Promise.resolve(createJsonResponse({ config: {} }));
      }
      if (path === '/pipelines/files') {
        expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer test-token');
        return Promise.resolve(
          createJsonResponse({
            ebooks: [],
            outputs: [],
            books_root: '/ebooks',
            output_root: '/output'
          })
        );
      }
      throw new Error(`Unhandled request for ${path}`);
    });

    renderWithProviders();

    await user.type(screen.getByLabelText(/Username/i), 'alice');
    await user.type(screen.getByLabelText(/Password/i), 'secret');
    await user.click(screen.getByRole('button', { name: /Sign in/i }));

    await waitFor(() => expect(screen.getByText(/Signed in as/i)).toBeInTheDocument());
    expect(screen.getByText(/alice/)).toBeInTheDocument();
    expect(localStorage.getItem(AUTH_STORAGE_KEY)).toContain('test-token');
  });

  it('shows an error when credentials are rejected', async () => {
    const user = userEvent.setup();

    vi.spyOn(global, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const path = resolvePath(input);
      if (path === '/auth/login') {
        return Promise.resolve(new Response('Invalid credentials', { status: 401 }));
      }
      throw new Error(`Unhandled request for ${path}`);
    });

    renderWithProviders();

    await user.type(screen.getByLabelText(/Username/i), 'alice');
    await user.type(screen.getByLabelText(/Password/i), 'wrong');
    await user.click(screen.getByRole('button', { name: /Sign in/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid credentials/i);
    expect(localStorage.getItem(AUTH_STORAGE_KEY)).toBeNull();
  });

  it('logs out the current user when requested', async () => {
    const user = userEvent.setup();
    const sessionResponse = {
      token: 'test-token',
      user: { username: 'alice', role: 'admin', last_login: '2024-03-01T12:00:00Z' }
    };

    vi.spyOn(global, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const path = resolvePath(input);
      if (path === '/auth/login') {
        return Promise.resolve(createJsonResponse(sessionResponse));
      }
      if (path === '/auth/logout') {
        expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer test-token');
        return Promise.resolve(createEmptyResponse());
      }
      if (path === '/pipelines/jobs') {
        return Promise.resolve(createJsonResponse({ jobs: [] }));
      }
      if (path === '/pipelines/defaults') {
        return Promise.resolve(createJsonResponse({ config: {} }));
      }
      if (path === '/pipelines/files') {
        return Promise.resolve(
          createJsonResponse({
            ebooks: [],
            outputs: [],
            books_root: '/ebooks',
            output_root: '/output'
          })
        );
      }
      throw new Error(`Unhandled request for ${path}`);
    });

    renderWithProviders();

    await user.type(screen.getByLabelText(/Username/i), 'alice');
    await user.type(screen.getByLabelText(/Password/i), 'secret');
    await user.click(screen.getByRole('button', { name: /Sign in/i }));
    await waitFor(() => expect(screen.getByText(/Signed in as/i)).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Log out/i }));

    await waitFor(() => expect(screen.getByRole('button', { name: /Sign in/i })).toBeInTheDocument());
    expect(localStorage.getItem(AUTH_STORAGE_KEY)).toBeNull();
  });

  it('updates the password successfully', async () => {
    const user = userEvent.setup();
    const sessionResponse = {
      token: 'test-token',
      user: { username: 'alice', role: 'admin', last_login: '2024-03-01T12:00:00Z' }
    };

    vi.spyOn(global, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const path = resolvePath(input);
      if (path === '/auth/login') {
        return Promise.resolve(createJsonResponse(sessionResponse));
      }
      if (path === '/auth/password') {
        expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer test-token');
        return Promise.resolve(createEmptyResponse());
      }
      if (path === '/pipelines/jobs') {
        return Promise.resolve(createJsonResponse({ jobs: [] }));
      }
      if (path === '/pipelines/defaults') {
        return Promise.resolve(createJsonResponse({ config: {} }));
      }
      if (path === '/pipelines/files') {
        return Promise.resolve(
          createJsonResponse({
            ebooks: [],
            outputs: [],
            books_root: '/ebooks',
            output_root: '/output'
          })
        );
      }
      throw new Error(`Unhandled request for ${path}`);
    });

    renderWithProviders();

    await user.type(screen.getByLabelText(/Username/i), 'alice');
    await user.type(screen.getByLabelText(/Password/i), 'secret');
    await user.click(screen.getByRole('button', { name: /Sign in/i }));
    await waitFor(() => expect(screen.getByText(/Signed in as/i)).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Change password/i }));
    await user.type(screen.getByLabelText(/Current password/i), 'secret');
    await user.type(screen.getByLabelText(/^New password/i), 'updated');
    await user.type(screen.getByLabelText(/Confirm new password/i), 'updated');
    await user.click(screen.getByRole('button', { name: /Update password/i }));

    expect(await screen.findByText(/password updated successfully/i)).toBeInTheDocument();
  });

  it('surfaces API errors when password updates fail', async () => {
    const user = userEvent.setup();
    const sessionResponse = {
      token: 'test-token',
      user: { username: 'alice', role: 'admin', last_login: '2024-03-01T12:00:00Z' }
    };

    vi.spyOn(global, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const path = resolvePath(input);
      if (path === '/auth/login') {
        return Promise.resolve(createJsonResponse(sessionResponse));
      }
      if (path === '/auth/password') {
        expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer test-token');
        return Promise.resolve(new Response('Current password incorrect', { status: 400 }));
      }
      if (path === '/pipelines/jobs') {
        return Promise.resolve(createJsonResponse({ jobs: [] }));
      }
      if (path === '/pipelines/defaults') {
        return Promise.resolve(createJsonResponse({ config: {} }));
      }
      if (path === '/pipelines/files') {
        return Promise.resolve(
          createJsonResponse({
            ebooks: [],
            outputs: [],
            books_root: '/ebooks',
            output_root: '/output'
          })
        );
      }
      throw new Error(`Unhandled request for ${path}`);
    });

    renderWithProviders();

    await user.type(screen.getByLabelText(/Username/i), 'alice');
    await user.type(screen.getByLabelText(/Password/i), 'secret');
    await user.click(screen.getByRole('button', { name: /Sign in/i }));
    await waitFor(() => expect(screen.getByText(/Signed in as/i)).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Change password/i }));
    await user.type(screen.getByLabelText(/Current password/i), 'secret');
    await user.type(screen.getByLabelText(/^New password/i), 'updated');
    await user.type(screen.getByLabelText(/Confirm new password/i), 'updated');
    await user.click(screen.getByRole('button', { name: /Update password/i }));

    expect(await screen.findByText(/current password incorrect/i)).toBeInTheDocument();
  });

  it('allows admins to access the user management panel', async () => {
    const user = userEvent.setup();
    const sessionResponse = {
      token: 'test-token',
      user: { username: 'alice', role: 'admin', last_login: '2024-03-01T12:00:00Z' }
    };

    vi.spyOn(global, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const path = resolvePath(input);
      if (path === '/auth/login') {
        return Promise.resolve(createJsonResponse(sessionResponse));
      }
      if (path === '/pipelines/jobs') {
        return Promise.resolve(createJsonResponse({ jobs: [] }));
      }
      if (path === '/pipelines/defaults') {
        return Promise.resolve(createJsonResponse({ config: {} }));
      }
      if (path === '/pipelines/files') {
        return Promise.resolve(
          createJsonResponse({
            ebooks: [],
            outputs: [],
            books_root: '/ebooks',
            output_root: '/output'
          })
        );
      }
      if (path === '/admin/users') {
        expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer test-token');
        return Promise.resolve(createJsonResponse({ users: [] }));
      }
      throw new Error(`Unhandled request for ${path}`);
    });

    renderWithProviders();

    await user.type(screen.getByLabelText(/Username/i), 'alice');
    await user.type(screen.getByLabelText(/Password/i), 'secret');
    await user.click(screen.getByRole('button', { name: /Sign in/i }));

    await waitFor(() => expect(screen.getByText(/Signed in as/i)).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /User management/i }));

    await waitFor(() =>
      expect(screen.getByRole('heading', { level: 1, name: /User management/i })).toBeInTheDocument()
    );
    expect(screen.getByText(/No users registered yet/i)).toBeInTheDocument();
  });

  it('hides admin controls for standard users', async () => {
    const user = userEvent.setup();
    const sessionResponse = {
      token: 'test-token',
      user: { username: 'sarah', role: 'standard_user', last_login: '2024-03-01T12:00:00Z' }
    };

    vi.spyOn(global, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const path = resolvePath(input);
      if (path === '/auth/login') {
        return Promise.resolve(createJsonResponse(sessionResponse));
      }
      if (path === '/pipelines/jobs') {
        return Promise.resolve(createJsonResponse({ jobs: [] }));
      }
      if (path === '/pipelines/defaults') {
        return Promise.resolve(createJsonResponse({ config: {} }));
      }
      if (path === '/pipelines/files') {
        return Promise.resolve(
          createJsonResponse({
            ebooks: [],
            outputs: [],
            books_root: '/ebooks',
            output_root: '/output'
          })
        );
      }
      throw new Error(`Unhandled request for ${path}`);
    });

    renderWithProviders();

    await user.type(screen.getByLabelText(/Username/i), 'sarah');
    await user.type(screen.getByLabelText(/Password/i), 'secret');
    await user.click(screen.getByRole('button', { name: /Sign in/i }));

    await waitFor(() => expect(screen.getByText(/Signed in as/i)).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /User management/i })).toBeNull();
  });
});
