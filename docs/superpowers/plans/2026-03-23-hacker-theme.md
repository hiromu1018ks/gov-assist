# Hacker Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform GovAssist frontend from a plain admin dashboard into an immersive hacker terminal experience with Matrix/terminal aesthetics, tmux-style layout, glow effects, and playful animations.

**Architecture:** Pure CSS theme overhaul with React effect components. CSS custom properties in `base.css` provide the entire color/font system. New `effects/` directory holds canvas/CSS animation components. No backend changes.

**Tech Stack:** React 18, Vite, plain CSS, Google Fonts (Share Tech Mono), HTML5 Canvas

**Spec:** `docs/superpowers/specs/2026-03-23-hacker-theme-design.md`

---

## File Structure

### Files to modify (existing)

| File | Responsibility |
|------|---------------|
| `frontend/index.html` | Add Google Fonts link |
| `frontend/src/main.jsx` | Import new `animations.css` |
| `frontend/src/App.jsx` | Wrap with scanline overlay, add bottom status bar |
| `frontend/src/css/base.css` | Replace all token values, add glow/font tokens |
| `frontend/src/css/layout.css` | Rewrite to tmux panel layout |
| `frontend/src/css/components.css` | Update all component colors, hardcoded colors, radius |
| `frontend/src/components/Header.jsx` | Convert to status bar |
| `frontend/src/components/SideMenu.jsx` | Convert to left panel with hacker styling |
| `frontend/src/components/WarningModal.jsx` | Dark theme modal |

### Files to create (new)

| File | Responsibility |
|------|---------------|
| `frontend/src/css/animations.css` | All @keyframes, prefers-reduced-motion overrides |
| `frontend/src/effects/ScanlineOverlay.jsx` | CRT scanline CSS overlay |
| `frontend/src/effects/MatrixRain.jsx` | Canvas-based falling binary characters |
| `frontend/src/effects/BootSequence.jsx` | BIOS-style startup animation |
| `frontend/src/effects/useStatusMessages.js` | Random status message hook |

### Files NOT changed

All files under `frontend/src/api/`, `frontend/src/utils/`, `frontend/src/tools/proofreading/preprocess.js`, `frontend/src/tools/proofreading/fileExtractor.js`, `frontend/src/context/AuthContext.jsx`, backend.

---

## Task 1: Design Tokens & Font Setup

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/css/base.css`
- Test: run `cd frontend && npm run build` (visual check)

- [ ] **Step 1: Add Google Fonts to index.html**

Add Share Tech Mono font link to `<head>`:

```html
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>GovAssist</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Replace all CSS custom properties in base.css**

Replace the entire `:root` block and `body` font-family. Keep the CSS reset unchanged.

```css
body {
  font-family: 'Share Tech Mono', 'Hiragino Sans', 'Noto Sans JP', 'Yu Gothic', 'Meiryo', monospace;
  color: var(--color-text);
  background-color: var(--color-bg);
}

:root {
  /* Font */
  --font-mono: 'Share Tech Mono', 'Courier New', monospace;
  --font-body: 'Share Tech Mono', 'Hiragino Sans', 'Noto Sans JP', 'Yu Gothic', monospace;

  /* Text colors */
  --color-text: #c0ffd8;
  --color-text-bright: #00ff41;
  --color-text-muted: #5a8a62;

  /* Background colors */
  --color-bg: #000000;
  --color-bg-secondary: #0a0a0a;
  --color-bg-elevated: #0d1117;
  --color-bg-hover: rgba(0, 255, 65, 0.08);
  --color-bg-active: rgba(0, 255, 65, 0.15);

  /* Border */
  --color-border: rgba(0, 255, 65, 0.2);
  --color-border-focus: #00ff41;

  /* Accent */
  --color-primary: #00ff41;
  --color-primary-hover: #33ff66;
  --color-primary-active: #00cc33;
  --color-accent: #00ffff;
  --color-danger: #ff0040;
  --color-danger-hover: #ff3366;
  --color-warning: #ffaa00;
  --color-success: #39ff14;
  --color-info: #00ffff;

  /* Diff colors */
  --color-diff-delete-bg: rgba(255, 0, 64, 0.25);
  --color-diff-delete-text: #ff2244;
  --color-diff-insert-bg: rgba(0, 255, 65, 0.25);
  --color-diff-insert-text: #44ff88;

  /* Layout dimensions */
  --header-height: 32px;
  --sidebar-width: 200px;
  --status-bar-height: 28px;

  /* Spacing scale (unchanged) */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;

  /* Typography */
  --font-size-xs: 0.7rem;
  --font-size-sm: 0.8rem;
  --font-size-base: 0.85rem;
  --font-size-lg: 1rem;
  --font-size-xl: 1.125rem;
  --font-size-2xl: 1.25rem;

  /* Border radius — sharp for hacker feel */
  --radius-sm: 1px;
  --radius: 2px;
  --radius-lg: 3px;

  /* Shadows — glow-based */
  --shadow-sm: 0 0 4px rgba(0, 255, 65, 0.1);
  --shadow: 0 0 6px rgba(0, 255, 65, 0.15);
  --shadow-lg: 0 0 12px rgba(0, 255, 65, 0.2);

  /* Glow tokens */
  --glow-primary: 0 0 8px #00ff41;
  --glow-accent: 0 0 8px #00ffff;
  --glow-danger: 0 0 8px #ff0040;
  --glow-success: 0 0 8px #39ff14;
  --glow-warning: 0 0 8px #ffaa00;

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition: 200ms ease;
}
```

