# Task 19: Action Buttons & Status Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up the complete proofreading flow in Proofreading.jsx — preprocessing, API calls, loading/error states, retry, clear, and action buttons (copy, download, save to history).

**Architecture:** `Proofreading.jsx` is the orchestrator connecting `InputArea`, `OptionPanel`, and `ResultView` to the backend API. A new `apiPostBlob` helper in `client.js` handles binary `.docx` downloads. All state lives in `Proofreading.jsx` via React hooks.

**Tech Stack:** React 18 hooks, vitest, @testing-library/react, Clipboard API, Blob download

**Design spec sections:** §3.3.5 (processing states), §3.3.6 (action buttons)

---

## Current State

`Proofreading.jsx` has a stub `handleSubmit` that only logs. Key pieces exist but are unwired:

| Piece | Status |
|-------|--------|
| `preprocess.js` | Implemented, tested, **not imported** in Proofreading |
| `api/client.js` (`apiPost`) | Implemented, **not imported** in Proofreading |
| `isSubmitting` setter | Destructured but unused — no loading state |
| `result` state | Never set — `ResultView` always receives `null` |
| `ResultView` (`onRetry` prop) | Accepted but not passed from Proofreading |
| `error` state | Does not exist |
| Action buttons (copy/download/save/clear) | Do not exist |
| `apiPostBlob` (binary download) | Does not exist in client |

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/api/client.js` | Modify | Add `apiPostBlob` for binary responses |
| `frontend/src/api/client.test.js` | Modify | Tests for `apiPostBlob` |
| `frontend/src/tools/proofreading/Proofreading.jsx` | Rewrite | Full orchestrator: submit, preprocess, API call, loading, error, retry, clear, copy, download, save |
| `frontend/src/tools/proofreading/Proofreading.test.jsx` | Create | All tests for Proofreading component |
| `frontend/src/css/components.css` | Modify | Add `.action-bar` styles |

---

### Task 1: Add `apiPostBlob` to API client

The `/api/export/docx` endpoint returns binary data. The current `request()` tries to parse as JSON/text, which breaks binary responses.

**Files:**
- Modify: `frontend/src/api/client.js`
- Modify: `frontend/src/api/client.test.js`

- [ ] **Step 1: Write failing test — `apiPostBlob` returns blob on success**

Add to `frontend/src/api/client.test.js`:

```js
describe('apiPostBlob', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('returns blob on successful response', async () => {
    setToken('my-token');
    const blob = new Blob(['docx-content'], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }),
      blob: () => Promise.resolve(blob),
    });

    const { apiPostBlob } = await import('./client');
    const result = await apiPostBlob('/api/export/docx', { corrected_text: 'test' });

    expect(result).toBe(blob);
    expect(fetch).toHaveBeenCalledWith('/api/export/docx', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ corrected_text: 'test' }),
      headers: expect.objectContaining({
        Authorization: 'Bearer my-token',
        'X-Request-ID': expect.any(String),
      }),
    }));
  });

  it('throws ApiError on non-OK response', async () => {
    setToken('my-token');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 500,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ message: 'サーバーエラー' }),
    });

    const { apiPostBlob } = await import('./client');

    await expect(apiPostBlob('/api/export/docx', { corrected_text: 'test' })).rejects.toThrow(ApiError);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/client.test.js`
Expected: FAIL — `apiPostBlob` is not exported

- [ ] **Step 3: Implement `apiPostBlob`**

Add to `frontend/src/api/client.js`, after the existing `apiDelete` function:

```js
export async function apiPostBlob(path, body) {
  const requestId = generateRequestId();
  const token = getToken();

  const headers = {
    'Content-Type': 'application/json',
    'X-Request-ID': requestId,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const response = await fetch(path, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (response.status === 401) {
    removeToken();
    window.dispatchEvent(new CustomEvent('auth:logout'));
  }

  if (!response.ok) {
    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }
    throw new ApiError(response.status, data, requestId);
  }

  return response.blob();
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/client.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.js frontend/src/api/client.test.js
git commit -m "feat(api): add apiPostBlob for binary response handling"
```

---

### Task 2: Proofreading core flow — submit, loading, error, retry, clear

This is the main task. It rewrites `Proofreading.jsx` from a stub to a fully functional orchestrator.

**Files:**
- Create: `frontend/src/tools/proofreading/Proofreading.test.jsx`
- Modify: `frontend/src/tools/proofreading/Proofreading.jsx`

- [ ] **Step 1: Write failing tests — submit success flow**

Create `frontend/src/tools/proofreading/Proofreading.test.jsx`:

```jsx
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Proofreading from './Proofreading';

// --- Mocks ---

vi.mock('../../api/client', () => ({
  apiPost: vi.fn(),
  apiPostBlob: vi.fn(),
}));

vi.mock('../../utils/storage', () => ({
  loadSettings: vi.fn(() => ({
    model: 'kimi-k2.5',
    document_type: 'official',
    options: { typo: true, keigo: true, terminology: true, style: true, legal: false, readability: true },
  })),
}));

vi.mock('./preprocess', () => ({
  preprocessText: vi.fn((text) => ({ text: text.trim(), error: null })),
}));

import { apiPost } from '../../api/client';
import { preprocessText } from './preprocess';

const mockApiPost = vi.mocked(apiPost);
const mockPreprocessText = vi.mocked(preprocessText);

// --- Fixtures ---

const SUCCESS_RESPONSE = {
  request_id: 'test-uuid-001',
  status: 'success',
  status_reason: null,
  warnings: [],
  corrected_text: '校正済みテキストです。',
  summary: '1件の修正を行いました。',
  corrections: [
    { original: '修正前', corrected: '修正後', reason: 'タイポ修正', category: '誤字脱字', diff_matched: true },
  ],
  diffs: [
    { type: 'equal', text: 'テキスト', start: 0, position: null, reason: null },
    { type: 'delete', text: '前', start: 4, position: null, reason: 'タイポ修正' },
    { type: 'insert', text: '後', start: 4, position: 'after', reason: 'タイポ修正' },
  ],
};

const PARTIAL_RESPONSE = {
  request_id: 'test-uuid-002',
  status: 'partial',
  status_reason: 'diff_timeout',
  warnings: [],
  corrected_text: '部分的に校正済み。',
  summary: null,
  corrections: [],
  diffs: [],
};

function setup(text = 'テストテキスト') {
  mockApiPost.mockResolvedValue(SUCCESS_RESPONSE);
  const user = userEvent.setup();
  const utils = render(<Proofreading />);
  const textarea = screen.getByPlaceholderText(/校正したいテキスト/);
  return { user, utils, textarea, async submitText: () => { await user.type(textarea, text); await user.click(screen.getByRole('button', { name: '校正実行' })); } };
}

describe('Proofreading', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockApiPost.mockResolvedValue(SUCCESS_RESPONSE);
    localStorage.clear();
  });

  // --- Submit flow ---

  it('preprocesses text and calls API on submit', async () => {
    const { user, submitText } = setup();

    await submitText();

    expect(mockPreprocessText).toHaveBeenCalledWith('テストテキスト');
    expect(mockApiPost).toHaveBeenCalledWith('/api/proofread', expect.objectContaining({
      request_id: expect.stringMatching(/^[0-9a-f-]+$/),
      text: 'テストテキスト',  // preprocessText returns text.trim()
      document_type: 'official',
      model: 'kimi-k2.5',
    }));
  });

  it('shows loading spinner during API call', async () => {
    let resolveApi;
    mockApiPost.mockReturnValue(new Promise((resolve) => { resolveApi = resolve; }));
    const { submitText } = setup();

    await submitText();

    expect(screen.getByText('AI が校正しています...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '校正実行' })).toBeDisabled();

    resolveApi(SUCCESS_RESPONSE);
    await waitFor(() => {
      expect(screen.queryByText('AI が校正しています...')).not.toBeInTheDocument();
    });
  });

  it('disables input area and option panel during submit', async () => {
    let resolveApi;
    mockApiPost.mockReturnValue(new Promise((resolve) => { resolveApi = resolve; }));
    const { submitText } = setup();

    await submitText();

    expect(screen.getByPlaceholderText(/校正したいテキスト/)).toBeDisabled();
    expect(screen.getByRole('group', { name: '校正オプション' })).toBeDisabled();

    resolveApi(SUCCESS_RESPONSE);
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/校正したいテキスト/)).not.toBeDisabled();
    });
  });

  it('displays result after successful API response', async () => {
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByText('1件の修正を行いました。')).toBeInTheDocument();
    });
    expect(screen.getByText('校正済みテキストです。')).toBeInTheDocument();
  });

  it('shows error and retry button when API throws', async () => {
    mockApiPost.mockRejectedValue(new Error('AI応答がタイムアウトしました（60秒）'));
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByText('AI応答がタイムアウトしました（60秒）')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
  });

  it('retries with same params when retry is clicked', async () => {
    mockApiPost.mockRejectedValueOnce(new Error('タイムアウト'));
    mockApiPost.mockResolvedValueOnce(SUCCESS_RESPONSE);
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '再試行' }));

    await waitFor(() => {
      expect(screen.getByText('1件の修正を行いました。')).toBeInTheDocument();
    });
    expect(mockApiPost).toHaveBeenCalledTimes(2);
  });

  it('shows preprocess error without calling API', async () => {
    mockPreprocessText.mockReturnValueOnce({ text: '', error: '前処理後のテキストが8000文字を超えています。' });
    const { submitText } = setup();

    await submitText();

    expect(mockApiPost).not.toHaveBeenCalled();
    expect(screen.getByText('前処理後のテキストが8000文字を超えています。')).toBeInTheDocument();
  });

  it('clears result, error, and resets input on clear', async () => {
    const { submitText } = setup('テストテキスト');

    await submitText();

    await waitFor(() => {
      expect(screen.getByText('1件の修正を行いました。')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: 'クリア' }));

    expect(screen.queryByText('1件の修正を行いました。')).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText(/校正したいテキスト/)).toHaveValue('');
  });

  it('shows clear button during error state (not only on success)', async () => {
    mockApiPost.mockRejectedValue(new Error('タイムアウト'));
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'クリア' })).toBeInTheDocument();
  });

  it('handles partial response (diff_timeout)', async () => {
    mockApiPost.mockResolvedValue(PARTIAL_RESPONSE);
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByText(/差分計算がタイムアウト/)).toBeInTheDocument();
    });
  });

  it('retries from ResultView retry button when API returns status error', async () => {
    const errorResponse = {
      ...SUCCESS_RESPONSE,
      status: 'error',
      status_reason: 'parse_fallback',
      corrected_text: '',
      diffs: [],
      corrections: [],
    };
    mockApiPost.mockRejectedValueOnce(new Error('タイムアウト'));
    mockApiPost.mockResolvedValueOnce(errorResponse);
    mockApiPost.mockResolvedValueOnce(SUCCESS_RESPONSE);
    const { submitText } = setup();

    // First attempt fails with network error
    await submitText();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
    });

    // Retry returns status: "error"
    await userEvent.click(screen.getByRole('button', { name: '再試行' }));
    await waitFor(() => {
      expect(screen.getByText(/校正結果を取得できませんでした/)).toBeInTheDocument();
    });

    // ResultView has its own retry button
    await userEvent.click(screen.getByRole('button', { name: '再試行' }));
    await waitFor(() => {
      expect(screen.getByText('1件の修正を行いました。')).toBeInTheDocument();
    });
    expect(mockApiPost).toHaveBeenCalledTimes(3);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/tools/proofreading/Proofreading.test.js`
Expected: FAIL — submit flow not implemented

- [ ] **Step 3: Implement Proofreading.jsx**

Replace the entire contents of `frontend/src/tools/proofreading/Proofreading.jsx`:

```jsx
import { useState, useCallback } from 'react';
import { loadSettings } from '../../utils/storage';
import { apiPost } from '../../api/client';
import { preprocessText } from './preprocess';
import InputArea from './InputArea';
import OptionPanel from './OptionPanel';
import ResultView from './ResultView';

