# Task 12: フロントエンドプロジェクトセットアップ & CSS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the Vite + React 18 frontend project with a complete CSS architecture (reset, layout, component styles) matching the design spec, verified with a minimal layout shell.

**Architecture:** Vite dev server (port 5173) with `/api` proxy to FastAPI backend (port 8000). Plain CSS with BEM-like naming convention and CSS custom properties for theming. Layout uses CSS Flexbox with a 200px fixed sidebar as specified in §3.1. No Tailwind, no TypeScript.

**Tech Stack:** React 18, Vite, plain CSS (no Tailwind)

**Design Spec References:** §2.2 (tech stack), §3.1 (overall layout), §3.2 (side menu composition), §3.3.4 (diff colors), §11 (directory structure)

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `frontend/` | Vite + React 18 project (via `create-vite`) |
| Modify | `frontend/vite.config.js` | Dev server config with `/api` proxy to backend |
| Modify | `frontend/index.html` | Set `lang="ja"`, title "GovAssist" |
| Modify | `frontend/package.json` | Ensure React 18 pinned, add project metadata |
| Create | `frontend/public/.gitkeep` | Keep empty public dir in git |
| Create | `frontend/src/main.jsx` | React entry point, CSS imports |
| Modify | `frontend/src/App.jsx` | Minimal layout shell for CSS verification |
| Create | `frontend/src/css/base.css` | CSS reset, custom properties, basic typography |
| Create | `frontend/src/css/layout.css` | Header, 200px sidebar, main content layout |
| Create | `frontend/src/css/components.css` | Buttons, inputs, tabs, messages, spinner, diff highlights, modal, tooltip, drop zone, card, badge |
| Create | `frontend/src/components/.gitkeep` | Placeholder for Task 13+ |
| Create | `frontend/src/tools/.gitkeep` | Placeholder for Task 15+ |
| Modify | `.gitignore` | Add `node_modules/`, `dist/` ignores |

### Key Constraints

- **No Tailwind** — plain CSS only (§2.2, CLAUDE.md)
- **No TypeScript** — `.jsx` files only
- **All rendering via React JSX** — never inject raw HTML (§8.2 XSS対策)
- **React 18** — not React 19 (§2.2)
- **Sidebar width**: 200px fixed (§3.1)
- **Diff colors**: delete `#ffcccc`, insert `#ccffcc` (§3.3.4)
- **Backend CORS**: already configured for `http://localhost:5173` in `backend/main.py`

---

## Task 1: Vite project scaffolding

**Files:**
- Create: `frontend/` (full Vite + React 18 project)

- [ ] **Step 1: Create Vite React project**

```bash
cd /home/hart/Code/gov-assist
npm create vite@latest frontend -- --template react
```

Expected: Creates `frontend/` with `package.json`, `vite.config.js`, `index.html`, `src/main.jsx`, `src/App.jsx`, `src/App.css`, `src/index.css`, `src/assets/`, `public/vite.svg`.

- [ ] **Step 2: Install dependencies and pin React 18**

```bash
cd /home/hart/Code/gov-assist/frontend
npm install
npm install react@18 react-dom@18
```

Expected: `package.json` shows `react@^18.x.x` and `react-dom@^18.x.x`.

- [ ] **Step 3: Verify React 18 is installed**

```bash
cd /home/hart/Code/gov-assist/frontend
node -e "console.log(require('./node_modules/react/package.json').version)"
```

Expected: Version starts with `18.` (e.g., `18.3.1`). If it starts with `19.`, run:
```bash
npm install react@18 react-dom@18
```

- [ ] **Step 4: Clean up default template files**

Remove Vite boilerplate that we don't need:

```bash
cd /home/hart/Code/gov-assist/frontend
rm -f src/App.css src/index.css
rm -rf src/assets
rm -f public/vite.svg
touch public/.gitkeep
```

- [ ] **Step 5: Configure `vite.config.js`**

Replace the entire file:

```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

> The proxy forwards all `/api` requests to the FastAPI backend during development, avoiding CORS complexity. The backend CORS config (already in `backend/main.py`) remains as a safety net.

- [ ] **Step 6: Update `index.html`**

Replace the entire file:

```html
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>GovAssist</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

Changes from template: `lang="en"` → `lang="ja"`, removed favicon link, title → "GovAssist".

- [ ] **Step 7: Create placeholder directories**

```bash
cd /home/hart/Code/gov-assist/frontend
mkdir -p src/components src/tools/proofreading src/tools/history src/tools/settings
touch src/components/.gitkeep src/tools/.gitkeep
```

