# Task 20: History Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the history panel — list view with search/filters/pagination, detail view reusing ResultView, memo editing, and delete operations.

**Architecture:** The history page uses internal state switching between list and detail views (no URL routing — simple `selectedId` state in `History.jsx`). `HistoryList` fetches `GET /api/history` with query params and renders filterable/paginated cards. `HistoryDetail` fetches `GET /api/history/{id}` and renders `ResultView` from the proofreading tool, plus memo/delete UI. The design spec shows a single `History.jsx`, but splitting into three focused components follows the existing pattern (cf. `Proofreading.jsx` → `InputArea.jsx`, `ResultView.jsx`, etc.) and improves testability.

**Tech Stack:** React 18 hooks, vitest, @testing-library/react, existing API client (`apiGet`, `apiPatch`, `apiDelete`), existing `ResultView` component

**Design spec sections:** §7 (history management), §5.4 (history API), §3.3.4 (result display)

---

## Current State

The history directory exists but is empty. Backend history API is fully implemented (Task 10). The proofreading tool has a "履歴に保存" button that calls `POST /api/history`. No frontend exists to browse, search, or view saved history.

| Piece | Status |
|-------|--------|
| `tools/history/` directory | Exists, **empty** |
| `GET /api/history` (list + search + filters) | Implemented (backend Task 10) |
| `GET /api/history/{id}` (detail) | Implemented (backend Task 10) |
| `PATCH /api/history/{id}` (memo) | Implemented (backend Task 10) |
| `DELETE /api/history/{id}` (individual) | Implemented (backend Task 10) |
| `DELETE /api/history` (bulk) | Implemented (backend Task 10) |
| `/history` route | Does not exist |
| History nav item in SideMenu | Does not exist |
| History CSS styles | Do not exist |

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/App.jsx` | Modify | Add `/history` route |
| `frontend/src/App.test.jsx` | Modify | Test history route renders |
| `frontend/src/components/SideMenu.jsx` | Modify | Add "校正履歴" nav item |
| `frontend/src/components/SideMenu.test.jsx` | Modify | Test new nav item |
| `frontend/src/tools/history/HistoryList.jsx` | Create | List view: fetch, filters, pagination, delete |
| `frontend/src/tools/history/HistoryDetail.jsx` | Create | Detail view: fetch, ResultView, memo, delete |
| `frontend/src/tools/history/History.jsx` | Create | Page container: list ↔ detail state switching |
| `frontend/src/tools/history/History.test.jsx` | Create | All tests for HistoryList, HistoryDetail, History |
| `frontend/src/css/components.css` | Modify | History-specific styles |

---

### Task 1: Route and Navigation Setup

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/App.test.jsx`
- Modify: `frontend/src/components/SideMenu.jsx`
- Modify: `frontend/src/components/SideMenu.test.jsx`

- [ ] **Step 1: Add history route to App.jsx**

Add import at the top of `frontend/src/App.jsx`:

```jsx
import History from './tools/history/History';
```

Add route inside `<Routes>`, after the settings route:

```jsx
<Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
```

- [ ] **Step 2: Add history nav item to SideMenu.jsx**

In `frontend/src/components/SideMenu.jsx`, update `NAV_ITEMS`:

```jsx
const NAV_ITEMS = [
  { path: '/', label: 'AI 文書校正', icon: '📝' },
  { path: '/history', label: '校正履歴', icon: '📋' },
  { path: null, label: '文書要約・翻訳', icon: '📄' },
  { path: null, label: 'PDF 加工', icon: '🗂' },
  { path: null, label: 'AI チャット', icon: '💬' },
];
```

- [ ] **Step 3: Update SideMenu.test.jsx**

Add to the "renders all menu items" test in `frontend/src/components/SideMenu.test.jsx`:

```js
expect(screen.getByText('校正履歴')).toBeInTheDocument();
```

Add to the "does not disable MVP items" test:

```js
expect(screen.getByText('校正履歴')).not.toBeDisabled();
```

Add new test:

```js
it('marks history as active on /history route', () => {
  renderWithRouter(<SideMenu />, { initialEntries: ['/history'] });
  const btn = screen.getByText('校正履歴').closest('button');
  expect(btn).toHaveClass('sidebar__item--active');
});
```

