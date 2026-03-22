# Task 16: テキスト前処理 & 校正オプション — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the client-side text preprocessing utility (`preprocess.js`) and the proofreading options panel component (`OptionPanel.jsx`) with 6 checkboxes, integrating both into the proofreading page.

**Architecture:** `preprocess.js` is a pure function module — `preprocessText(text)` returns `{ text, error }` after applying normalization rules from §3.3.2. `OptionPanel.jsx` is a controlled-ish component that initializes checkbox state from `localStorage` via `loadSettings()`, renders 6 proofreading options in a 2-column grid, and notifies the parent of changes via `onChange`. Both are wired into `Proofreading.jsx`; the actual submit-time preprocessing call is deferred to Task 19.

**Tech Stack:** React 18, Vitest, React Testing Library, plain CSS (no Tailwind)

**Design Spec References:** §3.3.2 (前処理ルール), §3.3.3 (校正オプション), §3.4 (localStorage 設定), §4.2 (ProofreadOptions schema)

---

## File Structure

### New files (4)

| File | Responsibility |
|------|---------------|
| `src/tools/proofreading/preprocess.js` | Pure utility: `preprocessText(text)` — normalize newlines, trim lines, remove control chars, validate char count |
| `src/tools/proofreading/preprocess.test.js` | Unit tests for all preprocessing rules and edge cases |
| `src/tools/proofreading/OptionPanel.jsx` | 6-checkbox panel for proofreading options, initialized from localStorage |
| `src/tools/proofreading/OptionPanel.test.jsx` | Tests for OptionPanel rendering, interaction, and localStorage integration |

### Modified files (2)

| File | Changes |
|------|---------|
| `src/tools/proofreading/Proofreading.jsx` | Import and render `OptionPanel`; store current options in state; pass `options` to `console.log` in placeholder handleSubmit |
| `src/css/components.css` | Add `.option-panel` styles (fieldset, legend, 2-column grid) |

### Key Constraints

- **No `dangerouslySetInnerHTML`** — all rendering via React JSX (§8.2)
- **No Tailwind** — plain CSS only (CLAUDE.md)
- **preprocess.js is pure** — no React, no side effects, easily testable
- **OptionPanel initializes from `loadSettings().options`** — matches `ProofreadOptions` schema in backend (§4.2): `{ typo, keigo, terminology, style, legal, readability }`
- **`legal` defaults to `false`**, all others default to `true` — per backend schema and `storage.js` DEFAULTS
- **OptionPanel does NOT save to localStorage** — saving defaults is Task 21 (Settings page)
- **preprocess is called at submit time** — not on every keystroke. Actual wiring in Task 19.

---

## Task 1: preprocess.js — テキスト前処理ユーティリティ

### Step 1: Write the failing test