- [ ] **Step 8: Verify dev server starts**

```bash
cd /home/hart/Code/gov-assist/frontend
npm run dev &
sleep 3
curl -s http://localhost:5173 | head -5
kill %1
```

Expected: HTML response containing `<html lang="ja">` and `<title>GovAssist</title>`.

- [ ] **Step 9: Commit**

```bash
cd /home/hart/Code/gov-assist
git add frontend/
git commit -m "feat(frontend): scaffold Vite + React 18 project with dev server proxy"
```

---

## Task 2: Git configuration

**Files:**
- Modify: `.gitignore` (root)

- [ ] **Step 1: Update root `.gitignore`**

Read the current file first, then append frontend ignores:

```bash
cd /home/hart/Code/gov-assist
echo "" >> .gitignore
echo "# Frontend" >> .gitignore
echo "node_modules/" >> .gitignore
echo "dist/" >> .gitignore
```

Verify the file now contains `node_modules/` and `dist/`.

- [ ] **Step 2: Verify `node_modules/` is ignored**

```bash
cd /home/hart/Code/gov-assist
git status --short frontend/
```

Expected: No `node_modules/` files appear. Only tracked files like `frontend/package.json`, `frontend/vite.config.js`, etc.

- [ ] **Step 3: Commit**

```bash
cd /home/hart/Code/gov-assist
git add .gitignore
git commit -m "chore: add node_modules and dist to gitignore"
```

---

## Task 3: base.css — CSS reset & custom properties

**Files:**
- Create: `frontend/src/css/base.css`
- Modify: `frontend/src/main.jsx`

- [ ] **Step 1: Create `base.css`**

```css
/* ============================================
   base.css — CSS Reset & Custom Properties
   ============================================ */

/* --- CSS Reset --- */

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: 16px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family:
    'Hiragino Sans',
    'Hiragino Kaku Gothic ProN',
    'Noto Sans JP',
    'Yu Gothic',
    'Meiryo',
    sans-serif;
  color: var(--color-text);
  background-color: var(--color-bg);
}

img,
svg {
  display: block;
  max-width: 100%;
}

a {
  color: var(--color-primary);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

ul,
ol {
  list-style: none;
}

button {
  font-family: inherit;
  cursor: pointer;
}

input,
textarea,
select {
  font-family: inherit;
}

/* --- CSS Custom Properties --- */

:root {
  /* Text colors */
  --color-text: #333;
  --color-text-secondary: #666;
  --color-text-muted: #999;

  /* Background colors */
  --color-bg: #f5f5f5;
  --color-bg-white: #fff;
  --color-bg-hover: #e8e8e8;
  --color-bg-active: #ddd;

  /* Border */
  --color-border: #ddd;
  --color-border-focus: #4a90d9;

  /* Accent */
  --color-primary: #4a90d9;
  --color-primary-hover: #357abd;
  --color-primary-active: #2a6aad;
  --color-danger: #d94a4a;
  --color-danger-hover: #bd3535;
  --color-warning: #f0ad4e;
  --color-success: #5cb85c;

  /* Diff colors (§3.3.4) */
  --color-diff-delete-bg: #ffcccc;
  --color-diff-insert-bg: #ccffcc;

  /* Layout dimensions (§3.1) */
  --header-height: 48px;
  --sidebar-width: 200px;

  /* Spacing scale */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;

  /* Typography */
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;

  /* Border radius */
  --radius-sm: 3px;
  --radius: 5px;
  --radius-lg: 8px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.08);
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition: 200ms ease;
}
```

- [ ] **Step 2: Update `main.jsx` to import CSS**

Replace the entire file:

```jsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './css/base.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 3: Verify build succeeds**

```bash
cd /home/hart/Code/gov-assist/frontend
npm run build
```

Expected: Build completes with exit code 0, output in `dist/`.

- [ ] **Step 4: Commit**

```bash
cd /home/hart/Code/gov-assist
git add frontend/src/css/base.css frontend/src/main.jsx
git commit -m "feat(frontend): add CSS reset and custom properties (base.css)"
```

---

## Task 4: layout.css — Page layout & minimal App.jsx

**Files:**
- Create: `frontend/src/css/layout.css`
- Modify: `frontend/src/main.jsx` (add import)
- Modify: `frontend/src/App.jsx` (minimal layout shell for verification)

- [ ] **Step 1: Create `layout.css`**

```css
/* ============================================
   layout.css — Header, Sidebar, Main Content
   ============================================ */