function Proofreading() {
  const [options, setOptions] = useState(() => loadSettings().options);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [lastParams, setLastParams] = useState(null);
  const [clearKey, setClearKey] = useState(0);

  const callProofreadApi = useCallback(async (text, documentType, model) => {
    setIsSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiPost('/api/proofread', {
        request_id: crypto.randomUUID(),
        text,
        document_type: documentType,
        options: options || {},
        model,
      });
      setResult(response);
    } catch (err) {
      setError(err.message || '校正に失敗しました。');
    } finally {
      setIsSubmitting(false);
    }
  }, [options]);

  const handleSubmit = useCallback(async (rawText, documentType) => {
    const { text: preprocessed, error: preprocessError } = preprocessText(rawText);
    if (preprocessError) {
      setError(preprocessError);
      return;
    }

    const settings = loadSettings();
    // Store both raw text (for history) and preprocessed text (for API/retry)
    setLastParams({ rawText, text: preprocessed, documentType, model: settings.model });
    await callProofreadApi(preprocessed, documentType, settings.model);
  }, [callProofreadApi]);

  const handleRetry = useCallback(async () => {
    if (!lastParams || isSubmitting) return;
    await callProofreadApi(lastParams.text, lastParams.documentType, lastParams.model);
  }, [lastParams, isSubmitting, callProofreadApi]);

  const handleClear = useCallback(() => {
    setResult(null);
    setError(null);
    setLastParams(null);
    setClearKey((k) => k + 1);
  }, []);

  const hasContent = result || error;

  return (
    <div>
      <h2>AI 文書校正</h2>
      <div className="mt-md">
        <InputArea key={clearKey} onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </div>
      <div className="mt-md">
        <OptionPanel onChange={setOptions} disabled={isSubmitting} />
      </div>
      {isSubmitting && (
        <div className="loading mt-lg">
          <div className="spinner" role="status" aria-label="校正中"></div>
          <span>AI が校正しています...</span>
        </div>
      )}
      {error && !isSubmitting && (
        <div className="message message--error mt-md" role="alert">
          {error}
        </div>
      )}
      {!result && error && !isSubmitting && lastParams && (
        <button className="btn btn--secondary mt-sm" onClick={handleRetry} type="button">
          再試行
        </button>
      )}
      <ResultView result={result} onRetry={handleRetry} />
      {hasContent && (
        <div className="action-bar mt-md">
          <button className="btn btn--secondary" onClick={handleClear} type="button">
            クリア
          </button>
        </div>
      )}
    </div>
  );
}

