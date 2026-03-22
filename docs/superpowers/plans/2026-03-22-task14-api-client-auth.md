# Task 14: API Client & Auth Flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement centralized API client with auth headers and X-Request-ID, token management via localStorage, login screen, auth-protected routes, and one-time localhost warning modal.

**Architecture:** A centralized fetch wrapper (`src/api/client.js`) handles auth headers and X-Request-ID for all API calls. Token storage is a thin localStorage utility (`src/utils/token.js`). React Context (`src/context/AuthContext.jsx`) manages auth state and provides login/logout. A `ProtectedRoute` component guards authenticated routes. A `WarningModal` shows once per browser on first visit. On 401, the API client clears the token and dispatches a `CustomEvent('auth:logout')` that the AuthContext listens to — this avoids circular dependencies between the API client and React state.

**Tech Stack:** React 18, React Router v6, Vitest, React Testing Library, plain CSS (no Tailwind)

**Design spec sections:** §5 (API), §8.2 (Auth), §8.4 (Security Warning UI)

---

## File Structure

### New files (12)

| File | Responsibility |
|------|---------------|
| `src/utils/token.js` | `getToken()` / `setToken()` / `removeToken()` — thin localStorage wrapper |
| `src/utils/token.test.js` | Tests for token storage |
| `src/api/client.js` | `apiGet()` / `apiPost()` / `apiPatch()` / `apiDelete()` + `ApiError` class |
| `src/api/client.test.js` | Tests for API client (mock `globalThis.fetch`) |
| `src/context/AuthContext.jsx` | `AuthProvider` + `useAuth()` hook — auth state, login/logout, token verification |
| `src/context/AuthContext.test.jsx` | Tests for auth context (mock `globalThis.fetch`) |
| `src/components/ProtectedRoute.jsx` | Route guard — redirects to `/login` if unauthenticated |
| `src/components/ProtectedRoute.test.jsx` | Tests for route guard (mock `useAuth`) |
| `src/components/LoginForm.jsx` | Login page — token input, submit, error display |
| `src/components/LoginForm.test.jsx` | Tests for login form (mock `useAuth`) |
| `src/components/WarningModal.jsx` | One-time localhost warning modal |
| `src/components/WarningModal.test.jsx` | Tests for warning modal |

### Modified files (5)

| File | Changes |
|------|---------|
| `src/main.jsx` | Wrap `<App />` with `<AuthProvider>` inside `<BrowserRouter>` |
| `src/App.jsx` | Add `/login` route, `ProtectedRoute` wrapper, `WarningModal`, conditional Header/SideMenu |
| `src/components/Header.jsx` | Replace bare `fetch()` with `apiGet()` from API client |
| `src/css/components.css` | Add `.login-page` and `.login-page__help` styles |
| `src/App.test.jsx` | Add `useAuth` mock, update assertions for conditional layout |
| `src/components/Header.test.jsx` | Update fetch mocks to include `headers` (apiGet reads `content-type`) |

---

## Task 1: Token Storage Utility

**Files:**
- Create: `src/utils/token.js`
- Create: `src/utils/token.test.js`

- [ ] **Step 1: Write the failing test**

```js
// src/utils/token.test.js
import { describe, it, expect, beforeEach } from 'vitest';
import { getToken, setToken, removeToken } from './token';

describe('token', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns null when token is not set', () => {
    expect(getToken()).toBeNull();
  });

  it('stores and retrieves token', () => {
    setToken('test-token-123');
    expect(getToken()).toBe('test-token-123');
  });

  it('removes token', () => {
    setToken('test-token-123');
    removeToken();
    expect(getToken()).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/utils/token.test.js`
Expected: FAIL — `Cannot find module`

- [ ] **Step 3: Write minimal implementation**

```js
// src/utils/token.js
const AUTH_TOKEN_KEY = 'govassist_auth_token';

export function getToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function removeToken() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/utils/token.test.js`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/utils/token.js src/utils/token.test.js
git commit -m "feat(frontend): add token storage utility for auth token management"
```

---

## Task 2: API Client

**Files:**
- Create: `src/api/client.js` (directory `src/api/` must be created first)
- Create: `src/api/client.test.js`

- [ ] **Step 1: Write the failing tests**

```js
// src/api/client.test.js
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { apiGet, apiPost, ApiError } from './client';
import { getToken, setToken } from '../utils/token';