- [ ] **Step 3: Build and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors. Open dev server and verify black background with green text.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html frontend/src/css/base.css
git commit -m "feat(hacker-theme): replace design tokens with hacker terminal palette"
```

---

## Task 2: Layout — tmux Panel Structure

**Files:**
- Modify: `frontend/src/css/layout.css`
- Modify: `frontend/src/App.jsx`
- Test: run `cd frontend && npm run build`

- [ ] **Step 1: Rewrite layout.css for tmux panels**

Replace entire `layout.css`:

```css
/* ============================================
   layout.css — tmux-style Panel Layout
   ============================================ */

/* --- App container (full viewport) --- */

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background-color: var(--color-bg);
}

/* --- Top Status Bar --- */

.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--header-height);
  padding: 0 var(--spacing-md);
  background-color: var(--color-bg-elevated);
  flex-shrink: 0;
  z-index: 100;
  font-size: var(--font-size-sm);
  border-bottom: 1px solid var(--color-border);
}

.status-bar::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 255, 65, 0.4), transparent);
}

.status-bar__left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--color-text-bright);
  text-shadow: var(--glow-primary);
}

.status-bar__prompt {
  color: var(--color-primary);
  font-weight: bold;
}

.status-bar__version {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.status-bar__indicator {
  color: var(--color-success);
  text-shadow: var(--glow-success);
}

.status-bar__right {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--color-accent);
  font-size: var(--font-size-xs);
}

.status-bar__actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

/* --- Panel area (sidebar + main) --- */

.app-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* --- Left Panel (modules nav) --- */

.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  background-color: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  flex-shrink: 0;
  font-size: var(--font-size-sm);
}

.sidebar__nav {
  flex: 1;
  padding: var(--spacing-sm) 0;
}

.sidebar__footer {
  padding: var(--spacing-sm) 0;
  border-top: 1px solid var(--color-border);
}

.sidebar__label {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  letter-spacing: 2px;
  padding: var(--spacing-xs) var(--spacing-md);
  text-transform: uppercase;
}

.sidebar__item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
  user-select: none;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
  border-left: 2px solid transparent;
}

.sidebar__item:hover {
  background-color: var(--color-bg-hover);
  color: var(--color-text);
}

.sidebar__item--active {
  background-color: rgba(0, 255, 65, 0.08);
  color: var(--color-text-bright);
  border-left-color: var(--color-primary);
  text-shadow: var(--glow-primary);
}

.sidebar__item--disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.3;
}

.sidebar__item--disabled:hover {
  background-color: transparent;
  color: var(--color-text-muted);
}

.sidebar__item-icon {
  font-size: 1em;
  width: 1.2em;
  text-align: center;
  flex-shrink: 0;
}

/* --- Main Panel --- */

.main-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-md);
  background-color: var(--color-bg);
}

/* --- Bottom System Bar --- */

.system-bar {
  display: flex;
  align-items: center;
  height: var(--status-bar-height);
  padding: 0 var(--spacing-md);
  background-color: var(--color-bg-elevated);
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  gap: var(--spacing-sm);
}

.system-bar__status {
  color: var(--color-success);
}

.system-bar__message {
  color: var(--color-text-muted);
  margin-left: var(--spacing-md);
}

.system-bar__spacer {
  flex: 1;
}

.system-bar__info {
  color: var(--color-text-muted);
  opacity: 0.5;
}
```

- [ ] **Step 2: Update App.jsx — add status bar + system bar**

```jsx
// src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import SideMenu from './components/SideMenu';
import WarningModal from './components/WarningModal';
import Proofreading from './tools/proofreading/Proofreading';
import History from './tools/history/History';
import Settings from './tools/settings/Settings';

function App() {
  return (
    <div className="app">
      <WarningModal />
      <Header />
      <div className="app-content">
        <SideMenu />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Proofreading />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/history" element={<History />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
      <div className="system-bar">
        <span className="system-bar__status">●</span>
        <span>READY</span>
        <span className="system-bar__message">All systems operational.</span>
        <span className="system-bar__spacer" />
        <span className="system-bar__info">localhost:8000</span>
      </div>
    </div>
  );
}

export default App;
```

- [ ] **Step 3: Build and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds. Visual: top status bar, left panel, main content, bottom system bar visible.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/css/layout.css frontend/src/App.jsx
git commit -m "feat(hacker-theme): convert layout to tmux-style panel structure"
```

---

## Task 3: Component Styles — Buttons, Inputs, Forms

**Files:**
- Modify: `frontend/src/css/components.css` (buttons, inputs, labels, checkboxes, form groups, select dropdown)

- [ ] **Step 1: Update button styles in components.css**

