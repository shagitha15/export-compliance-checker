const TOKEN_KEY = 'export_compliance_access_token_v1';
const REFRESH_KEY = 'export_compliance_refresh_token_v1';
const EXPIRES_AT_KEY = 'export_compliance_expires_at_v1';
const ACTIVE_ORG_KEY = 'export_compliance_active_org_v1';

function readItem(key: string): string | null {
  try {
    const localVal = localStorage.getItem(key);
    if (localVal !== null) {
      return localVal;
    }
  } catch {
    // ignore storage errors
  }
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function getPreferredStorage(rememberMe?: boolean): Storage | null {
  if (rememberMe === true) {
    return typeof localStorage !== 'undefined' ? localStorage : null;
  }
  if (rememberMe === false) {
    return typeof sessionStorage !== 'undefined' ? sessionStorage : null;
  }
  try {
    if (typeof sessionStorage !== 'undefined' && sessionStorage.getItem(TOKEN_KEY)) {
      return sessionStorage;
    }
  } catch {
    // ignore
  }
  return typeof localStorage !== 'undefined' ? localStorage : null;
}

function clearStorageKeys(storage: Storage | null | undefined, keys: string[]): void {
  if (!storage) return;
  try {
    keys.forEach((k) => storage.removeItem(k));
  } catch {
    // ignore
  }
}

type SessionExpiredListener = (reason: string) => void;
const sessionExpiredListeners = new Set<SessionExpiredListener>();

export function decodeJwtExpMs(token: string): number | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
    const json = atob(padded);
    const payload = JSON.parse(json) as { exp?: unknown };
    if (typeof payload.exp === 'number' && Number.isFinite(payload.exp)) {
      return payload.exp * 1000;
    }
    return null;
  } catch {
    return null;
  }
}

export const authStorage = {
  getAccessToken(): string | null {
    return readItem(TOKEN_KEY);
  },

  getRefreshToken(): string | null {
    return readItem(REFRESH_KEY);
  },

  getExpiresAtMs(): number | null {
    const raw = readItem(EXPIRES_AT_KEY);
    if (raw) {
      const parsed = Number(raw);
      if (Number.isFinite(parsed) && parsed > 0) {
        return parsed;
      }
    }
    const token = this.getAccessToken();
    return token ? decodeJwtExpMs(token) : null;
  },

  isAccessTokenExpiredOrExpiring(bufferSeconds = 60): boolean {
    const token = this.getAccessToken();
    if (!token) {
      return false;
    }
    const expMs = this.getExpiresAtMs();
    if (expMs === null) {
      return false;
    }
    return Date.now() >= expMs - bufferSeconds * 1000;
  },

  getActiveOrgId(): string | null {
    return readItem(ACTIVE_ORG_KEY);
  },

  setSession(
    accessToken: string,
    refreshToken: string,
    expiresInSeconds?: number,
    rememberMe?: boolean
  ): void {
    const targetStorage = getPreferredStorage(rememberMe);
    const otherStorage =
      targetStorage === (typeof localStorage !== 'undefined' ? localStorage : null)
        ? typeof sessionStorage !== 'undefined'
          ? sessionStorage
          : null
        : typeof localStorage !== 'undefined'
          ? localStorage
          : null;

    clearStorageKeys(otherStorage, [TOKEN_KEY, REFRESH_KEY, EXPIRES_AT_KEY, ACTIVE_ORG_KEY]);

    if (!targetStorage) return;
    try {
      targetStorage.setItem(TOKEN_KEY, accessToken);
      if (refreshToken) {
        targetStorage.setItem(REFRESH_KEY, refreshToken);
      }
      const jwtExpMs = decodeJwtExpMs(accessToken);
      const computedExpMs =
        jwtExpMs ??
        (typeof expiresInSeconds === 'number' && expiresInSeconds > 0
          ? Date.now() + expiresInSeconds * 1000
          : null);
      if (computedExpMs !== null) {
        targetStorage.setItem(EXPIRES_AT_KEY, String(computedExpMs));
      } else {
        targetStorage.removeItem(EXPIRES_AT_KEY);
      }
    } catch {
      // ignore storage errors
    }
  },

  setActiveOrgId(orgId: string | null): void {
    const targetStorage = getPreferredStorage();
    if (!targetStorage) return;
    try {
      if (orgId) {
        targetStorage.setItem(ACTIVE_ORG_KEY, orgId);
      } else {
        targetStorage.removeItem(ACTIVE_ORG_KEY);
      }
    } catch {
      // ignore
    }
  },

  clear(): void {
    const keys = [TOKEN_KEY, REFRESH_KEY, EXPIRES_AT_KEY, ACTIVE_ORG_KEY];
    clearStorageKeys(typeof localStorage !== 'undefined' ? localStorage : null, keys);
    clearStorageKeys(typeof sessionStorage !== 'undefined' ? sessionStorage : null, keys);
  },

  getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {};
    const token = this.getAccessToken();
    const orgId = this.getActiveOrgId();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    if (orgId) {
      headers['X-Organization-ID'] = orgId;
    }
    return headers;
  },

  onSessionExpired(listener: SessionExpiredListener): () => void {
    sessionExpiredListeners.add(listener);
    return () => {
      sessionExpiredListeners.delete(listener);
    };
  },

  notifySessionExpired(reason: string): void {
    sessionExpiredListeners.forEach((listener) => {
      try {
        listener(reason);
      } catch {
        // ignore listener errors
      }
    });
  },
};
