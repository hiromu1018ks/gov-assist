import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('./fileExtractor', () => ({
  extractText: vi.fn(),
}));

vi.mock('../../utils/storage', () => ({
  loadSettings: vi.fn(() => ({
    version: 1,
    model: 'kimi-k2.5',
    document_type: 'official',
    options: {},
  })),
  saveSettings: vi.fn(),
}));

import InputArea from './InputArea';
import { loadSettings } from '../../utils/storage';

describe('InputArea', () => {
  const onSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loadSettings).mockReturnValue({
      version: 1,
      model: 'kimi-k2.5',
      document_type: 'official',
      options: {},
    });
  });

  function renderInputArea(props = {}) {
    return render(<InputArea onSubmit={onSubmit} isSubmitting={false} {...props} />);
  }

  // --- Core tests ---

  it('renders security warning message', () => {
    renderInputArea();
    expect(screen.getByText(/外部 AI サービス/)).toBeInTheDocument();
    expect(screen.getByText(/個人情報・機密情報/)).toBeInTheDocument();
  });

  it('renders document type selector with all 4 options', () => {
    renderInputArea();
    const selector = screen.getByLabelText('文書種別');
    expect(selector).toBeInTheDocument();

    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(4);
    expect(options.map((o) => o.value)).toEqual(['email', 'report', 'official', 'other']);
  });

  it('defaults document type to saved setting', () => {
    vi.mocked(loadSettings).mockReturnValue({
      version: 1, model: 'kimi-k2.5', document_type: 'report', options: {},
    });
    renderInputArea();

    expect(screen.getByLabelText('文書種別')).toHaveValue('report');
  });

  it('renders textarea with accessible label', () => {
    renderInputArea();
    expect(screen.getByLabelText('校正テキスト入力')).toBeInTheDocument();
  });

  it('shows character counter with correct count', () => {
    renderInputArea();
    expect(screen.getByText('0 / 8,000 文字')).toBeInTheDocument();
  });

  it('updates character counter when text is typed', async () => {
    const user = userEvent.setup();
    renderInputArea();

    await user.type(screen.getByLabelText('校正テキスト入力'), 'テスト');

    expect(screen.getByText('3 / 8,000 文字')).toBeInTheDocument();
  });

  it('shows error style when character count exceeds 8,000', () => {
    renderInputArea();

    const textarea = screen.getByLabelText('校正テキスト入力');
    fireEvent.change(textarea, { target: { value: 'x'.repeat(8001) } });

    const counter = screen.getByText('8,001 / 8,000 文字');
    expect(counter.className).toContain('char-counter--over');
  });

  it('disables submit button when text is empty', () => {
    renderInputArea();
    expect(screen.getByRole('button', { name: '校正実行' })).toBeDisabled();
  });

  it('disables submit button when text exceeds 8,000 characters', () => {
    renderInputArea();

    const textarea = screen.getByLabelText('校正テキスト入力');
    fireEvent.change(textarea, { target: { value: 'x'.repeat(8001) } });

    expect(screen.getByRole('button', { name: '校正実行' })).toBeDisabled();
  });

  it('enables submit button with valid text', async () => {
    const user = userEvent.setup();
    renderInputArea();

    await user.type(screen.getByLabelText('校正テキスト入力'), '校正してください。');

    expect(screen.getByRole('button', { name: '校正実行' })).not.toBeDisabled();
  });

  it('calls onSubmit with text and documentType on submit', async () => {
    const user = userEvent.setup();
    renderInputArea();

    await user.type(screen.getByLabelText('校正テキスト入力'), 'テスト文書');
    await user.click(screen.getByRole('button', { name: '校正実行' }));

    expect(onSubmit).toHaveBeenCalledWith('テスト文書', 'official');
  });

  it('disables textarea when isSubmitting is true', () => {
    renderInputArea({ isSubmitting: true });
    expect(screen.getByLabelText('校正テキスト入力')).toBeDisabled();
  });

  it('disables submit button when isSubmitting is true', () => {
    renderInputArea({ isSubmitting: true });
    expect(screen.getByRole('button', { name: '校正実行' })).toBeDisabled();
  });
});
