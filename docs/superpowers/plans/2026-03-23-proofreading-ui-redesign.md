# Proofreading UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace diff-centric 3-tab layout (Highlight/Compare/Comments) with full-text reading experience (校正前/校正後/差分).

**Architecture:** Create a new `FullTextView` component for plain text display. Restructure `ResultView` to use new tab names and render `FullTextView` for before/after tabs. Rename `CorrectionList` to `DiffListView` and add summary/warnings. Thread `originalText` prop from parent components.

**Tech Stack:** React 18, Vitest, React Testing Library, plain CSS

**Spec:** `docs/superpowers/specs/2026-03-23-proofreading-ui-redesign-design.md`

---

### Task 1: Create FullTextView component with tests

**Files:**
- Create: `frontend/src/tools/proofreading/FullTextView.jsx`
- Create: `frontend/src/tools/proofreading/FullTextView.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
// FullTextView.test.jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import FullTextView from './FullTextView';

describe('FullTextView', () => {
  it('renders text content', () => {
    render(<FullTextView text="テスト文書です。" label="校正後" />);
    expect(screen.getByText('テスト文書です。')).toBeInTheDocument();
  });

  it('renders empty string without crashing', () => {
    const { container } = render(<FullTextView text="" label="校正後" />);
    expect(container.innerHTML).not.toBe('');
  });

  it('applies full-text-view class to container', () => {
    const { container } = render(<FullTextView text="内容" label="校正前" />);
    expect(container.firstChild).toHaveClass('full-text-view');
  });

  it('has role="region" and aria-label for accessibility', () => {
    render(<FullTextView text="内容" label="校正後" />);
    const region = screen.getByRole('region', { name: '校正後' });
    expect(region).toBeInTheDocument();
  });

  it('preserves whitespace with pre-wrap', () => {
    const { container } = render(<FullTextView text="1行目\n2行目" label="テスト" />);
    const el = container.querySelector('.full-text-view');
    expect(el).toHaveStyle({ 'white-space': 'pre-wrap' });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/tools/proofreading/FullTextView.test.jsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```jsx
