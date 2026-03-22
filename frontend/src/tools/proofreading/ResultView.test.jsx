import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ResultView from './ResultView';

// --- Test data factory ---

function createResult(overrides = {}) {
  return {
    request_id: 'test-uuid-1234',
    status: 'success',
    status_reason: null,
    warnings: [],
    corrected_text: '校正済みテキストです。',
    summary: '3 件の修正を行いました。',
    corrections: [
      {
        original: '修正前テキスト',
        corrected: '修正後テキスト',
        reason: '誤字を修正しました。',
        category: '誤字脱字',
        diff_matched: true,
      },
    ],
    diffs: [
      { type: 'equal', text: '前半', start: 0, position: null, reason: null },
      { type: 'delete', text: '旧', start: 2, position: null, reason: '理由' },
      { type: 'insert', text: '新', start: 2, position: 'after', reason: '理由' },
      { type: 'equal', text: '後半', start: 3, position: null, reason: null },
    ],
    ...overrides,
  };
}

describe('ResultView', () => {
  // --- Null result ---

  it('returns null when result is null', () => {
    const { container } = render(<ResultView result={null} />);
    expect(container.innerHTML).toBe('');
  });

  // --- Success status ---

  describe('success status', () => {
    it('renders all 3 tabs', () => {
      render(<ResultView result={createResult()} />);
      expect(screen.getByRole('tab', { name: /ハイライト表示/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /比較表示/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /コメント一覧/ })).toBeInTheDocument();
    });

    it('renders summary text', () => {
      render(<ResultView result={createResult()} />);
      expect(screen.getByText('3 件の修正を行いました。')).toBeInTheDocument();
    });

    it('renders diff-based notice', () => {
      render(<ResultView result={createResult()} />);
      expect(screen.getByText(/表示は差分ベースです/)).toBeInTheDocument();
    });

    it('defaults to first tab (highlight) as active', () => {
      render(<ResultView result={createResult()} />);
      expect(screen.getByRole('tab', { name: /ハイライト表示/ })).toHaveAttribute(
        'aria-selected',
        'true',
      );
    });

    it('does not show status message for success', () => {
      render(<ResultView result={createResult()} />);
      expect(screen.queryByText(/タイムアウト/)).not.toBeInTheDocument();
      expect(screen.queryByText(/不完全でした/)).not.toBeInTheDocument();
    });

    it('does not render summary section when summary is null', () => {
      const { container } = render(<ResultView result={createResult({ summary: null })} />);
      expect(container.querySelector('.result-view__summary')).toBeNull();
    });
  });

  // --- Large rewrite warning ---

  describe('large rewrite warning', () => {
    it('shows warning when warnings includes large_rewrite', () => {
      render(<ResultView result={createResult({ warnings: ['large_rewrite'] })} />);
      expect(screen.getByText(/AI が広範囲を書き換えました/)).toBeInTheDocument();
    });

    it('does not show warning when warnings is empty', () => {
      render(<ResultView result={createResult({ warnings: [] })} />);
      expect(screen.queryByText(/AI が広範囲を書き換えました/)).not.toBeInTheDocument();
    });
  });

  // --- Tab ③ comments list ---

  describe('tab ③ comments list', () => {
    it('shows corrections with original, corrected, reason, category', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} />);

      await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));

      expect(screen.getByText('修正前テキスト')).toBeInTheDocument();
      expect(screen.getByText('修正後テキスト')).toBeInTheDocument();
      expect(screen.getByText('誤字を修正しました。')).toBeInTheDocument();
      expect(screen.getByText('誤字脱字')).toBeInTheDocument();
    });

    it('shows "修正箇所はありません" when corrections is empty', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult({ corrections: [] })} />);

      await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));
      expect(screen.getByText('修正箇所はありません。')).toBeInTheDocument();
    });

    it('shows "参考（AI推定）" badge for diff_matched: false', async () => {
      const user = userEvent.setup();
      render(
        <ResultView
          result={createResult({
            corrections: [
              {
                original: 'ですます',
                corrected: 'である',
                reason: '文体を統一しました。',
                category: '文体',
                diff_matched: false,
              },
            ],
          })}
        />,
      );

      await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));
      expect(screen.getByText('参考（AI推定）')).toBeInTheDocument();
    });

    it('does not show badge for diff_matched: true', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} />);

      await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));
      expect(screen.queryByText('参考（AI推定）')).not.toBeInTheDocument();
    });

    it('handles correction with missing reason gracefully', async () => {
      const user = userEvent.setup();
      render(
        <ResultView
          result={createResult({
            corrections: [
              {
                original: 'A',
                corrected: 'B',
                reason: null,
                category: '誤字脱字',
                diff_matched: true,
              },
            ],
          })}
        />,
      );

      await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));
      expect(screen.getByText('A')).toBeInTheDocument();
      expect(screen.getByText('B')).toBeInTheDocument();
      // No crash, no reason label when reason is null
      expect(screen.queryByText(/^理由：/)).not.toBeInTheDocument();
    });
  });

  // --- Partial status ---

  describe('partial status', () => {
    it('shows all tabs + info message for diff_timeout with diffs', () => {
      render(
        <ResultView
          result={createResult({
            status: 'partial',
            status_reason: 'diff_timeout',
            diffs: [{ type: 'equal', text: 'テスト', start: 0, position: null, reason: null }],
          })}
        />,
      );

      expect(screen.getByText(/差分計算がタイムアウトしました/)).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /ハイライト表示/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /コメント一覧/ })).toBeInTheDocument();
    });

    it('shows only tab ③ + corrected text for diff_timeout without diffs', () => {
      render(
        <ResultView
          result={createResult({
            status: 'partial',
            status_reason: 'diff_timeout',
            diffs: [],
          })}
        />,
      );

      expect(screen.getByText(/差分計算に失敗しました/)).toBeInTheDocument();
      expect(screen.queryByRole('tab', { name: /ハイライト表示/ })).not.toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /コメント一覧/ })).toBeInTheDocument();
      // corrected_text displayed prominently
      expect(screen.getByText('校正済みテキスト')).toBeInTheDocument();
    });

    it('shows only tab ③ + corrected text for parse_fallback', () => {
      render(
        <ResultView
          result={createResult({
            status: 'partial',
            status_reason: 'parse_fallback',
            diffs: [],
          })}
        />,
      );

      expect(screen.getByText(/AI の応答形式が不完全でした/)).toBeInTheDocument();
      expect(screen.queryByRole('tab', { name: /ハイライト表示/ })).not.toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /コメント一覧/ })).toBeInTheDocument();
      expect(screen.getByText('校正済みテキスト')).toBeInTheDocument();
    });
  });

  // --- Error status ---

  describe('error status', () => {
    it('shows error message and retry button', () => {
      const onRetry = vi.fn();
      render(
        <ResultView
          result={createResult({ status: 'error', status_reason: 'parse_fallback' })}
          onRetry={onRetry}
        />,
      );

      expect(screen.getByText(/校正結果を取得できませんでした/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
    });

    it('calls onRetry when retry button is clicked', async () => {
      const onRetry = vi.fn();
      const user = userEvent.setup();
      render(
        <ResultView
          result={createResult({ status: 'error', status_reason: 'parse_fallback' })}
          onRetry={onRetry}
        />,
      );

      await user.click(screen.getByRole('button', { name: '再試行' }));
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it('does not show retry button without onRetry prop', () => {
      render(
        <ResultView
          result={createResult({ status: 'error', status_reason: 'parse_fallback' })}
        />,
      );

      expect(screen.queryByRole('button', { name: '再試行' })).not.toBeInTheDocument();
    });

    it('does not show tabs or notice for error status', () => {
      render(
        <ResultView
          result={createResult({ status: 'error', status_reason: 'parse_fallback' })}
        />,
      );

      expect(screen.queryByRole('tab')).not.toBeInTheDocument();
      expect(screen.queryByText(/表示は差分ベース/)).not.toBeInTheDocument();
    });
  });

  // --- Tab switching ---

  describe('tab switching', () => {
    it('switches content when tab is clicked', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} />);

      // Initially on highlight tab — shows diff content
      expect(screen.getByText('前半')).toBeInTheDocument();

      // Switch to compare tab
      await user.click(screen.getByRole('tab', { name: /比較表示/ }));
      expect(screen.getByText(/修正前/)).toBeInTheDocument();

      // Switch to comments tab
      await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));
      expect(screen.getByText('修正前テキスト')).toBeInTheDocument();
    });
  });
});
