import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HighlightView, CompareView } from './DiffView';

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

  // --- 空配列・null/undefined ---

  it('shows empty message when diffs is empty', () => {
    render(<HighlightView diffs={[]} />);
    expect(screen.getByText('表示する差分がありません。')).toBeInTheDocument();
  });

  it('shows empty message when diffs is null', () => {
    render(<HighlightView diffs={null} />);
    expect(screen.getByText('表示する差分がありません。')).toBeInTheDocument();
  });

  it('shows empty message when diffs prop is omitted', () => {
    render(<HighlightView />);
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

describe('CompareView', () => {
  // --- 基本レンダリング ---

  it('renders left panel (before) and right panel (after)', () => {
    const diffs = [
      { type: 'equal', text: '共通', start: 0, position: null, reason: null },
      { type: 'delete', text: '旧', start: 2, position: null, reason: '理由' },
      { type: 'insert', text: '新', start: 2, position: 'after', reason: '理由' },
      { type: 'equal', text: '終わり', start: 3, position: null, reason: null },
    ];
    render(<CompareView diffs={diffs} />);
    expect(screen.getByText(/修正前/)).toBeInTheDocument();
    expect(screen.getByText(/修正後/)).toBeInTheDocument();
  });

  it('left panel contains equal and delete text only', () => {
    const diffs = [
      { type: 'equal', text: 'A', start: 0, position: null, reason: null },
      { type: 'delete', text: 'X', start: 1, position: null, reason: null },
      { type: 'insert', text: 'Y', start: 1, position: 'after', reason: null },
      { type: 'equal', text: 'B', start: 2, position: null, reason: null },
    ];
    render(<CompareView diffs={diffs} />);
    const panels = document.querySelectorAll('.diff-compare__panel');
    expect(panels).toHaveLength(2);
    const leftText = panels[0].textContent;
    expect(leftText).toContain('A');
    expect(leftText).toContain('X');
    expect(leftText).toContain('B');
    expect(leftText).not.toContain('Y');
  });

  it('right panel contains equal and insert text only', () => {
    const diffs = [
      { type: 'equal', text: 'A', start: 0, position: null, reason: null },
      { type: 'delete', text: 'X', start: 1, position: null, reason: null },
      { type: 'insert', text: 'Y', start: 1, position: 'after', reason: null },
      { type: 'equal', text: 'B', start: 2, position: null, reason: null },
    ];
    render(<CompareView diffs={diffs} />);
    const panels = document.querySelectorAll('.diff-compare__panel');
    const rightText = panels[1].textContent;
    expect(rightText).toContain('A');
    expect(rightText).toContain('Y');
    expect(rightText).toContain('B');
    expect(rightText).not.toContain('X');
  });

  // --- diff-delete / diff-insert クラス ---

  it('applies diff-delete class in left panel', () => {
    const diffs = [
      { type: 'delete', text: '削除', start: 0, position: null, reason: null },
    ];
    render(<CompareView diffs={diffs} />);
    const panels = document.querySelectorAll('.diff-compare__panel');
    const el = panels[0].querySelector('.diff-delete');
    expect(el).toBeInTheDocument();
    expect(el.textContent).toBe('削除');
  });

  it('applies diff-insert class in right panel', () => {
    const diffs = [
      { type: 'insert', text: '追加', start: 0, position: 'after', reason: null },
    ];
    render(<CompareView diffs={diffs} />);
    const panels = document.querySelectorAll('.diff-compare__panel');
    const el = panels[1].querySelector('.diff-insert');
    expect(el).toBeInTheDocument();
    expect(el.textContent).toBe('追加');
  });

  // --- ツールチップ ---

  it('adds tooltip to delete block with reason in left panel', () => {
    const diffs = [
      { type: 'delete', text: '誤字', start: 0, position: null, reason: '修正理由' },
    ];
    render(<CompareView diffs={diffs} />);
    const el = document.querySelector('.diff-delete.tooltip');
    expect(el).toHaveAttribute('data-tooltip', '修正理由');
  });

  it('adds tooltip to insert block with reason in right panel', () => {
    const diffs = [
      { type: 'insert', text: '正字', start: 0, position: 'after', reason: '修正理由' },
    ];
    render(<CompareView diffs={diffs} />);
    const el = document.querySelector('.diff-insert.tooltip');
    expect(el).toHaveAttribute('data-tooltip', '修正理由');
  });

  // --- 空配列 ---

  it('shows empty message when diffs is empty', () => {
    render(<CompareView diffs={[]} />);
    expect(screen.getByText('表示する差分がありません。')).toBeInTheDocument();
  });

  // --- スクロール同期（構造確認のみ） ---

  it('has two scrollable panels for scroll sync', () => {
    const diffs = [
      { type: 'equal', text: 'テスト', start: 0, position: null, reason: null },
    ];
    render(<CompareView diffs={diffs} />);
    const panels = document.querySelectorAll('.diff-compare__panel');
    expect(panels).toHaveLength(2);
    expect(panels[0]).toHaveClass('diff-compare__panel--scroll-sync');
    expect(panels[1]).toHaveClass('diff-compare__panel--scroll-sync');
  });
});
