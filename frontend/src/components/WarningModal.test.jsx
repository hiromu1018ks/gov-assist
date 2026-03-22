import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import WarningModal from './WarningModal';

describe('WarningModal', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('shows warning on first visit', () => {
    render(<WarningModal />);

    expect(screen.getByText('ご確認ください')).toBeInTheDocument();
    expect(screen.getByText(/localhost 限定/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '確認しました' })).toBeInTheDocument();
  });

  it('hides modal after clicking confirm', async () => {
    const user = userEvent.setup();
    render(<WarningModal />);

    await user.click(screen.getByRole('button', { name: '確認しました' }));

    expect(screen.queryByText('ご確認ください')).not.toBeInTheDocument();
    expect(localStorage.getItem('govassist_warning_accepted')).toBe('true');
  });

  it('does not show modal after previously accepted', () => {
    localStorage.setItem('govassist_warning_accepted', 'true');
    render(<WarningModal />);

    expect(screen.queryByText('ご確認ください')).not.toBeInTheDocument();
  });
});
