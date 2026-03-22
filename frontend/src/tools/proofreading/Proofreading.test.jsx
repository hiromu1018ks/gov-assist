import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Proofreading from './Proofreading';

// --- Mocks ---

vi.mock('../../api/client', () => ({
  apiPost: vi.fn(),
  apiPostBlob: vi.fn(),
}));

vi.mock('../../utils/storage', () => ({
  loadSettings: vi.fn(() => ({
    model: 'kimi-k2.5',
    document_type: 'official',
    options: { typo: true, keigo: true, terminology: true, style: true, legal: false, readability: true },
  })),
}));

vi.mock('./preprocess', () => ({
  preprocessText: vi.fn((text) => ({ text: text.trim(), error: null })),
}));

vi.mock('./fileExtractor', () => ({
  extractText: vi.fn(),
}));

import { apiPost } from '../../api/client';
import { preprocessText } from './preprocess';

const mockApiPost = vi.mocked(apiPost);
const mockPreprocessText = vi.mocked(preprocessText);

// --- Fixtures ---

const SUCCESS_RESPONSE = {
  request_id: 'test-uuid-001',
  status: 'success',
  status_reason: null,
  warnings: [],
  corrected_text: '校正済みテキストです。',
  summary: '1件の修正を行いました。',
  corrections: [
    { original: '修正前', corrected: '修正後', reason: 'タイポ修正', category: '誤字脱字', diff_matched: true },
  ],
  diffs: [
    { type: 'equal', text: 'テキスト', start: 0, position: null, reason: null },
    { type: 'delete', text: '前', start: 4, position: null, reason: 'タイポ修正' },
    { type: 'insert', text: '後', start: 4, position: 'after', reason: 'タイポ修正' },
  ],
};

const PARTIAL_RESPONSE = {
  request_id: 'test-uuid-002',
  status: 'partial',
  status_reason: 'diff_timeout',
  warnings: [],
  corrected_text: '部分的に校正済み。',
  summary: null,
  corrections: [],
  diffs: [
    { type: 'equal', text: 'テスト', start: 0, position: null, reason: null },
  ],
};

function setup(text = 'テストテキスト') {
  const user = userEvent.setup();
  const utils = render(<Proofreading />);
  const textarea = screen.getByPlaceholderText(/校正したいテキスト/);
  return {
    user, utils, textarea,
    submitText: async () => { await user.type(textarea, text); await user.click(screen.getByRole('button', { name: '校正実行' })); },
  };
}

describe('Proofreading', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockApiPost.mockReset();
    mockApiPost.mockResolvedValue(SUCCESS_RESPONSE);
    mockPreprocessText.mockReset();
    mockPreprocessText.mockImplementation((text) => ({ text: text.trim(), error: null }));
    localStorage.clear();
  });

  // --- Submit flow ---

  it('preprocesses text and calls API on submit', async () => {
    const { user, submitText } = setup();

    await submitText();

    expect(mockPreprocessText).toHaveBeenCalledWith('テストテキスト');
    expect(mockApiPost).toHaveBeenCalledWith('/api/proofread', expect.objectContaining({
      request_id: expect.stringMatching(/^[0-9a-f-]+$/),
      text: 'テストテキスト',
      document_type: 'official',
      model: 'kimi-k2.5',
    }));
  });

  it('shows loading spinner during API call', async () => {
    let resolveApi;
    mockApiPost.mockReturnValue(new Promise((resolve) => { resolveApi = resolve; }));
    const { submitText } = setup();

    await submitText();

    expect(screen.getByText('AI が校正しています...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '校正実行' })).toBeDisabled();

    resolveApi(SUCCESS_RESPONSE);
    await waitFor(() => {
      expect(screen.queryByText('AI が校正しています...')).not.toBeInTheDocument();
    });
  });

  it('disables input area and option panel during submit', async () => {
    let resolveApi;
    mockApiPost.mockReturnValue(new Promise((resolve) => { resolveApi = resolve; }));
    const { submitText } = setup();

    await submitText();

    expect(screen.getByPlaceholderText(/校正したいテキスト/)).toBeDisabled();
    expect(screen.getByRole('group', { name: '校正オプション' })).toBeDisabled();

    resolveApi(SUCCESS_RESPONSE);
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/校正したいテキスト/)).not.toBeDisabled();
    });
  });

  it('displays result after successful API response', async () => {
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByText('1件の修正を行いました。')).toBeInTheDocument();
    });
  });

  it('shows error and retry button when API throws', async () => {
    mockApiPost.mockRejectedValue(new Error('AI応答がタイムアウトしました（60秒）'));
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByText('AI応答がタイムアウトしました（60秒）')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
  });

  it('retries with same params when retry is clicked', async () => {
    mockApiPost.mockRejectedValueOnce(new Error('タイムアウト'));
    mockApiPost.mockResolvedValueOnce(SUCCESS_RESPONSE);
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '再試行' }));

    await waitFor(() => {
      expect(screen.getByText('1件の修正を行いました。')).toBeInTheDocument();
    });
    expect(mockApiPost).toHaveBeenCalledTimes(2);
  });

  it('shows preprocess error without calling API', async () => {
    mockPreprocessText.mockReturnValueOnce({ text: '', error: '前処理後のテキストが8000文字を超えています。' });
    const { submitText } = setup();

    await submitText();

    expect(mockApiPost).not.toHaveBeenCalled();
    expect(screen.getByText('前処理後のテキストが8000文字を超えています。')).toBeInTheDocument();
  });

  it('clears result, error, and resets input on clear', async () => {
    const { submitText } = setup('テストテキスト');

    await submitText();

    await waitFor(() => {
      expect(screen.getByText('1件の修正を行いました。')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: 'クリア' }));

    expect(screen.queryByText('1件の修正を行いました。')).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText(/校正したいテキスト/)).toHaveValue('');
  });

  it('shows clear button during error state (not only on success)', async () => {
    mockApiPost.mockRejectedValue(new Error('タイムアウト'));
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'クリア' })).toBeInTheDocument();
  });

  it('handles partial response (diff_timeout)', async () => {
    mockApiPost.mockResolvedValue(PARTIAL_RESPONSE);
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByText(/差分計算がタイムアウト/)).toBeInTheDocument();
    });
  });

  it('retries from ResultView retry button when API returns status error', async () => {
    const errorResponse = {
      ...SUCCESS_RESPONSE,
      status: 'error',
      status_reason: 'parse_fallback',
      corrected_text: '',
      diffs: [],
      corrections: [],
    };
    mockApiPost.mockRejectedValueOnce(new Error('タイムアウト'));
    mockApiPost.mockResolvedValueOnce(errorResponse);
    mockApiPost.mockResolvedValueOnce(SUCCESS_RESPONSE);
    const { submitText } = setup();

    // First attempt fails with network error
    await submitText();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
    });

    // Retry returns status: "error"
    await userEvent.click(screen.getByRole('button', { name: '再試行' }));
    await waitFor(() => {
      expect(screen.getByText(/校正結果を取得できませんでした/)).toBeInTheDocument();
    });

    // ResultView has its own retry button
    await userEvent.click(screen.getByRole('button', { name: '再試行' }));
    await waitFor(() => {
      expect(screen.getByText('1件の修正を行いました。')).toBeInTheDocument();
    });
    expect(mockApiPost).toHaveBeenCalledTimes(3);
  });
});
