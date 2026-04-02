// HTTP client with JWT token caching and auto-refresh

let accessToken = null;
let refreshToken = null;
let currentUser = null;

const BASE_URL = process.env.TREMLY_API_URL || 'http://localhost:8000/api/v1/';

function url(path) {
  // Ensure no double slashes between base and path
  const base = BASE_URL.endsWith('/') ? BASE_URL : BASE_URL + '/';
  const p = path.startsWith('/') ? path.slice(1) : path;
  return base + p;
}

async function request(method, path, body = null, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (accessToken && !opts.noAuth) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const fetchOpts = { method, headers };
  if (body !== null) {
    fetchOpts.body = JSON.stringify(body);
  }
  if (opts.timeout) {
    fetchOpts.signal = AbortSignal.timeout(opts.timeout);
  }

  let res = await fetch(url(path), fetchOpts);

  // Auto-refresh on 401
  if (res.status === 401 && refreshToken && !opts.noAuth && !opts.isRefresh) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${accessToken}`;
      fetchOpts.headers = headers;
      res = await fetch(url(path), fetchOpts);
    }
  }

  return res;
}

async function tryRefresh() {
  try {
    const res = await request('POST', 'auth/token/refresh/', { refresh: refreshToken }, { noAuth: true, isRefresh: true });
    if (res.ok) {
      const data = await res.json();
      accessToken = data.access;
      if (data.refresh) refreshToken = data.refresh;
      return true;
    }
  } catch (e) {
    // refresh failed
  }
  accessToken = null;
  refreshToken = null;
  currentUser = null;
  return false;
}

export async function login(email, password) {
  const res = await request('POST', 'auth/login/', { email, password }, { noAuth: true });
  const status = res.status;
  if (!res.ok) {
    const error = await res.text();
    return { ok: false, error, status };
  }
  const data = await res.json();
  accessToken = data.access;
  refreshToken = data.refresh;
  currentUser = data.user || null;
  return { ok: true, data, status };
}

export async function apiGet(path, opts = {}) {
  const res = await request('GET', path, null, opts);
  const status = res.status;
  try {
    const data = await res.json();
    return res.ok ? { ok: true, data, status } : { ok: false, error: data, status };
  } catch {
    const text = await res.text().catch(() => '');
    return { ok: false, error: text || res.statusText, status };
  }
}

export async function apiPost(path, body = {}, opts = {}) {
  const res = await request('POST', path, body, opts);
  const status = res.status;
  try {
    const data = await res.json();
    return res.ok ? { ok: true, data, status } : { ok: false, error: data, status };
  } catch {
    const text = await res.text().catch(() => '');
    return res.ok
      ? { ok: true, data: text || null, status }
      : { ok: false, error: text || res.statusText, status };
  }
}

export async function apiPatch(path, body = {}, opts = {}) {
  const res = await request('PATCH', path, body, opts);
  const status = res.status;
  try {
    const data = await res.json();
    return res.ok ? { ok: true, data, status } : { ok: false, error: data, status };
  } catch {
    const text = await res.text().catch(() => '');
    return res.ok
      ? { ok: true, data: text || null, status }
      : { ok: false, error: text || res.statusText, status };
  }
}

export async function apiDelete(path, opts = {}) {
  const res = await request('DELETE', path, null, opts);
  const status = res.status;
  if (status === 204) return { ok: true, data: null, status };
  try {
    const data = await res.json();
    return res.ok ? { ok: true, data, status } : { ok: false, error: data, status };
  } catch {
    return res.ok ? { ok: true, data: null, status } : { ok: false, error: res.statusText, status };
  }
}

export async function apiPostFormData(path, formData, opts = {}) {
  const headers = {};
  if (accessToken && !opts.noAuth) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  const fetchOpts = { method: 'POST', headers, body: formData };
  if (opts.timeout) {
    fetchOpts.signal = AbortSignal.timeout(opts.timeout);
  }
  let res = await fetch(url(path), fetchOpts);

  if (res.status === 401 && refreshToken && !opts.noAuth) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${accessToken}`;
      fetchOpts.headers = headers;
      res = await fetch(url(path), fetchOpts);
    }
  }

  const status = res.status;
  try {
    const data = await res.json();
    return res.ok ? { ok: true, data, status } : { ok: false, error: data, status };
  } catch {
    const text = await res.text().catch(() => '');
    return res.ok
      ? { ok: true, data: text || null, status }
      : { ok: false, error: text || res.statusText, status };
  }
}

export function isAuthenticated() {
  return !!accessToken;
}

export function getCurrentUser() {
  return currentUser;
}

export function getTokens() {
  return { access: accessToken, refresh: refreshToken };
}