Create `frontend/src/tools/proofreading/preprocess.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { preprocessText } from './preprocess';

describe('preprocessText', () => {
  // --- Rule: NULL文字除去 (§3.3.2) ---

  it('removes NULL and control characters but preserves tab, newline, carriage return, form feed', () => {
    // \x00 (NULL), \x01-\x08, \x0b (VT), \x0e-\x1f should be removed
    // \x09 (TAB), \x0a (LF), \x0d (CR), \x0c/\f (FF — handled by page break rule) are preserved
    const input = 'hel\x00lo\two\x08rld\x0b\x0e\x1f';
    const { text } = preprocessText(input);
    expect(text).toBe('hello\tworld');
  });

  it('preserves tab characters in text', () => {
    const { text } = preprocessText('col1\tcol2\tcol3');
    expect(text).toBe('col1\tcol2\tcol3');
  });

  // --- Rule: ページ区切りの除去 (§3.3.2) ---

  it('replaces form feed (\\f) with newline', () => {
    const { text } = preprocessText('page1\fpage2');
    expect(text).toBe('page1\npage2');
  });

  it('replaces multiple form feeds with newlines', () => {
    const { text } = preprocessText('a\fb\f\fc');
    expect(text).toBe('a\nb\n\nc');
  });

  // --- Rule: 行頭・行末の空白トリム (§3.3.2) ---

  it('trims leading and trailing whitespace from each line', () => {
    const { text } = preprocessText('  hello  \n  world  ');
    expect(text).toBe('hello\nworld');
  });

  it('removes tabs from line edges', () => {
    const { text } = preprocessText('\t\tindented\t\n\tnext\t');
    expect(text).toBe('indented\nnext');
  });

  // --- Rule: 連続改行の正規化 (§3.3.2) ---

  it('collapses 3+ consecutive newlines to 2', () => {
    const { text } = preprocessText('a\n\n\nb');
    expect(text).toBe('a\n\nb');
  });

  it('collapses many consecutive newlines to 2', () => {
    const { text } = preprocessText('a\n\n\n\n\n\nb');
    expect(text).toBe('a\n\nb');
  });

  it('preserves exactly 2 consecutive newlines', () => {
    const { text } = preprocessText('a\n\nb');
    expect(text).toBe('a\n\nb');
  });

  it('preserves single newlines', () => {
    const { text } = preprocessText('a\nb');
    expect(text).toBe('a\nb');
  });

  // --- Combined preprocessing ---

  it('applies all rules in sequence for realistic PDF extraction output', () => {
    // Simulates PDF extraction: form feeds, extra newlines, control chars, whitespace, CRLF
    const input = '  Document Title  \x00\r\n\n\f  Section 1  \x0b\r\n  Content here  \n\n\n\n  ';
    const { text } = preprocessText(input);
    expect(text).toBe('Document Title\n\nSection 1\nContent here');
  });

  it('handles empty string', () => {
    const { text, error } = preprocessText('');
    expect(text).toBe('');
    expect(error).toBeNull();
  });

  it('handles string with only whitespace and control characters', () => {
    const { text, error } = preprocessText('  \x00\x01\n\n\n  ');
    expect(text).toBe('');
    expect(error).toBeNull();
  });

  it('handles normal Japanese text without changes', () => {
    const input = 'これはテスト文書です。\n\n段落2です。';
    const { text } = preprocessText(input);
    expect(text).toBe(input);
  });

  // --- 文字数チェック (§3.3.2) ---

  it('returns error when preprocessed text exceeds 8000 characters', () => {
    const longText = 'あ'.repeat(8001);
    const { text, error } = preprocessText(longText);
    expect(text.length).toBe(8001);
    expect(error).toContain('8,000');
    expect(error).toContain('8,001');
  });

  it('returns no error when text is exactly 8000 characters', () => {
    const text8000 = 'あ'.repeat(8000);
    const { text, error } = preprocessText(text8000);
    expect(text.length).toBe(8000);
    expect(error).toBeNull();
  });

  it('returns no error for short text', () => {
    const { text, error } = preprocessText('短いテキスト');
    expect(error).toBeNull();
    expect(text).toBe('短いテキスト');
  });

  // --- Edge cases ---

  it('handles non-string input gracefully', () => {
    const { text, error } = preprocessText(null);
    expect(text).toBe('');
    expect(error).toBe('テキストが文字列ではありません。');
  });

  it('handles undefined input gracefully', () => {
    const { text, error } = preprocessText(undefined);
    expect(text).toBe('');
    expect(error).toBe('テキストが文字列ではありません。');
  });

  it('handles numeric input gracefully', () => {
    const { text, error } = preprocessText(12345);
    expect(text).toBe('');
    expect(error).toBe('テキストが文字列ではありません。');
  });

  it('removes carriage returns (\\r) from CRLF sequences correctly', () => {
    const { text } = preprocessText('a\r\n\r\nb');
    expect(text).toBe('a\n\nb');
  });

  it('normalizes bare \\r to \\n', () => {
    const { text } = preprocessText('hel\rlo');
    expect(text).toBe('hel\nlo');
  });
});
```

### Step 2: Run test to verify it fails

