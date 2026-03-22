# Auth Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Comment out all authentication code (backend + frontend) for localhost MVP, preserving it for future re-enablement.

**Architecture:** Backend auth dependency (`verify_token`) is commented out in `dependencies.py` and all 5 routers. Frontend auth guards (`ProtectedRoute`, `AuthContext` token verification, `client.js` Authorization headers) are bypassed. All commented-out code is left in-place for future restoration.

**Tech Stack:** Python / FastAPI (backend), React 18 / Vitest (frontend tests)

---

## File Map

| # | File | Action | Responsibility |
|---|------|--------|----------------|
| 1 | `backend/dependencies.py` | Modify | Comment out `get_app_token()` and `verify_token()` |
| 2 | `backend/main.py` | Modify | Comment out `verify_token, get_app_token` import |
| 3 | `backend/routers/models_router.py` | Modify | Comment out `verify_token` import and `Depends(verify_token)` |
| 4 | `backend/routers/settings.py` | Modify | Comment out `verify_token` import and 2x `Depends(verify_token)` |
| 5 | `backend/routers/proofread.py` | Modify | Comment out `verify_token` import and `Depends(verify_token)` |
| 6 | `backend/routers/history.py` | Modify | Comment out `verify_token` import and 6x `Depends(verify_token)` |
| 7 | `backend/routers/export.py` | Modify | Comment out `verify_token` import and `Depends(verify_token)` |
| 8 | `backend/.env.example` | Modify | Comment out `APP_TOKEN` line |
| 9 | `backend/tests/test_auth.py` | Modify | Add `@pytest.mark.skip` to all test classes/functions |
| 10 | `backend/tests/conftest.py` | Modify | Comment out `get_app_token` import and `dependency_overrides` |
| 11 | `frontend/src/context/AuthContext.jsx` | Modify | Hardcode `isAuthenticated: true`, comment out token verification |
| 12 | `frontend/src/components/ProtectedRoute.jsx` | Modify | Always render `children`, comment out auth checks |
| 13 | `frontend/src/App.jsx` | Modify | Remove `ProtectedRoute` wrapping and `/login` route |
| 14 | `frontend/src/api/client.js` | Modify | Comment out Authorization header and 401 handling in `request()` and `apiPostBlob()` |
| 15 | `frontend/src/context/AuthContext.test.jsx` | Modify | Add `describe.skip` |
| 16 | `frontend/src/components/ProtectedRoute.test.jsx` | Modify | Add `describe.skip` |
| 17 | `frontend/src/components/LoginForm.test.jsx` | Modify | Add `describe.skip` |
| 18 | `frontend/src/utils/token.test.js` | Modify | Add `describe.skip` |
| 19 | `frontend/src/api/client.test.js` | Modify | Skip auth-related tests only |
| 20 | `frontend/src/App.test.jsx` | Modify | Update to match new App.jsx structure |
| 21 | `docs/design.md` | Modify | Update sections 5.5, 8.2, 10 |
| 22 | `CLAUDE.md` | Modify | Annotate auth references as disabled |

---

### Task 1: Disable backend auth — dependencies.py

**Files:**
- Modify: `backend/dependencies.py`

- [ ] **Step 1: Comment out `get_app_token()` and `verify_token()`**

Replace the entire file body (after the module docstring) with commented-out versions:

```python
"""Shared FastAPI dependencies — extracted from main.py to avoid circular imports."""
import os
import hmac

from fastapi import Depends, HTTPException, Request

# --- Auth disabled for localhost MVP ---
# To re-enable: uncomment get_app_token() and verify_token() below,
# then uncomment Depends(verify_token) in all routers.
#
# def get_app_token() -> str:
#     """Retrieve the APP_TOKEN from environment."""
#     return os.getenv("APP_TOKEN", "")
#
#
# async def verify_token(request: Request, app_token: str = Depends(get_app_token)) -> str:
#     """Validate Bearer token from Authorization header.
#
#     Used as a FastAPI dependency: `Depends(verify_token)`.
#     Returns the validated token string on success.
#     Raises HTTPException on failure.
#     """
#     auth_header = request.headers.get("Authorization")
#     if not auth_header or not auth_header.startswith("Bearer "):
#         raise HTTPException(status_code=401, detail="認証トークンが不足しています")
#
#     token = auth_header[7:]  # Skip "Bearer " prefix (7 chars)
#
#     if not app_token:
#         raise HTTPException(
#             status_code=500,
#             detail="サーバー設定が不完全です（APP_TOKEN未設定）",
#         )
#
#     if not hmac.compare_digest(token, app_token):
#         raise HTTPException(status_code=401, detail="認証トークンが一致しません")
#
#     return token
```

