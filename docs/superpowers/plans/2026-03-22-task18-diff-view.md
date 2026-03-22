# Task 18: DiffView — タブ① ハイライト & タブ② 比較表示 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 校正結果の diff 配列を reduce 的逐次レンダリングでハイライト表示（タブ①）と左右比較表示（タブ②）を実装する。

**Architecture:** `DiffView.jsx` は2つの内部コンポーネント（`HighlightView`、`CompareView`）をエクスポートする。`ResultView.jsx` はプレースホルダーを `<DiffView>` に差し替える。diff の `start` 座標はレンダリングに使用せず、配列の順序のみに依存する。スクロール同期は `onScroll` イベントの連動で実現する。

**Tech Stack:** React 18, plain CSS（既存 `components.css` に追記）, Vitest + Testing Library

**設計書参照:** §3.3.4（校正結果表示）、§4.5（diff と corrections の対応付け）、§4.6（レスポンス JSON 構造）

---

## ファイル構成

| ファイル | 役割 |
|----------|------|
| `frontend/src/tools/proofreading/DiffView.jsx` | **新規作成** — `HighlightView` と `CompareView` をエクスポート |
| `frontend/src/tools/proofreading/DiffView.test.jsx` | **新規作成** — HighlightView / CompareView のテスト |
| `frontend/src/tools/proofreading/ResultView.jsx` | **修正** — プレースホルダーを DiffView に差し替え（lines 198-207） |
| `frontend/src/tools/proofreading/ResultView.test.jsx` | **修正** — プレースホルダー関連テストの更新 |
| `frontend/src/css/components.css` | **修正** — DiffView 用スタイル追記 |

---

## Task 1: CSS スタイル追加

**Files:**
- Modify: `frontend/src/css/components.css`

- [ ] **Step 1: DiffView 用 CSS を追加**

`components.css` の末尾（line 690 の後）に以下を追記する:

```css
/* --- Diff View (§3.3.4: Tab ① Highlight & Tab ② Compare) --- */

/* Highlight view: single-column diff display */
.diff-highlight {
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
}

.diff-highlight__empty {
  color: var(--color-text-muted);
  font-style: italic;
  text-align: center;
  padding: var(--spacing-lg) 0;
}

/* Compare view: two-column side-by-side layout */
.diff-compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
  max-height: 400px;
}

.diff-compare__panel {
  font-size: var(--font-size-base);
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
  padding: var(--spacing-md);
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow-y: auto;
  max-height: 400px;
}

.diff-compare__panel-header {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-sm);
  padding-bottom: var(--spacing-xs);
  border-bottom: 1px solid var(--color-border);
}
```

- [ ] **Step 2: コミット**

```bash
git add frontend/src/css/components.css
git commit -m "style(frontend): add DiffView CSS for highlight and compare display"
```

---

## Task 2: HighlightView コンポーネントとテスト

**Files:**
- Create: `frontend/src/tools/proofreading/DiffView.jsx`（HighlightView 部分）
- Create: `frontend/src/tools/proofreading/DiffView.test.jsx`（HighlightView テスト部分）

- [ ] **Step 1: HighlightView のテストを書く**

`DiffView.test.jsx` を作成:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HighlightView } from './DiffView';

