import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HighlightView } from './DiffView';

describe('HighlightView', () => {
  // --- 基本レンダリング ---

  it('renders equal text as plain text', () => {
    const diffs = [
      { type: 'equal', text: 'こんにちは。', start: 0, position: null, reason: null },
    ];
    render(<HighlightView diffs={diffs} />);
    expect(screen.getByText('こんにちは。')).toBeInTheDocument();
  });

  it('renders delete text with diff-delete class', () => {
    const diffs = [
      { type: 'delete', text: '旧', start: 0, position: null, reason: null },
    ];
    render(<HighlightView diffs={diffs} />);
    const el = screen.getByText('旧');
    expect(el).toHaveClass('diff-delete');
  });

  it('renders insert text with diff-insert class', () => {
    const diffs = [
      { type: 'insert', text: '新', start: 0, position: null, reason: null },
    ];
    render(<HighlightView diffs={diffs} />);
    const el = screen.getByText('新');
    expect(el).toHaveClass('diff-insert');
  });

  // --- 混合 diff ---

  it('renders mixed diffs in array order (not start order)', () => {
    const diffs = [
      { type: 'equal', text: 'A', start: 10, position: null, reason: null },
      { type: 'delete', text: 'X', start: 5, position: null, reason: null },
      { type: 'insert', text: 'Y', start: 5, position: 'after', reason: null },
      { type: 'equal', text: 'B', start: 20, position: null, reason: null },
    ];
    render(<HighlightView diffs={diffs} />);
    const container = document.querySelector('.diff-highlight');
    expect(container.textContent).toBe('AXYB');
  });

  // --- ツールチップ（reason） ---

  it('adds tooltip class and data-tooltip when reason is present', () => {
    const diffs = [
      { type: 'delete', text: '誤字', start: 0, position: null, reason: '誤字を修正' },
    ];
    render(<HighlightView diffs={diffs} />);
    const el = screen.getByText('誤字');
    expect(el).toHaveClass('tooltip');
    expect(el).toHaveAttribute('data-tooltip', '誤字を修正');
  });

  it('does not add tooltip class when reason is null', () => {
    const diffs = [
      { type: 'delete', text: '旧', start: 0, position: null, reason: null },
    ];
    render(<HighlightView diffs={diffs} />);
    const el = screen.getByText('旧');
    expect(el).not.toHaveClass('tooltip');
    expect(el).not.toHaveAttribute('data-tooltip');
  });

  it('adds tooltip to insert block with reason', () => {
    const diffs = [
      { type: 'insert', text: '正', start: 0, position: 'after', reason: '正しい表記' },
    ];
    render(<HighlightView diffs={diffs} />);
    const el = screen.getByText('正');
    expect(el).toHaveClass('tooltip');
    expect(el).toHaveAttribute('data-tooltip', '正しい表記');
  });

  // --- 空配列 ---

  it('shows empty message when diffs is empty', () => {
    render(<HighlightView diffs={[]} />);
    expect(screen.getByText('表示する差分がありません。')).toBeInTheDocument();
  });

  // --- 改行保持 ---

  it('preserves line breaks in diff text', () => {
    const diffs = [
      { type: 'equal', text: '1行目\n2行目', start: 0, position: null, reason: null },
    ];
    const { container } = render(<HighlightView diffs={diffs} />);
    const el = container.querySelector('.diff-highlight > span');
    expect(el.textContent).toBe('1行目\n2行目');
  });

  // --- 連続する same-type ブロック ---

  it('renders consecutive same-type blocks as separate spans', () => {
    const diffs = [
      { type: 'equal', text: '前半', start: 0, position: null, reason: null },
      { type: 'equal', text: '後半', start: 2, position: null, reason: null },
    ];
    const { container } = render(<HighlightView diffs={diffs} />);
    const spans = container.querySelectorAll('.diff-highlight > span');
    expect(spans).toHaveLength(2);
    expect(container.textContent).toBe('前半後半');
  });
});
