# Proofreading UI Redesign: Full-Text View with Tab Navigation

**Date**: 2026-03-23
**Status**: Approved
**Scope**: `frontend/src/tools/proofreading/ResultView.jsx`, `DiffView.jsx`, `Proofreading.jsx`, `HistoryDetail.jsx`, CSS

## Problem

The current proofreading result UI uses a diff-centric 3-tab layout (Highlight / Compare / Comments) that makes it difficult to read the full corrected text naturally. Users must mentally reconstruct the corrected document from colored diff spans, and long documents become hard to navigate.

## Solution

Replace the diff-centric tabs with a full-text reading experience:

| Tab | Content |
|-----|---------|
| **校正前** (Before) | Original text displayed in full, plain formatting |
| **校正後** (After) | Corrected text (`corrected_text`) displayed in full, plain formatting |
| **差分** (Diff) | Correction list with before/after/reason per item, plus AI summary and warnings |

This lets users read the corrected document naturally, then check specific changes via the diff tab when needed.

## Component Changes

### Delete

- **`DiffView.jsx`** — Entire file. Contains `HighlightView` (inline diff) and `CompareView` (side-by-side with scroll sync). No longer needed.
- **`DiffView.test.jsx`** — All tests for deleted components.

### Create

- **`FullTextView.jsx`** — Simple full-text display component.
  - Props: `text` (string), `label` (string for accessibility)
  - Renders text with `white-space: pre-wrap` in a scrollable container (max-height: 400px, overflow-y: auto)
  - Scrollable container has `role="region"` and `aria-label={label}` for accessibility
  - No diff highlighting; all rendering via standard React text nodes
  - Shared between 校正前 and 校正後 tabs

### Modify

- **`ResultView.jsx`** — Major restructure:
  - New props: `originalText` (string) — the user's original input text, passed from parent
  - Tab names: "Highlight" / "Compare" / "Comments" → "校正前" / "校正後" / "差分"
  - `getAvailableTabs()` returns new tab identifiers based on status
  - Content area renders `FullTextView` or `DiffListView` based on active tab
  - 校正前 tab renders `<FullTextView text={originalText} label="校正前" />`
  - 校正後 tab renders `<FullTextView text={result.corrected_text} label="校正後" />`
  - Status message placement: warnings shown above tab content (not in separate section)
  - Always-visible notice updated and placed below action buttons:
    "※ 差分タブのコメントは AI 推定であり、正確でない場合があります。"

- **`Proofreading.jsx`** — Pass original text to ResultView:
  - Change `<ResultView result={result} onRetry={handleRetry} />` to `<ResultView result={result} originalText={lastParams.rawText} onRetry={handleRetry} />`

- **`HistoryDetail.jsx`** — Pass original text to ResultView:
  - Change `<ResultView result={detail.result} />` to `<ResultView result={detail.result} originalText={detail.input_text} />`

- **`CorrectionList`** (inline in ResultView.jsx) → **`DiffListView`** (rename + extend):
  - Adds AI summary display at the top of the list
  - Adds warning badges (e.g., `large_rewrite`) in the summary area
  - Existing correction item rendering unchanged

### CSS Changes (components.css)

**Delete**:
- `.diff-highlight`, `.diff-highlight__empty` and all child selectors
- `.diff-compare`, `.diff-compare__panel`, `.diff-compare__panel-header`, `.diff-compare__panel--scroll-sync`, `.diff-compare__panel--before`, `.diff-compare__panel--after`
- Tooltip-related styles for diff spans
- `.result-view__corrected-text`, `.result-view__corrected-text-body` (dead code after redesign — replaced by FullTextView)

**Add**:
- `.full-text-view` — container styling (pre-wrap, max-height, overflow-y, padding)
- `.diff-list-summary` — AI summary box styling
- `.diff-list-warning` — warning badge styling

## Status Branching

| Status | 校正前 | 校正後 | 差分 | Message |
|--------|--------|--------|------|---------|
| `success` | `originalText` prop | `corrected_text` | list + summary + warnings | none |
| `partial` + `diff_timeout` + has diffs | `originalText` prop | `corrected_text` | list + info | timeout warning above tabs |
| `partial` + `diff_timeout` + no diffs | hidden | `corrected_text` | empty list + info | "no diffs available" warning |
| `partial` + `parse_fallback` | hidden | `corrected_text` | empty list + info | parse failure warning |
| `error` | no tabs | no tabs | no tabs | error message + retry button |

Note: `originalText` comes from the parent component's state (`lastParams.rawText` in Proofreading, `detail.input_text` in HistoryDetail), not from the API response. It is always available when ResultView is rendered.

## Constraints (Unchanged)

- All rendering via standard React data binding (no innerHTML)
- `corrected_text` is used as-is for copy/download, never reconstructed from diffs
- localStorage treated as cache with schema versioning
- Plain CSS only (no Tailwind)
- AI output never trusted blindly — server validates, frontend handles partial/error gracefully
- Diffs in the diff list tab rendered in sequential reduce-style order (array order only, `start` index not used for rendering)

## Constraints (Not Applicable)

The following constraints from the main design spec do not apply to this redesign because the full-text views do not use diff data:
- "Diffs rendered in sequential reduce-style order" — only applies to diff list tab
- "`start` index not used for rendering" — only applies to diff list tab

## Testing

| File | Action |
|------|--------|
| `DiffView.test.jsx` | Delete entirely |
| `FullTextView.test.jsx` | Create — text rendering, pre-wrap behavior, label prop, ARIA attributes |
| `ResultView.test.jsx` | Update — tab names (Japanese labels), `originalText` prop, tab control logic, status branching, updated notice text |
| `ResultView.integration.test.jsx` | Update — remove DiffView references, test new tab flow with originalText prop |
| `Proofreading.integration.test.jsx` | Update — tab label assertions changed from English to Japanese (e.g., "Highlight" → "校正前") |

## Out of Scope

- Theme/visual redesign (hacker theme stays as-is)
- Input area changes
- Option panel changes
- Action button behavior changes (copy, download, save work the same)
- Backend API changes (no new fields needed — `originalText` comes from parent state)
