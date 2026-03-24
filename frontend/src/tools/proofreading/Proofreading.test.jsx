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
    model: 'gpt-oss-120b',
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

import { apiPost, apiPostBlob } from '../../api/client';
import { preprocessText } from './preprocess';

const mockApiPost = vi.mocked(apiPost);
const mockApiPostBlob = vi.mocked(apiPostBlob);
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
    mockApiPostBlob.mockReset();
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
      model: 'gpt-oss-120b',
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
    const { user, submitText } = setup();

    await submitText();

    // Summary is displayed in the diff tab
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /差分/ })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('tab', { name: /差分/ }));

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
    const { user, submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: '再試行' }));

    // Summary is displayed in the diff tab
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /差分/ })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('tab', { name: /差分/ }));

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
    const { user, submitText } = setup('テストテキスト');

    await submitText();

    // Summary is displayed in the diff tab — switch to verify result is shown
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /差分/ })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('tab', { name: /差分/ }));

    await waitFor(() => {
      expect(screen.getByText('1件の修正を行いました。')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: 'クリア' }));

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
    const { user, submitText } = setup();

    // First attempt fails with network error
    await submitText();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
    });

    // Retry returns status: "error"
    await user.click(screen.getByRole('button', { name: '再試行' }));
    await waitFor(() => {
      expect(screen.getByText(/校正結果を取得できませんでした/)).toBeInTheDocument();
    });

    // ResultView has its own retry button
    await user.click(screen.getByRole('button', { name: '再試行' }));

    // Summary is displayed in the diff tab
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /差分/ })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('tab', { name: /差分/ }));

    await waitFor(() => {
      expect(screen.getByText('1件の修正を行いました。')).toBeInTheDocument();
    });
    expect(mockApiPost).toHaveBeenCalledTimes(3);
  });

  // --- Action buttons ---

  it('shows copy, download, save buttons after successful result', async () => {
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '校正済みテキストをコピー' })).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /Word.*ダウンロード/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '履歴に保存' })).toBeInTheDocument();
  });

  it('does not show copy/download/save buttons when result has error status', async () => {
    const errorResponse = { ...SUCCESS_RESPONSE, status: 'error', status_reason: 'parse_fallback', corrected_text: '', diffs: [], corrections: [] };
    mockApiPost.mockResolvedValue(errorResponse);
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByText(/校正結果を取得できませんでした/)).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: '校正済みテキストをコピー' })).not.toBeInTheDocument();
  });

  // --- Copy ---

  it('copies corrected_text to clipboard on copy click', async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    const origDesc = Object.getOwnPropertyDescriptor(window, 'navigator');
    Object.defineProperty(window, 'navigator', {
      get() { return { ...origDesc.get.call(window), clipboard: { writeText: writeTextMock } }; },
      configurable: true,
    });
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '校正済みテキストをコピー' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '校正済みテキストをコピー' }));

    expect(writeTextMock).toHaveBeenCalledWith('校正済みテキストです。');
    await waitFor(() => {
      expect(screen.getByText('コピーしました')).toBeInTheDocument();
    });
  });

  it('shows error when clipboard copy fails', async () => {
    const origDesc = Object.getOwnPropertyDescriptor(window, 'navigator');
    Object.defineProperty(window, 'navigator', {
      get() { return { ...origDesc.get.call(window), clipboard: { writeText: vi.fn().mockRejectedValue(new Error('Denied')) } }; },
      configurable: true,
    });
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '校正済みテキストをコピー' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '校正済みテキストをコピー' }));

    await waitFor(() => {
      expect(screen.getByText('クリップボードへのコピーに失敗しました。')).toBeInTheDocument();
    });
  });

  // --- Download ---

  it('downloads docx via apiPostBlob', async () => {
    const blob = new Blob(['docx'], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    mockApiPostBlob.mockResolvedValue(blob);

    // Mock URL.createObjectURL and DOM for download link
    const mockUrl = 'blob:http://localhost/test';
    vi.spyOn(URL, 'createObjectURL').mockReturnValue(mockUrl);
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const clickMock = vi.fn();
    const mockAnchor = { href: '', download: '', click: clickMock, style: {} };
    const originalCreateElement = document.createElement.bind(document);
    const originalAppendChild = document.body.appendChild.bind(document.body);
    const originalRemoveChild = document.body.removeChild.bind(document.body);
    vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
      if (tagName === 'a') return mockAnchor;
      return originalCreateElement(tagName);
    });
    vi.spyOn(document.body, 'appendChild').mockImplementation((node) => {
      if (node === mockAnchor) return mockAnchor;
      return originalAppendChild(node);
    });
    vi.spyOn(document.body, 'removeChild').mockImplementation((node) => {
      if (node === mockAnchor) return mockAnchor;
      return originalRemoveChild(node);
    });

    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Word.*ダウンロード/ })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: /Word.*ダウンロード/ }));

    expect(mockApiPostBlob).toHaveBeenCalledWith('/api/export/docx', {
      corrected_text: '校正済みテキストです。',
      document_type: 'official',
    });
    expect(clickMock).toHaveBeenCalled();
  });

  it('shows error when download fails', async () => {
    mockApiPostBlob.mockRejectedValue(new Error('サーバーエラー'));
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Word.*ダウンロード/ })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: /Word.*ダウンロード/ }));

    await waitFor(() => {
      expect(screen.getByText('Word ファイルのダウンロードに失敗しました。')).toBeInTheDocument();
    });
  });

  // --- Save to history ---

  it('saves raw text (not preprocessed) to history via apiPost', async () => {
    mockApiPost.mockResolvedValueOnce(SUCCESS_RESPONSE);
    mockApiPost.mockResolvedValueOnce({ id: 1, message: '保存しました' });
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '履歴に保存' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '履歴に保存' }));

    // Verify raw text is sent as input_text (the text the user typed)
    expect(mockApiPost).toHaveBeenCalledWith('/api/history', expect.objectContaining({
      input_text: 'テストテキスト',
      model: 'gpt-oss-120b',
      document_type: 'official',
    }));

    await waitFor(() => {
      expect(screen.getByText('保存しました')).toBeInTheDocument();
    });
  });

  it('disables save button after successful save', async () => {
    mockApiPost.mockResolvedValueOnce(SUCCESS_RESPONSE);
    mockApiPost.mockResolvedValueOnce({ id: 1, message: '保存しました' });
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '履歴に保存' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '履歴に保存' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '保存しました' })).toBeDisabled();
    });
  });

  it('shows error when save fails', async () => {
    mockApiPost.mockResolvedValueOnce(SUCCESS_RESPONSE);
    mockApiPost.mockRejectedValueOnce(new Error('DB エラー'));
    const { submitText } = setup();

    await submitText();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '履歴に保存' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '履歴に保存' }));

    await waitFor(() => {
      expect(screen.getByText('履歴への保存に失敗しました。')).toBeInTheDocument();
    });
  });
});
