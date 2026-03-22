// Proofreading.integration.test.jsx
/**
 * Integration tests for Proofreading page — edge cases not covered by unit tests.
 * Tests full component interactions including ResultView integration.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Same mock pattern as existing Proofreading.test.jsx
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

import Proofreading from './Proofreading';
import { apiPost } from '../../api/client';

const mockApiPost = vi.mocked(apiPost);

function setup() {
  const user = userEvent.setup();
  const utils = render(<Proofreading />);
  const textarea = screen.getByPlaceholderText(/校正したいテキスト/);
  return {
    user, utils, textarea,
    submitText: async (text = 'テスト文書です。') => {
      await user.type(textarea, text);
      await user.click(screen.getByRole('button', { name: '校正実行' }));
    },
  };
}

describe('Proofreading — large_rewrite warning', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockApiPost.mockReset();
    localStorage.clear();
  });

  it('displays large_rewrite warning when response contains warnings', async () => {
    mockApiPost.mockResolvedValueOnce({
      request_id: 'test-req',
      status: 'success',
      status_reason: null,
      warnings: ['large_rewrite'],
      corrected_text: '校正済みテキスト',
      summary: '1件の修正を行いました。',
      corrections: [],
      diffs: [],
    });

    const { submitText } = setup();
    await submitText();

    await waitFor(() => {
      expect(screen.getByText(/広範囲を書き換えました/)).toBeInTheDocument();
    });
  });

  it('does not display warning when warnings is empty', async () => {
    mockApiPost.mockResolvedValueOnce({
      request_id: 'test-req',
      status: 'success',
      status_reason: null,
      warnings: [],
      corrected_text: '校正済みテキスト',
      summary: '1件の修正を行いました。',
      corrections: [],
      diffs: [],
    });

    const { submitText } = setup();
    await submitText();

    await waitFor(() => {
      expect(screen.getByText(/1件の修正を行いました/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/広範囲を書き換えました/)).not.toBeInTheDocument();
  });
});

describe('Proofreading — parse_fallback partial status', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockApiPost.mockReset();
    localStorage.clear();
  });

  it('displays corrected text for parse_fallback status', async () => {
    mockApiPost.mockResolvedValueOnce({
      request_id: 'test-req',
      status: 'partial',
      status_reason: 'parse_fallback',
      warnings: [],
      corrected_text: 'フォールバックテキスト',
      summary: null,
      corrections: [],
      diffs: [],
    });

    const { submitText } = setup();
    await submitText();

    await waitFor(() => {
      expect(screen.getByText(/フォールバックテキスト/)).toBeInTheDocument();
    });
  });
});

describe('Proofreading — API error code handling', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockApiPost.mockReset();
    localStorage.clear();
  });

  it('displays error message for 504 timeout', async () => {
    mockApiPost.mockRejectedValueOnce(new Error('AI応答がタイムアウトしました（60秒）'));

    const { submitText } = setup();
    await submitText();

    await waitFor(() => {
      expect(screen.getByText(/タイムアウト/)).toBeInTheDocument();
    });
  });

  it('displays error message for 422 validation error', async () => {
    mockApiPost.mockRejectedValueOnce(new Error('入力テキストの文字数が上限を超えています'));

    const { submitText } = setup();
    await submitText();

    await waitFor(() => {
      expect(screen.getByText(/文字数が上限/)).toBeInTheDocument();
    });
  });

  it('shows retry button after API error', async () => {
    mockApiPost.mockRejectedValueOnce(new Error('エラーが発生しました'));

    const { submitText } = setup();
    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
    });
  });
});