/* --- App container (full viewport) --- */

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* --- Header (§3.1) --- */

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--header-height);
  padding: 0 var(--spacing-md);
  background-color: var(--color-bg-white);
  border-bottom: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
  z-index: 100;
}

.app-header__title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
}

.app-header__actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

/* --- Content area (sidebar + main) --- */

.app-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* --- Sidebar (§3.1: 200px fixed) --- */

.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  background-color: var(--color-bg-white);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar__nav {
  flex: 1;
  padding: var(--spacing-sm) 0;
}

.sidebar__footer {
  padding: var(--spacing-sm) 0;
  border-top: 1px solid var(--color-border);
}

.sidebar__item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-base);
  color: var(--color-text);
  cursor: pointer;
  transition: background-color var(--transition-fast);
  user-select: none;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
}

.sidebar__item:hover {
  background-color: var(--color-bg-hover);
}

.sidebar__item--active {
  background-color: var(--color-bg-hover);
  font-weight: 600;
  color: var(--color-primary);
  border-left: 3px solid var(--color-primary);
}

.sidebar__item--disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.6;
}

.sidebar__item--disabled:hover {
  background-color: transparent;
}

.sidebar__item-icon {
  font-size: 1.1em;
  width: 1.5em;
  text-align: center;
  flex-shrink: 0;
}

/* --- Main content area --- */

.main-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
  background-color: var(--color-bg);
}
```

- [ ] **Step 2: Add `layout.css` import to `main.jsx`**

Read the current file first, then add the import after `base.css`:

```jsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './css/base.css';
import './css/layout.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 3: Create minimal `App.jsx` for layout verification**

This is a smoke-test component that verifies the CSS layout renders correctly. It will be replaced with the real implementation in Task 13.

Replace the entire file:

```jsx
function App() {
  return (
    <div className="app">
      <header className="app-header">
        <span className="app-header__title">GovAssist</span>
        <div className="app-header__actions">
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            Task 13 で実装
          </span>
        </div>
      </header>
      <div className="app-content">
        <aside className="sidebar">
          <nav className="sidebar__nav">
            <button className="sidebar__item sidebar__item--active">
              <span className="sidebar__item-icon">📝</span>
              AI 文書校正
            </button>
            <button className="sidebar__item sidebar__item--disabled">
              <span className="sidebar__item-icon">📄</span>
              文書要約・翻訳
            </button>
            <button className="sidebar__item sidebar__item--disabled">
              <span className="sidebar__item-icon">🗂</span>
              PDF 加工
            </button>
            <button className="sidebar__item sidebar__item--disabled">
              <span className="sidebar__item-icon">💬</span>
              AI チャット
            </button>
          </nav>
          <div className="sidebar__footer">
            <button className="sidebar__item">
              <span className="sidebar__item-icon">⚙</span>
              設定
            </button>
          </div>
        </aside>
        <main className="main-content">
          <div className="card">
            <h2 style={{ marginBottom: 'var(--spacing-sm)' }}>GovAssist へようこそ</h2>
            <p style={{ color: 'var(--color-text-secondary)' }}>
              フロントエンドプロジェクトセットアップ完了（Task 12）
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
```

> Note: The `card` class is defined in `components.css` (Task 5). The layout will render correctly without it — `card` just adds background/border/padding.

- [ ] **Step 4: Verify build succeeds**

```bash
cd /home/hart/Code/gov-assist/frontend
npm run build
```

Expected: Build completes with exit code 0.

- [ ] **Step 5: Visual verification**

```bash
cd /home/hart/Code/gov-assist/frontend
npm run dev &
```

Open `http://localhost:5173` in a browser and verify:
- Header at top with "GovAssist" title
- Left sidebar (200px wide) with 4 menu items (first one highlighted, rest disabled)
- "設定" item at sidebar bottom, separated by a border
- Main content area shows welcome message
- Disabled items appear muted with reduced opacity

After verification, stop the dev server:

```bash
kill %1
```

- [ ] **Step 6: Commit**

```bash
cd /home/hart/Code/gov-assist
git add frontend/src/css/layout.css frontend/src/main.jsx frontend/src/App.jsx
git commit -m "feat(frontend): add page layout CSS with 200px sidebar and minimal App shell"
```

---

## Task 5: components.css — Common UI styles

**Files:**
- Create: `frontend/src/css/components.css`
- Modify: `frontend/src/main.jsx` (add import)

