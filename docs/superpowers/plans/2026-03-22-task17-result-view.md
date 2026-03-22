# Task 17: 結果表示 — フレームワーク & タブ③ コメント一覧 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `ResultView.jsx` component — a pure display component that renders proofreading results with a 3-tab framework, status-based UI branching, large rewrite warnings, and a fully implemented Tab ③ (comments list with `diff_matched` badge).

**Architecture:** `ResultView.jsx` is a stateless-ish display component — it receives the full `ProofreadResponse` object and an `onRetry` callback via props. It manages only `activeTab` state internally. The 3-tab framework renders tab bar + content area; tabs ①② show placeholder text (DiffView.jsx is Task 18); tab ③ renders a numbered correction list with original/corrected/reason/category fields and a "参考（AI推定）" badge for `diff_matched: false` items. Status branching (§3.3.4 table) determines which tabs are available, what messages/warnings to show, and whether corrected_text is displayed prominently.

**Tech Stack:** React 18, Vitest, React Testing Library, @testing-library/user-event, plain CSS (no Tailwind)

**Design Spec References:** §3.3.4 (校正結果表示), §4.6 (diff と corrections の対応付け), §3.3.5 (処理中状態), §5.2 (レスポンス JSON 構造)

---

## File Structure

### New files (2)

| File | Responsibility |
|------|---------------|
| `src/tools/proofreading/ResultView.jsx` | Result display: 3-tab framework, status branching, Tab ③ comments list, large rewrite warning, corrected_text display |
| `src/tools/proofreading/ResultView.test.jsx` | Tests for all ResultView behaviors (19 tests) |

### Modified files (2)

| File | Changes |
|------|---------|
| `src/tools/proofreading/Proofreading.jsx` | Import ResultView, add `result` state (initially null), conditionally render below InputArea + OptionPanel |
| `src/css/components.css` | Add `.result-view`, `.correction-list`, `.correction-item` CSS classes |

### Key Constraints

- **No innerHTML injection** — all rendering via React JSX only (§8.2, CLAUDE.md)
- **No Tailwind** — plain CSS only (CLAUDE.md)
- **ResultView is a pure display component** — no API calls, no side effects, receives data via props only
- **Frontend does NOT reconstruct `corrected_text` from diffs** — diffs are for display only (design principle)
- **Tab ①② are placeholders** — DiffView.jsx is Task 18; ResultView renders placeholder text for these tabs
- **Status branching follows §3.3.4 table exactly** — determines available tabs, messages, and corrected_text visibility
- **"表示は差分ベース" notice shown in all non-error states** — per §3.3.4 UI spec

---

## Task 1: ResultView テストの作成

### Step 1: テストファイルの作成

Create `frontend/src/tools/proofreading/ResultView.test.jsx`:

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ResultView from './ResultView';

// --- Test data factory ---

function createResult(overrides = {}) {
  return {
    request_id: 'test-uuid-1234',
    status: 'success',
    status_reason: null,
    warnings: [],
    corrected_text: '校正済みテキストです。',
    summary: '3 件の修正を行いました。',
    corrections: [
      {
        original: '修正前テキスト',
        corrected: '修正後テキスト',
        reason: '誤字を修正しました。',
        category: '誤字脱字',
        diff_matched: true,
      },
    ],
    diffs: [
      { type: 'equal', text: '前半', start: 0, position: null, reason: null },
      { type: 'delete', text: '旧', start: 2, position: null, reason: '理由' },
      { type: 'insert', text: '新', start: 2, position: 'after', reason: '理由' },
      { type: 'equal', text: '後半', start: 3, position: null, reason: null },
    ],
    ...overrides,
  };
}

