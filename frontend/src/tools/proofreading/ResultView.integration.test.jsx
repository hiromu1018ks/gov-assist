// ResultView.integration.test.jsx
/**
 * Integration tests for ResultView — edge cases for corrections display and tab switching.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';

import ResultView from './ResultView';

describe('ResultView — multiple corrections in comments tab', () => {
  it('displays all corrections after switching to comments tab', async () => {
    const user = userEvent.setup();
    const result = {
      request_id: 'test',
      status: 'success',
      status_reason: null,
      warnings: [],
      corrected_text: '校正済み',
      summary: '3件修正',
      corrections: [
        { original: '修正前テキストA', corrected: '修正後テキストB', reason: '理由1', category: '誤字脱字', diff_matched: true },
        { original: '修正前テキストC', corrected: '修正後テキストD', reason: '理由2', category: '敬語', diff_matched: false },
        { original: '修正前テキストE', corrected: '修正後テキストF', reason: '理由3', category: '用語', diff_matched: true },
      ],
      diffs: [
        { type: 'equal', text: 'テスト', start: 0, position: null, reason: null },
      ],
    };

    render(<ResultView result={result} />);

    // Switch to comments tab (tab 3) — actual label is "③ コメント一覧"
    const commentsTab = screen.getByRole('tab', { name: /コメント一覧/ });
    await user.click(commentsTab);

    expect(screen.getByText('理由1')).toBeInTheDocument();
    expect(screen.getByText('理由2')).toBeInTheDocument();
    expect(screen.getByText('理由3')).toBeInTheDocument();
    // diff_matched: false should show badge
    expect(screen.getByText(/参考.*AI推定/)).toBeInTheDocument();
  });
});

describe('ResultView — edge cases', () => {
  it('handles correction with missing reason gracefully', async () => {
    const user = userEvent.setup();
    const result = {
      request_id: 'test',
      status: 'success',
      status_reason: null,
      warnings: [],
      corrected_text: '校正済み',
      summary: null,
      corrections: [
        { original: '修正前テキストX', corrected: '修正後テキストY', reason: '', category: '文体', diff_matched: true },
      ],
      diffs: [
        { type: 'equal', text: 'テスト', start: 0, position: null, reason: null },
      ],
    };

    render(<ResultView result={result} />);
    // Should not crash — component checks {c.reason && (...)}
    // Navigate to comments tab to verify the correction renders
    await user.click(screen.getByRole('tab', { name: /コメント一覧/ }));
    expect(screen.getByText('修正前テキストX')).toBeInTheDocument();
    // Empty string reason should not render a reason block
    expect(screen.queryByText(/^理由：/)).not.toBeInTheDocument();
  });

  it('shows corrected text for partial status without diffs', () => {
    const result = {
      request_id: 'test',
      status: 'partial',
      status_reason: 'diff_timeout',
      warnings: [],
      corrected_text: 'タイムアウト時の校正テキスト',
      summary: '差分計算がタイムアウトしました。',
      corrections: [],
      diffs: [],
    };

    render(<ResultView result={result} />);
    expect(screen.getByText('タイムアウト時の校正テキスト')).toBeInTheDocument();
    // Component returns "差分計算に失敗しました" for diff_timeout without diffs
    expect(screen.getByText(/差分計算に失敗しました/)).toBeInTheDocument();
  });

  it('shows error message and retry button for error status', () => {
    const result = {
      request_id: 'test',
      status: 'error',
      status_reason: 'parse_fallback',
      warnings: [],
      corrected_text: '',
      summary: null,
      corrections: [],
      diffs: [],
    };

    const onRetry = () => {};
    render(<ResultView result={result} onRetry={onRetry} />);
    expect(screen.getByText(/校正結果を取得できませんでした/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
  });
});
