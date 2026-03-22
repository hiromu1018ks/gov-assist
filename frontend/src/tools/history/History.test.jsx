import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// --- Mocks ---

vi.mock('../../api/client', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));

vi.mock('../proofreading/ResultView', () => ({
  default: ({ result }) => (
    <div data-testid="result-view">{result ? `Status: ${result.status}` : 'no result'}</div>
  ),
}));

import { apiGet, apiPatch, apiDelete } from '../../api/client';
import HistoryList from './HistoryList';
import HistoryDetail from './HistoryDetail';

const mockApiGet = vi.mocked(apiGet);
const mockApiPatch = vi.mocked(apiPatch);
const mockApiDelete = vi.mocked(apiDelete);

// --- Fixtures ---

const LIST_RESPONSE = {
  items: [
    {
      id: 1,
      preview: 'これはテストテキストのプレビューです。校正結果の確認用に保存されました。',
      document_type: 'official',
      model: 'kimi-k2.5',
      created_at: '2026-03-22T10:00:00+09:00',
      truncated: false,
      memo: null,
    },
    {
      id: 2,
      preview: 'メールのテキストプレビュー。',
      document_type: 'email',
      model: 'kimi-k2.5',
      created_at: '2026-03-21T15:30:00+09:00',
      truncated: true,
      memo: '確認用メモ',
    },
  ],
  total: 2,
};

const EMPTY_RESPONSE = { items: [], total: 0 };

const PAGINATED_RESPONSE = {
  items: Array.from({ length: 20 }, (_, i) => ({
    id: i + 1,
    preview: `アイテム ${i + 1} のプレビュー`,
    document_type: 'official',
    model: 'kimi-k2.5',
    created_at: '2026-03-22T10:00:00+09:00',
    truncated: false,
    memo: null,
  })),
  total: 25,
};

function setupList(response = LIST_RESPONSE) {
  mockApiGet.mockResolvedValue(response);
  const onSelectItem = vi.fn();
  const utils = render(<HistoryList onSelectItem={onSelectItem} />);
  return { onSelectItem, utils };
}

const DETAIL_RESPONSE = {
  id: 1,
  input_text: 'テストテキストです。修正箇所があります。',
  result: {
    request_id: 'test-uuid-001',
    status: 'success',
    status_reason: null,
    warnings: [],
    corrected_text: 'テストテキストです。修正箇所があります。',
    summary: '1件の修正を行いました。',
    corrections: [
      { original: '修正前', corrected: '修正後', reason: 'タイポ修正', category: '誤字脱字', diff_matched: true },
    ],
    diffs: [
      { type: 'equal', text: 'テキスト', start: 0, position: null, reason: null },
      { type: 'delete', text: '前', start: 4, position: null, reason: 'タイポ修正' },
      { type: 'insert', text: '後', start: 4, position: 'after', reason: 'タイポ修正' },
    ],
  },
  model: 'kimi-k2.5',
  document_type: 'official',
  created_at: '2026-03-22T10:00:00+09:00',
  truncated: false,
  memo: null,
};

const TRUNCATED_DETAIL = {
  ...DETAIL_RESPONSE,
  id: 2,
  truncated: true,
  result: {
    ...DETAIL_RESPONSE.result,
    corrections: [],
    diffs: [],
  },
};

function setupDetail(response = DETAIL_RESPONSE) {
  mockApiGet.mockResolvedValue(response);
  mockApiPatch.mockResolvedValue(response);
  const onBack = vi.fn();
  const utils = render(<HistoryDetail historyId={response.id} onBack={onBack} />);
  return { onBack, utils };
}