- [ ] **Step 1: Create `components.css`**

```css
/* ============================================
   components.css — Common UI Component Styles
   ============================================ */

/* --- Buttons --- */

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-base);
  line-height: 1.5;
  border: 1px solid transparent;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background-color var(--transition-fast),
              border-color var(--transition-fast),
              box-shadow var(--transition-fast);
  user-select: none;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn--primary {
  background-color: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.btn--primary:hover:not(:disabled) {
  background-color: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

.btn--primary:active:not(:disabled) {
  background-color: var(--color-primary-active);
}

.btn--secondary {
  background-color: var(--color-bg-white);
  color: var(--color-text);
  border-color: var(--color-border);
}

.btn--secondary:hover:not(:disabled) {
  background-color: var(--color-bg-hover);
}

.btn--danger {
  background-color: var(--color-danger);
  color: #fff;
  border-color: var(--color-danger);
}

.btn--danger:hover:not(:disabled) {
  background-color: var(--color-danger-hover);
  border-color: var(--color-danger-hover);
}

.btn--sm {
  padding: 2px var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.btn--lg {
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-lg);
}

/* --- Inputs --- */

.input,
.textarea,
.select {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-base);
  line-height: 1.5;
  color: var(--color-text);
  background-color: var(--color-bg-white);
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
  box-shadow: 0 0 0 3px rgba(74, 144, 217, 0.15);
}

.input::placeholder,
.textarea::placeholder {
  color: var(--color-text-muted);
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
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23666'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  background-size: 10px;
  cursor: pointer;
}

/* --- Label --- */

.label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

/* --- Checkbox --- */

.checkbox {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  user-select: none;
  font-size: var(--font-size-base);
}

.checkbox__input {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--color-primary);
}

/* --- Form group --- */

.form-group {
  margin-bottom: var(--spacing-md);
}

.form-row {
  display: flex;
  gap: var(--spacing-md);
  align-items: flex-start;
}

/* --- Tabs (§3.3.4: 3-tab result display) --- */

.tabs {
  display: flex;
  border-bottom: 2px solid var(--color-border);
  margin-bottom: var(--spacing-md);
}

.tab {
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: color var(--transition-fast),
              border-color var(--transition-fast);
}

.tab:hover {
  color: var(--color-text);
}

.tab--active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}

/* --- Messages --- */

.message {
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius);
  font-size: var(--font-size-base);
  line-height: 1.5;
}

.message--warning {
  background-color: #fff3cd;
  color: #856404;
  border: 1px solid #ffc107;
}

.message--error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.message--success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.message--info {
  background-color: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
}

/* --- Spinner --- */

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.spinner--sm {
  width: 14px;
  height: 14px;
  border-width: 2px;
}

.spinner--lg {
  width: 32px;
  height: 32px;
  border-width: 3px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg);
  color: var(--color-text-secondary);
}

/* --- Diff highlights (§3.3.4) --- */

.diff-delete {
  background-color: var(--color-diff-delete-bg);
  text-decoration: line-through;
}

.diff-insert {
  background-color: var(--color-diff-insert-bg);
}

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
  background-color: var(--color-text);
  color: #fff;
  font-size: var(--font-size-sm);
  border-radius: var(--radius-sm);
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--transition-fast);
  z-index: 1000;
}

.tooltip:hover::after {
  opacity: 1;
}

/* --- Modal (§8.2: localhost warning) --- */

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background-color: var(--color-bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: var(--spacing-lg);
  max-width: 480px;
  width: 90%;
}

.modal__title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  margin-bottom: var(--spacing-md);
}

.modal__body {
  margin-bottom: var(--spacing-lg);
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
}

/* --- Drop zone (§3.3.1: drag and drop) --- */

.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius);
  padding: var(--spacing-lg);
  text-align: center;
  color: var(--color-text-muted);
  transition: border-color var(--transition-fast),
              background-color var(--transition-fast);
  cursor: pointer;
}

.drop-zone:hover,
.drop-zone--active {
  border-color: var(--color-primary);
  background-color: rgba(74, 144, 217, 0.05);
}

.drop-zone__text {
  font-size: var(--font-size-base);
}

.drop-zone__hint {
  font-size: var(--font-size-sm);
  margin-top: var(--spacing-xs);
}

/* --- Card --- */

.card {
  background-color: var(--color-bg-white);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--spacing-md);
}

/* --- Badge (§7.1: truncated warning) --- */

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--spacing-sm);
  font-size: var(--font-size-sm);
  border-radius: var(--radius-sm);
  background-color: var(--color-warning);
  color: var(--color-text);
}

.badge--warning {
  background-color: #fff3cd;
  color: #856404;
}

.badge--info {
  background-color: #d1ecf1;
  color: #0c5460;
}

/* --- Utility: text alignment --- */

.text-center {
  text-align: center;
}

.text-right {
  text-align: right;
}

/* --- Utility: spacing --- */

.mt-sm { margin-top: var(--spacing-sm); }
.mt-md { margin-top: var(--spacing-md); }
.mt-lg { margin-top: var(--spacing-lg); }
.mb-sm { margin-bottom: var(--spacing-sm); }
.mb-md { margin-bottom: var(--spacing-md); }
.mb-lg { margin-bottom: var(--spacing-lg); }
.gap-sm { gap: var(--spacing-sm); }
.gap-md { gap: var(--spacing-md); }

/* --- Utility: flex --- */

.flex { display: flex; }
.flex-col { flex-direction: column; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.justify-end { justify-content: flex-end; }
.flex-1 { flex: 1; }

/* --- Utility: accessibility --- */

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

- [ ] **Step 2: Add `components.css` import to `main.jsx`**

Read the current file first, then add the import:

```jsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './css/base.css';
import './css/layout.css';
import './css/components.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 3: Verify build succeeds**

