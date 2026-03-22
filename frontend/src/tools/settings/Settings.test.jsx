import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// --- Mocks ---

vi.mock('../../api/client', () => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(),
}));

vi.mock('../../utils/storage', () => ({
  loadSettings: vi.fn(() => ({
    version: 1,
    model: 'kimi-k2.5',
    document_type: 'official',
    options: {
      typo: true, keigo: true, terminology: true,
      style: true, legal: false, readability: true,
    },
  })),
  saveSettings: vi.fn(),
}));

import { apiGet, apiPut } from '../../api/client';
import { loadSettings, saveSettings } from '../../utils/storage';
import Settings from './Settings';

const mockApiGet = vi.mocked(apiGet);
const mockApiPut = vi.mocked(apiPut);
const mockLoadSettings = vi.mocked(loadSettings);
const mockSaveSettings = vi.mocked(saveSettings);

const MODELS_RESPONSE = {
  models: [
    { model_id: 'kimi-k2.5', display_name: 'Kimi K2.5', max_tokens: 4096, temperature: 0.3, max_input_chars: 8000, json_forced: true },
    { model_id: 'gpt-4o', display_name: 'GPT-4o', max_tokens: 4096, temperature: 0.3, max_input_chars: 8000, json_forced: true },
  ],
};

const SETTINGS_RESPONSE = { history_limit: 50 };

function setup() {
  mockApiGet.mockImplementation((path) => {
    if (path === '/api/models') return Promise.resolve(MODELS_RESPONSE);
    if (path === '/api/settings') return Promise.resolve(SETTINGS_RESPONSE);
    return Promise.reject(new Error(`Unexpected path: ${path}`));
  });
  mockApiPut.mockResolvedValue(SETTINGS_RESPONSE);
  render(<Settings />);
}