// FullTextView.jsx
export default function FullTextView({ text, label }) {
  return (
    <div className="full-text-view" role="region" aria-label={label}>
      {text}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/tools/proofreading/FullTextView.test.jsx`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tools/proofreading/FullTextView.jsx frontend/src/tools/proofreading/FullTextView.test.jsx
git commit -m "feat(proofreading): add FullTextView component with tests"
```

---

### Task 2: Add FullTextView CSS

**Files:**
- Modify: `frontend/src/css/components.css` (after `.result-view__empty` block, around line 616)

- [ ] **Step 1: Add CSS for full-text-view**

Insert after `.result-view__empty` block (around line 616):

```css
/* Full text view: plain text display for before/after tabs */
.full-text-view {
  font-size: var(--font-size-base);
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
  padding: var(--spacing-md);
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  max-height: 400px;
  overflow-y: auto;
  color: var(--color-text);
}
```

- [ ] **Step 2: Verify no visual regression**

Run: `cd frontend && npx vitest run`
Expected: All existing tests pass

- [ ] **Step 3: Commit**

```bash
git add frontend/src/css/components.css
git commit -m "style(proofreading): add full-text-view CSS styles"
```

---

### Task 3: Restructure ResultView — tabs and FullTextView integration

**Files:**
- Modify: `frontend/src/tools/proofreading/ResultView.jsx`

- [ ] **Step 1: Update imports and TABS constant**

Replace lines 1-8 with:

```jsx
import { useState } from 'react';
import FullTextView from './FullTextView';

const TABS = [
  { id: 'before', label: '校正前' },
  { id: 'after', label: '校正後' },
  { id: 'diff', label: '差分' },
];
```

- [ ] **Step 2: Update getAvailableTabs**

Replace `getAvailableTabs` function (lines 14-23):

```jsx
function getAvailableTabs(result) {
  if (result.status === 'error') return [];
  if (result.status === 'partial') {
    if (result.status_reason === 'parse_fallback') return [TABS[1], TABS[2]];
    if (result.status_reason === 'diff_timeout') {
      return result.diffs && result.diffs.length > 0 ? TABS : [TABS[1], TABS[2]];
    }
  }
  return TABS;
}
```

- [ ] **Step 3: Update component signature**

Replace line 113:

```jsx
export default function ResultView({ result, originalText, onRetry }) {
```

- [ ] **Step 4: Replace tab content rendering**

Replace lines 145-213 (the return block) with:

```jsx
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
            {activeTab === 'before' && (
              <FullTextView text={originalText} label="校正前" />
            )}
            {activeTab === 'after' && (
              <FullTextView text={result.corrected_text} label="校正後" />
            )}
            {activeTab === 'diff' && (
              <DiffListView
                corrections={result.corrections}
                summary={result.summary}
                warnings={result.warnings}
              />
            )}
          </div>
        </>
      )}

      {/* Notice (below tabs, all non-error states) */}
      <div className="result-view__notice mt-md">
        ※ 差分タブのコメントは AI 推定であり、正確でない場合があります。
      </div>
    </div>
  );
```

- [ ] **Step 5: Rename CorrectionList to DiffListView and add summary/warnings**

Replace the `CorrectionList` function (lines 61-97) with:

```jsx
function DiffListView({ corrections, summary, warnings }) {
  const hasLargeRewrite = warnings && warnings.includes('large_rewrite');

  return (
    <div>
      {summary && (
        <div className="diff-list-summary">{summary}</div>
      )}
      {hasLargeRewrite && (
        <div className="diff-list-warning">
          ⚠️ AI が広範囲を書き換えました。内容を十分ご確認ください。
        </div>
      )}
      {!corrections || corrections.length === 0 ? (
        <p className="result-view__empty">修正箇所はありません。</p>
      ) : (
        <ol className="correction-list">
          {corrections.map((c, i) => (
            <li key={i} className="correction-item">
              <div className="correction-item__header">
                <span className="correction-item__number">{i + 1}</span>
                <span className="correction-item__category">{c.category}</span>
                {c.diff_matched === false && (
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
      )}
    </div>
  );
}
```

- [ ] **Step 6: Remove showCorrectedText variable**

Remove line 128-129 (`showCorrectedText` variable) since corrected text is now shown in the "after" tab.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/tools/proofreading/ResultView.jsx
git commit -m "feat(proofreading): restructure ResultView with before/after/diff tabs"
```

---

### Task 4: Update parent components to pass originalText

**Files:**
- Modify: `frontend/src/tools/proofreading/Proofreading.jsx:140`
- Modify: `frontend/src/tools/history/HistoryDetail.jsx:126`

- [ ] **Step 1: Update Proofreading.jsx**

Change line 140 from:
```jsx
      <ResultView result={result} onRetry={handleRetry} />
```
to:
```jsx
      <ResultView result={result} originalText={lastParams?.rawText ?? ''} onRetry={handleRetry} />
```

- [ ] **Step 2: Update HistoryDetail.jsx**

Change line 126 from:
```jsx
        <ResultView result={detail.result} />
```
to:
```jsx
        <ResultView result={detail.result} originalText={detail.input_text ?? ''} />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tools/proofreading/Proofreading.jsx frontend/src/tools/history/HistoryDetail.jsx
git commit -m "feat(proofreading): pass originalText prop to ResultView from parents"
```

---

### Task 5: Add DiffListView CSS

**Files:**
- Modify: `frontend/src/css/components.css`

- [ ] **Step 1: Add CSS for diff-list-summary and diff-list-warning**

Insert after the `.full-text-view` block (added in Task 2):

```css
.diff-list-summary {
  padding: var(--spacing-sm) var(--spacing-md);
  margin-bottom: var(--spacing-md);
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  color: var(--color-text);
  font-size: var(--font-size-sm);
}

.diff-list-warning {
  padding: var(--spacing-xs) var(--spacing-md);
  margin-bottom: var(--spacing-md);
  color: var(--color-warning);
  font-size: var(--font-size-sm);
  border-left: 3px solid var(--color-warning);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/css/components.css
git commit -m "style(proofreading): add diff-list-summary and diff-list-warning styles"
```

---

### Task 6: Delete DiffView and obsolete CSS

**Files:**
- Delete: `frontend/src/tools/proofreading/DiffView.jsx`
- Delete: `frontend/src/tools/proofreading/DiffView.test.jsx`
- Modify: `frontend/src/css/components.css`

- [ ] **Step 1: Delete DiffView files**

```bash
rm frontend/src/tools/proofreading/DiffView.jsx frontend/src/tools/proofreading/DiffView.test.jsx
```

- [ ] **Step 2: Delete obsolete CSS blocks**

Remove the following CSS blocks from `components.css`:

1. **Lines 292-320**: `.tooltip`, `.tooltip::after`, `.tooltip:hover::after`
2. **Lines 596-611**: `.result-view__corrected-text h4`, `.result-view__corrected-text-body`
3. **Lines 720-769**: `.diff-highlight`, `.diff-highlight__empty`, `.diff-compare`, `.diff-compare__panel`, `.diff-compare__panel-header`

- [ ] **Step 3: Commit**

```bash
git add -A frontend/src/tools/proofreading/DiffView.jsx frontend/src/tools/proofreading/DiffView.test.jsx frontend/src/css/components.css
git commit -m "refactor(proofreading): delete DiffView components and obsolete CSS"
```

---

### Task 7: Update ResultView tests

**Files:**
- Modify: `frontend/src/tools/proofreading/ResultView.test.jsx`

- [ ] **Step 1: Update createResult to include originalText in tests**

Add `originalText` to test renders. Every `<ResultView result={...} />` call needs `originalText="入力テキスト"` added.

Key changes to the test file:

1. **Line 47-51** (success status tabs): Change tab name assertions:
   - `/ハイライト表示/` → `/校正前/`
   - `/比較表示/` → `/校正後/`
   - `/コメント一覧/` → `/差分/`

2. **Line 58-61** (notice): Change `/表示は差分ベースです/` → `/差分タブのコメントは AI 推定/`

3. **Line 63-69** (default active tab): Change `/ハイライト表示/` → `/校正前/`

4. **Lines 100-173** (tab ③ comments → tab 差分): Change all `/コメント一覧/` → `/差分/`

5. **Lines 179-228** (partial status): Change tab name assertions:
   - `/ハイライト表示/` → `/校正前/`
   - `/コメント一覧/` → `/差分/`

6. **Lines 286-301** (tab switching): Update to test new tabs. Replace entire test:
```jsx
    it('switches content when tab is clicked', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} originalText="入力テキスト" />);

      // Initially on before tab — shows original text
      expect(screen.getByText('入力テキスト')).toBeInTheDocument();

      // Switch to after tab
      await user.click(screen.getByRole('tab', { name: /校正後/ }));
      expect(screen.getByText('校正済みテキストです。')).toBeInTheDocument();

      // Switch to diff tab
      await user.click(screen.getByRole('tab', { name: /差分/ }));
      expect(screen.getByText('修正前テキスト')).toBeInTheDocument();
    });