Note: Keep `import os, import hmac, from fastapi import ...` at the top (they'll be needed on re-enable).

- [ ] **Step 2: Run backend tests to see what breaks**

Run: `cd /home/hart/Code/gov-assist/backend && python -m pytest --tb=short -q`
Expected: Many test failures because routers still import `verify_token` and `conftest.py` still imports `get_app_token`. This is expected — subsequent tasks will fix them.

- [ ] **Step 3: Commit**

```bash
git add backend/dependencies.py
git commit -m "refactor(auth): comment out verify_token and get_app_token for localhost MVP"
```

---

### Task 2: Disable backend auth — main.py

**Files:**
- Modify: `backend/main.py:11`

- [ ] **Step 1: Comment out the import**

On line 11 of `backend/main.py`, change:

```python
from dependencies import verify_token, get_app_token
```

to:

```python
# from dependencies import verify_token, get_app_token  # Auth disabled for localhost MVP
```

- [ ] **Step 2: Commit**

```bash
git add backend/main.py
git commit -m "refactor(auth): comment out verify_token import in main.py"
```

---

### Task 3: Disable backend auth — all routers

**Files:**
- Modify: `backend/routers/models_router.py:4,12`
- Modify: `backend/routers/settings.py:8,36,52`
- Modify: `backend/routers/proofread.py:7,52`
- Modify: `backend/routers/history.py:10,41,74,92,106,119,130`
- Modify: `backend/routers/export.py:9,25`

For each router, comment out the import line and every `Depends(verify_token)` parameter (including the `token: str` parameter name).

- [ ] **Step 1: models_router.py**

Line 4 — change:
```python
# from dependencies import verify_token  # Auth disabled for localhost MVP
```
Line 12 — change:
```python
async def get_models():  # token: str = Depends(verify_token)  # Auth disabled
```

- [ ] **Step 2: settings.py**

Line 8:
```python
# from dependencies import verify_token  # Auth disabled for localhost MVP
```
Line 36:
```python
async def get_settings(  # token: str = Depends(verify_token)  # Auth disabled
    db: Session = Depends(get_db),
):
```
Line 52:
```python
async def update_settings(
    payload: SettingsUpdateRequest,
    # token: str = Depends(verify_token)  # Auth disabled
    db: Session = Depends(get_db),
):
```

- [ ] **Step 3: proofread.py**

Line 7:
```python
# from dependencies import verify_token  # Auth disabled for localhost MVP
```
Line 52:
```python
async def proofread(
    payload: ProofreadRequest,
    # token: str = Depends(verify_token)  # Auth disabled
):
```

- [ ] **Step 4: history.py**

Line 10:
```python
# from dependencies import verify_token  # Auth disabled for localhost MVP
```
Lines 41, 74, 92, 106, 119, 130 — comment out `token: str = Depends(verify_token)` in each endpoint function, keeping the other parameters (like `db: Session = Depends(get_db)`) intact.

- [ ] **Step 5: export.py**

Line 9:
```python
# from dependencies import verify_token  # Auth disabled for localhost MVP
```
Line 25:
```python
async def export_docx(
    payload: ExportDocxRequest,
    # token: str = Depends(verify_token)  # Auth disabled
):
```

- [ ] **Step 6: Run backend tests**

Run: `cd /home/hart/Code/gov-assist/backend && python -m pytest --tb=short -q`
Expected: `test_auth.py` fails (imports commented-out symbols). Other tests may still fail due to `conftest.py` — fixed in next task.

- [ ] **Step 7: Commit**

```bash
git add backend/routers/
git commit -m "refactor(auth): comment out verify_token in all routers"
```

---

### Task 4: Disable backend auth — conftest.py and test_auth.py

**Files:**
- Modify: `backend/tests/conftest.py:48,58`
- Modify: `backend/tests/test_auth.py`

- [ ] **Step 1: Comment out conftest.py auth override**

Line 48 — change:
```python
    # from dependencies import get_app_token  # Auth disabled for localhost MVP
```
Line 58 — change:
```python
    # app.dependency_overrides[get_app_token] = lambda: "test-secret-token"  # Auth disabled
```

- [ ] **Step 2: Comment out imports and skip test_auth.py tests**

**Important:** The import `from dependencies import verify_token, get_app_token` (line 7) must be commented out FIRST, otherwise `ImportError` will prevent `pytestmark` from being evaluated.

Comment out line 7:
```python
# from dependencies import verify_token, get_app_token  # Auth disabled for localhost MVP
```

Then add `pytestmark` at module level to skip all tests in the file. Add after the commented-out import:

```python
pytestmark = pytest.mark.skip(reason="Auth disabled for localhost MVP")
```

Leave all test code (`_create_test_app`, test classes, etc.) as-is — pytestmark skips the entire module so the commented-out imports won't cause errors during collection.

- [ ] **Step 3: Run backend tests**

Run: `cd /home/hart/Code/gov-assist/backend && python -m pytest --tb=short -q`
Expected: All tests pass (test_auth.py tests are skipped, other tests no longer depend on auth).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/conftest.py backend/tests/test_auth.py
git commit -m "refactor(auth): skip auth tests and remove conftest token override"
```

---

### Task 5: Disable backend auth — .env.example

**Files:**
- Modify: `backend/.env.example:5-6`

- [ ] **Step 1: Comment out APP_TOKEN**

Change:
```
# Simple auth token for API access
APP_TOKEN=change-me-to-a-secure-token
```
to:
```
# Simple auth token for API access (disabled for localhost MVP)
# APP_TOKEN=change-me-to-a-secure-token
```

- [ ] **Step 2: Commit**

```bash
git add backend/.env.example
git commit -m "refactor(auth): comment out APP_TOKEN in .env.example"
```

---

### Task 6: Disable frontend auth — AuthContext.jsx

**Files:**
- Modify: `frontend/src/context/AuthContext.jsx`

- [ ] **Step 1: Hardcode isAuthenticated, comment out token verification**

Replace the `AuthProvider` component body. Keep imports, keep `login`/`logout` methods as stubs. Comment out the token verification `useEffect` and the `auth:logout` event listener `useEffect`:

```jsx
export function AuthProvider({ children }) {
  // --- Auth disabled for localhost MVP ---
  // To re-enable: uncomment the useEffect hooks below and remove hardcoded state.
  const [isAuthenticated, setIsAuthenticated] = useState(true);  // Always authenticated
  const [isLoading, setIsLoading] = useState(false);  // No loading needed
  const mountedRef = useRef(true);

  // Verify stored token on mount — disabled for localhost MVP
  // useEffect(() => {
  //   const token = getToken();
  //   if (!token) {
  //     setIsLoading(false);
  //     return;
  //   }
  //
  //   apiGet('/api/models')
  //     .then(() => {
  //       if (mountedRef.current) setIsAuthenticated(true);
  //     })
  //     .catch(() => {
  //       removeToken();
  //       if (mountedRef.current) setIsAuthenticated(false);
  //     })
  //     .finally(() => {
  //       if (mountedRef.current) setIsLoading(false);
  //     });
  //
  //   return () => { mountedRef.current = false; };
  // }, []);

  // Listen for auth:logout events — disabled for localhost MVP
  // useEffect(() => {
  //   const handleLogout = () => {
  //     removeToken();
  //     setIsAuthenticated(false);
  //   };
  //   window.addEventListener('auth:logout', handleLogout);
  //   return () => window.removeEventListener('auth:logout', handleLogout);
  // }, []);

  const login = useCallback(async (newToken) => {
    // --- Auth disabled for localhost MVP ---
    // To re-enable: uncomment below and remove the hardcoded return.
    // storeToken(newToken);
    // try {
    //   await apiGet('/api/models');
    //   setIsAuthenticated(true);
    //   return true;
    // } catch {
    //   removeToken();
    //   setIsAuthenticated(false);
    //   return false;
    // }
    return true;
  }, []);

  const logout = useCallback(() => {
    // --- Auth disabled for localhost MVP ---
    // removeToken();
    // setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
```

Keep all imports at the top (needed for re-enable). Keep `useAuth` hook unchanged.

- [ ] **Step 2: Run frontend tests**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run --reporter=verbose 2>&1 | tail -30`
Expected: `AuthContext.test.jsx` tests fail (they test the commented-out verification logic). Other tests may still pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/context/AuthContext.jsx
git commit -m "refactor(auth): bypass AuthContext token verification for localhost MVP"
```

---

### Task 7: Disable frontend auth — ProtectedRoute.jsx

**Files:**
- Modify: `frontend/src/components/ProtectedRoute.jsx`

- [ ] **Step 1: Always render children, comment out auth checks**

```jsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

// --- Auth disabled for localhost MVP ---
// To re-enable: uncomment the loading/auth checks below.
export default function ProtectedRoute({ children }) {
  // const { isAuthenticated, isLoading } = useAuth();
  //
  // if (isLoading) {
  //   return (
  //     <div className="loading">
  //       <div className="spinner" role="status" aria-label="読み込み中"></div>
  //       <span>読み込み中...</span>
  //     </div>
  //   );
  // }
  //
  // if (!isAuthenticated) {
  //   return <Navigate to="/login" replace />;
  // }

  return children;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ProtectedRoute.jsx
git commit -m "refactor(auth): bypass ProtectedRoute for localhost MVP"
```

---

### Task 8: Disable frontend auth — App.jsx

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Remove ProtectedRoute wrapping and /login route**

```jsx
// src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom';
// import { useAuth } from './context/AuthContext';  // Auth disabled for localhost MVP
import Header from './components/Header';
import SideMenu from './components/SideMenu';
// import ProtectedRoute from './components/ProtectedRoute';  // Auth disabled for localhost MVP
import WarningModal from './components/WarningModal';
// import LoginForm from './components/LoginForm';  // Auth disabled for localhost MVP
import Proofreading from './tools/proofreading/Proofreading';
import History from './tools/history/History';
import Settings from './tools/settings/Settings';

function App() {
  // --- Auth disabled for localhost MVP ---
  // To re-enable: uncomment useAuth, ProtectedRoute, LoginForm imports and
  // restore the conditional rendering and /login route below.
  // const { isAuthenticated } = useAuth();

  return (
    <div className="app">
      <WarningModal />
      <Header />
      <div className="app-content">
        <SideMenu />
        <main className="main-content">
          <Routes>
            {/* <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <LoginForm />} /> */}
            <Route path="/" element={<Proofreading />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/history" element={<History />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
```

- [ ] **Step 2: Run App.test.jsx to see failures**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run src/App.test.jsx --reporter=verbose 2>&1 | tail -20`
Expected: Tests may need adjustment because layout structure changed (no more conditional rendering, Header/SideMenu now always shown).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "refactor(auth): remove ProtectedRoute wrapping and login route from App"
```

---

### Task 9: Disable frontend auth — client.js

**Files:**
- Modify: `frontend/src/api/client.js`

- [ ] **Step 1: Comment out Authorization header and 401 handling in request()**

In the `request()` function, comment out:

Line 19 (`const token = getToken();`):
```js
  // const token = getToken();  // Auth disabled for localhost MVP
```

Line 24 (Authorization header in headers object):
```js
    // ...(token ? { Authorization: `Bearer ${token}` } : {}),  // Auth disabled
```

Lines 35-38 (401 handling):
```js
  // if (response.status === 401) {  // Auth disabled for localhost MVP
  //   removeToken();
  //   window.dispatchEvent(new CustomEvent('auth:logout'));
  // }
```

- [ ] **Step 2: Comment out same patterns in apiPostBlob()**

Line 77:
```js
  // const token = getToken();  // Auth disabled for localhost MVP
```

Line 82:
```js
    // ...(token ? { Authorization: `Bearer ${token}` } : {}),  // Auth disabled
```

Lines 91-94:
```js
  // if (response.status === 401) {  // Auth disabled for localhost MVP
  //   removeToken();
  //   window.dispatchEvent(new CustomEvent('auth:logout'));
  // }
```

Keep the `import { getToken, removeToken } from '../utils/token';` at the top (needed for re-enable).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.js
git commit -m "refactor(auth): comment out Authorization header and 401 handling in API client"
```

---

### Task 10: Skip frontend auth tests

**Files:**
- Modify: `frontend/src/context/AuthContext.test.jsx`
- Modify: `frontend/src/components/ProtectedRoute.test.jsx`
- Modify: `frontend/src/components/LoginForm.test.jsx`
- Modify: `frontend/src/utils/token.test.js`
- Modify: `frontend/src/api/client.test.js`

- [ ] **Step 1: Skip entire auth test files**

For `AuthContext.test.jsx`, `ProtectedRoute.test.jsx`, `LoginForm.test.jsx`, `token.test.js` — change the outer `describe(` to `describe.skip(`:

```js
// AuthContext.test.jsx line 14:
describe.skip('AuthContext', () => {

// ProtectedRoute.test.jsx line 13:
describe.skip('ProtectedRoute', () => {

// LoginForm.test.jsx line 20:
describe.skip('LoginForm', () => {

// token.test.js line 5:
describe.skip('token', () => {
```

- [ ] **Step 2: Skip auth-related tests in client.test.js**

In `frontend/src/api/client.test.js`, wrap the 4 auth-specific tests in a `describe.skip` block:

- `sends Authorization header with stored token`
- `does not send Authorization header when no token`
- `throws ApiError on 401 and clears token`
- `dispatches auth:logout event on 401`

Move these 4 tests into a new `describe.skip('API client auth behavior', () => { ... })` block at the top of the file, with its own `beforeEach` and `mockFetchJson` helper. Keep all other tests (X-Request-ID, JSON parsing, 500 error, ApiError properties, POST, GET, PUT, apiPostBlob) in the original `describe('API client', ...)` block.

Note: Some remaining tests use `setToken('my-token')` but this is harmless — `getToken()` is no longer called in `client.js`, so the token is simply ignored.

**Important:** The `returns blob on successful response` test in the `describe('apiPostBlob', ...)` block also asserts `Authorization: 'Bearer my-token'` in the request headers. After Task 9 comments out the Authorization header in `apiPostBlob()`, this assertion will fail. Update this test to remove the `Authorization` line from the expected headers:

```js
// In the "returns blob on successful response" test, change:
headers: expect.objectContaining({
  Authorization: 'Bearer my-token',
  'X-Request-ID': expect.any(String),
}),
// to:
headers: expect.objectContaining({
  'X-Request-ID': expect.any(String),
}),
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/context/AuthContext.test.jsx frontend/src/components/ProtectedRoute.test.jsx frontend/src/components/LoginForm.test.jsx frontend/src/utils/token.test.js frontend/src/api/client.test.js
git commit -m "test(auth): skip auth-related frontend tests for localhost MVP"
```

---

### Task 11: Update App.test.jsx for new structure

**Files:**
- Modify: `frontend/src/App.test.jsx`

- [ ] **Step 1: Remove unused AuthProvider mock**

`App.jsx` no longer imports `AuthProvider`, so the mock on line 9 is unnecessary. Remove the `AuthProvider` line from the mock:

Change:
```jsx
vi.mock('./context/AuthContext', () => ({
  useAuth: vi.fn(() => ({ isAuthenticated: true, isLoading: false, login: vi.fn(), logout: vi.fn() })),
  AuthProvider: ({ children }) => children,
}));
```
to:
```jsx
vi.mock('./context/AuthContext', () => ({
  useAuth: vi.fn(() => ({ isAuthenticated: true, isLoading: false, login: vi.fn(), logout: vi.fn() })),
}));
```

- [ ] **Step 2: Run all frontend tests**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run --reporter=verbose 2>&1 | tail -30`
Expected: All non-skipped tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.test.jsx
git commit -m "test(auth): update App.test.jsx for auth-disabled structure"
```

---

### Task 12: Update design.md

**Files:**
- Modify: `docs/design.md:599,677-695,764`

- [ ] **Step 1: Update section 5.5 error response table (line 599)**

Change:
```
| 401 | `unauthorized` | 認証トークン不一致 |
```
to:
```
| 401 | `unauthorized` | 認証トークン不一致（MVP では認証無効。再有効化時に使用） |
```

- [ ] **Step 2: Update section 8.2 (lines 677-695)**

Replace the entire section 8.2 content with:

```markdown
### 8.2 認証

**MVP では認証なし（localhost 専用）**

MVP（ローカル環境での個人利用）では認証を無効化している。コードはコメントアウトで残されており、将来 Web 公開時に再有効化可能。

> **⚠️ 認証は無効化されています。本アプリは localhost 限定での使用を前提としています。**

| 項目 | 仕様 |
|------|------|
| 認証状態 | MVP では無効（コードはコメントアウトで保留） |
| 再有効化 | `docs/superpowers/specs/2026-03-22-auth-removal-design.md` の再有効化手順を参照 |
| **Origin チェック** | サーバー側でも `Origin` ヘッダーを検証し、許可リスト外のオリジンからのリクエストを拒否する。**これはセキュリティ対策ではなく誤操作防止**（curl 等の直接リクエストは防げない）として位置付ける。 |
| **XSS 対策** | React コンポーネント内で dangerouslySetInnerHTML の使用を禁止する。diff 表示・テキストレンダリングはすべて React の通常のデータバインディング（JSX）で行い、HTML を直接挿入しない。 |
| **起動時警告** | フロントエンド初回起動時に「本アプリは localhost 限定での使用を前提としています。外部ネットワークへの公開は絶対に行わないでください。」をモーダルで表示し、確認ボタンで閉じる。 |
```

- [ ] **Step 3: Update section 10 security row (line 764)**

Change:
```
| セキュリティ | API キーはバックエンド管理。CORS localhost 限定。簡易トークン認証（ローカル限定用途）。 |
```
to:
```
| セキュリティ | API キーはバックエンド管理。CORS localhost 限定。MVP では認証無効（再有効化可能）。 |
```

- [ ] **Step 4: Commit**

```bash
git add docs/design.md
git commit -m "docs: update design.md auth sections for localhost MVP"
```

---

### Task 13: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md:28,70,76,96`

- [ ] **Step 1: Annotate auth references**

Line 28 — change:
```
├── main.py                  # App factory (create_app()), auth dependency (disabled for MVP), CORS, OriginCheckMiddleware, logging
```

Line 70 — change:
```
Auth: **Disabled for localhost MVP.** Code preserved in comments. See `docs/superpowers/specs/2026-03-22-auth-removal-design.md` for re-enablement.
```

Line 76 — change:
```
- **Auth dependency `verify_token()`**: **Currently disabled (commented out) for localhost MVP.** Returns 401 for invalid/missing tokens, 500 if `APP_TOKEN` is not configured. Health endpoint is unprotected.
```

Line 96 — change:
```
- `APP_TOKEN` — simple auth token for API access (currently disabled, commented out in `.env.example`)
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: annotate CLAUDE.md auth references as disabled for MVP"
```

---

### Task 14: Final verification

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `cd /home/hart/Code/gov-assist/backend && python -m pytest --tb=short -v 2>&1 | tail -40`
Expected: All tests pass. `test_auth.py` tests show as SKIPPED.

- [ ] **Step 2: Run all frontend tests**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run --reporter=verbose 2>&1 | tail -40`
Expected: All non-skipped tests pass. Auth test files show as skipped.

- [ ] **Step 3: Verify app starts without APP_TOKEN**

Run: `cd /home/hart/Code/gov-assist/backend && APP_TOKEN= python -c "from main import app; print('App loaded successfully')"`
Expected: No import errors, prints success message.

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address issues found during final verification"
```
