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
    const { container } = render(<ResultView result={null} originalText="入力テキスト" />);
    expect(container.innerHTML).toBe('');
  });

  // --- Success status ---

  describe('success status', () => {
    it('renders all 3 tabs', () => {
      render(<ResultView result={createResult()} originalText="入力テキスト" />);
      expect(screen.getByRole('tab', { name: /校正前/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /校正後/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /差分/ })).toBeInTheDocument();
    });

    it('renders summary text in diff tab', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} originalText="入力テキスト" />);
      await user.click(screen.getByRole('tab', { name: /差分/ }));
      expect(screen.getByText('3 件の修正を行いました。')).toBeInTheDocument();
    });

    it('renders diff-based notice', () => {
      render(<ResultView result={createResult()} originalText="入力テキスト" />);
      expect(screen.getByText(/差分タブのコメントは AI 推定/)).toBeInTheDocument();
    });

    it('defaults to first tab (before) as active', () => {
      render(<ResultView result={createResult()} originalText="入力テキスト" />);
      expect(screen.getByRole('tab', { name: /校正前/ })).toHaveAttribute(
        'aria-selected',
        'true',
      );
    });

    it('does not show status message for success', () => {
      render(<ResultView result={createResult()} originalText="入力テキスト" />);
      expect(screen.queryByText(/タイムアウト/)).not.toBeInTheDocument();
      expect(screen.queryByText(/不完全でした/)).not.toBeInTheDocument();
    });

    it('does not render summary section when summary is null', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult({ summary: null })} originalText="入力テキスト" />);
      await user.click(screen.getByRole('tab', { name: /差分/ }));
      expect(screen.queryByText('3 件の修正を行いました。')).not.toBeInTheDocument();
    });

    it('renders originalText in before tab', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} originalText="オリジナル文書" />);
      expect(screen.getByText('オリジナル文書')).toBeInTheDocument();
    });

    it('renders corrected_text in after tab', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} originalText="入力" />);
      await user.click(screen.getByRole('tab', { name: /校正後/ }));
      expect(screen.getByText('校正済みテキストです。')).toBeInTheDocument();
    });
  });

  // --- Large rewrite warning ---

  describe('large rewrite warning', () => {
    it('shows warning when warnings includes large_rewrite', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult({ warnings: ['large_rewrite'] })} originalText="入力テキスト" />);
      await user.click(screen.getByRole('tab', { name: /差分/ }));
      expect(screen.getByText(/AI が広範囲を書き換えました/)).toBeInTheDocument();
    });

    it('does not show warning when warnings is empty', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult({ warnings: [] })} originalText="入力テキスト" />);
      await user.click(screen.getByRole('tab', { name: /差分/ }));
      expect(screen.queryByText(/AI が広範囲を書き換えました/)).not.toBeInTheDocument();
    });
  });

  // --- Diff tab ---

  describe('diff tab', () => {
    it('shows corrections with original, corrected, reason, category', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} originalText="入力テキスト" />);

      await user.click(screen.getByRole('tab', { name: /差分/ }));

      expect(screen.getByText('修正前テキスト')).toBeInTheDocument();
      expect(screen.getByText('修正後テキスト')).toBeInTheDocument();
      expect(screen.getByText('誤字を修正しました。')).toBeInTheDocument();
      expect(screen.getByText('誤字脱字')).toBeInTheDocument();
    });

    it('shows "修正箇所はありません" when corrections is empty', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult({ corrections: [] })} originalText="入力テキスト" />);

      await user.click(screen.getByRole('tab', { name: /差分/ }));
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
          originalText="入力テキスト"
        />,
      );

      await user.click(screen.getByRole('tab', { name: /差分/ }));
      expect(screen.getByText('参考（AI推定）')).toBeInTheDocument();
    });

    it('does not show badge for diff_matched: true', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} originalText="入力テキスト" />);

      await user.click(screen.getByRole('tab', { name: /差分/ }));
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
          originalText="入力テキスト"
        />,
      );

      await user.click(screen.getByRole('tab', { name: /差分/ }));
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
          originalText="入力テキスト"
        />,
      );

      expect(screen.getByText(/差分計算がタイムアウトしました/)).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /校正前/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /差分/ })).toBeInTheDocument();
    });

    it('shows after + diff tabs for diff_timeout without diffs', () => {
      render(
        <ResultView
          result={createResult({
            status: 'partial',
            status_reason: 'diff_timeout',
            diffs: [],
          })}
          originalText="入力テキスト"
        />,
      );

      expect(screen.getByText(/差分計算に失敗しました/)).toBeInTheDocument();
      expect(screen.queryByRole('tab', { name: /校正前/ })).not.toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /校正後/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /差分/ })).toBeInTheDocument();
      // corrected_text shown in "after" tab (default active)
      expect(screen.getByText('校正済みテキストです。')).toBeInTheDocument();
    });

    it('shows after + diff tabs for parse_fallback', () => {
      render(
        <ResultView
          result={createResult({
            status: 'partial',
            status_reason: 'parse_fallback',
            diffs: [],
          })}
          originalText="入力テキスト"
        />,
      );

      expect(screen.getByText(/AI の応答形式が不完全でした/)).toBeInTheDocument();
      expect(screen.queryByRole('tab', { name: /校正前/ })).not.toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /校正後/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /差分/ })).toBeInTheDocument();
      expect(screen.getByText('校正済みテキストです。')).toBeInTheDocument();
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
          originalText="入力テキスト"
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
          originalText="入力テキスト"
        />,
      );

      await user.click(screen.getByRole('button', { name: '再試行' }));
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it('does not show retry button without onRetry prop', () => {
      render(
        <ResultView
          result={createResult({ status: 'error', status_reason: 'parse_fallback' })}
          originalText="入力テキスト"
        />,
      );

      expect(screen.queryByRole('button', { name: '再試行' })).not.toBeInTheDocument();
    });

    it('does not show tabs or notice for error status', () => {
      render(
        <ResultView
          result={createResult({ status: 'error', status_reason: 'parse_fallback' })}
          originalText="入力テキスト"
        />,
      );

      expect(screen.queryByRole('tab')).not.toBeInTheDocument();
      expect(screen.queryByText(/差分タブのコメントは AI 推定/)).not.toBeInTheDocument();
    });
  });

  // --- Tab switching ---

  describe('tab switching', () => {
    it('switches content when tab is clicked', async () => {
      const user = userEvent.setup();
      render(<ResultView result={createResult()} originalText="入力テキスト" />);

      // Initially on before tab — shows original text
      expect(screen.getByText('入力テキスト')).toBeInTheDocument();

      // Switch to after tab
      await user.click(screen.getByRole('tab', { name: /校正後/ }));
      expect(screen.getByText('校正済みテキストです。')).toBeInTheDocument();

      // Switch to diff tab
      await user.click(screen.getByRole('tab', { name: /差分/ }));
      expect(screen.getByText('修正前テキスト')).toBeInTheDocument();
    });
  });
});