Run: `cd frontend && npx vitest run src/tools/proofreading/preprocess.test.js`
Expected: FAIL — `Cannot find module './preprocess'` or similar import error

### Step 3: Implement preprocess.js

Create `frontend/src/tools/proofreading/preprocess.js`:

```js
/**
 * テキスト前処理ユーティリティ（§3.3.2）
 * バックエンド送信前にテキストを正規化する
 */

const MAX_CHARS = 8000;

/**
 * テキストを前処理して正規化する
 * @param {string} text - 生テキスト
 * @returns {{ text: string, error: string|null }}
 */
export function preprocessText(text) {
  if (typeof text !== 'string') {
    return { text: '', error: 'テキストが文字列ではありません。' };
  }

  let result = text;

  // 1. NULL文字除去: 制御文字（\x00〜\x08、\x0b、\x0e〜\x1f）を除去
  //    \x0c(\f) はページ区切りルールで処理するため除外
  //    \t(0x09), \n(0x0a), \r(0x0d) は保持
  result = result.replace(/[\x00-\x08\x0b\x0e-\x1f]/g, '');

  // 2. ページ区切りの除去: \f を改行に変換
  result = result.replace(/\f/g, '\n');

  // 3. 改行の正規化: \r\n / \r を \n に統一
  result = result.replace(/\r\n?/g, '\n');

  // 4. 行頭・行末の空白トリム: 各行の先頭・末尾スペース・タブを除去
  result = result.split('\n').map((line) => line.trim()).join('\n');

  // 5. 連続改行の正規化: 3行以上の連続改行を2行に圧縮
  result = result.replace(/\n{3,}/g, '\n\n');

  // 6. 末尾の余分な改行を除去（実装追加: 空行化された末尾の整理）
  result = result.trimEnd();

  // 7. 文字数チェック
  if (result.length > MAX_CHARS) {
    return {
      text: result,
      error: `前処理後のテキストが${MAX_CHARS.toLocaleString()}文字を超えています（${result.length.toLocaleString()}文字）。テキストを短くしてください。`,
    };
  }

  return { text: result, error: null };
}
```

### Step 4: Run test to verify it passes

Run: `cd frontend && npx vitest run src/tools/proofreading/preprocess.test.js`
Expected: All 18 tests PASS

### Step 5: Commit

```bash
cd frontend
git add src/tools/proofreading/preprocess.js src/tools/proofreading/preprocess.test.js
git commit -m "feat(frontend): add text preprocessing utility (§3.3.2)

Implement preprocessText() with 6 normalization rules:
- Remove control chars (preserve tab/LF/CR/FF)
- Replace form feed with newline
- Normalize CRLF/LF to LF
- Trim whitespace from line edges
- Collapse 3+ consecutive newlines to 2
- Validate 8000 char limit after processing"
```

---

## Task 2: OptionPanel.jsx — 校正オプションパネル

### Step 1: Write the failing test

Create `frontend/src/tools/proofreading/OptionPanel.test.jsx`:

```jsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('../../utils/storage', () => ({
  loadSettings: vi.fn(),
  saveSettings: vi.fn(),
}));

import OptionPanel from './OptionPanel';
import { loadSettings } from '../../utils/storage';

describe('OptionPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loadSettings).mockReturnValue({
      version: 1,
      model: 'kimi-k2.5',
      document_type: 'official',
      options: {
        typo: true,
        keigo: true,
        terminology: true,
        style: true,
        legal: false,
        readability: true,
      },
    });
  });

  function renderPanel(props = {}) {
    return render(<OptionPanel {...props} />);
  }

  it('renders all 6 checkboxes with correct labels', () => {
    renderPanel();

    expect(screen.getByText('誤字・脱字・変換ミスの検出')).toBeInTheDocument();
    expect(screen.getByText('敬語・丁寧語の適切さチェック')).toBeInTheDocument();
    expect(screen.getByText('公文書用語・表現への統一（例：「ください」→「くださいますよう」）')).toBeInTheDocument();
    expect(screen.getByText('文体の統一（です・ます調 / である調）')).toBeInTheDocument();
    expect(screen.getByText('法令・条例用語の確認')).toBeInTheDocument();
    expect(screen.getByText('文章の読みやすさ・論理構成の改善提案')).toBeInTheDocument();
  });

  it('initializes checkbox states from localStorage', () => {
    renderPanel();

    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(6);

    // typo, keigo, terminology, style, readability = true
    expect(checkboxes[0]).toBeChecked(); // typo
    expect(checkboxes[1]).toBeChecked(); // keigo
    expect(checkboxes[2]).toBeChecked(); // terminology
    expect(checkboxes[3]).toBeChecked(); // style
    expect(checkboxes[4]).not.toBeChecked(); // legal (defaults to false)
    expect(checkboxes[5]).toBeChecked(); // readability
  });

  it('toggles checkbox on click', async () => {
    const user = userEvent.setup();
    renderPanel();

    const legalCheckbox = screen.getByRole('checkbox', { name: /法令・条例用語の確認/ });
    expect(legalCheckbox).not.toBeChecked();

    await user.click(legalCheckbox);
    expect(legalCheckbox).toBeChecked();
  });

  it('calls onChange with updated options when checkbox is toggled', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    renderPanel({ onChange });

    await user.click(screen.getByRole('checkbox', { name: /法令・条例用語の確認/ }));

    expect(onChange).toHaveBeenCalledTimes(1);
    const calledOptions = onChange.mock.calls[0][0];
    expect(calledOptions).toEqual({
      typo: true,
      keigo: true,
      terminology: true,
      style: true,
      legal: true,   // was false, now true
      readability: true,
    });
  });

  it('calls onChange with correct options when unchecking a default-true option', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    renderPanel({ onChange });

    await user.click(screen.getByRole('checkbox', { name: /誤字・脱字・変換ミス/ }));

    const calledOptions = onChange.mock.calls[0][0];
    expect(calledOptions.typo).toBe(false);
    expect(calledOptions.keigo).toBe(true); // other options unchanged
  });

  it('disables all checkboxes when disabled prop is true', () => {
    renderPanel({ disabled: true });

    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach((cb) => expect(cb).toBeDisabled());
  });

  it('does not call onChange when disabled', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    renderPanel({ onChange, disabled: true });

    await user.click(screen.getByRole('checkbox', { name: /誤字・脱字・変換ミス/ }));

    expect(onChange).not.toHaveBeenCalled();
  });

  it('renders legend with title', () => {
    renderPanel();
    expect(screen.getByText('校正オプション')).toBeInTheDocument();
  });

  it('works without onChange prop (no crash)', async () => {
    const user = userEvent.setup();
    renderPanel(); // no onChange prop

    // Should not throw
    await user.click(screen.getByRole('checkbox', { name: /誤字・脱字・変換ミス/ }));
  });

  it('initializes from localStorage custom settings', () => {
    vi.mocked(loadSettings).mockReturnValue({
      version: 1,
      model: 'kimi-k2.5',
      document_type: 'email',
      options: {
        typo: false,
        keigo: false,
        terminology: false,
        style: false,
        legal: false,
        readability: false,
      },
    });

    renderPanel();

    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach((cb) => expect(cb).not.toBeChecked());
  });

  it('handles missing options in localStorage gracefully', () => {
    vi.mocked(loadSettings).mockReturnValue({
      version: 1,
      model: 'kimi-k2.5',
      document_type: 'official',
      // options is undefined — should not crash
    });

    renderPanel();

    // Should render without crashing; checkboxes default to unchecked when options is undefined
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(6);
  });
});
```

### Step 2: Run test to verify it fails

Run: `cd frontend && npx vitest run src/tools/proofreading/OptionPanel.test.jsx`
Expected: FAIL — `Cannot find module './OptionPanel'`

### Step 3: Implement OptionPanel.jsx

Create `frontend/src/tools/proofreading/OptionPanel.jsx`:

