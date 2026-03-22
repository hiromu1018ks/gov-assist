# Task 21: 設定パネル (Settings Panel) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 設定画面を実装し、AIモデル選択・デフォルト文書種別・校正オプション初期値（localStorage）と履歴保存件数上限（サーバーAPI）を管理できるようにする。

**Architecture:** 設定画面は「クライアント設定」（localStorage、`storage.js` の `loadSettings()`/`saveSettings()` 経由）と「サーバー設定」（`GET/PUT /api/settings`）を明確に分離する。既存の `storage.js`・`client.js` を利用し、Settings.jsx はフォームUIの責務のみを持つ。

**Tech Stack:** React 18, Vitest, @testing-library/react, @testing-library/user-event, plain CSS

**Design Spec:** `docs/design.md` §3.4

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/api/client.js` | Modify | Add `apiPut` export |
| `frontend/src/tools/settings/Settings.test.jsx` | Create | Settings panel tests |
| `frontend/src/tools/settings/Settings.jsx` | Modify | Real settings panel UI |
| `frontend/src/css/components.css` | Modify | Settings-specific CSS |
| `frontend/src/App.test.jsx` | Modify | Update placeholder assertion |

---

## Existing Code Context

### `frontend/src/utils/storage.js` (read-only, already exists)
```js
const DEFAULTS = {
  version: 1,
  model: 'kimi-k2.5',
  document_type: 'official',
  options: {
    typo: true, keigo: true, terminology: true,
    style: true, legal: false, readability: true,
  },
};
export function loadSettings() { /* merges stored with defaults */ }
export function saveSettings(settings) { /* writes to localStorage */ }
```

### `frontend/src/api/client.js` (needs `apiPut` added)
Currently exports: `apiGet`, `apiPost`, `apiPatch`, `apiDelete`, `apiPostBlob`, `ApiError`.
The `request(method, path, body)` function is private — add a public `apiPut` wrapper.

### Backend API endpoints (already implemented)
- `GET /api/models` → `{ models: [{ model_id, display_name, ... }] }`
- `GET /api/settings` → `{ history_limit: 50 }`
- `PUT /api/settings` ← `{ history_limit: 50 }` → `{ history_limit: 50 }` (validated 1-200)

### Document types (from `backend/schemas.py` `DocumentType` enum)
- `email` — メール
- `report` — 報告書
- `official` — 公文書
- `other` — その他

### Proofreading options (from `OptionPanel.jsx` — same labels)
```js
const OPTIONS = [
  { key: 'typo', label: '誤字・脱字・変換ミスの検出' },
  { key: 'keigo', label: '敬語・丁寧語の適切さチェック' },
  { key: 'terminology', label: '公文書用語・表現への統一（例：「ください」→「くださいますよう」）' },
  { key: 'style', label: '文体の統一（です・ます調 / である調）' },
  { key: 'legal', label: '法令・条例用語の確認' },
  { key: 'readability', label: '文章の読みやすさ・論理構成の改善提案' },
];
```

---

### Task 1: Add `apiPut` to API client

**Files:**
- Modify: `frontend/src/api/client.js:63-69`

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/api/client.test.js` inside the first `describe('API client', ...)` block, after the last test:

```js
it('sends PUT request with JSON body', async () => {
  setToken('my-token');
  mockFetchJson({ history_limit: 100 });

  const { apiPut } = await import('./client');
  await apiPut('/api/settings', { history_limit: 100 });

  expect(fetch).toHaveBeenCalledWith('/api/settings', expect.objectContaining({
    method: 'PUT',
    body: JSON.stringify({ history_limit: 100 }),
  }));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/client.test.js`
Expected: FAIL — `apiPut` is not exported

- [ ] **Step 3: Write minimal implementation**

Add after `apiDelete` export in `frontend/src/api/client.js` (after line 69):

```js
export async function apiPut(path, body) {
  return request('PUT', path, body);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/client.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.js frontend/src/api/client.test.js
git commit -m "feat(api): add apiPut method to API client"
```

---

### Task 2: Write Settings panel tests (TDD — all tests first)

**Files:**
- Create: `frontend/src/tools/settings/Settings.test.jsx`

