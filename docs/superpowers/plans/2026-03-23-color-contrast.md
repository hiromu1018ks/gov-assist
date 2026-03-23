# Color Contrast Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve text readability by adjusting three CSS color tokens for better contrast against dark backgrounds.

**Architecture:** Pure CSS token change in `base.css`. No JavaScript, no component changes. All 27 referencing locations update automatically through CSS custom properties.

**Tech Stack:** CSS custom properties, Vitest

---

### Task 1: Update color tokens

**Files:**
- Modify: `frontend/src/css/base.css:69`
- Modify: `frontend/src/css/base.css:94-95`
- Test: `frontend/` (existing test suite)

- [ ] **Step 1: Update `--color-text-muted`**

In `frontend/src/css/base.css` line 69, change:
```css
--color-text-muted: #5a8a62;
```
to:
```css
--color-text-muted: #7ab882;
```

- [ ] **Step 2: Update `--color-diff-delete-bg`**

In `frontend/src/css/base.css` line 94, change:
```css
--color-diff-delete-bg: rgba(255, 0, 64, 0.25);
```
to:
```css
--color-diff-delete-bg: rgba(255, 0, 64, 0.15);
```

- [ ] **Step 3: Update `--color-diff-delete-text`**

In `frontend/src/css/base.css` line 95, change:
```css
--color-diff-delete-text: #ff2244;
```
to:
```css
--color-diff-delete-text: #ff5566;
```

- [ ] **Step 4: Run tests**

Run: `cd frontend && npm test`
Expected: All existing tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/css/base.css
git commit -m "style: improve color contrast for muted and diff-delete tokens"
```