```jsx
import { useState, useRef, useCallback } from 'react';
import { loadSettings } from '../../utils/storage';

const OPTIONS = [
  { key: 'typo', label: '誤字・脱字・変換ミスの検出' },
  { key: 'keigo', label: '敬語・丁寧語の適切さチェック' },
  { key: 'terminology', label: '公文書用語・表現への統一（例：「ください」→「くださいますよう」）' },
  { key: 'style', label: '文体の統一（です・ます調 / である調）' },
  { key: 'legal', label: '法令・条例用語の確認' },
  { key: 'readability', label: '文章の読みやすさ・論理構成の改善提案' },
];

export default function OptionPanel({ onChange, disabled }) {
  const [options, setOptions] = useState(() => loadSettings().options);
  // Ref to avoid stale closure in handleChange — consistent with InputArea.jsx pattern
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const handleChange = useCallback((key) => {
    const prev = optionsRef.current;
    const next = { ...prev, [key]: !prev[key] };
    setOptions(next);
    onChange?.(next);
  }, [onChange]);

  return (
    <fieldset className="option-panel" disabled={disabled}>
      <legend className="option-panel__legend">校正オプション</legend>
      <div className="option-panel__grid">
        {OPTIONS.map(({ key, label }) => (
          <label key={key} className="checkbox">
            <input
              type="checkbox"
              className="checkbox__input"
              checked={!!options[key]}
              onChange={() => handleChange(key)}
            />
            {label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
```

### Step 4: Add CSS styles for OptionPanel

Append to `frontend/src/css/components.css` (after the Input Area section at the end):

```css
/* --- Option Panel (§3.3.3) --- */

.option-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--spacing-sm) var(--spacing-md);
}

.option-panel__legend {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
  padding: 0 var(--spacing-sm);
}

.option-panel__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-sm) var(--spacing-lg);
  margin-top: var(--spacing-sm);
}

.option-panel:disabled {
  opacity: 0.5;
  pointer-events: none;
}
```

### Step 5: Run test to verify it passes

Run: `cd frontend && npx vitest run src/tools/proofreading/OptionPanel.test.jsx`
Expected: All 11 tests PASS

### Step 6: Commit

```bash
cd frontend
git add src/tools/proofreading/OptionPanel.jsx src/tools/proofreading/OptionPanel.test.jsx src/css/components.css
git commit -m "feat(frontend): add OptionPanel component with 6 proofreading options (§3.3.3)

2-column checkbox grid initialized from localStorage settings.
Matches backend ProofreadOptions schema (typo/keigo/terminology/style/legal/readability)."
```

---

## Task 3: Proofreading.jsx への統合

### Step 1: Wire OptionPanel into Proofreading.jsx

Update `frontend/src/tools/proofreading/Proofreading.jsx`:

```jsx
import { useState } from 'react';
import InputArea from './InputArea';
import OptionPanel from './OptionPanel';

function Proofreading() {
  const [options, setOptions] = useState(null);
  const [isSubmitting] = useState(false);

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
    </div>
  );
}

export default Proofreading;
```

### Step 2: Run full test suite to check for regressions

Run: `cd frontend && npx vitest run`
Expected: All existing tests PASS + new OptionPanel and preprocess tests PASS

### Step 3: Verify visually (manual check)

Run: `cd frontend && npm run dev`
Verify:
1. Proofreading page shows InputArea (existing) + OptionPanel below it
2. OptionPanel has "校正オプション" legend
3. 6 checkboxes in 2-column grid
4. `typo`, `keigo`, `terminology`, `style`, `readability` checked; `legal` unchecked
5. Toggling a checkbox works
6. No console errors

### Step 4: Commit

```bash
cd frontend
git add src/tools/proofreading/Proofreading.jsx
git commit -m "feat(frontend): integrate OptionPanel into Proofreading page

Wire OptionPanel below InputArea with options state management.
Pass options to placeholder handleSubmit for Task 19 integration."
```