describe('ResultView', () => {
  // --- Null result ---

  it('returns null when result is null', () => {
    const { container } = render(<ResultView result={null} />);
    expect(container.innerHTML).toBe('');
  });

  // --- Success status ---

  describe('success status', () => {
    it('renders all 3 tabs', () => {
      render(<ResultView result={createResult()} />);
      expect(screen.getByRole('tab', { name: /ハイライト表示/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /比較表示/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /コメント一覧/ })).toBeInTheDocument();
    });

    it('renders summary text', () => {
      render(<ResultView result={createResult()} />);
      expect(screen.getByText('3 件の修正を行いました。')).toBeInTheDocument();
    });

    it('renders diff-based notice', () => {
      render(<ResultView result={createResult()} />);
      expect(screen.getByText(/表示は差分ベースです/)).toBeInTheDocument();
    });

    it('defaults to first tab (highlight) as active', () => {
      render(<ResultView result={createResult()} />);
      expect(screen.getByRole('tab', { name: /ハイライト表示/ })).toHaveAttribute(
        'aria-selected',
        'true',
      );
    });

    it('does not show status message for success', () => {
      render(<ResultView result={createResult()} />);
      expect(screen.queryByText(/タイムアウト/)).not.toBeInTheDocument();
      expect(screen.queryByText(/不完全でした/)).not.toBeInTheDocument();
    });

    it('does not render summary section when summary is null', () => {
      const { container } = render(<ResultView result={createResult({ summary: null })} />);
      expect(container.querySelector('.result-view__summary')).toBeNull();
    });
  });

  // --- Large rewrite warning ---

  describe('large rewrite warning', () => {
    it('shows warning when warnings includes large_rewrite', () => {
      render(<ResultView result={createResult({ warnings: ['large_rewrite'] })} />);
      expect(screen.getByText(/AI が広範囲を書き換えました/)).toBeInTheDocument();
    });

    it('does not show warning when warnings is empty', () => {
      render(<ResultView result={createResult({ warnings: [] })} />);
      expect(screen.queryByText(/AI が広範囲を書き換えました/)).not.toBeInTheDocument();
    });
  });

  // --- Tab ③ comments list ---

  describe('tab ③ comments list', () => {
    it('shows corrections with original, corrected, reason, category', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} />);

      await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));

      expect(screen.getByText('修正前テキスト')).toBeInTheDocument();
      expect(screen.getByText('修正後テキスト')).toBeInTheDocument();
      expect(screen.getByText('誤字を修正しました。')).toBeInTheDocument();
      expect(screen.getByText('誤字脱字')).toBeInTheDocument();
    });

    it('shows "修正箇所はありません" when corrections is empty', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult({ corrections: [] })} />);

      await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));
      expect(screen.getByText('修正箇所はありません。')).toBeInTheDocument();
    });

    it('shows "参考（AI推定）" badge for diff_matched: false', async () => {
      const user = userEvent.setup();
      render(
        <ResultView
          result={createResult({
            corrections: [
              {
                original: 'ですます',
                corrected: 'である',
                reason: '文体を統一しました。',
                category: '文体',
                diff_matched: false,
              },
            ],
          })}
        />,
      );

      await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));
      expect(screen.getByText('参考（AI推定）')).toBeInTheDocument();
    });

    it('does not show badge for diff_matched: true', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} />);

      await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));
      expect(screen.queryByText('参考（AI推定）')).not.toBeInTheDocument();
    });

    it('handles correction with missing reason gracefully', async () => {
      const user = userEvent.setup();
      render(
        <ResultView
          result={createResult({
            corrections: [
              {
                original: 'A',
                corrected: 'B',
                reason: null,
                category: '誤字脱字',
                diff_matched: true,
              },
            ],
          })}
        />,
      );

      await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));
      expect(screen.getByText('A')).toBeInTheDocument();
      expect(screen.getByText('B')).toBeInTheDocument();
      // No crash, no reason label when reason is null
      expect(screen.queryByText(/^理由：/)).not.toBeInTheDocument();
    });
  });

  // --- Partial status ---

  describe('partial status', () => {
    it('shows all tabs + info message for diff_timeout with diffs', () => {
      render(
        <ResultView
          result={createResult({
            status: 'partial',
            status_reason: 'diff_timeout',
            diffs: [{ type: 'equal', text: 'テスト', start: 0, position: null, reason: null }],
          })}
        />,
      );

      expect(screen.getByText(/差分計算がタイムアウトしました/)).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /ハイライト表示/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /コメント一覧/ })).toBeInTheDocument();
    });

    it('shows only tab ③ + corrected text for diff_timeout without diffs', () => {
      render(
        <ResultView
          result={createResult({
            status: 'partial',
            status_reason: 'diff_timeout',
            diffs: [],
          })}
        />,
      );

      expect(screen.getByText(/差分計算に失敗しました/)).toBeInTheDocument();
      expect(screen.queryByRole('tab', { name: /ハイライト表示/ })).not.toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /コメント一覧/ })).toBeInTheDocument();
      // corrected_text displayed prominently
      expect(screen.getByText('校正済みテキスト')).toBeInTheDocument();
    });

    it('shows only tab ③ + corrected text for parse_fallback', () => {
      render(
        <ResultView
          result={createResult({
            status: 'partial',
            status_reason: 'parse_fallback',
            diffs: [],
          })}
        />,
      );

      expect(screen.getByText(/AI の応答形式が不完全でした/)).toBeInTheDocument();
      expect(screen.queryByRole('tab', { name: /ハイライト表示/ })).not.toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /コメント一覧/ })).toBeInTheDocument();
      expect(screen.getByText('校正済みテキスト')).toBeInTheDocument();
    });
  });

  // --- Error status ---

  describe('error status', () => {
    it('shows error message and retry button', () => {
      const onRetry = vi.fn();
      render(
        <ResultView
          result={createResult({ status: 'error', status_reason: 'parse_fallback' })}
          onRetry={onRetry}
        />,
      );

      expect(screen.getByText(/校正結果を取得できませんでした/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
    });

    it('calls onRetry when retry button is clicked', async () => {
      const onRetry = vi.fn();
      const user = userEvent.setup();
      render(
        <ResultView
          result={createResult({ status: 'error', status_reason: 'parse_fallback' })}
          onRetry={onRetry}
        />,
      );

      await user.click(screen.getByRole('button', { name: '再試行' }));
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it('does not show retry button without onRetry prop', () => {
      render(
        <ResultView
          result={createResult({ status: 'error', status_reason: 'parse_fallback' })}
        />,
      );

      expect(screen.queryByRole('button', { name: '再試行' })).not.toBeInTheDocument();
    });

    it('does not show tabs or notice for error status', () => {
      render(
        <ResultView
          result={createResult({ status: 'error', status_reason: 'parse_fallback' })}
        />,
      );

      expect(screen.queryByRole('tab')).not.toBeInTheDocument();
      expect(screen.queryByText(/表示は差分ベース/)).not.toBeInTheDocument();
    });
  });

  // --- Tab switching ---

  describe('tab switching', () => {
    it('switches content when tab is clicked', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} />);

      // Initially on highlight tab — shows placeholder
      expect(screen.getByText(/ハイライト表示は今後実装されます/)).toBeInTheDocument();

      // Switch to compare tab
      await user.click(screen.getByRole('tab', { name: /比較表示/ }));
      expect(screen.getByText(/比較表示は今後実装されます/)).toBeInTheDocument();

      // Switch to comments tab
      await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));
      expect(screen.getByText('修正前テキスト')).toBeInTheDocument();
    });
  });
});
```

### Step 2: テストを実行して失敗を確認

Run: `cd frontend && npx vitest run src/tools/proofreading/ResultView.test.jsx`
Expected: FAIL — `Cannot find module './ResultView'`

---

## Task 2: ResultView.jsx の実装 & CSS

### Step 1: ResultView.jsx の作成

Create `frontend/src/tools/proofreading/ResultView.jsx`:

```jsx
import { useState } from 'react';