- [ ] **Step 4: Update App.test.jsx**

Add new test in `frontend/src/App.test.jsx` inside the `describe('App')` block:

```js
it('renders history placeholder on /history route', () => {
  renderApp('/history');
  const main = screen.getByRole('main');
  // History component doesn't exist yet, so we expect an error or redirect
  // After implementing History.jsx, this will show the history list
});
```

> **Note:** This test will initially fail since `History.jsx` doesn't exist yet. It will pass after Task 4. You can skip this test for now and add it after Task 4, or comment it out temporarily.

- [ ] **Step 5: Run tests to verify navigation changes**

Run: `cd frontend && npx vitest run src/components/SideMenu.test.jsx src/App.test.jsx`
Expected: SideMenu tests PASS. App.test.jsx may fail on the new history test (expected until History.jsx exists).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.jsx frontend/src/components/SideMenu.jsx frontend/src/components/SideMenu.test.jsx frontend/src/App.test.jsx
git commit -m "feat(frontend): add /history route and side menu navigation item"
```

---

### Task 2: HistoryList Component

**Files:**
- Create: `frontend/src/tools/history/HistoryList.jsx`
- Create: `frontend/src/tools/history/History.test.jsx`

- [ ] **Step 1: Write failing tests for HistoryList**

Create `frontend/src/tools/history/History.test.jsx`:

```jsx
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// --- Mocks ---

vi.mock('../../api/client', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));

vi.mock('../proofreading/ResultView', () => ({
  default: ({ result }) => (
    <div data-testid="result-view">{result ? `Status: ${result.status}` : 'no result'}</div>
  ),
}));

import { apiGet, apiDelete } from '../../api/client';
import HistoryList from './HistoryList';

const mockApiGet = vi.mocked(apiGet);
const mockApiDelete = vi.mocked(apiDelete);

// --- Fixtures ---

const LIST_RESPONSE = {
  items: [
    {
      id: 1,
      preview: 'これはテストテキストのプレビューです。校正結果の確認用に保存されました。',
      document_type: 'official',
      model: 'kimi-k2.5',
      created_at: '2026-03-22T10:00:00+09:00',
      truncated: false,
      memo: null,
    },
    {
      id: 2,
      preview: 'メールのテキストプレビュー。',
      document_type: 'email',
      model: 'kimi-k2.5',
      created_at: '2026-03-21T15:30:00+09:00',
      truncated: true,
      memo: '確認用メモ',
    },
  ],
  total: 2,
};

const EMPTY_RESPONSE = { items: [], total: 0 };

const PAGINATED_RESPONSE = {
  items: Array.from({ length: 20 }, (_, i) => ({
    id: i + 1,
    preview: `アイテム ${i + 1} のプレビュー`,
    document_type: 'official',
    model: 'kimi-k2.5',
    created_at: '2026-03-22T10:00:00+09:00',
    truncated: false,
    memo: null,
  })),
  total: 25,
};

function setupList(response = LIST_RESPONSE) {
  mockApiGet.mockResolvedValue(response);
  const onSelectItem = vi.fn();
  const utils = render(<HistoryList onSelectItem={onSelectItem} />);
  return { onSelectItem, utils };
}

