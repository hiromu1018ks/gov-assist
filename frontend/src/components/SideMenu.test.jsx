import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import SideMenu from './SideMenu';

function renderWithRouter(ui, { initialEntries = ['/'] } = {}) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      {ui}
    </MemoryRouter>
  );
}

describe('SideMenu', () => {
  it('renders all menu items', () => {
    renderWithRouter(<SideMenu />);
    expect(screen.getByText('校正ツール')).toBeInTheDocument();
    expect(screen.getByText('履歴')).toBeInTheDocument();
    expect(screen.getByText('翻訳ツール')).toBeInTheDocument();
    expect(screen.getByText('要約ツール')).toBeInTheDocument();
    expect(screen.getByText('フォーマット')).toBeInTheDocument();
    expect(screen.getByText('設定')).toBeInTheDocument();
  });

  it('disables Phase 2/3 items', () => {
    renderWithRouter(<SideMenu />);
    expect(screen.getByText('翻訳ツール')).toBeDisabled();
    expect(screen.getByText('要約ツール')).toBeDisabled();
    expect(screen.getByText('フォーマット')).toBeDisabled();
  });

  it('does not disable MVP items', () => {
    renderWithRouter(<SideMenu />);
    expect(screen.getByText('校正ツール')).not.toBeDisabled();
    expect(screen.getByText('履歴')).not.toBeDisabled();
    expect(screen.getByText('設定')).not.toBeDisabled();
  });

  it('marks proofreading as active on / route', () => {
    renderWithRouter(<SideMenu />, { initialEntries: ['/'] });
    const btn = screen.getByText('校正ツール').closest('button');
    expect(btn).toHaveClass('sidebar__item--active');
  });

  it('marks settings as active on /settings route', () => {
    renderWithRouter(<SideMenu />, { initialEntries: ['/settings'] });
    const btn = screen.getByText('設定').closest('button');
    expect(btn).toHaveClass('sidebar__item--active');
  });

  it('does not mark proofreading as active on /settings', () => {
    renderWithRouter(<SideMenu />, { initialEntries: ['/settings'] });
    const btn = screen.getByText('校正ツール').closest('button');
    expect(btn).not.toHaveClass('sidebar__item--active');
  });

  it('marks history as active on /history route', () => {
    renderWithRouter(<SideMenu />, { initialEntries: ['/history'] });
    const btn = screen.getByText('履歴').closest('button');
    expect(btn).toHaveClass('sidebar__item--active');
  });

  it('navigates to settings on click', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SideMenu />);
    await user.click(screen.getByText('設定'));
    const btn = screen.getByText('設定').closest('button');
    expect(btn).toHaveClass('sidebar__item--active');
  });
});