- [ ] **Step 1: Write all failing tests**

Create `frontend/src/tools/settings/Settings.test.jsx`:

```jsx
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// --- Mocks ---

vi.mock('../../api/client', () => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(),
}));

vi.mock('../../utils/storage', () => ({
  loadSettings: vi.fn(() => ({
    version: 1,
    model: 'kimi-k2.5',
    document_type: 'official',
    options: {
      typo: true, keigo: true, terminology: true,
      style: true, legal: false, readability: true,
    },
  })),
  saveSettings: vi.fn(),
}));

import { apiGet, apiPut } from '../../api/client';
import { loadSettings, saveSettings } from '../../utils/storage';
import Settings from './Settings';

const mockApiGet = vi.mocked(apiGet);
const mockApiPut = vi.mocked(apiPut);
const mockLoadSettings = vi.mocked(loadSettings);
const mockSaveSettings = vi.mocked(saveSettings);

const MODELS_RESPONSE = {
  models: [
    { model_id: 'kimi-k2.5', display_name: 'Kimi K2.5', max_tokens: 4096, temperature: 0.3, max_input_chars: 8000, json_forced: true },
    { model_id: 'gpt-4o', display_name: 'GPT-4o', max_tokens: 4096, temperature: 0.3, max_input_chars: 8000, json_forced: true },
  ],
};

const SETTINGS_RESPONSE = { history_limit: 50 };

function setup() {
  mockApiGet.mockImplementation((path) => {
    if (path === '/api/models') return Promise.resolve(MODELS_RESPONSE);
    if (path === '/api/settings') return Promise.resolve(SETTINGS_RESPONSE);
    return Promise.reject(new Error(`Unexpected path: ${path}`));
  });
  mockApiPut.mockResolvedValue(SETTINGS_RESPONSE);
  render(<Settings />);
}

describe('Settings', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockApiGet.mockReset();
    mockApiPut.mockReset();
    mockLoadSettings.mockReset();
    mockSaveSettings.mockReset();
    // Default mock return for loadSettings
    mockLoadSettings.mockReturnValue({
      version: 1,
      model: 'kimi-k2.5',
      document_type: 'official',
      options: {
        typo: true, keigo: true, terminology: true,
        style: true, legal: false, readability: true,
      },
    });
  });

  // --- Initial render ---

  it('renders page title', async () => {
    setup();
    expect(screen.getByText('設定')).toBeInTheDocument();
  });

  it('fetches models and settings on mount', async () => {
    setup();
    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith('/api/models');
      expect(mockApiGet).toHaveBeenCalledWith('/api/settings');
    });
  });

  // --- Model selection section ---

  it('renders model selection section with loaded models', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByText('Kimi K2.5')).toBeInTheDocument();
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });
  });

  it('shows currently selected model from localStorage', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByDisplayValue('Kimi K2.5')).toBeInTheDocument();
    });
  });

  it('saves model change to localStorage on select', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    await userEvent.selectOptions(screen.getByLabelText('AI モデル'), 'gpt-4o');

    await waitFor(() => {
      expect(mockSaveSettings).toHaveBeenCalledWith(
        expect.objectContaining({ model: 'gpt-4o' })
      );
    });
  });

  it('falls back to first model when stored model is not available', async () => {
    mockLoadSettings.mockReturnValue({
      version: 1, model: 'nonexistent-model', document_type: 'official',
      options: { typo: true, keigo: true, terminology: true, style: true, legal: false, readability: true },
    });
    setup();
    await waitFor(() => {
      expect(screen.getByDisplayValue('Kimi K2.5')).toBeInTheDocument();
      expect(mockSaveSettings).toHaveBeenCalledWith(
        expect.objectContaining({ model: 'kimi-k2.5' })
      );
    });
  });

  // --- Document type section ---

  it('renders document type selector with current value from localStorage', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByDisplayValue('公文書')).toBeInTheDocument();
    });
  });

  it('saves document type change to localStorage', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByLabelText('デフォルト文書種別')).toBeInTheDocument();
    });

    await userEvent.selectOptions(screen.getByLabelText('デフォルト文書種別'), 'email');

    await waitFor(() => {
      expect(mockSaveSettings).toHaveBeenCalledWith(
        expect.objectContaining({ document_type: 'email' })
      );
    });
  });

  // --- Proofreading options section ---

  it('renders all 6 proofreading option checkboxes', async () => {
    setup();
    expect(screen.getByLabelText('誤字・脱字・変換ミスの検出')).toBeInTheDocument();
    expect(screen.getByLabelText('敬語・丁寧語の適切さチェック')).toBeInTheDocument();
    expect(screen.getByLabelText('公文書用語・表現への統一')).toBeInTheDocument();
    expect(screen.getByLabelText('文体の統一')).toBeInTheDocument();
    expect(screen.getByLabelText('法令・条例用語の確認')).toBeInTheDocument();
    expect(screen.getByLabelText('文章の読みやすさ・論理構成の改善提案')).toBeInTheDocument();
  });

  it('reflects current option values from localStorage', async () => {
    setup();
    expect(screen.getByLabelText('誤字・脱字・変換ミスの検出')).toBeChecked();
    expect(screen.getByLabelText('法令・条例用語の確認')).not.toBeChecked();
  });

  it('saves option change to localStorage on toggle', async () => {
    setup();
    await userEvent.click(screen.getByLabelText('法令・条例用語の確認'));

    await waitFor(() => {
      expect(mockSaveSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          options: expect.objectContaining({ legal: true }),
        })
      );
    });
  });

  // --- History limit section (server setting) ---

  it('renders history limit input with server value', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByLabelText('履歴保存件数上限')).toHaveValue(50);
    });
  });

  it('sends PUT /api/settings when save button is clicked', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByLabelText('履歴保存件数上限')).toBeInTheDocument();
    });

    const input = screen.getByLabelText('履歴保存件数上限');
    await userEvent.clear(input);
    await userEvent.type(input, '100');
    await userEvent.click(screen.getByRole('button', { name: 'サーバー設定を保存' }));

    await waitFor(() => {
      expect(mockApiPut).toHaveBeenCalledWith('/api/settings', { history_limit: 100 });
    });
  });

  it('shows success message after saving server settings', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByLabelText('履歴保存件数上限')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: 'サーバー設定を保存' }));

    await waitFor(() => {
      expect(screen.getByText('サーバー設定を保存しました。')).toBeInTheDocument();
    });
  });

  it('shows error message when server settings save fails', async () => {
    mockApiPut.mockRejectedValue(new Error('サーバーエラー'));
    setup();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'サーバー設定を保存' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: 'サーバー設定を保存' }));

    await waitFor(() => {
      expect(screen.getByText('サーバー設定の保存に失敗しました。')).toBeInTheDocument();
    });
  });

  it('disables save button while saving server settings', async () => {
    let resolvePut;
    mockApiPut.mockReturnValue(new Promise((resolve) => { resolvePut = resolve; }));
    setup();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'サーバー設定を保存' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: 'サーバー設定を保存' }));

    expect(screen.getByRole('button', { name: '保存中...' })).toBeDisabled();

    resolvePut(SETTINGS_RESPONSE);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'サーバー設定を保存' })).toBeEnabled();
    });
  });

  // --- Error states ---

  it('shows error when models API fails', async () => {
    mockApiGet.mockImplementation((path) => {
      if (path === '/api/models') return Promise.reject(new Error('Network error'));
      if (path === '/api/settings') return Promise.resolve(SETTINGS_RESPONSE);
      return Promise.reject(new Error(`Unexpected: ${path}`));
    });
    render(<Settings />);

    await waitFor(() => {
      expect(screen.getByText(/モデル一覧の取得に失敗しました/)).toBeInTheDocument();
    });
  });

  it('shows error when settings API fails', async () => {
    mockApiGet.mockImplementation((path) => {
      if (path === '/api/models') return Promise.resolve(MODELS_RESPONSE);
      if (path === '/api/settings') return Promise.reject(new Error('Network error'));
      return Promise.reject(new Error(`Unexpected: ${path}`));
    });
    render(<Settings />);

    await waitFor(() => {
      expect(screen.getByText(/サーバー設定の取得に失敗しました/)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/tools/settings/Settings.test.js`