export default Proofreading;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/tools/proofreading/Proofreading.test.js`
Expected: PASS (all 11 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tools/proofreading/Proofreading.jsx frontend/src/tools/proofreading/Proofreading.test.jsx
git commit -m "feat(frontend): wire up proofreading submit flow with loading, error, retry, clear"
```

---

### Task 3: Action buttons — copy, download, save to history

**Files:**
- Modify: `frontend/src/tools/proofreading/Proofreading.test.jsx`
- Modify: `frontend/src/tools/proofreading/Proofreading.jsx`

- [ ] **Step 1: Write failing tests — action buttons**

Add to `frontend/src/tools/proofreading/Proofreading.test.jsx` inside the `describe('Proofreading')` block (after existing tests). Also add the `apiPostBlob` mock import at the top:

Update the mock import at the top of the file:
```js
import { apiPost, apiPostBlob } from '../../api/client';

const mockApiPost = vi.mocked(apiPost);
const mockApiPostBlob = vi.mocked(apiPostBlob);
```

Add these tests inside the `describe('Proofreading')` block:

```jsx
  // --- Action buttons ---

  it('shows copy, download, save buttons after successful result', async () => {
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '校正済みテキストをコピー' })).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /Word.*ダウンロード/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '履歴に保存' })).toBeInTheDocument();
  });

  it('does not show copy/download/save buttons when result has error status', async () => {
    const errorResponse = { ...SUCCESS_RESPONSE, status: 'error', status_reason: 'parse_fallback', corrected_text: '', diffs: [], corrections: [] };
    mockApiPost.mockResolvedValue(errorResponse);
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByText(/校正結果を取得できませんでした/)).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: '校正済みテキストをコピー' })).not.toBeInTheDocument();
  });

  // --- Copy ---

  it('copies corrected_text to clipboard on copy click', async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText: writeTextMock } });
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '校正済みテキストをコピー' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '校正済みテキストをコピー' }));

    expect(writeTextMock).toHaveBeenCalledWith('校正済みテキストです。');
    await waitFor(() => {
      expect(screen.getByText('コピーしました')).toBeInTheDocument();
    });
  });

  it('shows error when clipboard copy fails', async () => {
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockRejectedValue(new Error('Denied')) } });
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '校正済みテキストをコピー' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '校正済みテキストをコピー' }));

    await waitFor(() => {
      expect(screen.getByText('クリップボードへのコピーに失敗しました。')).toBeInTheDocument();
    });
  });

  // --- Download ---

  it('downloads docx via apiPostBlob', async () => {
    const blob = new Blob(['docx'], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    mockApiPostBlob.mockResolvedValue(blob);

    // Mock URL.createObjectURL and DOM for download link
    const mockUrl = 'blob:http://localhost/test';
    vi.spyOn(URL, 'createObjectURL').mockReturnValue(mockUrl);
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const clickMock = vi.fn();
    const mockAnchor = { href: '', download: '', click: clickMock, style: {} };
    vi.spyOn(document, 'createElement').mockReturnValue(mockAnchor);
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockAnchor);
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => mockAnchor);

    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Word.*ダウンロード/ })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: /Word.*ダウンロード/ }));

    expect(mockApiPostBlob).toHaveBeenCalledWith('/api/export/docx', {
      corrected_text: '校正済みテキストです。',
      document_type: 'official',
    });
    expect(clickMock).toHaveBeenCalled();
  });

  it('shows error when download fails', async () => {
    mockApiPostBlob.mockRejectedValue(new Error('サーバーエラー'));
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Word.*ダウンロード/ })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: /Word.*ダウンロード/ }));

    await waitFor(() => {
      expect(screen.getByText('Word ファイルのダウンロードに失敗しました。')).toBeInTheDocument();
    });
  });

  // --- Save to history ---

  it('saves raw text (not preprocessed) to history via apiPost', async () => {
    mockApiPost.mockResolvedValue({ id: 1, message: '保存しました' });
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '履歴に保存' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '履歴に保存' }));

    // Verify raw text is sent as input_text (the text the user typed)
    expect(mockApiPost).toHaveBeenCalledWith('/api/history', expect.objectContaining({
      input_text: 'テストテキスト',
      model: 'kimi-k2.5',
      document_type: 'official',
    }));

    await waitFor(() => {
      expect(screen.getByText('保存しました')).toBeInTheDocument();
    });
  });

  it('disables save button after successful save', async () => {
    mockApiPost.mockResolvedValue({ id: 1, message: '保存しました' });
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '履歴に保存' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '履歴に保存' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '履歴に保存' })).toBeDisabled();
    });
  });

  it('shows error when save fails', async () => {
    mockApiPost.mockRejectedValueOnce(new Error('DB エラー'));
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '履歴に保存' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '履歴に保存' }));

    await waitFor(() => {
      expect(screen.getByText('履歴への保存に失敗しました。')).toBeInTheDocument();
    });
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/tools/proofreading/Proofreading.test.js`
Expected: FAIL — action buttons not implemented