```bash
cd /home/hart/Code/gov-assist/frontend
npm run build
```

Expected: Build completes with exit code 0.

- [ ] **Step 4: Commit**

```bash
cd /home/hart/Code/gov-assist
git add frontend/src/css/components.css frontend/src/main.jsx
git commit -m "feat(frontend): add common UI component styles (buttons, inputs, tabs, messages, diff, modal, etc.)"
```

---

## Task 6: Final verification

- [ ] **Step 1: Full build verification**

```bash
cd /home/hart/Code/gov-assist/frontend
npm run build
ls dist/
```

Expected: `dist/` contains `index.html`, `assets/` directory with JS and CSS bundles. Exit code 0.

- [ ] **Step 2: Verify production build output is clean**

```bash
cd /home/hart/Code/gov-assist/frontend
npm run build 2>&1 | grep -i "warning\|error" || echo "No warnings or errors"
```

Expected: No warnings or errors (or only Vite's standard informational messages).

- [ ] **Step 3: Verify file structure matches design spec section 11**

```bash
cd /home/hart/Code/gov-assist/frontend
find src -type f | sort
```

Expected output includes:
```
src/App.jsx
src/css/base.css
src/css/components.css
src/css/layout.css
src/main.jsx
src/components/.gitkeep
src/tools/.gitkeep
```

Plus placeholder directories under `tools/`:
```
src/tools/proofreading/.gitkeep (may not exist as file)
src/tools/history/.gitkeep (may not exist as file)
src/tools/settings/.gitkeep (may not exist as file)
```

- [ ] **Step 4: Visual verification (final)**

```bash
cd /home/hart/Code/gov-assist/frontend
npm run dev &
```

Open `http://localhost:5173` and verify all three CSS files are applied:
- **base.css**: Font is sans-serif, text color is `#333`, background is `#f5f5f5`
- **layout.css**: Header at top, 200px sidebar on left, main content fills remaining space
- **components.css**: The welcome message renders inside a `.card` with white background, border, and padding

After verification:

```bash
kill %1
```

- [ ] **Step 5: Final commit (if any cleanup needed)**

```bash
cd /home/hart/Code/gov-assist
git status
# If any uncommitted changes:
git add -A
git commit -m "chore(frontend): final cleanup for Task 12 project setup"
```

---

## Summary of commits

| # | Message |
|---|---------|
| 1 | `feat(frontend): scaffold Vite + React 18 project with dev server proxy` |
| 2 | `chore: add node_modules and dist to gitignore` |
| 3 | `feat(frontend): add CSS reset and custom properties (base.css)` |
| 4 | `feat(frontend): add page layout CSS with 200px sidebar and minimal App shell` |
| 5 | `feat(frontend): add common UI component styles (buttons, inputs, tabs, messages, diff, modal, etc.)` |
| 6 | `chore(frontend): final cleanup for Task 12 project setup` (if needed) |

## Next steps

After Task 12 is complete, the following tasks become available:
- **Task 13**: App Shell (Layout + Routing) — will replace the minimal `App.jsx` with real components
- **Task 14**: API Client and Auth Flow — will add `fetch` wrapper and auth components