Expected: FAIL — Settings is still a placeholder

- [ ] **Step 3: Commit test file (red phase)**

```bash
git add frontend/src/tools/settings/Settings.test.jsx
git commit -m "test(settings): add Settings panel tests (red phase)"
```

---

### Task 3: Implement Settings panel

**Files:**
- Modify: `frontend/src/tools/settings/Settings.jsx`
- Modify: `frontend/src/css/components.css`

- [ ] **Step 1: Implement Settings.jsx**

Replace the entire contents of `frontend/src/tools/settings/Settings.jsx`:

```jsx
import { useState, useEffect, useCallback } from 'react';
import { apiGet, apiPut } from '../../api/client';
import { loadSettings, saveSettings } from '../../utils/storage';

const DOCUMENT_TYPES = [
  { value: 'email', label: 'メール' },
  { value: 'report', label: '報告書' },
  { value: 'official', label: '公文書' },
  { value: 'other', label: 'その他' },
];

const OPTIONS = [
  { key: 'typo', label: '誤字・脱字・変換ミスの検出' },
  { key: 'keigo', label: '敬語・丁寧語の適切さチェック' },
  { key: 'terminology', label: '公文書用語・表現への統一（例：「ください」→「くださいますよう」）' },
  { key: 'style', label: '文体の統一（です・ます調 / である調）' },
  { key: 'legal', label: '法令・条例用語の確認' },
  { key: 'readability', label: '文章の読みやすさ・論理構成の改善提案' },
];

export default function Settings() {
  // --- Client settings state (lazy init from localStorage) ---
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(() => loadSettings().model);
  const [documentType, setDocumentType] = useState(() => loadSettings().document_type);
  const [options, setOptions] = useState(() => loadSettings().options);

  // --- Server settings state ---
  const [historyLimit, setHistoryLimit] = useState(50);
  const [savingServer, setSavingServer] = useState(false);
  const [serverMessage, setServerMessage] = useState(null);

  // --- Error state ---
  const [modelsError, setModelsError] = useState(null);
  const [settingsError, setSettingsError] = useState(null);

  // --- Fetch on mount ---
  useEffect(() => {
    apiGet('/api/models')
      .then((data) => {
        if (data.models?.length > 0) {
          setModels(data.models);
          const ids = data.models.map((m) => m.model_id);
          const current = loadSettings().model;
          if (!ids.includes(current)) {
            const fallback = data.models[0].model_id;
            setSelectedModel(fallback);
            saveSettings({ ...loadSettings(), model: fallback });
          }
        }
      })
      .catch(() => setModelsError('モデル一覧の取得に失敗しました。'));

    apiGet('/api/settings')
      .then((data) => setHistoryLimit(data.history_limit))
      .catch(() => setSettingsError('サーバー設定の取得に失敗しました。'));
  }, []);

  // --- Client settings handlers (localStorage, immediate) ---
  const handleModelChange = useCallback((e) => {
    const value = e.target.value;
    setSelectedModel(value);
    saveSettings({ ...loadSettings(), model: value });
  }, []);

  const handleDocumentTypeChange = useCallback((e) => {
    const value = e.target.value;
    setDocumentType(value);
    saveSettings({ ...loadSettings(), document_type: value });
  }, []);

  const handleOptionChange = useCallback((key) => {
    const next = { ...options, [key]: !options[key] };
    setOptions(next);
    saveSettings({ ...loadSettings(), options: next });
  }, [options]);

  // --- Server settings handler (PUT API) ---
  const handleSaveServerSettings = useCallback(async () => {
    setSavingServer(true);
    setServerMessage(null);
    try {
      await apiPut('/api/settings', { history_limit: Number(historyLimit) });
      setServerMessage({ type: 'success', text: 'サーバー設定を保存しました。' });
    } catch {
      setServerMessage({ type: 'error', text: 'サーバー設定の保存に失敗しました。' });
    } finally {
      setSavingServer(false);
    }
  }, [historyLimit]);

  return (
    <div className="settings">
      <h2>設定</h2>

      {/* --- Client Settings --- */}
      <section className="settings__section">
        <h3 className="settings__section-title">AI モデル</h3>
        {modelsError ? (
          <p className="message message--error">{modelsError}</p>
        ) : (
          <div className="form-group">
            <label className="label" htmlFor="settings-model">AI モデル</label>
            <select
              id="settings-model"
              className="select"
              value={selectedModel}
              onChange={handleModelChange}
            >
              {models.map((m) => (
                <option key={m.model_id} value={m.model_id}>
                  {m.display_name}
                </option>
              ))}
            </select>
          </div>
        )}
      </section>

      <section className="settings__section">
        <h3 className="settings__section-title">校正の初期設定</h3>

        <div className="form-group">
          <label className="label" htmlFor="settings-doc-type">デフォルト文書種別</label>
          <select
            id="settings-doc-type"
            className="select"
            value={documentType}
            onChange={handleDocumentTypeChange}
          >
            {DOCUMENT_TYPES.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        <fieldset className="option-panel">
          <legend className="option-panel__legend">デフォルト校正オプション</legend>
          <div className="option-panel__grid">
            {OPTIONS.map(({ key, label }) => (
              <label key={key} className="checkbox">
                <input
                  type="checkbox"
                  className="checkbox__input"
                  checked={!!options[key]}
                  onChange={() => handleOptionChange(key)}
                />
                {label}
              </label>
            ))}
          </div>
        </fieldset>
      </section>

      {/* --- Server Settings --- */}
      <section className="settings__section">
        <h3 className="settings__section-title">サーバー設定</h3>
        {settingsError ? (
          <p className="message message--error">{settingsError}</p>
        ) : (
          <>
            <div className="form-group">
              <label className="label" htmlFor="settings-history-limit">履歴保存件数上限</label>
              <input
                id="settings-history-limit"
                className="input"
                type="number"
                min="1"
                max="200"
                value={historyLimit}
                onChange={(e) => setHistoryLimit(e.target.value)}
              />
              <p className="settings__hint">1〜200件で設定してください。古い履歴から自動削除されます。</p>
            </div>
            <button
              className="btn btn--primary"
              onClick={handleSaveServerSettings}
              disabled={savingServer}
            >
              {savingServer ? '保存中...' : 'サーバー設定を保存'}
            </button>
            {serverMessage && (
              <p className={`message mt-sm ${serverMessage.type === 'error' ? 'message--error' : 'message--success'}`}>
                {serverMessage.text}
              </p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Add settings CSS to components.css**

Append to `frontend/src/css/components.css` (after the last line):

```css