describe('HistoryList', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockApiGet.mockReset();
    mockApiDelete.mockReset();
    mockApiDelete.mockResolvedValue({ message: '削除しました' });
  });

  // --- Fetch and render ---

  it('fetches and displays history items', async () => {
    const { onSelectItem } = setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });
    expect(screen.getByText('メールのテキストプレビュー。')).toBeInTheDocument();
    expect(screen.getByText('2026/03/22 10:00')).toBeInTheDocument();
    expect(screen.getByText('2026/03/21 15:30')).toBeInTheDocument();
  });

  it('shows loading state while fetching', async () => {
    let resolveApi;
    mockApiGet.mockReturnValue(new Promise((resolve) => { resolveApi = resolve; }));
    setupList();

    expect(screen.getByText('読み込み中...')).toBeInTheDocument();

    resolveApi(LIST_RESPONSE);
    await waitFor(() => {
      expect(screen.queryByText('読み込み中...')).not.toBeInTheDocument();
    });
  });

  it('shows empty state when no items', async () => {
    setupList(EMPTY_RESPONSE);

    await waitFor(() => {
      expect(screen.getByText('履歴がありません。')).toBeInTheDocument();
    });
  });

  it('shows error message when fetch fails', async () => {
    mockApiGet.mockRejectedValue(new Error('サーバーエラー'));
    const onSelectItem = vi.fn();
    render(<HistoryList onSelectItem={onSelectItem} />);

    await waitFor(() => {
      expect(screen.getByText('サーバーエラー')).toBeInTheDocument();
    });
  });

  // --- Filters ---

  it('applies search query on form submit', async () => {
    setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('キーワード検索');
    await userEvent.type(searchInput, 'テスト');
    await userEvent.click(screen.getByRole('button', { name: '検索' }));

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith(
        expect.stringContaining('q=%E3%83%86%E3%82%B9%E3%83%88')
      );
    });
  });

  it('applies document type filter on form submit', async () => {
    setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    await userEvent.selectOptions(screen.getByLabelText('文書種別'), 'email');
    await userEvent.click(screen.getByRole('button', { name: '検索' }));

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith(
        expect.stringContaining('document_type=email')
      );
    });
  });

  it('clears all filters and refetches', async () => {
    setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    await userEvent.type(screen.getByPlaceholderText('キーワード検索'), 'テスト');
    await userEvent.click(screen.getByRole('button', { name: 'クリア' }));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('キーワード検索')).toHaveValue('');
    });

    // Last apiGet call should have no filters
    const lastCall = mockApiGet.mock.calls[mockApiGet.mock.calls.length - 1][0];
    expect(lastCall).not.toContain('q=');
    expect(lastCall).not.toContain('document_type=');
  });

  // --- Pagination ---

  it('shows pagination info and next button when more items exist', async () => {
    setupList(PAGINATED_RESPONSE);

    await waitFor(() => {
      expect(screen.getByText('1-20件 / 全25件')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '次へ' })).not.toBeDisabled();
    expect(screen.getByRole('button', { name: '前へ' })).toBeDisabled();
  });

  it('navigates to next page on click', async () => {
    setupList(PAGINATED_RESPONSE);

    await waitFor(() => {
      expect(screen.getByText('1-20件 / 全25件')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '次へ' }));

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('offset=20'));
    });
  });

  // --- Item interaction ---

  it('calls onSelectItem when item is clicked', async () => {
    const { onSelectItem } = setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。'));

    expect(onSelectItem).toHaveBeenCalledWith(1);
  });

  // --- Truncated badge ---

  it('shows truncated badge for truncated items', async () => {
    setupList();

    await waitFor(() => {
      expect(screen.getByText('⚠ 詳細省略')).toBeInTheDocument();
    });
  });

  // --- Delete ---

  it('deletes individual item with confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole('button', { name: '削除' });
    await userEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith('この履歴を削除しますか？');
    expect(mockApiDelete).toHaveBeenCalledWith('/api/history/1');
  });

  it('does not delete when confirmation is cancelled', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    setupList();

    await waitFor(() => {
      expect(screen.getByText('これはテストテキストのプレビューです。校正結果の確認用に保存されました。')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole('button', { name: '削除' });
    await userEvent.click(deleteButtons[0]);

    expect(mockApiDelete).not.toHaveBeenCalled();
  });

  it('deletes all items with confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockApiDelete.mockResolvedValue({ message: '2件の履歴を削除しました' });
    setupList();

    await waitFor(() => {
      expect(screen.getByText('全件削除')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '全件削除' }));

    expect(window.confirm).toHaveBeenCalledWith('全ての履歴を削除しますか？この操作は取り消せません。');
    expect(mockApiDelete).toHaveBeenCalledWith('/api/history');
  });
});

