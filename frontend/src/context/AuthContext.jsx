import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { getToken, setToken as storeToken, removeToken } from '../utils/token';
import { apiGet } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // --- Auth disabled for localhost MVP ---
  // To re-enable: uncomment the useEffect hooks below and remove hardcoded state.
  const [isAuthenticated, setIsAuthenticated] = useState(true);  // Always authenticated
  const [isLoading, setIsLoading] = useState(false);  // No loading needed
  const mountedRef = useRef(true);

  // Verify stored token on mount — disabled for localhost MVP
  // useEffect(() => {
  //   const token = getToken();
  //   if (!token) {
  //     setIsLoading(false);
  //     return;
  //   }
  //
  //   apiGet('/api/models')
  //     .then(() => {
  //       if (mountedRef.current) setIsAuthenticated(true);
  //     })
  //     .catch(() => {
  //       removeToken();
  //       if (mountedRef.current) setIsAuthenticated(false);
  //     })
  //     .finally(() => {
  //       if (mountedRef.current) setIsLoading(false);
  //     });
  //
  //   return () => { mountedRef.current = false; };
  // }, []);

  // Listen for auth:logout events — disabled for localhost MVP
  // useEffect(() => {
  //   const handleLogout = () => {
  //     removeToken();
  //     setIsAuthenticated(false);
  //   };
  //   window.addEventListener('auth:logout', handleLogout);
  //   return () => window.removeEventListener('auth:logout', handleLogout);
  // }, []);

  const login = useCallback(async (newToken) => {
    // --- Auth disabled for localhost MVP ---
    // To re-enable: uncomment below and remove the hardcoded return.
    // storeToken(newToken);
    // try {
    //   await apiGet('/api/models');
    //   setIsAuthenticated(true);
    //   return true;
    // } catch {
    //   removeToken();
    //   setIsAuthenticated(false);
    //   return false;
    // }
    return true;
  }, []);

  const logout = useCallback(() => {
    // --- Auth disabled for localhost MVP ---
    // removeToken();
    // setIsAuthenticated(false);
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