Replace the Buttons section:

```css
/* --- Buttons --- */

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-mono);
  line-height: 1.5;
  border: 1px solid transparent;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background-color var(--transition-fast),
              border-color var(--transition-fast),
              box-shadow var(--transition-fast),
              color var(--transition-fast);
  user-select: none;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn--primary {
  background-color: var(--color-primary);
  color: #000;
  border-color: var(--color-primary);
  font-weight: bold;
  box-shadow: var(--glow-primary);
}

.btn--primary:hover:not(:disabled) {
  background-color: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
  box-shadow: 0 0 14px rgba(0, 255, 65, 0.4);
}

.btn--primary:active:not(:disabled) {
  background-color: var(--color-primary-active);
}

.btn--secondary {
  background-color: transparent;
  color: var(--color-primary);
  border-color: var(--color-border);
}

.btn--secondary:hover:not(:disabled) {
  background-color: var(--color-bg-hover);
  border-color: var(--color-primary);
  box-shadow: var(--glow-primary);
}

.btn--danger {
  background-color: transparent;
  color: var(--color-danger);
  border-color: rgba(255, 0, 64, 0.3);
}

.btn--danger:hover:not(:disabled) {
  background-color: rgba(255, 0, 64, 0.1);
  border-color: var(--color-danger);
  box-shadow: var(--glow-danger);
}

.btn--sm {
  padding: 1px var(--spacing-sm);
  font-size: var(--font-size-xs);
}

.btn--lg {
  padding: var(--spacing-xs) var(--spacing-lg);
  font-size: var(--font-size-base);
}
```

- [ ] **Step 2: Update input, textarea, select styles**

Replace the Inputs section:

```css
/* --- Inputs --- */

.input,
.textarea,
.select {
  width: 100%;
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-family: var(--font-mono);
  line-height: 1.5;
  color: var(--color-text);
  background-color: rgba(0, 255, 65, 0.03);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  transition: border-color var(--transition-fast),
              box-shadow var(--transition-fast);
}

.input:focus,
.textarea:focus,
.select:focus {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: var(--glow-primary);
}

.input::placeholder,
.textarea::placeholder {
  color: var(--color-text-muted);
}

.input:disabled,
.textarea:disabled,
.select:disabled {
  opacity: 0.3;
}

.textarea {
  min-height: 10rem;
  resize: vertical;
}

.select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  padding-right: 2.5rem;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%2300ff41'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  background-size: 10px;
  cursor: pointer;
}
```

- [ ] **Step 3: Update label, checkbox, form styles**

Replace the Label, Checkbox, and Form group sections:

```css
/* --- Label --- */

.label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-bright);
  font-weight: normal;
  letter-spacing: 0.5px;
}

/* --- Checkbox --- */

.checkbox {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  user-select: none;
  font-size: var(--font-size-sm);
  color: var(--color-text);
}

.checkbox__input {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: var(--color-primary);
}
```

- [ ] **Step 4: Build and verify**

Run: `cd frontend && npm run build`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/css/components.css
git commit -m "feat(hacker-theme): update button, input, form component styles"
```

---

## Task 4: Component Styles — Tabs, Messages, Spinner, Tooltip, Modal

**Files:**
- Modify: `frontend/src/css/components.css` (tabs, messages, spinner, tooltip, modal sections)

- [ ] **Step 1: Update tabs**

Replace the Tabs section:

```css
/* --- Tabs --- */

.tabs {
  display: flex;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--spacing-md);
}

.tab {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-mono);
  color: var(--color-text-muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  cursor: pointer;
  transition: color var(--transition-fast),
              border-color var(--transition-fast),
              text-shadow var(--transition-fast);
}

.tab:hover {
  color: var(--color-text);
}

.tab--active {
  color: var(--color-text-bright);
  border-bottom-color: var(--color-primary);
  text-shadow: var(--glow-primary);
}
```

- [ ] **Step 2: Update messages (hardcoded colors)**

Replace the Messages section:

```css
/* --- Messages --- */

.message {
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius);
  font-size: var(--font-size-sm);
  line-height: 1.5;
  border: 1px solid;
}

.message--warning {
  background-color: rgba(255, 170, 0, 0.1);
  color: var(--color-warning);
  border-color: rgba(255, 170, 0, 0.2);
}

.message--error {
  background-color: rgba(255, 0, 64, 0.1);
  color: var(--color-danger);
  border-color: rgba(255, 0, 64, 0.2);
}

.message--success {
  background-color: rgba(57, 255, 20, 0.1);
  color: var(--color-success);
  border-color: rgba(57, 255, 20, 0.2);
}

.message--info {
  background-color: rgba(0, 255, 255, 0.1);
  color: var(--color-accent);
  border-color: rgba(0, 255, 255, 0.2);
}
```

- [ ] **Step 3: Update spinner, tooltip, modal**

Replace Spinner section (color only — keep @keyframes):

```css
/* --- Spinner --- */

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  box-shadow: var(--glow-primary);
}
/* spinner--sm and --lg unchanged */

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg);
  color: var(--color-text-muted);
}
```

Replace Tooltip section:

```css
/* --- Tooltip --- */