describe('HighlightView', () => {
  // --- 基本レンダリング ---

  it('renders equal text as plain text', () => {
    const diffs = [
      { type: 'equal', text: 'こんにちは。', start: 0, position: null, reason: null },
    ];
    render(<HighlightView diffs={diffs} />);
    expect(screen.getByText('こんにちは。')).toBeInTheDocument();
  });

  it('renders delete text with diff-delete class', () => {
    const diffs = [
      { type: 'delete', text: '旧', start: 0, position: null, reason: null },
    ];
    render(<HighlightView diffs={diffs} />);
    const el = screen.getByText('旧');
    expect(el).toHaveClass('diff-delete');
  });

  it('renders insert text with diff-insert class', () => {
    const diffs = [
      { type: 'insert', text: '新', start: 0, position: null, reason: null },
    ];
    render(<HighlightView diffs={diffs} />);
    const el = screen.getByText('新');
    expect(el).toHaveClass('diff-insert');
  });

  // --- 混合 diff ---

  it('renders mixed diffs in array order (not start order)', () => {
    const diffs = [
      { type: 'equal', text: 'A', start: 10, position: null, reason: null },
      { type: 'delete', text: 'X', start: 5, position: null, reason: null },
      { type: 'insert', text: 'Y', start: 5, position: 'after', reason: null },
      { type: 'equal', text: 'B', start: 20, position: null, reason: null },
    ];
    render(<HighlightView diffs={diffs} />);
    const container = document.querySelector('.diff-highlight');
    // Verify children order matches array order: A, X, Y, B
    expect(container.textContent).toBe('AXYB');
  });

  // --- ツールチップ（reason） ---

  it('adds tooltip class and data-tooltip when reason is present', () => {
    const diffs = [
      { type: 'delete', text: '誤字', start: 0, position: null, reason: '誤字を修正' },
    ];
    render(<HighlightView diffs={diffs} />);
    const el = screen.getByText('誤字');
    expect(el).toHaveClass('tooltip');
    expect(el).toHaveAttribute('data-tooltip', '誤字を修正');
  });

  it('does not add tooltip class when reason is null', () => {
    const diffs = [
      { type: 'delete', text: '旧', start: 0, position: null, reason: null },
    ];
    render(<HighlightView diffs={diffs} />);
    const el = screen.getByText('旧');
    expect(el).not.toHaveClass('tooltip');
    expect(el).not.toHaveAttribute('data-tooltip');
  });

  it('adds tooltip to insert block with reason', () => {
    const diffs = [
      { type: 'insert', text: '正', start: 0, position: 'after', reason: '正しい表記' },
    ];
    render(<HighlightView diffs={diffs} />);
    const el = screen.getByText('正');
    expect(el).toHaveClass('tooltip');
    expect(el).toHaveAttribute('data-tooltip', '正しい表記');
  });

  // --- 空配列 ---

  it('shows empty message when diffs is empty', () => {
    render(<HighlightView diffs={[]} />);
    expect(screen.getByText('表示する差分がありません。')).toBeInTheDocument();
  });

  // --- 改行保持 ---

  it('preserves line breaks in diff text', () => {
    const diffs = [
      { type: 'equal', text: '1行目\n2行目', start: 0, position: null, reason: null },
    ];
    render(<HighlightView diffs={diffs} />);
    const el = screen.getByText('1行目\n2行目');
    // white-space: pre-wrap preserves line breaks
    expect(el).toBeInTheDocument();
  });

  // --- 連続する same-type ブロック ---

  it('renders consecutive same-type blocks as separate spans', () => {
    const diffs = [
      { type: 'equal', text: '前半', start: 0, position: null, reason: null },
      { type: 'equal', text: '後半', start: 2, position: null, reason: null },
    ];
    const { container } = render(<HighlightView diffs={diffs} />);
    const spans = container.querySelectorAll('.diff-highlight > span');
    expect(spans).toHaveLength(2);
    expect(container.textContent).toBe('前半後半');
  });
});
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run src/tools/proofreading/DiffView.test.jsx`
Expected: FAIL — `HighlightView` が存在しない

- [ ] **Step 3: HighlightView を実装**

`DiffView.jsx` を作成（CompareView は空のスタブを置く）:

```jsx
import { useRef, useCallback } from 'react';

/**
 * DiffView — diff-based display components for proofreading results.
 *
 * §3.3.4: Frontend renders diffs in reduce-style sequential order.
 * `start` index is NOT used for rendering; only array order matters.
 * All rendering via standard React data binding (no dangerouslySetInnerHTML).
 */

