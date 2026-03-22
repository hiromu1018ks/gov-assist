import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';

function AuthStateViewer() {
  const { isAuthenticated, isLoading } = useAuth();
  return (
    <div data-testid="auth-state">
      {JSON.stringify({ authenticated: isAuthenticated, loading: isLoading })}
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  function mockFetchOk(body = { models: [] }) {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve(body),
    });
  }

  function mockFetchUnauthorized() {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ detail: '認証トークンが一致しません' }),
    });
  }

  it('starts unauthenticated when no token is stored', async () => {
    mockFetchOk();

    render(
      <AuthProvider>
        <AuthStateViewer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-state')).toHaveTextContent('"loading":false');
    });
    expect(screen.getByTestId('auth-state')).toHaveTextContent('"authenticated":false');
  });

  it('verifies stored token on mount and sets authenticated', async () => {
    localStorage.setItem('govassist_auth_token', 'valid-token');
    mockFetchOk();

    render(
      <AuthProvider>
        <AuthStateViewer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-state')).toHaveTextContent('"authenticated":true');
    });
    expect(screen.getByTestId('auth-state')).toHaveTextContent('"loading":false');
  });

  it('clears invalid stored token on mount', async () => {
    localStorage.setItem('govassist_auth_token', 'invalid-token');
    mockFetchUnauthorized();

    render(
      <AuthProvider>
        <AuthStateViewer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-state')).toHaveTextContent('"loading":false');
    });
    expect(screen.getByTestId('auth-state')).toHaveTextContent('"authenticated":false');
    expect(localStorage.getItem('govassist_auth_token')).toBeNull();
  });

  it('login() stores token, verifies, and sets authenticated on success', async () => {
    mockFetchOk();

    let authRef;
    function AuthActions() {
      authRef = useAuth();
      return <AuthStateViewer />;
    }

    render(
      <AuthProvider>
        <AuthActions />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-state')).toHaveTextContent('"loading":false');
    });

    let result;
    await act(async () => {
      result = await authRef.login('new-valid-token');
    });

    expect(result).toBe(true);
    expect(localStorage.getItem('govassist_auth_token')).toBe('new-valid-token');
    expect(screen.getByTestId('auth-state')).toHaveTextContent('"authenticated":true');
  });

  it('login() returns false and clears token on failure', async () => {
    mockFetchUnauthorized();

    let authRef;
    function AuthActions() {
      authRef = useAuth();
      return <AuthStateViewer />;
    }

    render(
      <AuthProvider>
        <AuthActions />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-state')).toHaveTextContent('"loading":false');
    });

    let result;
    await act(async () => {
      result = await authRef.login('bad-token');
    });

    expect(result).toBe(false);
    expect(localStorage.getItem('govassist_auth_token')).toBeNull();
    expect(screen.getByTestId('auth-state')).toHaveTextContent('"authenticated":false');
  });

  it('logout() clears token and sets unauthenticated', async () => {
    localStorage.setItem('govassist_auth_token', 'valid-token');
    mockFetchOk();

    let authRef;
    function AuthActions() {
      authRef = useAuth();
      return <AuthStateViewer />;
    }

    render(
      <AuthProvider>
        <AuthActions />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-state')).toHaveTextContent('"authenticated":true');
    });

    act(() => { authRef.logout(); });

    expect(screen.getByTestId('auth-state')).toHaveTextContent('"authenticated":false');
    expect(localStorage.getItem('govassist_auth_token')).toBeNull();
  });

  it('handles auth:logout event from API client', async () => {
    localStorage.setItem('govassist_auth_token', 'valid-token');
    mockFetchOk();

    render(
      <AuthProvider>
        <AuthStateViewer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-state')).toHaveTextContent('"authenticated":true');
    });

    act(() => {
      window.dispatchEvent(new CustomEvent('auth:logout'));
    });

    expect(screen.getByTestId('auth-state')).toHaveTextContent('"authenticated":false');
    expect(localStorage.getItem('govassist_auth_token')).toBeNull();
  });

  it('useAuth throws when used outside AuthProvider', () => {
    // Suppress React error boundary console output for this test
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<AuthStateViewer />)).toThrow(
      'useAuth must be used within AuthProvider'
    );
    spy.mockRestore();
  });
});