.tooltip {
  position: relative;
}

.tooltip::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: calc(100% + var(--spacing-xs));
  left: 50%;
  transform: translateX(-50%);
  padding: var(--spacing-xs) var(--spacing-sm);
  background-color: var(--color-bg-elevated);
  color: var(--color-text);
  font-size: var(--font-size-xs);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--transition-fast);
  z-index: 1000;
  box-shadow: var(--glow-primary);
}

.tooltip:hover::after {
  opacity: 1;
}
```

Replace Modal section:

```css
/* --- Modal --- */

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--glow-primary);
  padding: var(--spacing-lg);
  max-width: 480px;
  width: 90%;
}

.modal__title {
  font-size: var(--font-size-lg);
  color: var(--color-text-bright);
  text-shadow: var(--glow-primary);
  margin-bottom: var(--spacing-md);
  letter-spacing: 1px;
}

.modal__body {
  margin-bottom: var(--spacing-lg);
  line-height: 1.6;
  color: var(--color-text);
}

.modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
}
```

- [ ] **Step 4: Build and verify**

Run: `cd frontend && npm run build`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/css/components.css
git commit -m "feat(hacker-theme): update tabs, messages, spinner, tooltip, modal styles"
```

---

## Task 5: Component Styles — Diff, Badge, Drop Zone, Cards, Remaining

**Files:**
- Modify: `frontend/src/css/components.css` (diff, badge, drop zone, card, correction list, history, settings, utilities)

- [ ] **Step 1: Update diff styles with glow effects**

Replace Diff highlights section:

```css
/* --- Diff highlights --- */

.diff-delete {
  background-color: var(--color-diff-delete-bg);
  color: var(--color-diff-delete-text);
  text-decoration: line-through;
  text-shadow: 0 0 6px rgba(255, 0, 64, 0.4);
  border: 1px solid rgba(255, 0, 64, 0.2);
  padding: 0 2px;
  border-radius: 1px;
}

.diff-insert {
  background-color: var(--color-diff-insert-bg);
  color: var(--color-diff-insert-text);
  text-shadow: 0 0 6px rgba(0, 255, 65, 0.4);
  border: 1px solid rgba(0, 255, 65, 0.2);
  padding: 0 2px;
  border-radius: 1px;
  box-shadow: 0 0 8px rgba(0, 255, 65, 0.1);
}
```

- [ ] **Step 2: Update drop zone, card, badge**

Replace Drop zone section:

```css
/* --- Drop Zone --- */

.drop-zone {
  border: 1px dashed var(--color-border);
  border-radius: var(--radius);
  padding: var(--spacing-lg);
  text-align: center;
  color: var(--color-text-muted);
  transition: border-color var(--transition-fast),
              background-color var(--transition-fast),
              box-shadow var(--transition-fast);
  cursor: pointer;
}

.drop-zone:hover,
.drop-zone--active {
  border-color: var(--color-primary);
  background-color: rgba(0, 255, 65, 0.05);
  box-shadow: var(--glow-primary);
}
```

Replace Card section:

```css
/* --- Card --- */

.card {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--spacing-md);
}
```

Replace Badge section:

```css
/* --- Badge --- */

.badge {
  display: inline-flex;
  align-items: center;
  padding: 1px var(--spacing-sm);
  font-size: var(--font-size-xs);
  border-radius: var(--radius-sm);
  background-color: rgba(255, 170, 0, 0.15);
  color: var(--color-warning);
  border: 1px solid rgba(255, 170, 0, 0.2);
}

.badge--warning {
  background-color: rgba(255, 170, 0, 0.15);
  color: var(--color-warning);
  border-color: rgba(255, 170, 0, 0.2);
}

.badge--info {
  background-color: rgba(0, 255, 255, 0.15);
  color: var(--color-accent);
  border-color: rgba(0, 255, 255, 0.2);
}
```

- [ ] **Step 3: Update correction list styles**

Replace the Correction List section with hacker-styled items:

```css
/* --- Correction List --- */

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
  background-color: var(--color-bg-secondary);
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
  width: 22px;
  height: 22px;
  border-radius: var(--radius);
  background-color: var(--color-primary);
  color: #000;
  font-size: var(--font-size-xs);
  font-weight: bold;
  flex-shrink: 0;
  text-shadow: none;
}

.correction-item__category {
  font-size: var(--font-size-xs);
  color: var(--color-accent);
  background-color: rgba(0, 255, 255, 0.1);
  padding: 1px var(--spacing-sm);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(0, 255, 255, 0.2);
}

.correction-item__pair {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.correction-item__original,
.correction-item__corrected {
  font-size: var(--font-size-sm);
  line-height: 1.6;
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-sm);
}

.correction-item__original {
  background-color: rgba(255, 0, 64, 0.1);
  color: var(--color-diff-delete-text);
}

.correction-item__corrected {
  background-color: rgba(0, 255, 65, 0.1);
  color: var(--color-diff-insert-text);
}

.correction-item__label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: normal;
  margin-right: var(--spacing-xs);
}

.correction-item__reason {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-top: var(--spacing-xs);
  padding-top: var(--spacing-xs);
  border-top: 1px dashed var(--color-border);
}
```

