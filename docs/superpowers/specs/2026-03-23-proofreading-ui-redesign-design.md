# Proofreading UI Redesign: Full-Text View with Tab Navigation

**Date**: 2026-03-23
**Status**: Approved
**Scope**: `frontend/src/tools/proofreading/ResultView.jsx`, `DiffView.jsx`, CSS

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
- **`DiffView.test.jsx`** — All 233 lines of tests for deleted components.

### Create

- **`FullTextView`** — Simple full-text display component.
  - Props: `text` (string), `label` (string for accessibility)
  - Renders text with `white-space: pre-wrap` in a scrollable container (max-height: 400px)
  - No diff highlighting; all rendering via standard React text nodes
  - Shared between 校正前 and 校正後 tabs

### Modify

- **`ResultView.jsx`** — Major restructure:
  - Tab names: "Highlight" / "Compare" / "Comments" → "校正前" / "校正後" / "差分"
  - `getAvailableTabs()` returns new tab identifiers based on status
  - Content area renders `FullTextView` or `DiffListView` based on active tab
  - Status message placement: warnings shown above tab content (not in separate section)
  - Always-visible notice moved below action buttons

- **`CorrectionList`** → **`DiffListView`** (rename + extend):
  - Adds AI summary display at the top of the list
  - Adds warning badges (e.g., `large_rewrite`) in the summary area
  - Existing correction item rendering unchanged

### CSS Changes (components.css)

**Delete** (~40-50 lines):
- `.highlight-view` and all child selectors (`.diff-equal`, `.diff-delete`, `.diff-insert`)
- `.compare-view`, `.compare-panel`, `.compare-panel-header`, `.compare-before`, `.compare-after`
- Tooltip-related styles (`.diff-delete:hover::after`, etc.)

**Add** (~15-20 lines):
- `.full-text-view` — container styling (pre-wrap, max-height, overflow, padding)
- `.diff-list-summary` — AI summary box styling
- `.diff-list-warning` — warning badge styling

## Status Branching

| Status | 校正前 | 校正後 | 差分 | Message |
|--------|--------|--------|------|---------|
| `success` | `original_text` | `corrected_text` | list + summary + warnings | none |
| `partial` + `diff_timeout` + has diffs | `original_text` | `corrected_text` | list + info | timeout warning above tabs |
| `partial` + `diff_timeout` + no diffs | hidden | `corrected_text` | empty list + info | "no diffs available" warning |
| `partial` + `parse_fallback` | hidden | `corrected_text` | empty list + info | parse failure warning |
| `error` | no tabs | no tabs | no tabs | error message + retry button |

## Constraints (Unchanged)

- All rendering via standard React data binding (no innerHTML)
- `corrected_text` is used as-is for copy/download, never reconstructed from diffs
- localStorage treated as cache with schema versioning
- Plain CSS only (no Tailwind)
- AI output never trusted blindly — server validates, frontend handles partial/error gracefully

## Constraints (Relaxed)

- "Diffs rendered in sequential reduce-style order" — applies only to diff list tab, not to full-text views
- "`start` index not used for rendering" — applies only to diff list tab, not to full-text views

## Testing

| File | Action |
|------|--------|
| `DiffView.test.jsx` | Delete entirely |
| `FullTextView.test.jsx` | Create — text rendering, pre-wrap behavior, label prop |
| `ResultView.test.jsx` | Update — tab names, tab control logic, status branching |
| `ResultView.integration.test.jsx` | Update — remove DiffView references, test new tab flow |
| `Proofreading.integration.test.jsx` | Update if it references DiffView components |

## Out of Scope

- Theme/visual redesign (hacker theme stays as-is)
- Input area changes
- Option panel changes
- Action button behavior changes (copy, download, save work the same)
- History detail view (reuses ResultView — will update automatically)
