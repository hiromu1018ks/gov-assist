import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { getToken, setToken as storeToken, removeToken } from '../utils/token';
import { apiGet } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const mountedRef = useRef(true);

  // Verify stored token on mount
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    apiGet('/api/models')
      .then(() => {
        if (mountedRef.current) setIsAuthenticated(true);
      })
      .catch(() => {
        removeToken();
        if (mountedRef.current) setIsAuthenticated(false);
      })
      .finally(() => {
        if (mountedRef.current) setIsLoading(false);
      });

    return () => { mountedRef.current = false; };
  }, []);

  // Listen for auth:logout events dispatched by API client on 401
  useEffect(() => {
    const handleLogout = () => {
      removeToken();
      setIsAuthenticated(false);
    };
    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, []);

  const login = useCallback(async (newToken) => {
    storeToken(newToken);
    try {
      await apiGet('/api/models');
      setIsAuthenticated(true);
      return true;
    } catch {
      removeToken();
      setIsAuthenticated(false);
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    removeToken();
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
