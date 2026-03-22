import { describe, it, expect, beforeEach } from 'vitest';
import { getToken, setToken, removeToken } from './token';

describe('token', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns null when token is not set', () => {
    expect(getToken()).toBeNull();
  });

  it('stores and retrieves token', () => {
    setToken('test-token-123');
    expect(getToken()).toBe('test-token-123');
  });

  it('removes token', () => {
    setToken('test-token-123');
    removeToken();
    expect(getToken()).toBeNull();
  });
});
