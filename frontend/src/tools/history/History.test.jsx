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

import { apiGet, apiDelete } from '../../api/client';
import HistoryList from './HistoryList';

const mockApiGet = vi.mocked(apiGet);
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
