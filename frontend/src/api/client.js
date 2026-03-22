import { getToken, removeToken } from '../utils/token';

export class ApiError extends Error {
  constructor(status, data, requestId) {
    super(data?.message || data?.detail || `API エラー: ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    this.requestId = requestId;
  }
}

function generateRequestId() {
  return crypto.randomUUID();
}

async function request(method, path, body) {
  const requestId = generateRequestId();
  const token = getToken();

  const headers = {
    'Content-Type': 'application/json',
    'X-Request-ID': requestId,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const config = {
    method,
    headers,
    ...(body != null ? { body: JSON.stringify(body) } : {}),
  };

  const response = await fetch(path, config);

  if (response.status === 401) {
    removeToken();
    window.dispatchEvent(new CustomEvent('auth:logout'));
  }

  let data;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    throw new ApiError(response.status, data, requestId);
  }

  return data;
}

export async function apiGet(path) {
  return request('GET', path, null);
}

export async function apiPost(path, body) {
  return request('POST', path, body);
}

export async function apiPatch(path, body) {
  return request('PATCH', path, body);
}

export async function apiDelete(path) {
  return request('DELETE', path, null);
}

export async function apiPut(path, body) {
  return request('PUT', path, body);
}

export async function apiPostBlob(path, body) {
  const requestId = generateRequestId();
  const token = getToken();

  const headers = {
    'Content-Type': 'application/json',
    'X-Request-ID': requestId,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const response = await fetch(path, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (response.status === 401) {
    removeToken();
    window.dispatchEvent(new CustomEvent('auth:logout'));
  }

  if (!response.ok) {
    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }
    throw new ApiError(response.status, data, requestId);
  }

  return response.blob();
}