- [ ] **Step 3: Implement action buttons in Proofreading.jsx**

Update the import line:

```jsx
import { useState, useCallback } from 'react';
import { loadSettings } from '../../utils/storage';
import { apiPost, apiPostBlob } from '../../api/client';
import { preprocessText } from './preprocess';
import InputArea from './InputArea';
import OptionPanel from './OptionPanel';
import ResultView from './ResultView';
```

Add new state variables inside the function (after existing state):

```jsx
const [copySuccess, setCopySuccess] = useState(false);
const [saveSuccess, setSaveSuccess] = useState(false);
```

Add handler functions after `handleClear`:

```jsx
  const handleCopy = useCallback(async () => {
    if (!result?.corrected_text) return;
    try {
      await navigator.clipboard.writeText(result.corrected_text);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch {
      setError('クリップボードへのコピーに失敗しました。');
    }
  }, [result]);

  const handleDownload = useCallback(async () => {
    if (!result?.corrected_text) return;
    try {
      const blob = await apiPostBlob('/api/export/docx', {
        corrected_text: result.corrected_text,
        document_type: lastParams?.documentType || 'official',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = '校正済み文書.docx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setError('Word ファイルのダウンロードに失敗しました。');
    }
  }, [result, lastParams]);

  const handleSaveHistory = useCallback(async () => {
    if (!result || !lastParams) return;
    try {
      await apiPost('/api/history', {
        input_text: lastParams.rawText,
        result,
        model: lastParams.model,
        document_type: lastParams.documentType,
      });
      setSaveSuccess(true);
    } catch {
      setError('履歴への保存に失敗しました。');
    }
  }, [result, lastParams]);
```

