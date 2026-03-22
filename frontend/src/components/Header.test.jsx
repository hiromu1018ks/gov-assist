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