/**
 * Tab ① Highlight View
 *
 * Displays original text with color-coded highlights for delete/insert blocks.
 * Mouse hover shows nearby-matched reason as tooltip (data-tooltip attribute).
 *
 * Props:
 *   diffs: array of { type: 'equal'|'delete'|'insert', text, start, position, reason }
 */
export function HighlightView({ diffs }) {
  if (!diffs || diffs.length === 0) {
    return (
      <div className="diff-highlight">
        <p className="diff-highlight__empty">表示する差分がありません。</p>
      </div>
    );
  }

  return (
    <div className="diff-highlight">
      {diffs.map((diff, i) => {
        const className =
          diff.type === 'delete'
            ? 'diff-delete'
            : diff.type === 'insert'
              ? 'diff-insert'
              : '';

        const tooltipProps =
          diff.reason
            ? { className: `${className} tooltip`, 'data-tooltip': diff.reason }
            : { className };

        return <span key={i} {...tooltipProps}>{diff.text}</span>;
      })}
    </div>
  );
}

/**
 * Tab ② Compare View
 *
 * Side-by-side display: left = before (equal + delete), right = after (equal + insert).
 * Synchronized scrolling between panels via onScroll event.
 *
 * Props:
 *   diffs: array of { type, text, start, position, reason }
 */