```

7. **Line 195-211** (partial without diffs): The `showCorrectedText` inline display is removed. Now corrected text shows in "after" tab. Update to check for the "after" tab and its content instead of checking for inline `校正済みテキスト` heading.

8. **Add new test** for `originalText` prop:
```jsx
    it('renders originalText in before tab', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} originalText="オリジナル文書" />);
      expect(screen.getByText('オリジナル文書')).toBeInTheDocument();
    });

    it('renders corrected_text in after tab', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} originalText="入力" />);
      await user.click(screen.getByRole('tab', { name: /校正後/ }));
      expect(screen.getByText('校正済みテキストです。')).toBeInTheDocument();
    });
```

9. **Add test for summary in diff tab**:
```jsx
    it('renders summary in diff tab', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} originalText="入力" />);
      await user.click(screen.getByRole('tab', { name: /差分/ }));
      expect(screen.getByText('3 件の修正を行いました。')).toBeInTheDocument();
    });
```

- [ ] **Step 2: Run tests to verify**

Run: `cd frontend && npx vitest run src/tools/proofreading/ResultView.test.jsx`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tools/proofreading/ResultView.test.jsx
git commit -m "test(proofreading): update ResultView tests for new tab structure"
```

---

### Task 8: Update integration tests

**Files:**
- Modify: `frontend/src/tools/proofreading/ResultView.integration.test.jsx`
- Modify: `frontend/src/tools/proofreading/Proofreading.integration.test.jsx`

- [ ] **Step 1: Update ResultView.integration.test.jsx**

Key changes:

1. **Line 34**: Change `/コメント一覧/` → `/差分/`
2. **Line 66**: Change `/コメント一覧/` → `/差分/`
3. **Line 31**: Add `originalText="テスト入力"` to `<ResultView>` render calls
4. **Line 63**: Add `originalText="テスト入力"` to `<ResultView>` render calls

- [ ] **Step 2: Verify Proofreading.integration.test.jsx still passes**

Run: `cd frontend && npx vitest run src/tools/proofreading/Proofreading.integration.test.jsx`
Expected: PASS — this file does not assert tab labels directly

If failures occur, fix them (likely need to check that `corrected_text` is still accessible in the "after" tab for parse_fallback assertions).

- [ ] **Step 3: Run all tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add frontend/src/tools/proofreading/ResultView.integration.test.jsx frontend/src/tools/proofreading/Proofreading.integration.test.jsx
git commit -m "test(proofreading): update integration tests for new tab structure"
```

---

### Task 9: Final verification

- [ ] **Step 1: Run full test suite**

Run: `cd frontend && npx vitest run`
Expected: All tests pass

- [ ] **Step 2: Verify no dangling imports**

Run: `cd frontend && npx vitest run 2>&1 | grep -i "error"`
Expected: No import errors

- [ ] **Step 3: Spot-check CSS for dead selectors**

Search for any remaining references to deleted classes:
```bash
cd frontend/src && grep -rn "diff-highlight\|diff-compare\|compare-panel\|\.tooltip\|corrected-text-body" --include="*.jsx" --include="*.js" --include="*.css"
```
Expected: No matches (all references removed)

- [ ] **Step 4: Verify the app starts without errors**

Run: `cd frontend && npx vite build` (or `npm run build` if configured)
Expected: Build succeeds with no errors
