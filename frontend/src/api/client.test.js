import { describe, it, expect, beforeEach, vi } from 'vitest';
import { apiGet, apiPost, ApiError } from './client';
import { getToken, setToken } from '../utils/token';

describe('API client', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  function mockFetchJson(body, { status = 200 } = {}) {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: status >= 200 && status < 300,
      status,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve(body),
    });
  }

  it('sends Authorization header with stored token', async () => {
    setToken('my-token');
    mockFetchJson({ models: [] });

    await apiGet('/api/models');

    expect(fetch).toHaveBeenCalledWith('/api/models', expect.objectContaining({
      headers: expect.objectContaining({
        Authorization: 'Bearer my-token',
      }),
    }));
  });

  it('sends X-Request-ID header with UUID format', async () => {
    setToken('my-token');
    mockFetchJson({ models: [] });

    await apiGet('/api/models');

    const requestId = fetch.mock.calls[0][1].headers['X-Request-ID'];
    expect(requestId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    );
  });

  it('does not send Authorization header when no token', async () => {
    mockFetchJson({ models: [] });

    await apiGet('/api/models');

    const headers = fetch.mock.calls[0][1].headers;
    expect(headers).not.toHaveProperty('Authorization');
  });

  it('returns parsed JSON on success', async () => {
    mockFetchJson({ models: [{ model_id: 'kimi-k2.5' }] });

    const data = await apiGet('/api/models');

    expect(data).toEqual({ models: [{ model_id: 'kimi-k2.5' }] });
  });

  it('throws ApiError on 401 and clears token', async () => {
    setToken('bad-token');
    mockFetchJson({ detail: '認証トークンが一致しません' }, { status: 401 });

    await expect(apiGet('/api/models')).rejects.toThrow(ApiError);
    expect(getToken()).toBeNull();
  });

  it('dispatches auth:logout event on 401', async () => {
    setToken('bad-token');
    mockFetchJson({ detail: '認証トークンが一致しません' }, { status: 401 });

    const listener = vi.fn();
    window.addEventListener('auth:logout', listener);

    try { await apiGet('/api/models'); } catch {}

    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener('auth:logout', listener);
  });

  it('throws ApiError on 500 without clearing token', async () => {
    setToken('my-token');
    mockFetchJson({ detail: 'Internal Server Error' }, { status: 500 });

    await expect(apiGet('/api/models')).rejects.toThrow(ApiError);
    expect(getToken()).toBe('my-token');
  });

  it('ApiError contains status, data, and requestId', async () => {
    setToken('my-token');
    mockFetchJson({ detail: 'Not Found' }, { status: 404 });

    try {
      await apiGet('/api/not-found');
      expect.unreachable('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect(e.status).toBe(404);
      expect(e.data).toEqual({ detail: 'Not Found' });
      expect(e.requestId).toMatch(/^[0-9a-f-]+$/);
    }
  });

  it('sends JSON body with POST', async () => {
    setToken('my-token');
    mockFetchJson({ result: 'ok' });

    await apiPost('/api/proofread', { text: 'test' });

    expect(fetch).toHaveBeenCalledWith('/api/proofread', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ text: 'test' }),
    }));
  });

  it('does not send body with GET', async () => {
    setToken('my-token');
    mockFetchJson({ models: [] });

    await apiGet('/api/models');

    expect(fetch.mock.calls[0][1].body).toBeUndefined();
  });
});