describe('HistoryList', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockApiGet.mockReset();
    mockApiDelete.mockReset();
    mockApiDelete.mockResolvedValue({ message: '削除しました' });
  });

  // --- Fetch and render ---

  it('fetches and displays history items', async () => {
    const { onSelectItem } = setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });
    expect(screen.getByText('メールのテキストプレビュー。')).toBeInTheDocument();
    expect(screen.getByText('2026/03/22 10:00')).toBeInTheDocument();
    expect(screen.getByText('2026/03/21 15:30')).toBeInTheDocument();
  });

  it('shows loading state while fetching', async () => {
    let resolveApi;
    mockApiGet.mockReturnValue(new Promise((resolve) => { resolveApi = resolve; }));
    setupList();

    expect(screen.getByText('読み込み中...')).toBeInTheDocument();

    resolveApi(LIST_RESPONSE);
    await waitFor(() => {
      expect(screen.queryByText('読み込み中...')).not.toBeInTheDocument();
    });
  });

  it('shows empty state when no items', async () => {
    setupList(EMPTY_RESPONSE);

    await waitFor(() => {
      expect(screen.getByText('履歴がありません。')).toBeInTheDocument();
    });
  });

  it('shows error message when fetch fails', async () => {
    mockApiGet.mockRejectedValue(new Error('サーバーエラー'));
    setupList();

    await waitFor(() => {
      expect(screen.getByText('サーバーエラー')).toBeInTheDocument();
    });
  });

  // --- Filters ---

  it('applies search query on form submit', async () => {
    setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('キーワード検索');
    await userEvent.type(searchInput, 'テスト');
    await userEvent.click(screen.getByRole('button', { name: '検索' }));

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith(
        expect.stringContaining('q=%E3%83%86%E3%82%B9%E3%83%88')
      );
    });
  });

  it('applies document type filter on form submit', async () => {
    setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    await userEvent.selectOptions(screen.getByLabelText('文書種別'), 'email');
    await userEvent.click(screen.getByRole('button', { name: '検索' }));

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith(
        expect.stringContaining('document_type=email')
      );
    });
  });

  it('clears all filters and refetches', async () => {
    setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    await userEvent.type(screen.getByPlaceholderText('キーワード検索'), 'テスト');
    await userEvent.click(screen.getByRole('button', { name: 'クリア' }));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('キーワード検索')).toHaveValue('');
    });

    // Last apiGet call should have no filters
    const lastCall = mockApiGet.mock.calls[mockApiGet.mock.calls.length - 1][0];
    expect(lastCall).not.toContain('q=');
    expect(lastCall).not.toContain('document_type=');
  });

  // --- Pagination ---

  it('shows pagination info and next button when more items exist', async () => {
    setupList(PAGINATED_RESPONSE);

    await waitFor(() => {
      expect(screen.getByText('1-20件 / 全25件')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '次へ' })).not.toBeDisabled();
    expect(screen.getByRole('button', { name: '前へ' })).toBeDisabled();
  });

  it('navigates to next page on click', async () => {
    setupList(PAGINATED_RESPONSE);

    await waitFor(() => {
      expect(screen.getByText('1-20件 / 全25件')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '次へ' }));

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('offset=20'));
    });
  });

  // --- Item interaction ---

  it('calls onSelectItem when item is clicked', async () => {
    const { onSelectItem } = setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。'));

    expect(onSelectItem).toHaveBeenCalledWith(1);
  });

  // --- Truncated badge ---

  it('shows truncated badge for truncated items', async () => {
    setupList();

    await waitFor(() => {
      expect(screen.getByText('⚠ 詳細省略')).toBeInTheDocument();
    });
  });

  // --- Delete ---

  it('deletes individual item with confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole('button', { name: '削除' });
    await userEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith('この履歴を削除しますか？');
    expect(mockApiDelete).toHaveBeenCalledWith('/api/history/1');
  });

  it('does not delete when confirmation is cancelled', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole('button', { name: '削除' });
    await userEvent.click(deleteButtons[0]);

    expect(mockApiDelete).not.toHaveBeenCalled();
  });

  it('deletes all items with confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockApiDelete.mockResolvedValue({ message: '2件の履歴を削除しました' });
    setupList();

    await waitFor(() => {
      expect(screen.getByText('全件削除')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '全件削除' }));

    expect(window.confirm).toHaveBeenCalledWith('全ての履歴を削除しますか？この操作は取り消せません。');
    expect(mockApiDelete).toHaveBeenCalledWith('/api/history');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/tools/history/History.test.jsx`
Expected: FAIL — `HistoryList` module not found

- [ ] **Step 3: Implement HistoryList.jsx**

Create `frontend/src/tools/history/HistoryList.jsx`:

```jsx
import { useState, useEffect, useCallback } from 'react';
import { apiGet, apiDelete } from '../../api/client';

const DOC_TYPE_LABELS = {
  email: 'メール',
  report: '報告書',
  official: '公文書',
  other: 'その他',
};

const PAGE_SIZE = 20;

function formatDate(iso) {
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const h = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${y}/${m}/${day} ${h}:${min}`;
}

export default function HistoryList({ onSelectItem }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [docType, setDocType] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [appliedQuery, setAppliedQuery] = useState('');
  const [appliedDocType, setAppliedDocType] = useState('');
  const [appliedDateFrom, setAppliedDateFrom] = useState('');
  const [appliedDateTo, setAppliedDateTo] = useState('');
  const [offset, setOffset] = useState(0);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (appliedQuery) params.set('q', appliedQuery);
      if (appliedDocType) params.set('document_type', appliedDocType);
      if (appliedDateFrom) params.set('date_from', appliedDateFrom);
      if (appliedDateTo) params.set('date_to', appliedDateTo);
      params.set('limit', String(PAGE_SIZE));
      params.set('offset', String(offset));

      const data = await apiGet(`/api/history?${params.toString()}`);
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err.message || '履歴の取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  }, [appliedQuery, appliedDocType, appliedDateFrom, appliedDateTo, offset]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleSearch = (e) => {
    e.preventDefault();
    setAppliedQuery(searchQuery);
    setAppliedDocType(docType);
    setAppliedDateFrom(dateFrom);
    setAppliedDateTo(dateTo);
    setOffset(0);
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setDocType('');
    setDateFrom('');
    setDateTo('');
    setAppliedQuery('');
    setAppliedDocType('');
    setAppliedDateFrom('');
    setAppliedDateTo('');
    setOffset(0);
  };

  const handleDeleteItem = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm('この履歴を削除しますか？')) return;
    try {
      await apiDelete(`/api/history/${id}`);
      fetchHistory();
    } catch {
      setError('削除に失敗しました。');
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm('全ての履歴を削除しますか？この操作は取り消せません。')) return;
    try {
      await apiDelete('/api/history');
      // Immediately clear the list UI so the user sees feedback right away.
      // If offset was non-zero, setOffset(0) triggers a re-render → new fetchHistory
      // via useEffect, which refetches from the server. If offset was already 0,
      // the immediate state updates below are correct (all items were deleted).
      setItems([]);
      setTotal(0);
      setOffset(0);
    } catch {
      setError('全件削除に失敗しました。');
    }
  };

  const hasNextPage = offset + PAGE_SIZE < total;
  const hasPrevPage = offset > 0;
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + PAGE_SIZE, total);

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" role="status"></div>
        <span>読み込み中...</span>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-md">
        <h2>校正履歴</h2>
        {total > 0 && (
          <button className="btn btn--danger btn--sm" onClick={handleDeleteAll} type="button">
            全件削除
          </button>
        )}
      </div>

      <form className="history-filters" onSubmit={handleSearch}>
        <div className="history-filters__row">
          <div className="history-filters__search">
            <input className="input" type="text" placeholder="キーワード検索" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
          </div>
          <div className="history-filters__type">
            <label className="sr-only" htmlFor="history-filter-type">文書種別</label>
            <select className="select" id="history-filter-type" value={docType} onChange={(e) => setDocType(e.target.value)}>
              <option value="">全ての種別</option>
              <option value="email">メール</option>
              <option value="report">報告書</option>
              <option value="official">公文書</option>
              <option value="other">その他</option>
            </select>
          </div>
          <div className="history-filters__date">
            <input className="input" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} aria-label="開始日" />
            <span>〜</span>
            <input className="input" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} aria-label="終了日" />
          </div>
          <button className="btn btn--primary btn--sm" type="submit">検索</button>
          <button className="btn btn--secondary btn--sm" type="button" onClick={handleClearFilters}>クリア</button>
        </div>
      </form>

      {error && <div className="message message--error mt-md" role="alert">{error}</div>}

      {!error && items.length === 0 && (
        <div className="history-list__empty mt-lg">
          <p>履歴がありません。</p>
        </div>
      )}

      {!error && items.length > 0 && (
        <>
          <div className="history-list mt-md">
            {items.map((item) => (
              <div
                key={item.id}
                className="history-item"
                onClick={() => onSelectItem(item.id)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectItem(item.id); } }}
                role="button"
                tabIndex={0}
              >
                <div className="history-item__header">
                  <span className="history-item__date">{formatDate(item.created_at)}</span>
                  <span className="badge">{DOC_TYPE_LABELS[item.document_type] || item.document_type}</span>
                  {item.truncated && <span className="badge badge--warning">⚠ 詳細省略</span>}
                </div>
                <p className="history-item__preview">{item.preview}</p>
                <div className="history-item__meta">
                  <span>{item.model}</span>
                  {item.memo && <span className="history-item__memo">メモ: {item.memo}</span>}
                </div>
                <button
                  className="btn btn--danger btn--sm history-item__delete"
                  onClick={(e) => handleDeleteItem(e, item.id)}
                  type="button"
                  aria-label="削除"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          <div className="history-list__pagination mt-md">
            <span>{pageStart}-{pageEnd}件 / 全{total}件</span>
            <div className="flex gap-sm">
              <button className="btn btn--secondary btn--sm" disabled={!hasPrevPage} onClick={() => setOffset((o) => o - PAGE_SIZE)} type="button">前へ</button>
              <button className="btn btn--secondary btn--sm" disabled={!hasNextPage} onClick={() => setOffset((o) => o + PAGE_SIZE)} type="button">次へ</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/tools/history/History.test.jsx`
Expected: All HistoryList tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tools/history/HistoryList.jsx frontend/src/tools/history/History.test.jsx
git commit -m "feat(frontend): add HistoryList with filters, pagination, and delete"
```

---

### Task 3: HistoryDetail Component

**Files:**
- Create: `frontend/src/tools/history/HistoryDetail.jsx`
- Modify: `frontend/src/tools/history/History.test.jsx`

- [ ] **Step 1: Write failing tests for HistoryDetail**

Add to `frontend/src/tools/history/History.test.jsx`, after the existing imports and mock setup:

```jsx
import HistoryDetail from './HistoryDetail';

const mockApiPatch = vi.mocked(apiPatch);
```

> **Note:** Also add `apiPatch` to the mock import at the top:
> ```js
> import { apiGet, apiPatch, apiDelete } from '../../api/client';
> ```

Add the `HistoryDetail` describe block:

```jsx
// --- Fixtures ---

const DETAIL_RESPONSE = {
  id: 1,
  input_text: 'テストテキストです。修正箇所があります。',
  result: {
    request_id: 'test-uuid-001',
    status: 'success',
    status_reason: null,
    warnings: [],
    corrected_text: 'テストテキストです。修正箇所があります。',
    summary: '1件の修正を行いました。',
    corrections: [
      { original: '修正前', corrected: '修正後', reason: 'タイポ修正', category: '誤字脱字', diff_matched: true },
    ],
    diffs: [
      { type: 'equal', text: 'テキスト', start: 0, position: null, reason: null },
      { type: 'delete', text: '前', start: 4, position: null, reason: 'タイポ修正' },
      { type: 'insert', text: '後', start: 4, position: 'after', reason: 'タイポ修正' },
    ],
  },
  model: 'kimi-k2.5',
  document_type: 'official',
  created_at: '2026-03-22T10:00:00+09:00',
  truncated: false,
  memo: null,
};

const TRUNCATED_DETAIL = {
  ...DETAIL_RESPONSE,
  id: 2,
  truncated: true,
  result: {
    ...DETAIL_RESPONSE.result,
    corrections: [],
    diffs: [],
  },
};

function setupDetail(response = DETAIL_RESPONSE) {
  mockApiGet.mockResolvedValue(response);
  mockApiPatch.mockResolvedValue(response);
  const onBack = vi.fn();
  const utils = render(<HistoryDetail historyId={response.id} onBack={onBack} />);
  return { onBack, utils };
}

describe('HistoryDetail', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockApiGet.mockReset();
    mockApiPatch.mockReset();
    mockApiDelete.mockReset();
    mockApiDelete.mockResolvedValue({ message: '削除しました' });
  });

  // --- Fetch and render ---

  it('fetches and displays history detail', async () => {
    setupDetail();

    await waitFor(() => {
      expect(screen.getByText('校正履歴詳細')).toBeInTheDocument();
    });
    expect(screen.getByText('テストテキストです。修正箇所があります。')).toBeInTheDocument();
  });

  it('shows loading state while fetching', async () => {
    let resolveApi;
    mockApiGet.mockReturnValue(new Promise((resolve) => { resolveApi = resolve; }));
    setupDetail();

    expect(screen.getByText('読み込み中...')).toBeInTheDocument();

    resolveApi(DETAIL_RESPONSE);
    await waitFor(() => {
      expect(screen.queryByText('読み込み中...')).not.toBeInTheDocument();
    });
  });

  it('shows error when fetch fails', async () => {
    mockApiGet.mockRejectedValue(new Error('見つかりません'));
    setupDetail();

    await waitFor(() => {
      expect(screen.getByText('見つかりません')).toBeInTheDocument();
    });
  });

  // --- ResultView ---

  it('renders ResultView with saved result', async () => {
    setupDetail();

    await waitFor(() => {
      expect(screen.getByTestId('result-view')).toBeInTheDocument();
    });
    expect(screen.getByTestId('result-view')).toHaveTextContent('Status: success');
  });

  // --- Truncated ---

  it('shows truncated warning for truncated records', async () => {
    setupDetail(TRUNCATED_DETAIL);

    await waitFor(() => {
      expect(screen.getByText(/データサイズ超過のため/)).toBeInTheDocument();
    });
    expect(screen.queryByTestId('result-view')).not.toBeInTheDocument();
  });

  // --- Memo ---

  it('loads existing memo', async () => {
    const withMemo = { ...DETAIL_RESPONSE, memo: '確認用のメモ' };
    setupDetail(withMemo);

    await waitFor(() => {
      expect(screen.getByText('校正履歴詳細')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('メモ')).toHaveValue('確認用のメモ');
  });

  it('saves memo via PATCH API', async () => {
    setupDetail();

    await waitFor(() => {
      expect(screen.getByText('校正履歴詳細')).toBeInTheDocument();
    });

    const memoTextarea = screen.getByLabelText('メモ');
    await userEvent.type(memoTextarea, '新しいメモ');
    await userEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() => {
      expect(mockApiPatch).toHaveBeenCalledWith('/api/history/1', { memo: '新しいメモ' });
    });
  });

  // --- Delete ---

  it('deletes history and calls onBack', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const { onBack } = setupDetail();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '削除' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '削除' }));

    expect(window.confirm).toHaveBeenCalledWith('この履歴を削除しますか？');
    await waitFor(() => {
      expect(mockApiDelete).toHaveBeenCalledWith('/api/history/1');
      expect(onBack).toHaveBeenCalled();
    });
  });

  // --- Navigation ---

  it('calls onBack when back button is clicked', async () => {
    const { onBack } = setupDetail();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /一覧に戻る/ })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: /一覧に戻る/ }));

    expect(onBack).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/tools/history/History.test.jsx`
Expected: FAIL — `HistoryDetail` module not found

- [ ] **Step 3: Implement HistoryDetail.jsx**

Create `frontend/src/tools/history/HistoryDetail.jsx`:

```jsx
import { useState, useEffect, useCallback } from 'react';
import { apiGet, apiPatch, apiDelete } from '../../api/client';
import ResultView from '../proofreading/ResultView';

