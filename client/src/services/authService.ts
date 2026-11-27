import { API_ENDPOINTS } from '../constants/apiEndpoints';
import { AuthSessionResponse, OrganizationInfo, SignupResponse, UserInfo } from '../types/auth';
import { authStorage } from './authStorage';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

export class AuthApiError extends Error {
  status?: number;
  code?: string;

  constructor(message: string, status?: number, code?: string) {
    super(message);
    this.name = 'AuthApiError';
    this.status = status;
    this.code = code;
  }
}

export class SessionExpiredError extends AuthApiError {
  constructor(message = 'Your session has expired. Please sign in again.') {
    super(message, 401, 'session_expired');
    this.name = 'SessionExpiredError';
  }
}

export interface ResendConfirmationResponse {
  success: boolean;
  message: string;
}

export interface SignupInput {
  email: string;
  password: string;
  full_name?: string;
  organization_name?: string;
  iec?: string;
  gstin?: string;
}

let inFlightRefresh: Promise<AuthSessionResponse> | null = null;

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs = 8000
): Promise<Response> {
  if (typeof AbortController === 'undefined' || init.signal) {
    return fetch(input, init);
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

function persistSessionPayload(
  data: AuthSessionResponse,
  fallbackRefreshToken?: string,
  rememberMe?: boolean
): void {
  authStorage.setSession(
    data.access_token,
    data.refresh_token || fallbackRefreshToken || '',
    data.expires_in,
    rememberMe
  );
  const currentOrg = authStorage.getActiveOrgId();
  const orgList: OrganizationInfo[] = data.organizations || [];
  if (orgList.length > 0 && (!currentOrg || !orgList.some((o) => o.id === currentOrg))) {
    authStorage.setActiveOrgId(orgList[0].id);
  }
}

async function performRefreshSession(): Promise<AuthSessionResponse> {
  const refreshToken = authStorage.getRefreshToken();
  if (!refreshToken) {
    const msg = 'Your session has expired. Please sign in again.';
    authStorage.clear();
    authStorage.notifySessionExpired(msg);
    throw new SessionExpiredError(msg);
  }

  let res: Response;
  try {
    res = await fetchWithTimeout(`${BASE_URL}${API_ENDPOINTS.AUTH.REFRESH}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch (networkErr: unknown) {
    throw new AuthApiError(
      networkErr instanceof Error
        ? `Unable to refresh session: ${networkErr.message}`
        : 'Unable to reach authentication server to refresh session.',
      0,
      'refresh_network_error'
    );
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data?.access_token) {
    const msg =
      res.status === 401 || res.status === 403 || res.status === 400
        ? 'Your session has expired. Please sign in again.'
        : typeof data?.detail === 'string' && data.detail
          ? data.detail
          : `Session refresh failed (HTTP ${res.status}). Please sign in again.`;
    authStorage.clear();
    authStorage.notifySessionExpired(msg);
    throw new SessionExpiredError(msg);
  }

  const sessionData = data as AuthSessionResponse;
  persistSessionPayload(sessionData, refreshToken);
  return sessionData;
}

/**
 * Single-flight Supabase session refresh. Prevents concurrent refresh_token rotation races.
 */
export async function refreshSessionSingleFlight(): Promise<AuthSessionResponse> {
  if (!inFlightRefresh) {
    inFlightRefresh = performRefreshSession().finally(() => {
      inFlightRefresh = null;
    });
  }
  return inFlightRefresh;
}

/**
 * Returns a valid (and proactively refreshed if expiring within 60s) access token.
 * When `forceRefresh` is true, refreshes once unless another caller already rotated the token.
 */
export async function ensureValidAccessToken(
  forceRefresh = false,
  failedToken?: string | null
): Promise<string | null> {
  const currentToken = authStorage.getAccessToken();

  if (forceRefresh) {
    // If another concurrent request already refreshed the token, reuse the new token directly.
    if (currentToken && failedToken && currentToken !== failedToken && !authStorage.isAccessTokenExpiredOrExpiring(30)) {
      return currentToken;
    }
    const refreshed = await refreshSessionSingleFlight();
    return refreshed.access_token;
  }

  if (!currentToken) {
    return null;
  }

  if (authStorage.isAccessTokenExpiredOrExpiring(60) && authStorage.getRefreshToken()) {
    const refreshed = await refreshSessionSingleFlight();
    return refreshed.access_token;
  }

  return currentToken;
}

function buildHeadersWithAuth(initHeaders?: HeadersInit): Headers {
  const headers = new Headers(initHeaders || {});
  const authHeaders = authStorage.getAuthHeaders();
  Object.entries(authHeaders).forEach(([k, v]) => {
    headers.set(k, v);
  });
  return headers;
}

/**
 * Fetch wrapper that proactively refreshes expiring JWTs and performs one automatic
 * token refresh + retry when the backend responds with HTTP 401.
 */
export async function authenticatedFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  const initialToken = await ensureValidAccessToken(false);

  const firstRes = await fetch(input, {
    ...init,
    headers: buildHeadersWithAuth(init.headers),
  });

  if (firstRes.status !== 401) {
    return firstRes;
  }

  // Only attempt refresh when a refresh token is stored; otherwise surface expired session clearly.
  if (!authStorage.getRefreshToken()) {
    if (initialToken) {
      const msg = 'Your session has expired. Please sign in again.';
      authStorage.clear();
      authStorage.notifySessionExpired(msg);
      throw new SessionExpiredError(msg);
    }
    return firstRes;
  }

  await ensureValidAccessToken(true, initialToken);

  const retryRes = await fetch(input, {
    ...init,
    headers: buildHeadersWithAuth(init.headers),
  });

  if (retryRes.status === 401) {
    const msg = 'Your session has expired or is no longer valid. Please sign in again.';
    authStorage.clear();
    authStorage.notifySessionExpired(msg);
  }

  return retryRes;
}

export const authService = {
  async signup(payload: SignupInput): Promise<SignupResponse> {
    const res = await fetch(`${BASE_URL}${API_ENDPOINTS.AUTH.SIGNUP}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `Signup failed (HTTP ${res.status})`);
    }
    if (data.session?.access_token) {
      authStorage.setSession(
        data.session.access_token,
        data.session.refresh_token || '',
        data.session.expires_in
      );
      if (data.organizations?.length > 0) {
        authStorage.setActiveOrgId(data.organizations[0].id);
      }
    }
    return data as SignupResponse;
  },

  async login(email: string, password: string, rememberMe = true): Promise<AuthSessionResponse> {
    const res = await fetch(`${BASE_URL}${API_ENDPOINTS.AUTH.LOGIN}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail =
        typeof data.detail === 'string' && data.detail
          ? data.detail
          : `Login failed (HTTP ${res.status})`;
      const code =
        typeof data.error_code === 'string'
          ? data.error_code
          : detail.toLowerCase().includes('email not confirmed')
            ? 'email_not_confirmed'
            : undefined;
      throw new AuthApiError(detail, res.status, code);
    }
    const session = data as AuthSessionResponse;
    persistSessionPayload(session, undefined, rememberMe);
    return session;
  },

  async refreshSession(): Promise<AuthSessionResponse> {
    return refreshSessionSingleFlight();
  },

  async resendConfirmation(email: string): Promise<ResendConfirmationResponse> {
    const res = await fetch(`${BASE_URL}${API_ENDPOINTS.AUTH.RESEND_CONFIRMATION}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ email: email.trim() }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail =
        typeof data.detail === 'string' && data.detail
          ? data.detail
          : `Failed to resend confirmation email (HTTP ${res.status})`;
      throw new AuthApiError(
        detail,
        res.status,
        typeof data.error_code === 'string' ? data.error_code : undefined
      );
    }
    return {
      success: Boolean(data.success ?? true),
      message: data.message || 'Confirmation email sent. Please check your inbox.',
    };
  },

  async getMe(): Promise<{
    user: UserInfo;
    organizations: OrganizationInfo[];
    schema_ready: boolean;
    single_user_mode?: boolean;
  }> {
    const initialToken = await ensureValidAccessToken(false);
    const url = `${BASE_URL}${API_ENDPOINTS.AUTH.ME}`;
    let res = await fetchWithTimeout(url, {
      headers: buildHeadersWithAuth({ Accept: 'application/json' }),
    });
    if (res.status === 401 && authStorage.getRefreshToken()) {
      await ensureValidAccessToken(true, initialToken);
      res = await fetchWithTimeout(url, {
        headers: buildHeadersWithAuth({ Accept: 'application/json' }),
      });
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new AuthApiError(
        data.detail || `Session validation failed (HTTP ${res.status})`,
        res.status
      );
    }
    return data;
  },

  async logout(): Promise<void> {
    const token = authStorage.getAccessToken();
    const authHeaders = authStorage.getAuthHeaders();
    authStorage.clear();
    if (!token) {
      return;
    }
    try {
      await fetch(`${BASE_URL}${API_ENDPOINTS.AUTH.LOGOUT}`, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          ...authHeaders,
        },
      });
    } catch {
      // ignore network errors after clearing local session
    }
  },
};