describe('Settings', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockApiGet.mockReset();
    mockApiPut.mockReset();
    mockLoadSettings.mockReset();
    mockSaveSettings.mockReset();
    // Default mock return for loadSettings
    mockLoadSettings.mockReturnValue({
      version: 1,
      model: 'kimi-k2.5',
      document_type: 'official',
      options: {
        typo: true, keigo: true, terminology: true,
        style: true, legal: false, readability: true,
      },
    });
  });

  // --- Initial render ---

  it('renders page title', async () => {
    setup();
    expect(screen.getByText('設定')).toBeInTheDocument();
  });

  it('fetches models and settings on mount', async () => {
    setup();
    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith('/api/models');
      expect(mockApiGet).toHaveBeenCalledWith('/api/settings');
    });
  });

  // --- Model selection section ---

  it('renders model selection section with loaded models', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByText('Kimi K2.5')).toBeInTheDocument();
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });
  });

  it('shows currently selected model from localStorage', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByDisplayValue('Kimi K2.5')).toBeInTheDocument();
    });
  });

  it('saves model change to localStorage on select', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    await userEvent.selectOptions(screen.getByLabelText('AI モデル'), 'gpt-4o');

    await waitFor(() => {
      expect(mockSaveSettings).toHaveBeenCalledWith(
        expect.objectContaining({ model: 'gpt-4o' })
      );
    });
  });

  it('falls back to first model when stored model is not available', async () => {
    mockLoadSettings.mockReturnValue({
      version: 1, model: 'nonexistent-model', document_type: 'official',
      options: { typo: true, keigo: true, terminology: true, style: true, legal: false, readability: true },
    });
    setup();
    await waitFor(() => {
      expect(screen.getByDisplayValue('Kimi K2.5')).toBeInTheDocument();
      expect(mockSaveSettings).toHaveBeenCalledWith(
        expect.objectContaining({ model: 'kimi-k2.5' })
      );
    });
  });

  // --- Document type section ---

  it('renders document type selector with current value from localStorage', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByDisplayValue('公文書')).toBeInTheDocument();
    });
  });

  it('saves document type change to localStorage', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByLabelText('デフォルト文書種別')).toBeInTheDocument();
    });

    await userEvent.selectOptions(screen.getByLabelText('デフォルト文書種別'), 'email');

    await waitFor(() => {
      expect(mockSaveSettings).toHaveBeenCalledWith(
        expect.objectContaining({ document_type: 'email' })
      );
    });
  });

  // --- Proofreading options section ---

  it('renders all 6 proofreading option checkboxes', async () => {
    setup();
    expect(screen.getByLabelText('誤字・脱字・変換ミスの検出')).toBeInTheDocument();
    expect(screen.getByLabelText('敬語・丁寧語の適切さチェック')).toBeInTheDocument();
    expect(screen.getByLabelText(/公文書用語・表現への統一/)).toBeInTheDocument();
    expect(screen.getByLabelText(/文体の統一/)).toBeInTheDocument();
    expect(screen.getByLabelText('法令・条例用語の確認')).toBeInTheDocument();
    expect(screen.getByLabelText('文章の読みやすさ・論理構成の改善提案')).toBeInTheDocument();
  });

  it('reflects current option values from localStorage', async () => {
    setup();
    expect(screen.getByLabelText('誤字・脱字・変換ミスの検出')).toBeChecked();
    expect(screen.getByLabelText('法令・条例用語の確認')).not.toBeChecked();
  });

  it('saves option change to localStorage on toggle', async () => {
    setup();
    await userEvent.click(screen.getByLabelText('法令・条例用語の確認'));

    await waitFor(() => {
      expect(mockSaveSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          options: expect.objectContaining({ legal: true }),
        })
      );
    });
  });

  // --- History limit section (server setting) ---

  it('renders history limit input with server value', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByLabelText('履歴保存件数上限')).toHaveValue(50);
    });
  });

  it('sends PUT /api/settings when save button is clicked', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByLabelText('履歴保存件数上限')).toBeInTheDocument();
    });

    const input = screen.getByLabelText('履歴保存件数上限');
    await userEvent.clear(input);
    await userEvent.type(input, '100');
    await userEvent.click(screen.getByRole('button', { name: 'サーバー設定を保存' }));

    await waitFor(() => {
      expect(mockApiPut).toHaveBeenCalledWith('/api/settings', { history_limit: 100 });
    });
  });

  it('shows success message after saving server settings', async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByLabelText('履歴保存件数上限')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: 'サーバー設定を保存' }));

    await waitFor(() => {
      expect(screen.getByText('サーバー設定を保存しました。')).toBeInTheDocument();
    });
  });

  it('shows error message when server settings save fails', async () => {
    setup();
    mockApiPut.mockRejectedValue(new Error('サーバーエラー'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'サーバー設定を保存' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: 'サーバー設定を保存' }));

    await waitFor(() => {
      expect(screen.getByText('サーバー設定の保存に失敗しました。')).toBeInTheDocument();
    });
  });

  it('disables save button while saving server settings', async () => {
    let resolvePut;
    setup();
    mockApiPut.mockReturnValue(new Promise((resolve) => { resolvePut = resolve; }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'サーバー設定を保存' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: 'サーバー設定を保存' }));

    expect(screen.getByRole('button', { name: '保存中...' })).toBeDisabled();

    resolvePut(SETTINGS_RESPONSE);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'サーバー設定を保存' })).toBeEnabled();
    });
  });

  // --- Error states ---

  it('shows error when models API fails', async () => {
    mockApiGet.mockImplementation((path) => {
      if (path === '/api/models') return Promise.reject(new Error('Network error'));
      if (path === '/api/settings') return Promise.resolve(SETTINGS_RESPONSE);
      return Promise.reject(new Error(`Unexpected: ${path}`));
    });
    render(<Settings />);

    await waitFor(() => {
      expect(screen.getByText(/モデル一覧の取得に失敗しました/)).toBeInTheDocument();
    });
  });

  it('shows error when settings API fails', async () => {
    mockApiGet.mockImplementation((path) => {
      if (path === '/api/models') return Promise.resolve(MODELS_RESPONSE);
      if (path === '/api/settings') return Promise.reject(new Error('Network error'));
      return Promise.reject(new Error(`Unexpected: ${path}`));
    });
    render(<Settings />);

    await waitFor(() => {
      expect(screen.getByText(/サーバー設定の取得に失敗しました/)).toBeInTheDocument();
    });
  });
});