- [ ] **Step 4: Update history, settings, remaining styles**

Replace History Item section:

```css
/* --- History Item --- */

.history-item {
  position: relative;
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--spacing-sm) var(--spacing-md);
  cursor: pointer;
  transition: border-color var(--transition-fast),
              box-shadow var(--transition-fast);
}

.history-item:hover {
  border-color: var(--color-primary);
  box-shadow: var(--glow-primary);
}

.history-item__date {
  color: var(--color-text-muted);
}

.history-item__preview {
  color: var(--color-text);
}

.history-item__meta {
  color: var(--color-text-muted);
}
```

Update the following selectors that reference `--color-text-secondary` → `--color-text-bright`:
- `.history-item__date`
- `.history-detail__meta`
- `.result-view__notice`
- `.correction-item__label`
- `.correction-item__reason`
- `.diff-compare__panel-header`
- `.history-list__pagination`
- `.login-page__help`
- `.option-panel__legend`

Update `.result-view` and related:
```css
.result-view__summary {
  color: var(--color-text);
}

.result-view__notice {
  color: var(--color-text-muted);
}

.result-view__corrected-text h4 {
  color: var(--color-text-bright);
  text-shadow: var(--glow-primary);
}

.result-view__corrected-text-body {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--spacing-md);
  max-height: 400px;
  overflow-y: auto;
}

.result-view__panel {
  min-height: 100px;
}
```

Update settings:
```css
.settings__section-title {
  color: var(--color-text-bright);
  text-shadow: var(--glow-primary);
}

.settings__hint {
  color: var(--color-text-muted);
}

.history-detail__section h3 {
  color: var(--color-text-bright);
  text-shadow: var(--glow-primary);
}
```

- [ ] **Step 5: Build and verify**

Run: `cd frontend && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/css/components.css
git commit -m "feat(hacker-theme): update diff, badge, correction, history, settings styles"
```

---

## Task 6: Header → Status Bar + SideMenu → Left Panel

**Files:**
- Modify: `frontend/src/components/Header.jsx`
- Modify: `frontend/src/components/SideMenu.jsx`
- Test: run `cd frontend && npm test`

- [ ] **Step 1: Rewrite Header.jsx as status bar**

```jsx
// src/components/Header.jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSettings, saveSettings } from '../utils/storage';
import { apiGet } from '../api/client';

const DEFAULT_MODEL = { model_id: 'kimi-k2.5', display_name: 'Kimi K2.5' };

function Header() {
  const navigate = useNavigate();
  const [models, setModels] = useState([DEFAULT_MODEL]);
  const [selectedModel, setSelectedModel] = useState(() => loadSettings().model);

  useEffect(() => {
    apiGet('/api/models')
      .then(data => {
        if (data.models?.length > 0) {
          setModels(data.models);
          const settings = loadSettings();
          const ids = data.models.map(m => m.model_id);
          if (!ids.includes(settings.model)) {
            const fallback = data.models[0].model_id;
            setSelectedModel(fallback);
            saveSettings({ ...settings, model: fallback });
          }
        }
      })
      .catch(() => {});
  }, []);

  const handleModelChange = (e) => {
    const newModel = e.target.value;
    setSelectedModel(newModel);
    saveSettings({ ...loadSettings(), model: newModel });
  };

  return (
    <header className="status-bar">
      <div className="status-bar__left">
        <span className="status-bar__prompt">▶</span>
        <span>GOV_ASSIST</span>
        <span className="status-bar__version">v1.0</span>
        <span className="status-bar__indicator">● ONLINE</span>
      </div>
      <div className="status-bar__right">
        <span>[ AI: {models.find(m => m.model_id === selectedModel)?.display_name || selectedModel} ]</span>
        <div className="status-bar__actions">
          <select
            className="select"
            value={selectedModel}
            onChange={handleModelChange}
            style={{ width: 'auto', fontSize: 'var(--font-size-xs)' }}
            aria-label="AI モデル選択"
          >
            {models.map(model => (
              <option key={model.model_id} value={model.model_id}>
                {model.display_name}
              </option>
            ))}
          </select>
          <button
            className="btn btn--sm btn--secondary"
            onClick={() => navigate('/settings')}
            aria-label="設定を開く"
            type="button"
          >
            ⚙
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
```

- [ ] **Step 2: Rewrite SideMenu.jsx for left panel**

