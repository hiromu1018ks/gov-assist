import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('./fileExtractor', () => ({
  extractText: vi.fn(),
}));

vi.mock('../../utils/storage', () => ({
  loadSettings: vi.fn(() => ({
    version: 1,
    model: 'gpt-oss-120b',
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
      model: 'gpt-oss-120b',
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
      version: 1, model: 'gpt-oss-120b', document_type: 'report', options: {},
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

  // --- File Upload and Drag-and-Drop tests ---

  it('clicking file button triggers hidden file input', async () => {
    const user = userEvent.setup();
    renderInputArea();

    const fileButton = screen.getByRole('button', { name: 'ファイルを選択' });
    await user.click(fileButton);

    const fileInput = document.querySelector('input[type="file"]');
    expect(fileInput).toBeInTheDocument();
  });

  it('shows spinner and replaces text after successful file extraction', async () => {
    const { extractText } = await import('./fileExtractor');
    vi.mocked(extractText).mockResolvedValue({ text: 'extracted content from file', error: null });

    const user = userEvent.setup();
    renderInputArea();

    // Set some initial text
    await user.type(screen.getByLabelText('校正テキスト入力'), 'original text');

    // Trigger file input change
    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(['binary'], 'test.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    await user.upload(fileInput, file);

    // Should show extracted text
    await screen.findByDisplayValue('extracted content from file');
    expect(screen.getByText(/test.docx/)).toBeInTheDocument();
  });

  it('shows extraction source banner with filename after extraction', async () => {
    const { extractText } = await import('./fileExtractor');
    vi.mocked(extractText).mockResolvedValue({ text: 'content', error: null });

    const user = userEvent.setup();
    renderInputArea();

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(['binary'], 'report.pdf', { type: 'application/pdf' });
    await user.upload(fileInput, file);

    await screen.findByText(/report.pdf/);
    expect(screen.getByText(/テキストを抽出しました/)).toBeInTheDocument();
  });

  it('restores previous text when cancel button is clicked', async () => {
    const { extractText } = await import('./fileExtractor');
    vi.mocked(extractText).mockResolvedValue({ text: 'new content', error: null });

    const user = userEvent.setup();
    renderInputArea();

    // Set initial text
    await user.type(screen.getByLabelText('校正テキスト入力'), 'original text');

    // Upload file
    const fileInput = document.querySelector('input[type="file"]');
    await user.upload(fileInput, new File(['binary'], 'test.docx'));

    await screen.findByDisplayValue('new content');

    // Click cancel
    await user.click(screen.getByRole('button', { name: '元に戻す' }));

    expect(screen.getByLabelText('校正テキスト入力')).toHaveValue('original text');
    expect(screen.queryByText(/test.docx/)).not.toBeInTheDocument();
  });

  it('shows error message on extraction failure', async () => {
    const { extractText } = await import('./fileExtractor');
    vi.mocked(extractText).mockResolvedValue({
      text: '',
      error: 'テキストを抽出できませんでした。',
    });

    const user = userEvent.setup();
    renderInputArea();

    const fileInput = document.querySelector('input[type="file"]');
    await user.upload(fileInput, new File(['binary'], 'image.pdf'));

    await screen.findByText('テキストを抽出できませんでした。');
  });

  it('clears extraction banner when user types after extraction', async () => {
    const { extractText } = await import('./fileExtractor');
    vi.mocked(extractText).mockResolvedValue({ text: 'extracted', error: null });

    const user = userEvent.setup();
    renderInputArea();

    const fileInput = document.querySelector('input[type="file"]');
    await user.upload(fileInput, new File(['binary'], 'test.docx'));

    await screen.findByText(/test.docx/);

    // User types in textarea — banner should disappear
    await user.type(screen.getByLabelText('校正テキスト入力'), ' edit');

    expect(screen.queryByText(/test.docx/)).not.toBeInTheDocument();
  });

  it('applies drop-zone--active class when dragging files over textarea', () => {
    renderInputArea();
    const wrapper = document.querySelector('.input-area__textarea-wrapper');

    fireEvent.dragEnter(wrapper, {
      dataTransfer: { types: ['Files'] },
    });

    expect(wrapper.classList.contains('drop-zone--active')).toBe(true);
  });

  it('handles file drop and extracts text', async () => {
    const { extractText } = await import('./fileExtractor');
    vi.mocked(extractText).mockResolvedValue({ text: 'dropped content', error: null });

    renderInputArea();
    const wrapper = document.querySelector('.input-area__textarea-wrapper');

    const file = new File(['binary'], 'dropped.pdf');
    fireEvent.drop(wrapper, {
      dataTransfer: { files: [file], types: ['Files'] },
    });

    expect(extractText).toHaveBeenCalledWith(file);
    await screen.findByDisplayValue('dropped content');
  });
});
