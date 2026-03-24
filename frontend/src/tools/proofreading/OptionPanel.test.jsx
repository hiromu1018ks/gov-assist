import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('../../utils/storage', () => ({
  loadSettings: vi.fn(),
  saveSettings: vi.fn(),
}));

import OptionPanel from './OptionPanel';
import { loadSettings } from '../../utils/storage';

describe('OptionPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loadSettings).mockReturnValue({
      version: 1,
      model: 'gpt-oss-120b',
      document_type: 'official',
      options: {
        typo: true,
        keigo: true,
        terminology: true,
        style: true,
        legal: false,
        readability: true,
      },
    });
  });

  function renderPanel(props = {}) {
    return render(<OptionPanel {...props} />);
  }

  it('renders all 6 checkboxes with correct labels', () => {
    renderPanel();

    expect(screen.getByText('誤字・脱字・変換ミスの検出')).toBeInTheDocument();
    expect(screen.getByText('敬語・丁寧語の適切さチェック')).toBeInTheDocument();
    expect(screen.getByText('公文書用語・表現への統一（例：「ください」→「くださいますよう」）')).toBeInTheDocument();
    expect(screen.getByText('文体の統一（です・ます調 / である調）')).toBeInTheDocument();
    expect(screen.getByText('法令・条例用語の確認')).toBeInTheDocument();
    expect(screen.getByText('文章の読みやすさ・論理構成の改善提案')).toBeInTheDocument();
  });

  it('initializes checkbox states from localStorage', () => {
    renderPanel();

    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(6);

    // typo, keigo, terminology, style, readability = true
    expect(checkboxes[0]).toBeChecked(); // typo
    expect(checkboxes[1]).toBeChecked(); // keigo
    expect(checkboxes[2]).toBeChecked(); // terminology
    expect(checkboxes[3]).toBeChecked(); // style
    expect(checkboxes[4]).not.toBeChecked(); // legal (defaults to false)
    expect(checkboxes[5]).toBeChecked(); // readability
  });

  it('toggles checkbox on click', async () => {
    const user = userEvent.setup();
    renderPanel();

    const legalCheckbox = screen.getByRole('checkbox', { name: /法令・条例用語の確認/ });
    expect(legalCheckbox).not.toBeChecked();

    await user.click(legalCheckbox);
    expect(legalCheckbox).toBeChecked();
  });

  it('calls onChange with updated options when checkbox is toggled', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    renderPanel({ onChange });

    await user.click(screen.getByRole('checkbox', { name: /法令・条例用語の確認/ }));

    expect(onChange).toHaveBeenCalledTimes(1);
    const calledOptions = onChange.mock.calls[0][0];
    expect(calledOptions).toEqual({
      typo: true,
      keigo: true,
      terminology: true,
      style: true,
      legal: true,   // was false, now true
      readability: true,
    });
  });

  it('calls onChange with correct options when unchecking a default-true option', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    renderPanel({ onChange });

    await user.click(screen.getByRole('checkbox', { name: /誤字・脱字・変換ミス/ }));

    const calledOptions = onChange.mock.calls[0][0];
    expect(calledOptions.typo).toBe(false);
    expect(calledOptions.keigo).toBe(true); // other options unchanged
  });

  it('disables all checkboxes when disabled prop is true', () => {
    renderPanel({ disabled: true });

    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach((cb) => expect(cb).toBeDisabled());
  });

  it('does not call onChange when disabled', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    renderPanel({ onChange, disabled: true });

    await user.click(screen.getByRole('checkbox', { name: /誤字・脱字・変換ミス/ }));

    expect(onChange).not.toHaveBeenCalled();
  });

  it('renders legend with title', () => {
    renderPanel();
    expect(screen.getByText('校正オプション')).toBeInTheDocument();
  });

  it('works without onChange prop (no crash)', async () => {
    const user = userEvent.setup();
    renderPanel(); // no onChange prop

    // Should not throw
    await user.click(screen.getByRole('checkbox', { name: /誤字・脱字・変換ミス/ }));
  });

  it('initializes from localStorage custom settings', () => {
    vi.mocked(loadSettings).mockReturnValue({
      version: 1,
      model: 'gpt-oss-120b',
      document_type: 'email',
      options: {
        typo: false,
        keigo: false,
        terminology: false,
        style: false,
        legal: false,
        readability: false,
      },
    });

    renderPanel();

    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach((cb) => expect(cb).not.toBeChecked());
  });

  it('handles missing options in localStorage gracefully', () => {
    vi.mocked(loadSettings).mockReturnValue({
      version: 1,
      model: 'gpt-oss-120b',
      document_type: 'official',
      // options is undefined — should not crash
    });

    renderPanel();

    // Should render without crashing; checkboxes default to unchecked when options is undefined
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(6);
  });
});