```jsx
// src/components/SideMenu.jsx
import { useNavigate, useLocation } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/', label: 'proofread', displayLabel: '校正ツール', icon: '▸' },
  { path: '/history', label: 'history', displayLabel: '履歴', icon: '○' },
  { path: null, label: 'translate', displayLabel: '翻訳ツール', icon: '○' },
  { path: null, label: 'summarize', displayLabel: '要約ツール', icon: '○' },
  { path: null, label: 'format', displayLabel: 'フォーマット', icon: '○' },
];

const FOOTER_ITEMS = [
  { path: '/settings', label: 'settings', displayLabel: '設定', icon: '○' },
];

function MenuItem({ path, label, displayLabel, icon, isActive }) {
  const navigate = useNavigate();
  const disabled = !path;
  const activeIcon = isActive ? '▸' : icon;

  const className = [
    'sidebar__item',
    isActive ? 'sidebar__item--active' : '',
    disabled ? 'sidebar__item--disabled' : '',
  ].filter(Boolean).join(' ');

  return (
    <button
      className={className}
      disabled={disabled}
      onClick={() => { if (path) navigate(path); }}
    >
      <span className="sidebar__item-icon">{activeIcon}</span>
      {displayLabel}
    </button>
  );
}

function SideMenu() {
  const location = useLocation();

  return (
    <aside className="sidebar">
      <div className="sidebar__label">[ MODULES ]</div>
      <nav className="sidebar__nav">
        {NAV_ITEMS.map(item => (
          <MenuItem
            key={item.label}
            path={item.path}
            label={item.label}
            displayLabel={item.displayLabel}
            icon={item.icon}
            isActive={location.pathname === item.path}
          />
        ))}
      </nav>
      <div className="sidebar__footer">
        {FOOTER_ITEMS.map(item => (
          <MenuItem
            key={item.label}
            path={item.path}
            label={item.label}
            displayLabel={item.displayLabel}
            icon={item.icon}
            isActive={location.pathname === item.path}
          />
        ))}
      </div>
    </aside>
  );
}

export default SideMenu;
```

- [ ] **Step 3: Run tests**

Run: `cd frontend && npx vitest run src/components/Header.test.jsx src/components/SideMenu.test.jsx src/App.test.jsx`
Expected: Tests may fail due to class name changes. Update test assertions to match new class names and structure. Fix any broken selectors (`.app-header` → `.status-bar`, etc.).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Header.jsx frontend/src/components/SideMenu.jsx
git commit -m "feat(hacker-theme): convert Header to status bar, SideMenu to left panel"
```

---

## Task 7: Animations CSS & Scanline Overlay

**Files:**
- Create: `frontend/src/css/animations.css`
- Create: `frontend/src/effects/ScanlineOverlay.jsx`
- Modify: `frontend/src/main.jsx`

- [ ] **Step 1: Create animations.css**

```css
/* ============================================
   animations.css — @keyframes & motion overrides
   ============================================ */

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes flicker {
  0%, 95%, 100% { opacity: 1; }
  96% { opacity: 0.85; }
  97% { opacity: 1; }
  98% { opacity: 0.9; }
}

@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 8px rgba(0, 255, 65, 0.3); }
  50% { box-shadow: 0 0 16px rgba(0, 255, 65, 0.5); }
}

@keyframes text-glow-pulse {
  0%, 100% { text-shadow: 0 0 6px rgba(0, 255, 65, 0.3); }
  50% { text-shadow: 0 0 12px rgba(0, 255, 65, 0.6); }
}

@keyframes access-flash {
  0% { background-color: #00ff41; color: #000; text-shadow: none; }
  100% { background-color: transparent; color: #00ff41; text-shadow: 0 0 12px #00ff41; }
}

@keyframes glitch {
  0%, 90%, 100% { transform: translateX(0); }
  92% { transform: translateX(-2px); }
  94% { transform: translateX(2px); }
  96% { transform: translateX(-1px); }
  98% { transform: translateX(1px); }
}

@keyframes typewriter-cursor {
  0%, 50% { border-right-color: #00ff41; }
  51%, 100% { border-right-color: transparent; }
}

@keyframes blink-indicator {
  0%, 40%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

@keyframes scanline-scroll {
  0% { transform: translateY(0); }
  100% { transform: translateY(4px); }
}

/* --- prefers-reduced-motion: disable all animations and glow --- */

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }

  .scanline-overlay {
    display: none !important;
  }

  .status-bar__left,
  .status-bar__prompt,
  .sidebar__item--active,
  .modal__title,
  .settings__section-title,
  .history-detail__section h3,
  .tab--active {
    text-shadow: none !important;
  }
}
```

- [ ] **Step 2: Create ScanlineOverlay.jsx**

```jsx
// src/effects/ScanlineOverlay.jsx
export default function ScanlineOverlay() {
  return (
    <div
      className="scanline-overlay"
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'repeating-linear-gradient(0deg, rgba(0,255,65,0.03) 0px, rgba(0,255,65,0.03) 1px, transparent 1px, transparent 2px)',
        pointerEvents: 'none',
        zIndex: 9999,
      }}
    />
  );
}
```

- [ ] **Step 3: Add imports to main.jsx**

Add to `frontend/src/main.jsx`:

```jsx
import './css/animations.css';
import ScanlineOverlay from './effects/ScanlineOverlay';
```

And in the JSX render, add `<ScanlineOverlay />` as a sibling of `<App />` inside `<BrowserRouter>`:

```jsx
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ScanlineOverlay />
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
```

- [ ] **Step 4: Build and verify**

Run: `cd frontend && npm run build`
Expected: Scanline overlay visible across entire app. No flicker in reduced-motion mode.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/css/animations.css frontend/src/effects/ScanlineOverlay.jsx frontend/src/main.jsx
git commit -m "feat(hacker-theme): add CRT scanline overlay and animation keyframes"
```