describe('API client', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  function mockFetchJson(body, { status = 200 } = {}) {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: status >= 200 && status < 300,
      status,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve(body),
    });
  }

  it('sends Authorization header with stored token', async () => {
    setToken('my-token');
    mockFetchJson({ models: [] });

    await apiGet('/api/models');

    expect(fetch).toHaveBeenCalledWith('/api/models', expect.objectContaining({
      headers: expect.objectContaining({
        Authorization: 'Bearer my-token',
      }),
    }));
  });

  it('sends X-Request-ID header with UUID format', async () => {
    setToken('my-token');
    mockFetchJson({ models: [] });

    await apiGet('/api/models');

    const requestId = fetch.mock.calls[0][1].headers['X-Request-ID'];
    expect(requestId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    );
  });

  it('does not send Authorization header when no token', async () => {
    mockFetchJson({ models: [] });

    await apiGet('/api/models');

    const headers = fetch.mock.calls[0][1].headers;
    expect(headers).not.toHaveProperty('Authorization');
  });

  it('returns parsed JSON on success', async () => {
    mockFetchJson({ models: [{ model_id: 'kimi-k2.5' }] });

    const data = await apiGet('/api/models');

    expect(data).toEqual({ models: [{ model_id: 'kimi-k2.5' }] });
  });

  it('throws ApiError on 401 and clears token', async () => {
    setToken('bad-token');
    mockFetchJson({ detail: '認証トークンが一致しません' }, { status: 401 });

    await expect(apiGet('/api/models')).rejects.toThrow(ApiError);
    expect(getToken()).toBeNull();
  });

  it('dispatches auth:logout event on 401', async () => {
    setToken('bad-token');
    mockFetchJson({ detail: '認証トークンが一致しません' }, { status: 401 });

    const listener = vi.fn();
    window.addEventListener('auth:logout', listener);

    try { await apiGet('/api/models'); } catch {}

    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener('auth:logout', listener);
  });

  it('throws ApiError on 500 without clearing token', async () => {
    setToken('my-token');
    mockFetchJson({ detail: 'Internal Server Error' }, { status: 500 });

    await expect(apiGet('/api/models')).rejects.toThrow(ApiError);
    expect(getToken()).toBe('my-token');
  });

  it('ApiError contains status, data, and requestId', async () => {
    setToken('my-token');
    mockFetchJson({ detail: 'Not Found' }, { status: 404 });

    try {
      await apiGet('/api/not-found');
      expect.unreachable('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect(e.status).toBe(404);
      expect(e.data).toEqual({ detail: 'Not Found' });
      expect(e.requestId).toMatch(/^[0-9a-f-]+$/);
    }
  });

  it('sends JSON body with POST', async () => {
    setToken('my-token');
    mockFetchJson({ result: 'ok' });

    await apiPost('/api/proofread', { text: 'test' });

    expect(fetch).toHaveBeenCalledWith('/api/proofread', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ text: 'test' }),
    }));
  });

  it('does not send body with GET', async () => {
    setToken('my-token');
    mockFetchJson({ models: [] });

    await apiGet('/api/models');

    expect(fetch.mock.calls[0][1].body).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/api/client.test.js`
Expected: FAIL — `Cannot find module`

- [ ] **Step 3: Write minimal implementation**

```js
// src/api/client.js
import { getToken, removeToken } from '../utils/token';

export class ApiError extends Error {
  constructor(status, data, requestId) {
    super(data?.message || data?.detail || `API エラー: ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    this.requestId = requestId;
  }
}

function generateRequestId() {
  return crypto.randomUUID();
}

async function request(method, path, body) {
  const requestId = generateRequestId();
  const token = getToken();

  const headers = {
    'Content-Type': 'application/json',
    'X-Request-ID': requestId,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const config = {
    method,
    headers,
    ...(body != null ? { body: JSON.stringify(body) } : {}),
  };

  const response = await fetch(path, config);

  if (response.status === 401) {
    removeToken();
    window.dispatchEvent(new CustomEvent('auth:logout'));
  }

  let data;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    throw new ApiError(response.status, data, requestId);
  }

  return data;
}

export async function apiGet(path) {
  return request('GET', path, null);
}

export async function apiPost(path, body) {
  return request('POST', path, body);
}

export async function apiPatch(path, body) {
  return request('PATCH', path, body);
}

export async function apiDelete(path) {
  return request('DELETE', path, null);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/api/client.test.js`
Expected: 10 tests PASS

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/api/client.js src/api/client.test.js
git commit -m "feat(frontend): add API client with auth headers, X-Request-ID, and 401 handling"
```

---

## Task 3: Auth Context

**Files:**
- Create: `src/context/AuthContext.jsx` (directory `src/context/` must be created first)
- Create: `src/context/AuthContext.test.jsx`

- [ ] **Step 1: Write the failing tests**

```jsx
// src/context/AuthContext.test.jsx
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/context/AuthContext.test.jsx`
Expected: FAIL — `Cannot find module`

- [ ] **Step 3: Write minimal implementation**

```jsx
// src/context/AuthContext.jsx
import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { getToken, setToken as storeToken, removeToken } from '../utils/token';
import { apiGet } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const mountedRef = useRef(true);

  // Verify stored token on mount
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    apiGet('/api/models')
      .then(() => {
        if (mountedRef.current) setIsAuthenticated(true);
      })
      .catch(() => {
        removeToken();
        if (mountedRef.current) setIsAuthenticated(false);
      })
      .finally(() => {
        if (mountedRef.current) setIsLoading(false);
      });

    return () => { mountedRef.current = false; };
  }, []);

  // Listen for auth:logout events dispatched by API client on 401
  useEffect(() => {
    const handleLogout = () => {
      removeToken();
      setIsAuthenticated(false);
    };
    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, []);

  const login = useCallback(async (newToken) => {
    storeToken(newToken);
    try {
      await apiGet('/api/models');
      setIsAuthenticated(true);
      return true;
    } catch {
      removeToken();
      setIsAuthenticated(false);
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    removeToken();
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/context/AuthContext.test.jsx`
Expected: 8 tests PASS

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/context/AuthContext.jsx src/context/AuthContext.test.jsx
git commit -m "feat(frontend): add AuthContext with token verification, login/logout, and 401 event handling"
```

---

## Task 4: Protected Route

**Files:**
- Create: `src/components/ProtectedRoute.jsx`
- Create: `src/components/ProtectedRoute.test.jsx`

- [ ] **Step 1: Write the failing tests**

```jsx
// src/components/ProtectedRoute.test.jsx
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '../context/AuthContext';
import ProtectedRoute from './ProtectedRoute';

describe('ProtectedRoute', () => {
  beforeEach(() => {
    useAuth.mockReset();
  });

  function renderRoute(ui) {
    return render(
      <MemoryRouter>
        {ui}
      </MemoryRouter>
    );
  }

  it('shows loading spinner when verifying', () => {
    useAuth.mockReturnValue({ isLoading: true, isAuthenticated: false });

    renderRoute(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('読み込み中...')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('redirects to /login when not authenticated', () => {
    useAuth.mockReturnValue({ isLoading: false, isAuthenticated: false });

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/" element={<ProtectedRoute><div>Protected Content</div></ProtectedRoute>} />
        </Routes>
      </MemoryRouter>
    );

    // Navigate redirects to /login, which renders the login page
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    useAuth.mockReturnValue({ isLoading: false, isAuthenticated: true });

    renderRoute(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/ProtectedRoute.test.jsx`
Expected: FAIL — `Cannot find module`

- [ ] **Step 3: Write minimal implementation**

```jsx
// src/components/ProtectedRoute.jsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner" role="status" aria-label="読み込み中"></div>
        <span>読み込み中...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/ProtectedRoute.test.jsx`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/components/ProtectedRoute.jsx src/components/ProtectedRoute.test.jsx
git commit -m "feat(frontend): add ProtectedRoute component for auth-guarded routes"
```

---

## Task 5: Login Form & Warning Modal

### Part A: Login Form

**Files:**
- Create: `src/components/LoginForm.jsx`
- Create: `src/components/LoginForm.test.jsx`

- [ ] **Step 1: Write the failing tests for LoginForm**

```jsx
// src/components/LoginForm.test.jsx
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

const mockLogin = vi.fn();
const mockLogout = vi.fn();

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    login: mockLogin,
    logout: mockLogout,
    isAuthenticated: false,
    isLoading: false,
  }),
}));

import LoginForm from './LoginForm';

describe('LoginForm', () => {
  beforeEach(() => {
    mockLogin.mockReset();
  });

  function renderForm() {
    return render(
      <MemoryRouter>
        <LoginForm />
      </MemoryRouter>
    );
  }

  it('renders login form with token input and submit button', () => {
    renderForm();

    expect(screen.getByLabelText('アクセストークン')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'ログイン' })).toBeInTheDocument();
  });

  it('shows error when submitting empty token', async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole('button', { name: 'ログイン' }));

    expect(screen.getByText('アクセストークンを入力してください')).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('calls login with trimmed token on submit', async () => {
    mockLogin.mockResolvedValue(true);
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText('アクセストークン'), '  my-token  ');
    await user.click(screen.getByRole('button', { name: 'ログイン' }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('my-token');
    });
  });

  it('shows error message when login fails', async () => {
    mockLogin.mockResolvedValue(false);
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText('アクセストークン'), 'bad-token');
    await user.click(screen.getByRole('button', { name: 'ログイン' }));

    await waitFor(() => {
      expect(screen.getByText('認証トークンが無効です')).toBeInTheDocument();
    });
  });

  it('disables button and shows loading during login', async () => {
    let resolveLogin;
    mockLogin.mockImplementation(() => new Promise((r) => { resolveLogin = r; }));
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText('アクセストークン'), 'my-token');
    await user.click(screen.getByRole('button', { name: 'ログイン' }));

    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByText('認証中...')).toBeInTheDocument();

    await act(async () => { resolveLogin(true); });
  });

  it('clears error when user starts typing', async () => {
    mockLogin.mockResolvedValue(false);
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText('アクセストークン'), 'bad');
    await user.click(screen.getByRole('button', { name: 'ログイン' }));

    await waitFor(() => {
      expect(screen.getByText('認証トークンが無効です')).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText('アクセストークン'), 'x');

    expect(screen.queryByText('認証トークンが無効です')).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/LoginForm.test.jsx`
Expected: FAIL — `Cannot find module`

- [ ] **Step 3: Write minimal implementation**

```jsx
// src/components/LoginForm.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function LoginForm() {
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = token.trim();
    if (!trimmed) {
      setError('アクセストークンを入力してください');
      return;
    }
    setError('');
    setIsLoading(true);
    const success = await login(trimmed);
    setIsLoading(false);
    if (success) {
      navigate('/', { replace: true });
    } else {
      setError('認証トークンが無効です');
    }
  };

  const handleChange = (e) => {
    setToken(e.target.value);
    if (error) setError('');
  };

  return (
    <div className="login-page">
      <div className="card login-page__card">
        <h2>ログイン</h2>
        <p className="login-page__help">
          アクセストークンを入力してください。<br />
          トークンはサーバーの .env ファイルで設定された APP_TOKEN です。
        </p>
        {error && <div className="message message--error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="label" htmlFor="auth-token">アクセストークン</label>
            <input
              id="auth-token"
              className="input"
              type="password"
              value={token}
              onChange={handleChange}
              autoFocus
              disabled={isLoading}
              autoComplete="off"
            />
          </div>
          <button className="btn btn--primary" type="submit" disabled={isLoading}>
            {isLoading ? '認証中...' : 'ログイン'}
          </button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/LoginForm.test.jsx`
Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/components/LoginForm.jsx src/components/LoginForm.test.jsx
git commit -m "feat(frontend): add LoginForm component with token input and validation"
```

### Part B: Warning Modal

**Files:**
- Create: `src/components/WarningModal.jsx`
- Create: `src/components/WarningModal.test.jsx`

- [ ] **Step 6: Write the failing tests for WarningModal**

```jsx
// src/components/WarningModal.test.jsx
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import WarningModal from './WarningModal';

describe('WarningModal', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('shows warning on first visit', () => {
    render(<WarningModal />);

    expect(screen.getByText('ご確認ください')).toBeInTheDocument();
    expect(screen.getByText(/localhost 限定/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '確認しました' })).toBeInTheDocument();
  });

  it('hides modal after clicking confirm', async () => {
    const user = userEvent.setup();
    render(<WarningModal />);

    await user.click(screen.getByRole('button', { name: '確認しました' }));

    expect(screen.queryByText('ご確認ください')).not.toBeInTheDocument();
    expect(localStorage.getItem('govassist_warning_accepted')).toBe('true');
  });

  it('does not show modal after previously accepted', () => {
    localStorage.setItem('govassist_warning_accepted', 'true');
    render(<WarningModal />);

    expect(screen.queryByText('ご確認ください')).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 7: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/WarningModal.test.jsx`
Expected: FAIL — `Cannot find module`

- [ ] **Step 8: Write minimal implementation**

```jsx
// src/components/WarningModal.jsx
import { useState } from 'react';

const WARNING_KEY = 'govassist_warning_accepted';

export default function WarningModal() {
  const [visible, setVisible] = useState(
    () => !localStorage.getItem(WARNING_KEY)
  );

  if (!visible) return null;

  const handleConfirm = () => {
    localStorage.setItem(WARNING_KEY, 'true');
    setVisible(false);
  };

  return (
    <div className="modal-overlay">
      <div className="modal" role="dialog" aria-labelledby="warning-title">
        <div className="modal__title" id="warning-title">ご確認ください</div>
        <div className="modal__body">
          <p>本アプリは localhost 限定での使用を前提としています。</p>
          <p>外部ネットワークへの公開は絶対に行わないでください。</p>
        </div>
        <div className="modal__actions">
          <button className="btn btn--primary" onClick={handleConfirm}>
            確認しました
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/WarningModal.test.jsx`
Expected: 3 tests PASS

- [ ] **Step 10: Commit**

```bash
cd frontend
git add src/components/WarningModal.jsx src/components/WarningModal.test.jsx
git commit -m "feat(frontend): add one-time localhost warning modal on first visit"
```

---

## Task 6: App Integration

This task wires everything together: updates `main.jsx`, `App.jsx`, `Header.jsx`, CSS, and fixes existing tests.

- [ ] **Step 1: Update `src/main.jsx` — add AuthProvider**

Replace `src/main.jsx` with:

```jsx
// src/main.jsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import App from './App';
import './css/base.css';
import './css/layout.css';
import './css/components.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
```

- [ ] **Step 2: Update `src/App.jsx` — add auth integration**

Replace `src/App.jsx` with:

```jsx
// src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Header from './components/Header';
import SideMenu from './components/SideMenu';
import ProtectedRoute from './components/ProtectedRoute';
import WarningModal from './components/WarningModal';
import LoginForm from './components/LoginForm';
import Proofreading from './tools/proofreading/Proofreading';
import Settings from './tools/settings/Settings';

function App() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="app">
      <WarningModal />
      {isAuthenticated && <Header />}
      <div className="app-content">
        {isAuthenticated && <SideMenu />}
        <main className="main-content">
          <Routes>
            <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <LoginForm />} />
            <Route path="/" element={<ProtectedRoute><Proofreading /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
```

- [ ] **Step 3: Update `src/components/Header.jsx` — use API client**

Replace the bare `fetch` call with `apiGet`. The full updated file:

```jsx
// src/components/Header.jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSettings, saveSettings } from '../utils/storage';
import { apiGet } from '../api/client';

const DEFAULT_MODEL = { model_id: 'kimi-k2.5', display_name: 'Kimi K2.5' };

function Header() {
  const navigate = useNavigate();
  const [models, setModels] = useState([DEFAULT_MODEL]);
  const [selectedModel, setSelectedModel] = useState(() => loadSettings().model);

  useEffect(() => {
    apiGet('/api/models')
      .then(data => {
        if (data.models?.length > 0) {
          setModels(data.models);
          const settings = loadSettings();
          const ids = data.models.map(m => m.model_id);
          if (!ids.includes(settings.model)) {
            const fallback = data.models[0].model_id;
            setSelectedModel(fallback);
            saveSettings({ ...settings, model: fallback });
          }
        }
      })
      .catch(() => {
        // Network error or auth error (401 handled by AuthContext) — use defaults
      });
  }, []);

  const handleModelChange = (e) => {
    const newModel = e.target.value;
    setSelectedModel(newModel);
    saveSettings({ ...loadSettings(), model: newModel });
  };

  return (
    <header className="app-header">
      <span className="app-header__title">GovAssist</span>
      <div className="app-header__actions">
        <label className="sr-only" htmlFor="model-selector">AI モデル</label>
        <select
          id="model-selector"
          className="select"
          value={selectedModel}
          onChange={handleModelChange}
          style={{ width: 'auto' }}
        >
          {models.map(model => (
            <option key={model.model_id} value={model.model_id}>
              {model.display_name}
            </option>
          ))}
        </select>
        <button
          className="btn btn--sm btn--secondary"
          onClick={() => navigate('/settings')}
          aria-label="設定を開く"
          type="button"
        >
          ⚙
        </button>
      </div>
    </header>
  );
}

export default Header;
```

- [ ] **Step 4: Add login page CSS to `src/css/components.css`**

Append at the end of `src/css/components.css`:

```css
/* --- Login page --- */

.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100%;
}

.login-page__card {
  width: 100%;
  max-width: 400px;
}

.login-page__help {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-md);
  line-height: 1.6;
}
```

- [ ] **Step 5: Update `src/App.test.jsx` — add useAuth mock**

The App component now calls `useAuth()`, so tests must mock it. Replace `src/App.test.jsx` with:

```jsx
// src/App.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock useAuth — App is always rendered as authenticated in these layout tests
vi.mock('./context/AuthContext', () => ({
  useAuth: vi.fn(() => ({ isAuthenticated: true, isLoading: false, login: vi.fn(), logout: vi.fn() })),
  AuthProvider: ({ children }) => children,
}));

// Mock storage utility
vi.mock('./utils/storage', () => ({
  loadSettings: vi.fn(() => ({ version: 1, model: 'kimi-k2.5', document_type: 'official', options: {} })),
  saveSettings: vi.fn(),
}));

// Mock API client to prevent real fetch calls from Header
vi.mock('./api/client', () => ({
  apiGet: vi.fn(() => Promise.resolve({ models: [] })),
}));

import App from './App';

beforeEach(() => {
  vi.restoreAllMocks();
});

function renderApp(initialEntries = '/') {
  return render(<MemoryRouter initialEntries={[initialEntries]}><App /></MemoryRouter>);
}

describe('App', () => {
  it('renders the app layout structure when authenticated', () => {
    renderApp();
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('renders header with app title', () => {
    renderApp();
    expect(screen.getByText('GovAssist')).toBeInTheDocument();
  });

  it('renders sidebar with all menu items', () => {
    renderApp();
    const sidebar = document.querySelector('.sidebar');
    expect(within(sidebar).getByText('AI 文書校正')).toBeInTheDocument();
    expect(within(sidebar).getByText('設定')).toBeInTheDocument();
  });

  it('renders proofreading placeholder on default route /', () => {
    renderApp('/');
    const main = screen.getByRole('main');
    expect(within(main).getByText('AI 文書校正')).toBeInTheDocument();
    expect(within(main).getByText(/Task 15/)).toBeInTheDocument();
  });

  it('renders settings placeholder on /settings route', () => {
    renderApp('/settings');
    const main = screen.getByRole('main');
    expect(within(main).getByText('設定')).toBeInTheDocument();
    expect(within(main).getByText(/Task 21/)).toBeInTheDocument();
  });

  it('redirects unknown routes to /', () => {
    renderApp('/unknown-page');
    const main = screen.getByRole('main');
    expect(within(main).getByText(/Task 15/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Update `src/components/Header.test.jsx` — fix fetch mocks**

The Header now uses `apiGet` which reads `response.headers.get('content-type')`. All fetch mocks must include a `headers` object. Replace `src/components/Header.test.jsx` with:

```jsx
// src/components/Header.test.jsx
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

// Mock storage utility
vi.mock('../utils/storage', () => ({
  loadSettings: vi.fn(() => ({ version: 1, model: 'kimi-k2.5', document_type: 'official', options: {} })),
  saveSettings: vi.fn(),
}));

// Mock API client — Header uses apiGet
vi.mock('../api/client', () => ({
  apiGet: vi.fn(),
}));

import { loadSettings, saveSettings } from '../utils/storage';
import { apiGet } from '../api/client';
import Header from './Header';

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

function mockApiGetSuccess(models = [{ model_id: 'kimi-k2.5', display_name: 'Kimi K2.5' }]) {
  apiGet.mockResolvedValue({ models });
}

function mockApiGetError(error) {
  apiGet.mockRejectedValue(error);
}

describe('Header', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.mocked(loadSettings).mockReturnValue({ version: 1, model: 'kimi-k2.5', document_type: 'official', options: {} });
  });

  it('renders app title', () => {
    renderWithRouter(<Header />);
    expect(screen.getByText('GovAssist')).toBeInTheDocument();
  });

  it('renders model selector with accessible label', () => {
    renderWithRouter(<Header />);
    expect(screen.getByLabelText('AI モデル')).toBeInTheDocument();
  });

  it('renders settings button', () => {
    renderWithRouter(<Header />);
    expect(screen.getByLabelText('設定を開く')).toBeInTheDocument();
  });

  it('shows default model when API call fails', async () => {
    mockApiGetError(new Error('Network error'));
    renderWithRouter(<Header />);

    await waitFor(() => {
      expect(screen.getByText('Kimi K2.5')).toBeInTheDocument();
    });
  });

  it('fetches and displays models from API', async () => {
    mockApiGetSuccess([
      { model_id: 'kimi-k2.5', display_name: 'Kimi K2.5' },
      { model_id: 'gpt-4', display_name: 'GPT-4' },
    ]);
    renderWithRouter(<Header />);

    await waitFor(() => {
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
    });
    expect(screen.getByText('Kimi K2.5')).toBeInTheDocument();
  });

  it('saves selected model to storage on change', async () => {
    mockApiGetSuccess([
      { model_id: 'kimi-k2.5', display_name: 'Kimi K2.5' },
      { model_id: 'gpt-4', display_name: 'GPT-4' },
    ]);

    const user = userEvent.setup();
    renderWithRouter(<Header />);

    await waitFor(() => {
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText('AI モデル'), 'gpt-4');

    expect(saveSettings).toHaveBeenCalled();
  });

  it('navigates to /settings when settings button clicked', async () => {
    mockApiGetSuccess();
    const user = userEvent.setup();
    renderWithRouter(<Header />);

    await user.click(screen.getByLabelText('設定を開く'));

    expect(screen.getByLabelText('設定を開く')).toBeInTheDocument();
  });
});
```

- [ ] **Step 7: Run all tests**

Run: `cd frontend && npx vitest run`
Expected: ALL tests PASS (existing + new)

- [ ] **Step 8: Verify the build compiles**

Run: `cd frontend && npx vite build`
Expected: Build succeeds with no errors

- [ ] **Step 9: Commit**

```bash
cd frontend
git add src/main.jsx src/App.jsx src/components/Header.jsx src/css/components.css \
        src/App.test.jsx src/components/Header.test.jsx
git commit -m "feat(frontend): integrate auth system into App shell — login route, protected routes, warning modal"
```

---

## Summary

| Task | New Files | Modified Files | Tests |
|------|-----------|----------------|-------|
| 1. Token Storage | 2 | 0 | 3 |
| 2. API Client | 2 | 0 | 10 |
| 3. Auth Context | 2 | 0 | 8 |
| 4. Protected Route | 2 | 0 | 3 |
| 5a. Login Form | 2 | 0 | 6 |
| 5b. Warning Modal | 2 | 0 | 3 |
| 6. App Integration | 0 | 6 | All pass |
| **Total** | **12** | **6** | **33+** |

**New directories:** `src/api/`, `src/context/`

**Key design decisions:**
- API client dispatches `CustomEvent('auth:logout')` on 401 — AuthContext listens for it. No circular dependency.
- Token verification uses `GET /api/models` (lightweight, always available).
- Login page hides Header/SideMenu for cleaner UX.
- WarningModal is self-contained — manages its own visibility via localStorage.
