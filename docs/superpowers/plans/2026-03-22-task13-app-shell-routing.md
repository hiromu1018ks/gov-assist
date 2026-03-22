# Task 13: App Shell (Layout + Routing) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder App.jsx with a proper App Shell featuring React Router routing, SideMenu navigation, and Header with model selector.

**Architecture:** Single-page application with `BrowserRouter` wrapping the App. Sidebar uses `<button>` + `useNavigate`/`useLocation` for navigation (preserving existing CSS button styles). Header displays app title and model selector dropdown that fetches from `/api/models` with graceful fallback when auth is not configured (Task 14). Tool pages are placeholder components replaced in later tasks (15-19, 21). Model selection persisted to localStorage via a shared storage utility with schema versioning (`version: 1`).

**Tech Stack:** React 18, react-router-dom v6, Vitest, React Testing Library

**Design Spec References:** §2.3 (Architecture), §3.1 (Layout), §3.2 (Side Menu), §3.4 (Settings/localStorage), §4.2 (Model Config Table), §5.1 (GET /api/models), §11 (Directory Structure)

---

## Architecture Decisions

1. **Routing**: react-router-dom v6 with `<button>` + `useNavigate`/`useLocation` (not `<NavLink>`) — existing `.sidebar__item` CSS uses button-specific resets (`border: none; background: none;`) that wouldn't apply to `<a>` elements
2. **Model selector**: Direct `fetch('/api/models')` with graceful error fallback — no API client wrapper (that's Task 14); defaults to "Kimi K2.5" when auth/network fails
3. **State**: localStorage for model selection only (no React Context yet — introduced when needed in later tasks)
4. **Testing**: Vitest + React Testing Library with colocated test files (`Component.test.jsx` next to `Component.jsx`)
5. **Disabled sidebar items**: Phase 2/3 items rendered with `disabled` attribute, no route defined — unknown routes redirect to `/`
6. **Select width override**: `.select` has `width: 100%` from components.css — header select uses inline `width: auto` since it shares the class with form selects

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `frontend/vite.config.js` | Add Vitest `test` config (jsdom environment) |
| Create | `frontend/src/test/setup.js` | Test setup (`@testing-library/jest-dom`, cleanup) |
| Create | `frontend/src/utils/storage.js` | localStorage access with schema versioning |
| Create | `frontend/src/utils/storage.test.js` | Storage utility tests |
| Create | `frontend/src/components/SideMenu.jsx` | Sidebar navigation with tool items |
| Create | `frontend/src/components/SideMenu.test.jsx` | SideMenu tests |
| Create | `frontend/src/components/Header.jsx` | Header bar with model selector + settings button |
| Create | `frontend/src/components/Header.test.jsx` | Header tests |
| Create | `frontend/src/tools/proofreading/Proofreading.jsx` | Placeholder proofreading tool |
| Create | `frontend/src/tools/settings/Settings.jsx` | Placeholder settings page |
| Create | `frontend/src/App.test.jsx` | App Shell integration tests |
| Modify | `frontend/src/App.jsx` | Rewrite: App Shell with routing |
| Modify | `frontend/src/main.jsx` | Wrap with `BrowserRouter` |
| Modify | `frontend/package.json` | Add dependencies + test script |

## Prerequisites

- Task 12 complete (Vite + React 18 project, CSS files, placeholder App.jsx)
- Backend running on `localhost:8000` with `GET /api/models` endpoint (Tasks 1-8 complete)

---

### Task 1: Install Dependencies & Configure Vitest

- [ ] **Step 1: Install runtime dependency**

Run: `cd frontend && npm install react-router-dom@6`
Expected: `react-router-dom@6.x.x` added to `dependencies` in package.json

- [ ] **Step 2: Install dev dependencies**

Run: `cd frontend && npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom`
Expected: All packages added to `devDependencies`

- [ ] **Step 3: Add test script to package.json**

Add to `scripts` in `frontend/package.json`:

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 4: Configure Vitest in vite.config.js**

Replace contents of `frontend/vite.config.js` with:

```js
import { defineConfig } from 'vitest/config';
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
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    globals: true,
  },
});
```

> `defineConfig` from `vitest/config` is a superset of vite's `defineConfig` — adds `test` property support. The `server` config is preserved so `npm run dev` still works.

- [ ] **Step 5: Create test setup file**

Create `frontend/src/test/setup.js`:

```js
import '@testing-library/jest-dom/vitest';
```

> `@testing-library/jest-dom/vitest` auto-imports custom matchers (`toBeInTheDocument`, `toBeDisabled`, `toHaveClass`, etc.) into vitest's `expect`. No manual `afterEach(cleanup)` needed — React Testing Library v14+ auto-cleans up in vitest/jsdom.

- [ ] **Step 6: Verify Vitest runs**

Run: `cd frontend && npx vitest run --no-files`
Expected: "No test files found" (confirms vitest config loads without errors)

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.js frontend/src/test/setup.js
git commit -m "feat(frontend): add Vitest, React Testing Library, and react-router-dom v6"
```

---

### Task 2: Storage Utility (TDD)

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/utils/storage.test.js`:

```js
import { describe, it, expect, beforeEach } from 'vitest';
import { loadSettings, saveSettings } from './storage';

beforeEach(() => {
  localStorage.clear();
});

describe('loadSettings', () => {
  it('returns defaults when nothing is stored', () => {
    const settings = loadSettings();
    expect(settings.version).toBe(1);
    expect(settings.model).toBe('kimi-k2.5');
    expect(settings.document_type).toBe('official');
    expect(settings.options.typo).toBe(true);
    expect(settings.options.legal).toBe(false);
  });

  it('returns stored settings when version matches', () => {
    const stored = {
      version: 1,
      model: 'test-model',
      document_type: 'email',
      options: { typo: false, keigo: true, terminology: true, style: true, legal: true, readability: false },
    };
    localStorage.setItem('govassist_settings', JSON.stringify(stored));
    const settings = loadSettings();
    expect(settings.model).toBe('test-model');
    expect(settings.document_type).toBe('email');
    expect(settings.options.typo).toBe(false);
    expect(settings.options.legal).toBe(true);
  });

  it('returns defaults when localStorage has corrupted data', () => {
    localStorage.setItem('govassist_settings', 'not-json{{{');
    const settings = loadSettings();
    expect(settings.model).toBe('kimi-k2.5');
    expect(settings.version).toBe(1);
  });

  it('migrates settings from older version (keeps known fields)', () => {
    const old = { version: 0, model: 'old-model', document_type: 'report' };
    localStorage.setItem('govassist_settings', JSON.stringify(old));
    const settings = loadSettings();
    expect(settings.version).toBe(1);
    expect(settings.model).toBe('old-model');
    expect(settings.document_type).toBe('report');
    // New fields get defaults
    expect(settings.options).toBeDefined();
    expect(settings.options.typo).toBe(true);
  });

  it('handles missing options field gracefully', () => {
    const partial = { version: 1, model: 'test' };
    localStorage.setItem('govassist_settings', JSON.stringify(partial));
    const settings = loadSettings();
    expect(settings.model).toBe('test');
    expect(settings.options.typo).toBe(true);
  });
});

describe('saveSettings', () => {
  it('saves settings with version to localStorage', () => {
    saveSettings({ model: 'new-model', document_type: 'email', options: {} });
    const raw = localStorage.getItem('govassist_settings');
    const parsed = JSON.parse(raw);
    expect(parsed.version).toBe(1);
    expect(parsed.model).toBe('new-model');
  });

  it('overwrites existing settings', () => {
    saveSettings({ model: 'first', document_type: 'official', options: {} });
    saveSettings({ model: 'second', document_type: 'email', options: {} });
    const settings = loadSettings();
    expect(settings.model).toBe('second');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/utils/storage.test.js`
Expected: FAIL — `Cannot find module './storage'`

- [ ] **Step 3: Write the implementation**

Create `frontend/src/utils/storage.js`:

```js
const STORAGE_KEY = 'govassist_settings';
const CURRENT_VERSION = 1;

const DEFAULTS = {
  version: CURRENT_VERSION,
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
};

export function loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULTS };

    const stored = JSON.parse(raw);

    return {
      ...DEFAULTS,
      ...stored,
      version: CURRENT_VERSION,
      options: {
        ...DEFAULTS.options,
        ...(stored.options || {}),
      },
    };
  } catch {
    return { ...DEFAULTS };
  }
}

export function saveSettings(settings) {
  const toSave = { ...settings, version: CURRENT_VERSION };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/utils/storage.test.js`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/storage.js frontend/src/utils/storage.test.js
git commit -m "feat(frontend): add localStorage storage utility with schema versioning"
```

---

### Task 3: SideMenu Component (TDD)

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/SideMenu.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import SideMenu from './SideMenu';

function renderWithRouter(ui, { initialEntries = ['/'] } = {}) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      {ui}
    </MemoryRouter>
  );
}

describe('SideMenu', () => {
  it('renders all menu items', () => {
    renderWithRouter(<SideMenu />);
    expect(screen.getByText('AI 文書校正')).toBeInTheDocument();
    expect(screen.getByText('文書要約・翻訳')).toBeInTheDocument();
    expect(screen.getByText('PDF 加工')).toBeInTheDocument();
    expect(screen.getByText('AI チャット')).toBeInTheDocument();
    expect(screen.getByText('設定')).toBeInTheDocument();
  });

  it('disables Phase 2/3 items', () => {
    renderWithRouter(<SideMenu />);
    expect(screen.getByText('文書要約・翻訳')).toBeDisabled();
    expect(screen.getByText('PDF 加工')).toBeDisabled();
    expect(screen.getByText('AI チャット')).toBeDisabled();
  });

  it('does not disable MVP items', () => {
    renderWithRouter(<SideMenu />);
    expect(screen.getByText('AI 文書校正')).not.toBeDisabled();
    expect(screen.getByText('設定')).not.toBeDisabled();
  });

  it('marks proofreading as active on / route', () => {
    renderWithRouter(<SideMenu />, { initialEntries: ['/'] });
    const btn = screen.getByText('AI 文書校正').closest('button');
    expect(btn).toHaveClass('sidebar__item--active');
  });

  it('marks settings as active on /settings route', () => {
    renderWithRouter(<SideMenu />, { initialEntries: ['/settings'] });
    const btn = screen.getByText('設定').closest('button');
    expect(btn).toHaveClass('sidebar__item--active');
  });

  it('does not mark proofreading as active on /settings', () => {
    renderWithRouter(<SideMenu />, { initialEntries: ['/settings'] });
    const btn = screen.getByText('AI 文書校正').closest('button');
    expect(btn).not.toHaveClass('sidebar__item--active');
  });

  it('navigates to settings on click', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SideMenu />);
    await user.click(screen.getByText('設定'));
    const btn = screen.getByText('設定').closest('button');
    expect(btn).toHaveClass('sidebar__item--active');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/SideMenu.test.jsx`
Expected: FAIL — `Cannot find module './SideMenu'`

- [ ] **Step 3: Write the implementation**

Create `frontend/src/components/SideMenu.jsx`:

```jsx
import { useNavigate, useLocation } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/', label: 'AI 文書校正', icon: '📝' },
  { path: null, label: '文書要約・翻訳', icon: '📄' },
  { path: null, label: 'PDF 加工', icon: '🗂' },
  { path: null, label: 'AI チャット', icon: '💬' },
];

const FOOTER_ITEMS = [
  { path: '/settings', label: '設定', icon: '⚙' },
];

function MenuItem({ path, label, icon, isActive }) {
  const navigate = useNavigate();
  const disabled = !path;

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
      <span className="sidebar__item-icon">{icon}</span>
      {label}
    </button>
  );
}

function SideMenu() {
  const location = useLocation();

  return (
    <aside className="sidebar">
      <nav className="sidebar__nav">
        {NAV_ITEMS.map(item => (
          <MenuItem
            key={item.label}
            path={item.path}
            label={item.label}
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/SideMenu.test.jsx`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SideMenu.jsx frontend/src/components/SideMenu.test.jsx
git commit -m "feat(frontend): add SideMenu component with routing and disabled states"
```

---

### Task 4: Header Component (TDD)

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/Header.test.jsx`:

```jsx
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Header from './Header';

// Mock the storage utility to isolate Header from localStorage
vi.mock('../utils/storage', () => ({
  loadSettings: vi.fn(() => ({ version: 1, model: 'kimi-k2.5', document_type: 'official', options: {} })),
  saveSettings: vi.fn(),
}));

import { loadSettings, saveSettings } from '../utils/storage';

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('Header', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.mocked(loadSettings).mockReturnValue({ version: 1, model: 'kimi-k2.5', document_type: 'official', options: {} });
  });

  it('renders app title', () => {
    renderWithRouter(<Header />);
    expect(screen.getByText('GovAssist')).toBeInTheDocument();
  });

  it('renders model selector with accessible label', () => {
    renderWithRouter(<Header />);
    expect(screen.getByLabelText('AI モデル')).toBeInTheDocument();
  });

  it('renders settings button', () => {
    renderWithRouter(<Header />);
    expect(screen.getByLabelText('設定を開く')).toBeInTheDocument();
  });

  it('shows default model when fetch fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'));
    renderWithRouter(<Header />);

    await waitFor(() => {
      expect(screen.getByText('Kimi K2.5')).toBeInTheDocument();
    });
  });

  it('shows default model when API returns 401', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status: 401 });
    renderWithRouter(<Header />);

    await waitFor(() => {
      expect(screen.getByText('Kimi K2.5')).toBeInTheDocument();
    });
  });

  it('fetches and displays models from API', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        models: [
          { model_id: 'kimi-k2.5', display_name: 'Kimi K2.5' },
          { model_id: 'gpt-4', display_name: 'GPT-4' },
        ],
      }),
    });
    renderWithRouter(<Header />);

    await waitFor(() => {
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
    });
    expect(screen.getByText('Kimi K2.5')).toBeInTheDocument();
  });

  it('saves selected model to storage on change', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        models: [
          { model_id: 'kimi-k2.5', display_name: 'Kimi K2.5' },
          { model_id: 'gpt-4', display_name: 'GPT-4' },
        ],
      }),
    });

    const user = userEvent.setup();
    renderWithRouter(<Header />);

    await waitFor(() => {
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText('AI モデル'), 'gpt-4');

    expect(saveSettings).toHaveBeenCalled();
  });

  it('navigates to /settings when settings button clicked', async () => {
    const user = userEvent.setup();
    renderWithRouter(<Header />);

    await user.click(screen.getByLabelText('設定を開く'));

    // After navigation, the settings button should still be present
    expect(screen.getByLabelText('設定を開く')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/Header.test.jsx`
Expected: FAIL — `Cannot find module './Header'`

- [ ] **Step 3: Write the implementation**

Create `frontend/src/components/Header.jsx`:

```jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSettings, saveSettings } from '../utils/storage';

const DEFAULT_MODEL = { model_id: 'kimi-k2.5', display_name: 'Kimi K2.5' };

function Header() {
  const navigate = useNavigate();
  const [models, setModels] = useState([DEFAULT_MODEL]);
  const [selectedModel, setSelectedModel] = useState(() => loadSettings().model);

  useEffect(() => {
    fetch('/api/models')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
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
      .catch(() => {
        // Auth not configured (Task 14) or network error — use default
      });
  }, []);

  const handleModelChange = (e) => {
    const newModel = e.target.value;
    setSelectedModel(newModel);
    saveSettings({ ...loadSettings(), model: newModel });
  };

  return (
    <header className="app-header">
      <span className="app-header__title">GovAssist</span>
      <div className="app-header__actions">
        <label className="sr-only" htmlFor="model-selector">AI モデル</label>
        <select
          id="model-selector"
          className="select"
          value={selectedModel}
          onChange={handleModelChange}
          style={{ width: 'auto' }}
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
    </header>
  );
}

export default Header;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/Header.test.jsx`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Header.jsx frontend/src/components/Header.test.jsx
git commit -m "feat(frontend): add Header component with model selector and settings button"
```

---

### Task 5: App Shell with Routing (TDD)

- [ ] **Step 1: Create placeholder tool pages**

Create `frontend/src/tools/proofreading/Proofreading.jsx`:

```jsx
function Proofreading() {
  return (
    <div className="card">
      <h2>AI 文書校正</h2>
      <p className="mt-sm" style={{ color: 'var(--color-text-secondary)' }}>
        このツールは Task 15〜19 で実装されます。
      </p>
    </div>
  );
}

export default Proofreading;
```

Create `frontend/src/tools/settings/Settings.jsx`:

```jsx
function Settings() {
  return (
    <div className="card">
      <h2>設定</h2>
      <p className="mt-sm" style={{ color: 'var(--color-text-secondary)' }}>
        設定画面は Task 21 で実装されます。
      </p>
    </div>
  );
}

export default Settings;
```

- [ ] **Step 2: Write the failing App tests**

Create `frontend/src/App.test.jsx`:

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

// Mock storage utility
vi.mock('./utils/storage', () => ({
  loadSettings: vi.fn(() => ({ version: 1, model: 'kimi-k2.5', document_type: 'official', options: {} })),
  saveSettings: vi.fn(),
}));

// Mock fetch for Header model selector
beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('No API in tests'));
});

function renderApp(initialEntries = ['/']) {
  return render(<MemoryRouter initialEntries={initialEntries}><App /></MemoryRouter>);
}

describe('App', () => {
  it('renders the app layout structure', () => {
    renderApp();
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('renders header with app title', () => {
    renderApp();
    expect(screen.getByText('GovAssist')).toBeInTheDocument();
  });

  it('renders sidebar with all menu items', () => {
    renderApp();
    expect(screen.getByText('AI 文書校正')).toBeInTheDocument();
    expect(screen.getByText('設定')).toBeInTheDocument();
  });

  it('renders proofreading placeholder on default route /', () => {
    renderApp('/');
    const main = screen.getByRole('main');
    expect(within(main).getByText('AI 文書校正')).toBeInTheDocument();
    expect(within(main).getByText(/Task 15/)).toBeInTheDocument();
  });

  it('renders settings placeholder on /settings route', () => {
    renderApp('/settings');
    const main = screen.getByRole('main');
    expect(within(main).getByText('設定')).toBeInTheDocument();
    expect(within(main).getByText(/Task 21/)).toBeInTheDocument();
  });

  it('redirects unknown routes to /', () => {
    renderApp('/unknown-page');
    const main = screen.getByRole('main');
    expect(within(main).getByText(/Task 15/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/App.test.jsx`
Expected: FAIL — App still renders old placeholder, tests for `<main>` role and route content fail

- [ ] **Step 4: Rewrite App.jsx**

Replace contents of `frontend/src/App.jsx` with:

```jsx
import { Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import SideMenu from './components/SideMenu';
import Proofreading from './tools/proofreading/Proofreading';
import Settings from './tools/settings/Settings';

function App() {
  return (
    <div className="app">
      <Header />
      <div className="app-content">
        <SideMenu />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Proofreading />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
```

- [ ] **Step 5: Update main.jsx with BrowserRouter**

Replace contents of `frontend/src/main.jsx` with:

```jsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './css/base.css';
import './css/layout.css';
import './css/components.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/App.test.jsx`
Expected: All 6 tests PASS

- [ ] **Step 7: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS (storage: 7, SideMenu: 7, Header: 8, App: 6 = 22 total)

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.jsx frontend/src/App.test.jsx frontend/src/main.jsx \
       frontend/src/tools/proofreading/Proofreading.jsx frontend/src/tools/settings/Settings.jsx
git commit -m "feat(frontend): add App Shell with React Router, sidebar navigation, and placeholder pages"
```

---

### Task 6: Manual Verification

- [ ] **Step 1: Start dev server**

Run: `cd frontend && npm run dev`
Expected: Vite dev server starts on `http://localhost:5173`

- [ ] **Step 2: Verify layout renders**

Open `http://localhost:5173` in browser. Verify:
- Header shows "GovAssist" title + model selector dropdown + settings gear button
- Left sidebar (200px) shows 4 nav items (first active, rest disabled) + Settings in footer
- Main content shows "AI 文書校正" card with placeholder text

- [ ] **Step 3: Verify sidebar navigation**

- Click "設定" in sidebar footer → main content changes to Settings placeholder
- Click "AI 文書校正" in sidebar → main content changes back to Proofreading placeholder
- Active state (blue left border + bold) follows the clicked item
- Disabled items (文書要約・翻訳, PDF 加工, AI チャット) are grayed out and non-clickable

- [ ] **Step 4: Verify header settings button**

- Click ⚙ button in header → navigates to /settings (same as sidebar settings)

- [ ] **Step 5: Verify model selector**

- Dropdown shows "Kimi K2.5" (default — API call fails without auth token)
- Selecting a model updates localStorage (check DevTools → Application → Local Storage → `govassist_settings`)

- [ ] **Step 6: Verify direct URL navigation**

- Type `http://localhost:5173/settings` directly → Settings page loads
- Type `http://localhost:5173/unknown` → redirects to `/` (Proofreading)

- [ ] **Step 7: Verify browser back/forward**

- Navigate to Settings, click browser back → returns to Proofreading
- Click browser forward → returns to Settings

- [ ] **Step 8: Verify production build**

Run: `cd frontend && npm run build`
Expected: Build succeeds without errors

---

## Summary of Changes

| File | Action | Lines (approx) |
|------|--------|----------------|
| `vite.config.js` | Modify | +8 (vitest test config) |
| `src/test/setup.js` | Create | 1 |
| `src/utils/storage.js` | Create | 30 |
| `src/utils/storage.test.js` | Create | 65 |
| `src/components/SideMenu.jsx` | Create | 50 |
| `src/components/SideMenu.test.jsx` | Create | 55 |
| `src/components/Header.jsx` | Create | 55 |
| `src/components/Header.test.jsx` | Create | 90 |
| `src/tools/proofreading/Proofreading.jsx` | Create | 10 |
| `src/tools/settings/Settings.jsx` | Create | 10 |
| `src/App.jsx` | Rewrite | 25 |
| `src/App.test.jsx` | Create | 50 |
| `src/main.jsx` | Modify | +2 (BrowserRouter) |
| `package.json` | Modify | +5 (deps + scripts) |

**Total: 22 tests across 4 test files**

**Commits (6):**
1. `feat(frontend): add Vitest, React Testing Library, and react-router-dom v6`
2. `feat(frontend): add localStorage storage utility with schema versioning`
3. `feat(frontend): add SideMenu component with routing and disabled states`
4. `feat(frontend): add Header component with model selector and settings button`
5. `feat(frontend): add App Shell with React Router, sidebar navigation, and placeholder pages`
