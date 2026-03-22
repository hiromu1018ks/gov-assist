import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '../context/AuthContext';
import ProtectedRoute from './ProtectedRoute';

describe.skip('ProtectedRoute', () => {
  beforeEach(() => {
    useAuth.mockReset();
  });

  function renderRoute(ui) {
    return render(
      <MemoryRouter>
        {ui}
      </MemoryRouter>
    );
  }

  it('shows loading spinner when verifying', () => {
    useAuth.mockReturnValue({ isLoading: true, isAuthenticated: false });

    renderRoute(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('読み込み中...')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('redirects to /login when not authenticated', () => {
    useAuth.mockReturnValue({ isLoading: false, isAuthenticated: false });

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/" element={<ProtectedRoute><div>Protected Content</div></ProtectedRoute>} />
        </Routes>
      </MemoryRouter>
    );

    // Navigate redirects to /login, which renders the login page
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    useAuth.mockReturnValue({ isLoading: false, isAuthenticated: true });

    renderRoute(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });
});
