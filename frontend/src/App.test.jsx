// src/App.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock useAuth — App is always rendered as authenticated in these layout tests
vi.mock('./context/AuthContext', () => ({
  useAuth: vi.fn(() => ({ isAuthenticated: true, isLoading: false, login: vi.fn(), logout: vi.fn() })),
}));

// Mock storage utility
vi.mock('./utils/storage', () => ({
  loadSettings: vi.fn(() => ({ version: 1, model: 'kimi-k2.5', document_type: 'official', options: {} })),
  saveSettings: vi.fn(),
}));

// Mock API client to prevent real fetch calls from Header
vi.mock('./api/client', () => ({
  apiGet: vi.fn(() => Promise.resolve({ models: [] })),
}));

// Mock fileExtractor (used by InputArea)
vi.mock('./tools/proofreading/fileExtractor', () => ({
  extractText: vi.fn(),
}));

import App from './App';

beforeEach(() => {
  vi.restoreAllMocks();
});

function renderApp(initialEntries = '/') {
  return render(<MemoryRouter initialEntries={[initialEntries]}><App /></MemoryRouter>);
}

describe('App', () => {
  it('renders the app layout structure when authenticated', () => {
    renderApp();
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('renders header with app title', () => {
    renderApp();
    expect(screen.getByText('GOV_ASSIST')).toBeInTheDocument();
  });

  it('renders sidebar with all menu items', () => {
    renderApp();
    const sidebar = document.querySelector('.sidebar');
    expect(within(sidebar).getByText('校正ツール')).toBeInTheDocument();
    expect(within(sidebar).getByText('設定')).toBeInTheDocument();
  });

  it('renders proofreading tool on default route /', () => {
    renderApp('/');
    const main = screen.getByRole('main');
    expect(within(main).getByText('AI 文書校正')).toBeInTheDocument();
    expect(within(main).getByText(/外部 AI サービス/)).toBeInTheDocument();
  });

  it('renders settings placeholder on /settings route', () => {
    renderApp('/settings');
    const main = screen.getByRole('main');
    expect(within(main).getByText('設定')).toBeInTheDocument();
    expect(within(main).getByText('AI モデル')).toBeInTheDocument();
  });

  it('redirects unknown routes to /', () => {
    renderApp('/unknown-page');
    const main = screen.getByRole('main');
    expect(within(main).getByText(/外部 AI サービス/)).toBeInTheDocument();
  });
});