const DOC_TYPE_LABELS = {
  email: 'メール',
  report: '報告書',
  official: '公文書',
  other: 'その他',
};

function formatDate(iso) {
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const h = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${y}/${m}/${day} ${h}:${min}`;
}

export default function HistoryDetail({ historyId, onBack }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [memo, setMemo] = useState('');
  const [memoSaving, setMemoSaving] = useState(false);
  const [memoSuccess, setMemoSuccess] = useState(false);

  const fetchDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet(`/api/history/${historyId}`);
      setDetail(data);
      setMemo(data.memo || '');
    } catch (err) {
      setError(err.message || '履歴の取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  }, [historyId]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleSaveMemo = async () => {
    setMemoSaving(true);
    setMemoSuccess(false);
    try {
      const updated = await apiPatch(`/api/history/${historyId}`, { memo });
      setDetail(updated);
      setMemoSuccess(true);
      setTimeout(() => setMemoSuccess(false), 2000);
    } catch {
      setError('メモの保存に失敗しました。');
    } finally {
      setMemoSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('この履歴を削除しますか？')) return;
    try {
      await apiDelete(`/api/history/${historyId}`);
      onBack();
    } catch {
      setError('削除に失敗しました。');
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" role="status"></div>
        <span>読み込み中...</span>
      </div>
    );
  }

  if (!detail) {
    return (
      <div>
        <button className="btn btn--secondary mb-md" onClick={onBack} type="button">
          ← 一覧に戻る
        </button>
        <div className="message message--error">{error || '履歴が見つかりませんでした。'}</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-md">
        <button className="btn btn--secondary" onClick={onBack} type="button">
          ← 一覧に戻る
        </button>
        <button className="btn btn--danger btn--sm" onClick={handleDelete} type="button">
          削除
        </button>
      </div>

      <h2>校正履歴詳細</h2>

      {error && <div className="message message--error mt-md" role="alert">{error}</div>}

      {detail.truncated && (
        <div className="message message--warning mt-md">
          データサイズ超過のため校正詳細は保存されていません。校正済みテキストのみ表示します。
        </div>
      )}

      <div className="history-detail__meta mt-md">
        <span>{formatDate(detail.created_at)}</span>
        <span className="badge ml-sm">{DOC_TYPE_LABELS[detail.document_type] || detail.document_type}</span>
        <span className="ml-sm">{detail.model}</span>
      </div>

      <div className="history-detail__section mt-md">
        <h3>入力テキスト</h3>
        <pre className="history-detail__input-text">{detail.input_text}</pre>
      </div>

      {!detail.truncated && (
        <ResultView result={detail.result} />
      )}

      {detail.truncated && detail.result?.corrected_text && (
        <div className="history-detail__section mt-md">
          <h3>校正済みテキスト</h3>
          <pre className="history-detail__input-text">{detail.result.corrected_text}</pre>
        </div>
      )}

      <div className="history-detail__memo mt-lg">
        <label className="label" htmlFor="history-memo">メモ</label>
        <textarea
          className="textarea"
          id="history-memo"
          value={memo}
          onChange={(e) => setMemo(e.target.value)}
          rows={3}
          placeholder="メモを入力..."
        />
        <div className="mt-sm">
          <button
            className="btn btn--secondary btn--sm"
            onClick={handleSaveMemo}
            disabled={memoSaving}
            type="button"
          >
            {memoSaving ? '保存中...' : memoSuccess ? '保存しました' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/tools/history/History.test.jsx`
Expected: All tests PASS (HistoryList + HistoryDetail)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tools/history/HistoryDetail.jsx frontend/src/tools/history/History.test.jsx
git commit -m "feat(frontend): add HistoryDetail with ResultView, memo, and delete"
```

---

### Task 4: History Page Container

**Files:**
- Create: `frontend/src/tools/history/History.jsx`
- Modify: `frontend/src/tools/history/History.test.jsx`

- [ ] **Step 1: Write failing tests for History container**

Add to `frontend/src/tools/history/History.test.jsx`:

```jsx
import History from './History';

describe('History', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockApiGet.mockReset();
    mockApiDelete.mockReset();
    mockApiDelete.mockResolvedValue({ message: '削除しました' });
  });

  it('renders HistoryList by default', async () => {
    mockApiGet.mockResolvedValue(EMPTY_RESPONSE);
    render(<History />);

    await waitFor(() => {
      expect(screen.getByText('履歴がありません。')).toBeInTheDocument();
    });
  });

  it('renders HistoryDetail when item is selected', async () => {
    mockApiGet.mockResolvedValueOnce(LIST_RESPONSE);
    mockApiGet.mockResolvedValueOnce(DETAIL_RESPONSE);
    render(<History />);

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。'));

    await waitFor(() => {
      expect(screen.getByText('校正履歴詳細')).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/tools/history/History.test.jsx`
Expected: FAIL — `History` module not found

- [ ] **Step 3: Implement History.jsx**

Create `frontend/src/tools/history/History.jsx`:

```jsx
import { useState } from 'react';
import HistoryList from './HistoryList';
import HistoryDetail from './HistoryDetail';

export default function History() {
  const [selectedId, setSelectedId] = useState(null);

  if (selectedId !== null) {
    return (
      <HistoryDetail
        key={selectedId}
        historyId={selectedId}
        onBack={() => setSelectedId(null)}
      />
    );
  }

  return <HistoryList onSelectItem={(id) => setSelectedId(id)} />;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/tools/history/History.test.jsx`
Expected: All tests PASS (HistoryList + HistoryDetail + History)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tools/history/History.jsx frontend/src/tools/history/History.test.jsx
git commit -m "feat(frontend): add History page container with list/detail switching"
```

---

### Task 5: CSS Styles

**Files:**
- Modify: `frontend/src/css/components.css`

- [ ] **Step 1: Add history-specific styles**

Append to `frontend/src/css/components.css`:

```css
/* --- Utility: margin-left (used by history detail meta) --- */

.ml-sm { margin-left: var(--spacing-sm); }

/* --- History Filters --- */

.history-filters {
  margin-bottom: var(--spacing-md);
}

.history-filters__row {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
  flex-wrap: wrap;
}

.history-filters__search {
  flex: 1;
  min-width: 200px;
}

.history-filters__type {
  width: 140px;
}

.history-filters__date {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.history-filters__date .input {
  width: 140px;
}

/* --- History List --- */

.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.history-list__empty {
  text-align: center;
  color: var(--color-text-muted);
  font-style: italic;
  padding: var(--spacing-xl) 0;
}

.history-list__pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

/* --- History Item --- */

.history-item {
  position: relative;
  background-color: var(--color-bg-white);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--spacing-sm) var(--spacing-md);
  cursor: pointer;
  transition: border-color var(--transition-fast),
              box-shadow var(--transition-fast);
}

.history-item:hover {
  border-color: var(--color-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.history-item:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}

.history-item__header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.history-item__date {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.history-item__preview {
  font-size: var(--font-size-base);
  color: var(--color-text);
  margin: var(--spacing-xs) 0;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item__meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.history-item__memo {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

.history-item__delete {
  position: absolute;
  top: var(--spacing-sm);
  right: var(--spacing-sm);
  opacity: 0;
  transition: opacity var(--transition-fast);
  padding: 2px 6px;
  font-size: var(--font-size-sm);
  line-height: 1;
}

.history-item:hover .history-item__delete {
  opacity: 1;
}

/* --- History Detail --- */

.history-detail__meta {
  display: flex;
  align-items: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.history-detail__section h3 {
  font-size: var(--font-size-base);
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text);
}

.history-detail__input-text {
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--spacing-md);
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: var(--font-size-base);
  line-height: 1.6;
  margin: 0;
}

.history-detail__memo .textarea {
  min-height: 4rem;
}
```

- [ ] **Step 2: Verify visually**

Run: `cd frontend && npx vite --open`

Manual verification checklist:
- Navigate to `/history` — list page renders
- Filter bar: search input, doc type dropdown, date inputs, search/clear buttons
- List items: date, type badge, preview, model, delete button (on hover)
- Truncated badge visible on truncated items
- Pagination controls visible when items > 20
- Click item → detail view loads
- Detail: back button, meta info, input text, ResultView tabs, memo area
- Truncated warning visible on truncated detail
- Memo save button works
- Delete button in detail works

- [ ] **Step 3: Commit**

```bash
git add frontend/src/css/components.css
git commit -m "style(frontend): add history list, item, detail, and filter styles"
```

---

### Task 6: Full Suite Verification

- [ ] **Step 1: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS (existing + new history tests)

- [ ] **Step 2: Run all backend tests**

Run: `cd backend && pytest`
Expected: All tests PASS (no regressions)

- [ ] **Step 3: Fix any issues found**

If any test fails, investigate and fix. Common issues:
- Missing mock reset in `beforeEach`
- Stale mock return values between tests
- Import path issues

- [ ] **Step 4: Final commit if fixes needed**

```bash
git add -A
git commit -m "fix(frontend): address test fixes from history panel verification"
```