describe('HistoryDetail', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockApiGet.mockReset();
    mockApiPatch.mockReset();
    mockApiDelete.mockReset();
    mockApiDelete.mockResolvedValue({ message: '削除しました' });
  });

  // --- Fetch and render ---

  it('fetches and displays history detail', async () => {
    setupDetail();

    await waitFor(() => {
      expect(screen.getByText('校正履歴詳細')).toBeInTheDocument();
    });
    expect(screen.getByText('テストテキストです。修正箇所があります。')).toBeInTheDocument();
  });

  it('shows loading state while fetching', async () => {
    let resolveApi;
    mockApiGet.mockReturnValue(new Promise((resolve) => { resolveApi = resolve; }));
    setupDetail();

    expect(screen.getByText('読み込み中...')).toBeInTheDocument();

    resolveApi(DETAIL_RESPONSE);
    await waitFor(() => {
      expect(screen.queryByText('読み込み中...')).not.toBeInTheDocument();
    });
  });

  it('shows error when fetch fails', async () => {
    mockApiGet.mockRejectedValue(new Error('見つかりません'));
    const onBack = vi.fn();
    render(<HistoryDetail historyId={1} onBack={onBack} />);

    await waitFor(() => {
      expect(screen.getByText('見つかりません')).toBeInTheDocument();
    });
  });

  // --- ResultView ---

  it('renders ResultView with saved result', async () => {
    setupDetail();

    await waitFor(() => {
      expect(screen.getByTestId('result-view')).toBeInTheDocument();
    });
    expect(screen.getByTestId('result-view')).toHaveTextContent('Status: success');
  });

  // --- Truncated ---

  it('shows truncated warning for truncated records', async () => {
    setupDetail(TRUNCATED_DETAIL);

    await waitFor(() => {
      expect(screen.getByText(/データサイズ超過のため/)).toBeInTheDocument();
    });
    expect(screen.queryByTestId('result-view')).not.toBeInTheDocument();
  });

  // --- Memo ---

  it('loads existing memo', async () => {
    const withMemo = { ...DETAIL_RESPONSE, memo: '確認用のメモ' };
    setupDetail(withMemo);

    await waitFor(() => {
      expect(screen.getByText('校正履歴詳細')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('メモ')).toHaveValue('確認用のメモ');
  });

  it('saves memo via PATCH API', async () => {
    setupDetail();

    await waitFor(() => {
      expect(screen.getByText('校正履歴詳細')).toBeInTheDocument();
    });

    const memoTextarea = screen.getByLabelText('メモ');
    await userEvent.type(memoTextarea, '新しいメモ');
    await userEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() => {
      expect(mockApiPatch).toHaveBeenCalledWith('/api/history/1', { memo: '新しいメモ' });
    });
  });

  // --- Delete ---

  it('deletes history and calls onBack', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const { onBack } = setupDetail();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '削除' })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: '削除' }));

    expect(window.confirm).toHaveBeenCalledWith('この履歴を削除しますか？');
    await waitFor(() => {
      expect(mockApiDelete).toHaveBeenCalledWith('/api/history/1');
      expect(onBack).toHaveBeenCalled();
    });
  });

  // --- Navigation ---

  it('calls onBack when back button is clicked', async () => {
    const { onBack } = setupDetail();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /一覧に戻る/ })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: /一覧に戻る/ }));

    expect(onBack).toHaveBeenCalled();
  });
});
