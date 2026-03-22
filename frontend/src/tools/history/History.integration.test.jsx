// History.integration.test.jsx
/**
 * Integration tests for History — edge cases for pagination and error handling.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Same mock pattern as existing History.test.jsx
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
import History from './History';

const mockItems = (count, startId = 1) =>
  Array.from({ length: count }, (_, i) => ({
    id: startId + i,
    preview: `テスト文書${startId + i}`,
    document_type: 'official',
    model: 'kimi-k2.5',
    created_at: new Date(Date.now() - i * 86400000).toISOString(),
    truncated: false,
    memo: null,
  }));

describe('History — pagination', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiGet.mockResolvedValue({ items: mockItems(5), total: 25 });
  });

  it('shows total count and pagination info', async () => {
    render(<History />);
    await waitFor(() => {
      expect(screen.getByText(/25件/)).toBeInTheDocument();
    });
  });

  it('navigates to next page', async () => {
    const user = userEvent.setup();
    apiGet.mockResolvedValueOnce({ items: mockItems(20), total: 25 });
    apiGet.mockResolvedValueOnce({ items: mockItems(5, 21), total: 25 });

    render(<History />);

    // Button text is "次へ" (not "次のページ")
    await waitFor(() => {
      expect(screen.getByText('次へ')).toBeInTheDocument();
    });
    await user.click(screen.getByText('次へ'));

    await waitFor(() => {
      expect(apiGet).toHaveBeenLastCalledWith(expect.stringContaining('offset=20'));
    });
  });
});

describe('History — error handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays error when list fetch fails', async () => {
    apiGet.mockRejectedValueOnce(new Error('ネットワークエラー'));

    render(<History />);
    await waitFor(() => {
      expect(screen.getByText(/ネットワークエラー/)).toBeInTheDocument();
    });
  });

  it('displays error when delete fails', async () => {
    const user = userEvent.setup();
    apiGet.mockResolvedValue({ items: mockItems(1), total: 1 });
    apiDelete.mockRejectedValueOnce(new Error('削除に失敗しました。'));

    // Mock window.confirm to return true (user clicks OK)
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(<History />);

    await waitFor(() => {
      expect(screen.getByText('テスト文書1')).toBeInTheDocument();
    });

    // Delete button has aria-label="削除"
    const deleteButton = screen.getByRole('button', { name: '削除' });
    await user.click(deleteButton);

    await waitFor(() => {
      expect(screen.getByText(/削除に失敗しました/)).toBeInTheDocument();
    });

    confirmSpy.mockRestore();
  });
});