---

## Task 8: Matrix Rain Canvas Effect

**Files:**
- Create: `frontend/src/effects/MatrixRain.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Create MatrixRain.jsx**

```jsx
// src/effects/MatrixRain.jsx
import { useEffect, useRef } from 'react';

const CHARS = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';

export default function MatrixRain() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationId;
    let columns = [];
    const fontSize = 12;

    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      const colCount = Math.floor(canvas.width / fontSize);
      columns = Array.from({ length: colCount }, () => Math.random() * canvas.height / fontSize);
    }

    resize();
    window.addEventListener('resize', resize);

    function draw() {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#00ff41';
      ctx.font = `${fontSize}px monospace`;

      for (let i = 0; i < columns.length; i++) {
        const char = CHARS[Math.floor(Math.random() * CHARS.length)];
        const x = i * fontSize;
        const y = columns[i] * fontSize;
        ctx.globalAlpha = Math.random() * 0.3 + 0.1;
        ctx.fillText(char, x, y);
        ctx.globalAlpha = 1;

        if (y > canvas.height && Math.random() > 0.975) {
          columns[i] = 0;
        }
        columns[i]++;
      }

      animationId = requestAnimationFrame(draw);
    }

    animationId = requestAnimationFrame(draw);

    // Pause when tab is not visible
    const handleVisibility = () => {
      if (document.hidden) {
        cancelAnimationFrame(animationId);
      } else {
        animationId = requestAnimationFrame(draw);
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
        opacity: 0.4,
      }}
    />
  );
}
```

- [ ] **Step 2: Add MatrixRain to App.jsx**

Import and render `<MatrixRain />` inside `.app` div, before `<WarningModal />`:

```jsx
import MatrixRain from './effects/MatrixRain';
```

```jsx
<div className="app">
  <MatrixRain />
  <WarningModal />
  {/* ... rest ... */}
</div>
```

- [ ] **Step 3: Build and verify**

Run: `cd frontend && npm run build`
Expected: Green characters falling in background. Performance should be smooth.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/effects/MatrixRain.jsx frontend/src/App.jsx
git commit -m "feat(hacker-theme): add Matrix rain canvas background effect"
```

---

## Task 9: Boot Sequence Effect

**Files:**
- Create: `frontend/src/effects/BootSequence.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Create BootSequence.jsx**

```jsx
// src/effects/BootSequence.jsx
import { useState, useEffect, useCallback } from 'react';

const BOOT_LINES = [
  'GOV_ASSIST BIOS v2.0 — POST check...',
  'Memory test... 8192K OK',
  'Loading AI kernel... kimi-k2.5',
  'Connecting to localhost:8000... CONNECTED',
  'Mounting SQLite database... MOUNTED',
  '[ SYSTEM READY ]',
];

const TYPE_DELAY = 80;  // ms per line
const SKIP_DELAY = 500; // ms after all lines shown

export default function BootSequence({ onComplete }) {
  const [visibleLines, setVisibleLines] = useState([]);
  const [complete, setComplete] = useState(false);

  useEffect(() => {
    const lines = [...BOOT_LINES];
    let index = 0;

    const timer = setInterval(() => {
      if (index < lines.length) {
        setVisibleLines(prev => [...prev, lines[index]]);
        index++;
      } else {
        clearInterval(timer);
        setTimeout(() => setComplete(true), SKIP_DELAY);
      }
    }, TYPE_DELAY);

    return () => clearInterval(timer);
  }, []);

  const handleSkip = useCallback(() => {
    setComplete(true);
  }, []);

  useEffect(() => {
    if (complete && onComplete) {
      onComplete();
    }
  }, [complete, onComplete]);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
        handleSkip();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [handleSkip]);

  if (complete) return null;

  return (
    <div
      onClick={handleSkip}
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        inset: 0,
        background: '#000',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        fontFamily: "'Share Tech Mono', 'Courier New', monospace",
      }}
    >
      <div style={{ color: '#00ff41', fontSize: '13px', lineHeight: '2', padding: '20px' }}>
        {visibleLines.map((line, i) => (
          <div
            key={i}
            style={{
              textShadow: '0 0 4px #00ff41',
              opacity: line.startsWith('[') ? 1 : 0.7,
            }}
          >
            {line}
          </div>
        ))}
        <div style={{ opacity: 0.3, marginTop: '8px' }}>click or press any key to skip</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add BootSequence to App.jsx**

```jsx
import { useState, useCallback } from 'react';
import BootSequence from './effects/BootSequence';
```

```jsx
function App() {
  const [bootDone, setBootDone] = useState(false);

  const handleBootComplete = useCallback(() => setBootDone(true), []);

  return (
    <div className="app">
      {!bootDone && <BootSequence onComplete={handleBootComplete} />}
      {/* ... rest ... */}
    </div>
  );
}
```

- [ ] **Step 3: Build and verify**

