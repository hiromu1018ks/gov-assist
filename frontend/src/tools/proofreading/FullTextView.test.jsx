import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import FullTextView from './FullTextView';

describe('FullTextView', () => {
  it('renders text content', () => {
    render(<FullTextView text="テスト文書です。" label="校正後" />);
    expect(screen.getByText('テスト文書です。')).toBeInTheDocument();
  });

  it('renders empty string without crashing', () => {
    const { container } = render(<FullTextView text="" label="校正後" />);
    expect(container.innerHTML).not.toBe('');
  });

  it('applies full-text-view class to container', () => {
    const { container } = render(<FullTextView text="内容" label="校正前" />);
    expect(container.firstChild).toHaveClass('full-text-view');
  });

  it('has role="region" and aria-label for accessibility', () => {
    render(<FullTextView text="内容" label="校正後" />);
    const region = screen.getByRole('region', { name: '校正後' });
    expect(region).toBeInTheDocument();
  });

  it('preserves whitespace with pre-wrap', () => {
    const { container } = render(<FullTextView text="1行目\n2行目" label="テスト" />);
    const el = container.querySelector('.full-text-view');
    expect(el).toHaveStyle({ 'white-space': 'pre-wrap' });
  });
});