const TABS = [
  { id: 'highlight', label: '① ハイライト表示' },
  { id: 'compare', label: '② 比較表示' },
  { id: 'comments', label: '③ コメント一覧' },
];

/**
 * Determine which tabs are available based on result status.
 * §3.3.4 status branching table.
 */
function getAvailableTabs(result) {
  if (result.status === 'error') return [];
  if (result.status === 'partial') {
    if (result.status_reason === 'parse_fallback') return [TABS[2]];
    if (result.status_reason === 'diff_timeout') {
      return result.diffs && result.diffs.length > 0 ? TABS : [TABS[2]];
    }
  }
  return TABS;
}

/**
 * Get status message for partial/error states.
 * Returns { type, text } or null.
 */
function getStatusMessage(result) {
  if (result.status === 'partial') {
    if (result.status_reason === 'diff_timeout') {
      if (result.diffs && result.diffs.length > 0) {
        return {
          type: 'info',
          text: '差分計算がタイムアウトしました。行単位での差分を表示しています。',
        };
      }
      return {
        type: 'info',
        text: '差分計算に失敗しました。校正済みテキストのみ表示します。',
      };
    }
    if (result.status_reason === 'parse_fallback') {
      return {
        type: 'info',
        text: 'AI の応答形式が不完全でした。取得できたテキストのみ表示します。',
      };
    }
  }
  if (result.status === 'error') {
    return { type: 'error', text: '校正結果を取得できませんでした。' };
  }
  return null;
}

