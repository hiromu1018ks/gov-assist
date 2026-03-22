import { describe, it, expect, vi, beforeEach } from 'vitest';
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

function renderApp(initialEntries = '/') {
  return render(<MemoryRouter initialEntries={[initialEntries]}><App /></MemoryRouter>);
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
    const sidebar = document.querySelector('.sidebar');
    expect(within(sidebar).getByText('AI 文書校正')).toBeInTheDocument();
    expect(within(sidebar).getByText('設定')).toBeInTheDocument();
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
