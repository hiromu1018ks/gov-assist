import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

const mockLogin = vi.fn();
const mockLogout = vi.fn();

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    login: mockLogin,
    logout: mockLogout,
    isAuthenticated: false,
    isLoading: false,
  }),
}));

import LoginForm from './LoginForm';

describe('LoginForm', () => {
  beforeEach(() => {
    mockLogin.mockReset();
  });

  function renderForm() {
    return render(
      <MemoryRouter>
        <LoginForm />
      </MemoryRouter>
    );
  }

  it('renders login form with token input and submit button', () => {
    renderForm();

    expect(screen.getByLabelText('アクセストークン')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'ログイン' })).toBeInTheDocument();
  });

  it('shows error when submitting empty token', async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole('button', { name: 'ログイン' }));

    expect(screen.getByText('アクセストークンを入力してください')).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('calls login with trimmed token on submit', async () => {
    mockLogin.mockResolvedValue(true);
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText('アクセストークン'), '  my-token  ');
    await user.click(screen.getByRole('button', { name: 'ログイン' }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('my-token');
    });
  });

  it('shows error message when login fails', async () => {
    mockLogin.mockResolvedValue(false);
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText('アクセストークン'), 'bad-token');
    await user.click(screen.getByRole('button', { name: 'ログイン' }));

    await waitFor(() => {
      expect(screen.getByText('認証トークンが無効です')).toBeInTheDocument();
    });
  });

  it('disables button and shows loading during login', async () => {
    let resolveLogin;
    mockLogin.mockImplementation(() => new Promise((r) => { resolveLogin = r; }));
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText('アクセストークン'), 'my-token');
    await user.click(screen.getByRole('button', { name: 'ログイン' }));

    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByText('認証中...')).toBeInTheDocument();

    await act(async () => { resolveLogin(true); });
  });

  it('clears error when user starts typing', async () => {
    mockLogin.mockResolvedValue(false);
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText('アクセストークン'), 'bad');
    await user.click(screen.getByRole('button', { name: 'ログイン' }));

    await waitFor(() => {
      expect(screen.getByText('認証トークンが無効です')).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText('アクセストークン'), 'x');

    expect(screen.queryByText('認証トークンが無効です')).not.toBeInTheDocument();
  });
});