/**
 * Tab ③: Comments list — displays all corrections as a numbered list.
 * Each item shows original, corrected, reason, category.
 * diff_matched: false items get a badge.
 */
function CorrectionList({ corrections }) {
  if (!corrections || corrections.length === 0) {
    return <p className="result-view__empty">修正箇所はありません。</p>;
  }

  return (
    <ol className="correction-list">
      {corrections.map((c, i) => (
        <li key={i} className="correction-item">
          <div className="correction-item__header">
            <span className="correction-item__number">{i + 1}</span>
            <span className="correction-item__category">{c.category}</span>
            {!c.diff_matched && (
              <span className="badge badge--info">参考（AI推定）</span>
            )}
          </div>
          <div className="correction-item__pair">
            <div className="correction-item__original">
              <span className="correction-item__label">修正前：</span>
              <span className="diff-delete">{c.original}</span>
            </div>
            <div className="correction-item__corrected">
              <span className="correction-item__label">修正後：</span>
              <span className="diff-insert">{c.corrected}</span>
            </div>
          </div>
          {c.reason && (
            <div className="correction-item__reason">
              <span className="correction-item__label">理由：</span>
              {c.reason}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}

/**
 * ResultView — displays proofreading results with 3-tab framework.
 *
 * Props:
 *   result: ProofreadResponse object or null
 *   onRetry: callback for retry button (error state)
 *
 * Status branching per design spec §3.3.4:
 *   success: all 3 tabs, summary, notice
 *   partial + diff_timeout + diffs: all 3 tabs + info message
 *   partial + diff_timeout + no diffs: tab ③ only + corrected_text
 *   partial + parse_fallback: tab ③ only + corrected_text
 *   error: no tabs, error message + retry button
 */
export default function ResultView({ result, onRetry }) {
  // IMPORTANT: useState must be called before any conditional returns
  // to comply with React's Rules of Hooks (hooks must not be conditional).
  // The initial value computes available tabs from result, defaulting to empty.
  const [activeTab, setActiveTab] = useState(() => {
    if (!result) return null;
    const tabs = getAvailableTabs(result);
    return tabs.length > 0 ? tabs[0].id : null;
  });

  if (!result) return null;

  const availableTabs = getAvailableTabs(result);
  const statusMessage = getStatusMessage(result);
  const hasLargeRewrite = result.warnings && result.warnings.includes('large_rewrite');
  const showCorrectedText =
    result.status === 'partial' && (!result.diffs || result.diffs.length === 0);

  // Error state: no tabs, error message + retry
  if (result.status === 'error') {
    return (
      <div className="result-view mt-lg">
        <div className="message message--error">{statusMessage.text}</div>
        {onRetry && (
          <button className="btn btn--secondary mt-md" onClick={onRetry}>
            再試行
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="result-view mt-lg">
      {/* Large rewrite warning */}
      {hasLargeRewrite && (
        <div className="message message--warning mb-md">
          ⚠️ AI が広範囲を書き換えました。内容を十分ご確認ください。
        </div>
      )}

      {/* Status reason message */}
      {statusMessage && (
        <div className={`message message--${statusMessage.type} mb-md`}>
          {statusMessage.text}
        </div>
      )}

      {/* Summary */}
      {result.summary && (
        <div className="result-view__summary mb-md">{result.summary}</div>
      )}

      {/* Diff-based notice (shown in all non-error states) */}
      <div className="result-view__notice mb-md">
        表示は差分ベースです。コメントは AI 推定であり正確でない場合があります。
      </div>

      {/* Corrected text (prominent display for partial states without diffs) */}
      {showCorrectedText && result.corrected_text && (
        <div className="result-view__corrected-text mb-md">
          <h4>校正済みテキスト</h4>
          <pre className="result-view__corrected-text-body">
            {result.corrected_text}
          </pre>
        </div>
      )}

      {/* Tab bar + content */}
      {availableTabs.length > 0 && (
        <>
          <div className="tabs" role="tablist">
            {availableTabs.map((tab) => (
              <button
                key={tab.id}
                role="tab"
                className={`tab ${activeTab === tab.id ? 'tab--active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
                aria-selected={activeTab === tab.id}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="result-view__panel" role="tabpanel">
            {activeTab === 'highlight' && (
              <div className="result-view__placeholder">
                <p>ハイライト表示は今後実装されます。</p>
              </div>
            )}
            {activeTab === 'compare' && (
              <div className="result-view__placeholder">
                <p>比較表示は今後実装されます。</p>
              </div>
            )}
            {activeTab === 'comments' && (
              <CorrectionList corrections={result.corrections} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
```

### Step 2: CSS スタイルの追加

Append to `frontend/src/css/components.css` (after the Option Panel section at the end of the file):

```css
/* --- Result View (§3.3.4) --- */

.result-view {
  border-top: 2px solid var(--color-border);
  padding-top: var(--spacing-md);
}

.result-view__summary {
  font-size: var(--font-size-base);
  line-height: 1.6;
  color: var(--color-text);
}

.result-view__notice {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-style: italic;
}

.result-view__corrected-text h4 {
  font-size: var(--font-size-base);
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text);
}

.result-view__corrected-text-body {
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--spacing-md);
  font-size: var(--font-size-base);
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow-y: auto;
}

.result-view__empty {
  color: var(--color-text-muted);
  font-style: italic;
}

.result-view__placeholder {
  color: var(--color-text-muted);
  font-style: italic;
  padding: var(--spacing-lg) 0;
  text-align: center;
}

.result-view__panel {
  min-height: 100px;
}

/* --- Correction List (Tab ③) --- */

.correction-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.correction-item {
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--spacing-sm) var(--spacing-md);
}

.correction-item__header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.correction-item__number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: var(--color-primary);
  color: #fff;
  font-size: var(--font-size-sm);
  font-weight: 600;
  flex-shrink: 0;
}

.correction-item__category {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  background-color: var(--color-bg);
  padding: 1px var(--spacing-sm);
  border-radius: var(--radius-sm);
}

.correction-item__pair {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.correction-item__original,
.correction-item__corrected {
  font-size: var(--font-size-base);
  line-height: 1.6;
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-sm);
}

.correction-item__original {
  background-color: rgba(255, 204, 204, 0.3);
}

.correction-item__corrected {
  background-color: rgba(204, 255, 204, 0.3);
}

.correction-item__label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
  margin-right: var(--spacing-xs);
}

.correction-item__reason {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-top: var(--spacing-xs);
  padding-top: var(--spacing-xs);
  border-top: 1px dashed var(--color-border);
}
```

### Step 3: テストを実行して成功を確認

Run: `cd frontend && npx vitest run src/tools/proofreading/ResultView.test.jsx`
Expected: All 19 tests PASS

### Step 4: コミット

```bash
cd frontend
git add src/tools/proofreading/ResultView.jsx src/tools/proofreading/ResultView.test.jsx src/css/components.css
git commit -m "feat(frontend): add ResultView with 3-tab framework and comments list (§3.3.4)

- 3-tab framework: highlight (placeholder), compare (placeholder), comments
- Tab ③: numbered correction list with original/corrected/reason/category
- '参考（AI推定）' badge for diff_matched: false corrections
- Status branching: success/partial/error per §3.3.4 table
- Large rewrite warning display
- Corrected text prominent display for partial states without diffs
- Diff-based notice shown in all non-error states"
```

---

## Task 3: Proofreading.jsx への統合

### Step 1: ResultView のインポートとレンダリング

Update `frontend/src/tools/proofreading/Proofreading.jsx`:

```jsx
import { useState } from 'react';
import InputArea from './InputArea';
import OptionPanel from './OptionPanel';
import ResultView from './ResultView';

function Proofreading() {
  const [options, setOptions] = useState(null);
  const [isSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = (text, documentType) => {
    // Task 19 will implement the full proofreading flow:
    // preprocessing -> API call -> result display
    console.log('Proofread requested:', { textLength: text.length, documentType, options });
  };

  return (
    <div>
      <h2>AI 文書校正</h2>
      <div className="mt-md">
        <InputArea onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </div>
      <div className="mt-md">
        <OptionPanel onChange={setOptions} disabled={isSubmitting} />
      </div>
      <ResultView result={result} />
    </div>
  );
}

export default Proofreading;
```

### Step 2: フルテストスイートの実行

Run: `cd frontend && npx vitest run`
Expected: All tests PASS (existing ~104 tests + 19 new ResultView tests)

### Step 3: コミット

```bash
cd frontend
git add src/tools/proofreading/Proofreading.jsx
git commit -m "feat(frontend): integrate ResultView into Proofreading page

Add result state and conditional rendering below InputArea + OptionPanel.
Actual API call wiring deferred to Task 19."
```