/* --- Settings Panel (§3.4) --- */

.settings {
  max-width: 640px;
}

.settings__section {
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.settings__section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.settings__section-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-md);
}

.settings__hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-top: var(--spacing-xs);
}
```

- [ ] **Step 3: Update App.test.jsx placeholder assertion**

In `frontend/src/App.test.jsx`, change line 69:

```jsx
// Before:
expect(within(main).getByText(/Task 21/)).toBeInTheDocument();

// After:
expect(within(main).getByText('AI モデル')).toBeInTheDocument();
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/tools/settings/Settings.test.js`
Expected: All PASS

Run: `cd frontend && npx vitest run src/App.test.jsx`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tools/settings/Settings.jsx frontend/src/css/components.css frontend/src/App.test.jsx
git commit -m "feat(settings): implement settings panel with client and server settings"
```

---

### Task 4: Run full test suite and verify

- [ ] **Step 1: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All PASS (existing tests + new Settings tests)

- [ ] **Step 2: Manual verification**

1. Start backend: `cd backend && uvicorn main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to `/settings`
4. Verify:
   - Model dropdown shows models from `/api/models`
   - Document type dropdown shows 4 types
   - 6 proofreading option checkboxes reflect localStorage
   - History limit input shows value from `/api/settings`
   - Changing model/doc-type/options immediately saves to localStorage
   - "サーバー設定を保存" button sends PUT to `/api/settings`
   - Header model selector updates when changed in Settings (both read from localStorage)
   - Going back to Proofreading page shows the updated default options

- [ ] **Step 3: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix(settings): address review findings"
```
