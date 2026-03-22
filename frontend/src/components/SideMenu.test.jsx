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
    expect(screen.getByText('AI 文書校正')).toBeInTheDocument();
    expect(screen.getByText('文書要約・翻訳')).toBeInTheDocument();
    expect(screen.getByText('PDF 加工')).toBeInTheDocument();
    expect(screen.getByText('AI チャット')).toBeInTheDocument();
    expect(screen.getByText('設定')).toBeInTheDocument();
  });

  it('disables Phase 2/3 items', () => {
    renderWithRouter(<SideMenu />);
    expect(screen.getByText('文書要約・翻訳')).toBeDisabled();
    expect(screen.getByText('PDF 加工')).toBeDisabled();
    expect(screen.getByText('AI チャット')).toBeDisabled();
  });

  it('does not disable MVP items', () => {
    renderWithRouter(<SideMenu />);
    expect(screen.getByText('AI 文書校正')).not.toBeDisabled();
    expect(screen.getByText('設定')).not.toBeDisabled();
  });

  it('marks proofreading as active on / route', () => {
    renderWithRouter(<SideMenu />, { initialEntries: ['/'] });
    const btn = screen.getByText('AI 文書校正').closest('button');
    expect(btn).toHaveClass('sidebar__item--active');
  });

  it('marks settings as active on /settings route', () => {
    renderWithRouter(<SideMenu />, { initialEntries: ['/settings'] });
    const btn = screen.getByText('設定').closest('button');
    expect(btn).toHaveClass('sidebar__item--active');
  });

  it('does not mark proofreading as active on /settings', () => {
    renderWithRouter(<SideMenu />, { initialEntries: ['/settings'] });
    const btn = screen.getByText('AI 文書校正').closest('button');
    expect(btn).not.toHaveClass('sidebar__item--active');
  });

  it('navigates to settings on click', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SideMenu />);
    await user.click(screen.getByText('設定'));
    const btn = screen.getByText('設定').closest('button');
    expect(btn).toHaveClass('sidebar__item--active');
  });
});