export function CompareView({ diffs }) {
  const leftRef = useRef(null);
  const rightRef = useRef(null);
  const isScrolling = useRef(false);

  const handleScroll = useCallback((source) => {
    if (isScrolling.current) return;
    isScrolling.current = true;

    const target = source === 'left' ? rightRef.current : leftRef.current;
    if (target) {
      target.scrollTop = source === 'left' ? leftRef.current.scrollTop : rightRef.current.scrollTop;
    }

    requestAnimationFrame(() => {
      isScrolling.current = false;
    });
  }, []);

  if (!diffs || diffs.length === 0) {
    return (
      <div className="diff-highlight">
        <p className="diff-highlight__empty">表示する差分がありません。</p>
      </div>
    );
  }

  return (
    <div className="diff-compare">
      <div
        className="diff-compare__panel diff-compare__panel--scroll-sync"
        ref={leftRef}
        onScroll={() => handleScroll('left')}
      >
        <div className="diff-compare__panel-header">修正前</div>
        {diffs.map((diff, i) => {
          if (diff.type === 'insert') return null;
          const className = diff.type === 'delete' ? 'diff-delete' : '';
          const tooltipProps = diff.reason
            ? { className: `${className} tooltip`, 'data-tooltip': diff.reason }
            : { className };
          return <span key={i} {...tooltipProps}>{diff.text}</span>;
        })}
      </div>
      <div
        className="diff-compare__panel diff-compare__panel--scroll-sync"
        ref={rightRef}
        onScroll={() => handleScroll('right')}
      >
        <div className="diff-compare__panel-header">修正後</div>
        {diffs.map((diff, i) => {
          if (diff.type === 'delete') return null;
          const className = diff.type === 'insert' ? 'diff-insert' : '';
          const tooltipProps = diff.reason
            ? { className: `${className} tooltip`, 'data-tooltip': diff.reason }
            : { className };
          return <span key={i} {...tooltipProps}>{diff.text}</span>;
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: テストを実行して成功を確認**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run src/tools/proofreading/DiffView.test.jsx`
Expected: すべて PASS

- [ ] **Step 5: コミット**

```bash
git add frontend/src/tools/proofreading/DiffView.jsx frontend/src/tools/proofreading/DiffView.test.jsx
git commit -m "feat(frontend): add HighlightView and CompareView with sequential diff rendering"
```

---

## Task 3: CompareView のテスト追加

**Files:**
- Modify: `frontend/src/tools/proofreading/DiffView.test.jsx`（CompareView テスト追加）

- [ ] **Step 1: CompareView のテストを追加**

`DiffView.test.jsx` の先頭 import に `CompareView` を追加:

```jsx
import { HighlightView, CompareView } from './DiffView';
```

ファイルの末尾（`HighlightView` の `describe` ブロックの外側）に以下を追加:

```jsx
describe('CompareView', () => {
  // --- 基本レンダリング ---

  it('renders left panel (before) and right panel (after)', () => {
    const diffs = [
      { type: 'equal', text: '共通', start: 0, position: null, reason: null },
      { type: 'delete', text: '旧', start: 2, position: null, reason: '理由' },
      { type: 'insert', text: '新', start: 2, position: 'after', reason: '理由' },
      { type: 'equal', text: '終わり', start: 3, position: null, reason: null },
    ];
    render(<CompareView diffs={diffs} />);
    expect(screen.getByText(/修正前/)).toBeInTheDocument();
    expect(screen.getByText(/修正後/)).toBeInTheDocument();
  });

  it('left panel contains equal and delete text only', () => {
    const diffs = [
      { type: 'equal', text: 'A', start: 0, position: null, reason: null },
      { type: 'delete', text: 'X', start: 1, position: null, reason: null },
      { type: 'insert', text: 'Y', start: 1, position: 'after', reason: null },
      { type: 'equal', text: 'B', start: 2, position: null, reason: null },
    ];
    render(<CompareView diffs={diffs} />);
    const panels = document.querySelectorAll('.diff-compare__panel');
    expect(panels).toHaveLength(2);
    const leftText = panels[0].textContent;
    expect(leftText).toContain('A');
    expect(leftText).toContain('X');
    expect(leftText).toContain('B');
    expect(leftText).not.toContain('Y');
  });

  it('right panel contains equal and insert text only', () => {
    const diffs = [
      { type: 'equal', text: 'A', start: 0, position: null, reason: null },
      { type: 'delete', text: 'X', start: 1, position: null, reason: null },
      { type: 'insert', text: 'Y', start: 1, position: 'after', reason: null },
      { type: 'equal', text: 'B', start: 2, position: null, reason: null },
    ];
    render(<CompareView diffs={diffs} />);
    const panels = document.querySelectorAll('.diff-compare__panel');
    const rightText = panels[1].textContent;
    expect(rightText).toContain('A');
    expect(rightText).toContain('Y');
    expect(rightText).toContain('B');
    expect(rightText).not.toContain('X');
  });

  // --- diff-delete / diff-insert クラス ---

  it('applies diff-delete class in left panel', () => {
    const diffs = [
      { type: 'delete', text: '削除', start: 0, position: null, reason: null },
    ];
    render(<CompareView diffs={diffs} />);
    const panels = document.querySelectorAll('.diff-compare__panel');
    const el = panels[0].querySelector('.diff-delete');
    expect(el).toBeInTheDocument();
    expect(el.textContent).toBe('削除');
  });

  it('applies diff-insert class in right panel', () => {
    const diffs = [
      { type: 'insert', text: '追加', start: 0, position: 'after', reason: null },
    ];
    render(<CompareView diffs={diffs} />);
    const panels = document.querySelectorAll('.diff-compare__panel');
    const el = panels[1].querySelector('.diff-insert');
    expect(el).toBeInTheDocument();
    expect(el.textContent).toBe('追加');
  });

  // --- ツールチップ ---

  it('adds tooltip to delete block with reason in left panel', () => {
    const diffs = [
      { type: 'delete', text: '誤字', start: 0, position: null, reason: '修正理由' },
    ];
    render(<CompareView diffs={diffs} />);
    const el = document.querySelector('.diff-delete.tooltip');
    expect(el).toHaveAttribute('data-tooltip', '修正理由');
  });

  it('adds tooltip to insert block with reason in right panel', () => {
    const diffs = [
      { type: 'insert', text: '正字', start: 0, position: 'after', reason: '修正理由' },
    ];
    render(<CompareView diffs={diffs} />);
    const el = document.querySelector('.diff-insert.tooltip');
    expect(el).toHaveAttribute('data-tooltip', '修正理由');
  });

  // --- 空配列 ---

  it('shows empty message when diffs is empty', () => {
    render(<CompareView diffs={[]} />);
    expect(screen.getByText('表示する差分がありません。')).toBeInTheDocument();
  });

  // --- スクロール同期（構造確認のみ） ---

  it('has two scrollable panels for scroll sync', () => {
    const diffs = [
      { type: 'equal', text: 'テスト', start: 0, position: null, reason: null },
    ];
    render(<CompareView diffs={diffs} />);
    const panels = document.querySelectorAll('.diff-compare__panel');
    expect(panels).toHaveLength(2);
    expect(panels[0]).toHaveClass('diff-compare__panel--scroll-sync');
    expect(panels[1]).toHaveClass('diff-compare__panel--scroll-sync');
  });
});
```

- [ ] **Step 2: テストを実行して成功を確認**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run src/tools/proofreading/DiffView.test.jsx`
Expected: すべて PASS

- [ ] **Step 3: コミット**

```bash
git add frontend/src/tools/proofreading/DiffView.test.jsx
git commit -m "test(frontend): add CompareView tests for side-by-side display and scroll sync"
```

---

## Task 4: ResultView への統合

**Files:**
- Modify: `frontend/src/tools/proofreading/ResultView.jsx:1, 198-207`
- Modify: `frontend/src/tools/proofreading/ResultView.test.jsx`

- [ ] **Step 1: ResultView.jsx に DiffView をインポートしてプレースホルダーを差し替え**

**1a.** `ResultView.jsx` の line 1 の後に import を追加:

```jsx
import { HighlightView, CompareView } from './DiffView';
```

**1b.** lines 198-207 のプレースホルダーを差し替え:

```jsx
{activeTab === 'highlight' && (
  <HighlightView diffs={result.diffs} />
)}
{activeTab === 'compare' && (
  <CompareView diffs={result.diffs} />
)}
```

- [ ] **Step 2: ResultView.test.jsx を更新**

プレースホルダーを参照しているテストを更新する:

**2a.** line 291 のテストを更新:
```jsx
// 変更前
expect(screen.getByText(/ハイライト表示は今後実装されます/)).toBeInTheDocument();
// 変更後
expect(screen.getByText('前半')).toBeInTheDocument();
```

**2b.** line 295 のテストを更新:
```jsx
// 変更前
expect(screen.getByText(/比較表示は今後実装されます/)).toBeInTheDocument();
// 変更後
expect(screen.getByText(/修正前/)).toBeInTheDocument();
```

> **補足:** `createResult()` のデフォルト diffs には `text: '前半'` と `text: '後半'` が含まれているため、ハイライト表示では「前半」が表示される。比較表示では「修正前」ヘッダーが表示される。

- [ ] **Step 3: 全テストを実行して成功を確認**

Run: `cd /home/hart/Code/gov-assist/frontend && npx vitest run src/tools/proofreading/`
Expected: すべて PASS（DiffView.test.jsx + ResultView.test.jsx + 他のテスト）

- [ ] **Step 4: コミット**

```bash
git add frontend/src/tools/proofreading/ResultView.jsx frontend/src/tools/proofreading/ResultView.test.jsx
git commit -m "feat(frontend): integrate DiffView into ResultView replacing placeholders"
```

---

## 実装時の注意事項

1. **`start` 座標を使用しない**: レンダリングは diffs 配列の順序のみに依存する。`start` はデバッグ用途のみ。
2. **`dangerouslySetInnerHTML` 禁止**: すべて React の通常データバインディングでレンダリングする。
3. **テキスト再構築禁止**: `corrected_text` はコピー・ダウンロード用途にそのまま使う。diffs から再構築しない。
4. **スクロール同期**: `onScroll` 連動で実装。`isScrolling` ref で無限ループを防止する。
5. **既存 CSS の活用**: `.diff-delete`、`.diff-insert`、`.tooltip` は既に `components.css` に定義済み。新規追加はレイアウト関連のみ。