Run: `cd frontend && npm run build`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/effects/BootSequence.jsx frontend/src/App.jsx
git commit -m "feat(hacker-theme): add BIOS-style boot sequence on startup"
```

---

## Task 10: Random Status Messages

**Files:**
- Create: `frontend/src/effects/useStatusMessages.js`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Create useStatusMessages.js**

```jsx
// src/effects/useStatusMessages.js
import { useState, useEffect, useRef } from 'react';

const MESSAGES = [
  'All systems operational.',
  'Firewall: ACTIVE (localhost only)',
  'Coffee level: CRITICAL',
  'There is no place like 127.0.0.1',
  'SSH connection secure. Probably.',
  'AI model loaded. Skynet is not activated.',
  'Remember: with great power comes great responsibility',
  'rm -rf /boredom',
  'Document processed: 0 errors found',
  'Uptime: calculating...',
  'Token budget: sufficient',
  'No backdoors found. Yet.',
];

const INTERVAL_MS = 5000;

export default function useStatusMessages() {
  const [message, setMessage] = useState(MESSAGES[0]);
  const indexRef = useRef(0);

  useEffect(() => {
    const timer = setInterval(() => {
      indexRef.current = (indexRef.current + 1) % MESSAGES.length;
      setMessage(MESSAGES[indexRef.current]);
    }, INTERVAL_MS);

    return () => clearInterval(timer);
  }, []);

  return message;
}
```

- [ ] **Step 2: Wire into App.jsx system bar**

```jsx
import useStatusMessages from './effects/useStatusMessages';
```

```jsx
function App() {
  const statusMessage = useStatusMessages();
  // ...

  return (
    // ...
    <div className="system-bar">
      <span className="system-bar__status">●</span>
      <span>READY</span>
      <span className="system-bar__message">{statusMessage}</span>
      <span className="system-bar__spacer" />
      <span className="system-bar__info">localhost:8000</span>
    </div>
  );
}
```

- [ ] **Step 3: Build and verify**

- [ ] **Step 4: Commit**

```bash
git add frontend/src/effects/useStatusMessages.js frontend/src/App.jsx
git commit -m "feat(hacker-theme): add random status messages to system bar"
```

---

## Task 11: Update Tests

**Files:**
- Modify: `frontend/src/components/Header.test.jsx`
- Modify: `frontend/src/components/SideMenu.test.jsx`
- Modify: `frontend/src/App.test.jsx`
- Modify: Any other tests that reference old class names or color values

- [ ] **Step 1: Run all tests and identify failures**

Run: `cd frontend && npx vitest run 2>&1 | head -100`

- [ ] **Step 2: Fix Header.test.jsx**

Update selectors from `.app-header` to `.status-bar`, `.app-header__title` to `.status-bar__left`, etc. Update expected text assertions.

- [ ] **Step 3: Fix SideMenu.test.jsx**

Update selector assertions. The component no longer uses emoji icons — it uses `▸` and `○` characters. Update icon assertions.

- [ ] **Step 4: Fix App.test.jsx**

The App structure now includes `MatrixRain`, `BootSequence`, and system bar. Update test assertions to match new structure.

- [ ] **Step 5: Fix any remaining test failures**

Check all test files for:
- References to `.app-header` → `.status-bar`
- References to `.app-header__title` → `.status-bar__left` or `.status-bar__prompt`
- Color value assertions (hex colors in snapshots or expect calls)
- Class name assertions

- [ ] **Step 6: Run all tests to verify**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "test(hacker-theme): update tests for new hacker theme structure"
```

---

## Task 12: Visual Polish & Final Verification

**Files:**
- Modify: Any files needing final adjustments after visual review

- [ ] **Step 1: Start dev server and review all pages**

Run: `cd frontend && npm run dev`

Review each page:
- [ ] Landing page (proofreading tool) — tmux layout, green theme, scanlines, matrix rain
- [ ] History list — dark cards, glow hover
- [ ] History detail — diff display with glow effects
- [ ] Settings — dark form elements
- [ ] Warning modal — dark overlay, green border glow
- [ ] Boot sequence on refresh
- [ ] Status bar with model selector
- [ ] System bar with rotating messages

- [ ] **Step 2: Test keyboard accessibility**

- [ ] Tab through all interactive elements
- [ ] Verify focus indicators (green glow border) are visible
- [ ] Test Escape/Enter/Space to skip boot sequence

- [ ] **Step 3: Test prefers-reduced-motion**

Open browser DevTools → Rendering → "prefers-reduced-motion: reduce"
- [ ] All animations stop
- [ ] Scanline overlay hidden
- [ ] Text glow (text-shadow) removed
- [ ] Matrix rain should pause (visibility change)

- [ ] **Step 4: Performance check**

Open DevTools → Performance tab
- [ ] Record 5 seconds of idle + interactions
- [ ] Check frame rate stays above 30fps
- [ ] If Matrix rain is too heavy, reduce opacity or column density

- [ ] **Step 5: Final commit with any polish fixes**

```bash
git add -A
git commit -m "feat(hacker-theme): visual polish and final adjustments"
```