Update `handleClear` to also reset new states:

```jsx
  const handleClear = useCallback(() => {
    setResult(null);
    setError(null);
    setLastParams(null);
    setCopySuccess(false);
    setSaveSuccess(false);
    setClearKey((k) => k + 1);
  }, []);
```

Add computed values and update the action bar JSX. Replace `const hasContent` and the action bar:

```jsx
  const hasContent = result || error;
  const showActions = result && result.status !== 'error' && result.corrected_text;
```

Replace the action bar JSX (after `<ResultView>`):

```jsx
      <ResultView result={result} onRetry={handleRetry} />
      {hasContent && (
        <div className="action-bar mt-md">
          {showActions && (
            <>
              <button className="btn btn--secondary" onClick={handleCopy} type="button">
                {copySuccess ? 'コピーしました' : '校正済みテキストをコピー'}
              </button>
              <button className="btn btn--secondary" onClick={handleDownload} type="button">
                Word でダウンロード (.docx)
              </button>
              <button className="btn btn--secondary" onClick={handleSaveHistory} type="button" disabled={saveSuccess}>
                {saveSuccess ? '保存しました' : '履歴に保存'}
              </button>
            </>
          )}
          <button className="btn btn--secondary" onClick={handleClear} type="button">
            クリア
          </button>
        </div>
      )}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/tools/proofreading/Proofreading.test.js`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tools/proofreading/Proofreading.jsx frontend/src/tools/proofreading/Proofreading.test.jsx
git commit -m "feat(frontend): add copy, download, and save-to-history action buttons"
```

---

### Task 4: CSS for action bar

**Files:**
- Modify: `frontend/src/css/components.css`

- [ ] **Step 1: Add action-bar styles**

Append to `frontend/src/css/components.css`:

```css
/* --- Action Bar (§3.3.6) --- */

.action-bar {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}
```

- [ ] **Step 2: Verify visually**

Run: `cd frontend && npx vite --open`
Manually verify: submit a proofreading → action bar appears with buttons → copy feedback → buttons layout.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/css/components.css
git commit -m "style(frontend): add action-bar flex layout"
```

---

### Task 5: Full suite verification

- [ ] **Step 1: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS (existing + new)

- [ ] **Step 2: Run all backend tests**

Run: `cd backend && pytest`
Expected: All tests PASS (no regressions)

- [ ] **Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix(frontend): address test fixes from verification"
```
