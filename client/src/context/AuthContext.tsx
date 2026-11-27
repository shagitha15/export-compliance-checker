import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  authService,
  ResendConfirmationResponse,
  SessionExpiredError,
  SignupInput,
} from '../services/authService';
import { authStorage } from '../services/authStorage';
import { OrganizationInfo, OrgRole, SignupResponse, UserInfo } from '../types/auth';

interface AuthContextValue {
  user: UserInfo | null;
  organizations: OrganizationInfo[];
  activeOrg: OrganizationInfo | null;
  activeRole: OrgRole | null;
  schemaReady: boolean;
  singleUserMode: boolean;
  loading: boolean;
  canWrite: boolean;
  isAdmin: boolean;
  sessionNotice: string | null;
  clearSessionNotice: () => void;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  signup: (payload: SignupInput) => Promise<SignupResponse>;
  resendConfirmation: (email: string) => Promise<ResendConfirmationResponse>;
  logout: () => Promise<void>;
  selectOrganization: (orgId: string) => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationInfo[]>([]);
  const [activeOrgId, setActiveOrgId] = useState<string | null>(() => authStorage.getActiveOrgId());
  const [schemaReady, setSchemaReady] = useState<boolean>(true);
  const [singleUserMode, setSingleUserMode] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(() => Boolean(authStorage.getAccessToken()));
  const [sessionNotice, setSessionNotice] = useState<string | null>(null);

  const clearSessionNotice = useCallback(() => {
    setSessionNotice(null);
  }, []);

  const syncOrgs = useCallback((orgs: OrganizationInfo[], preferredId?: string | null) => {
    setOrganizations(orgs);
    const stored = preferredId ?? authStorage.getActiveOrgId();
    if (orgs.length > 0) {
      const match = orgs.find((o) => o.id === stored) || orgs[0];
      setActiveOrgId(match.id);
      authStorage.setActiveOrgId(match.id);
    } else {
      setActiveOrgId(null);
      authStorage.setActiveOrgId(null);
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    const token = authStorage.getAccessToken();
    if (!token) {
      setUser(null);
      setOrganizations([]);
      setActiveOrgId(null);
      setLoading(false);
      return;
    }
    try {
      const me = await authService.getMe();
      setUser(me.user);
      setSchemaReady(me.schema_ready);
      setSingleUserMode(Boolean(me.single_user_mode));
      syncOrgs(me.organizations || []);
      setSessionNotice(null);
    } catch (err: unknown) {
      authStorage.clear();
      setUser(null);
      setOrganizations([]);
      setActiveOrgId(null);
      setSingleUserMode(false);
      if (err instanceof SessionExpiredError) {
        setSessionNotice(err.message);
      }
    } finally {
      setLoading(false);
    }
  }, [syncOrgs]);

  useEffect(() => {
    refreshProfile();
    return authStorage.onSessionExpired((reason) => {
      setUser(null);
      setOrganizations([]);
      setActiveOrgId(null);
      setSingleUserMode(false);
      setSessionNotice(reason);
    });
  }, [refreshProfile]);

  const login = async (email: string, password: string, rememberMe = true) => {
    const session = await authService.login(email, password, rememberMe);
    setSessionNotice(null);
    setUser(session.user);
    setSchemaReady(session.schema_ready);
    setSingleUserMode(Boolean(session.single_user_mode));
    syncOrgs(session.organizations || []);
  };

  const signup = async (payload: SignupInput): Promise<SignupResponse> => {
    const res = await authService.signup(payload);
    setSessionNotice(null);
    setSchemaReady(res.schema_ready);
    setSingleUserMode(Boolean(res.single_user_mode ?? res.session?.single_user_mode));
    if (res.session) {
      setUser(res.session.user);
      syncOrgs(res.organizations || res.session.organizations || []);
    }
    return res;
  };

  const resendConfirmation = async (email: string): Promise<ResendConfirmationResponse> => {
    return authService.resendConfirmation(email);
  };

  const logout = async () => {
    setUser(null);
    setOrganizations([]);
    setActiveOrgId(null);
    setSingleUserMode(false);
    setSessionNotice(null);
    await authService.logout();
  };

  const selectOrganization = (orgId: string) => {
    setActiveOrgId(orgId);
    authStorage.setActiveOrgId(orgId);
  };

  const activeOrg = organizations.find((o) => o.id === activeOrgId) || null;
  const activeRole = activeOrg?.role || null;
  const canWrite = singleUserMode || (activeRole !== null && activeRole !== 'Viewer');
  const isAdmin = activeRole === 'Admin';

  return (
    <AuthContext.Provider
      value={{
        user,
        organizations,
        activeOrg,
        activeRole,
        schemaReady,
        singleUserMode,
        loading,
        canWrite,
        isAdmin,
        sessionNotice,
        clearSessionNotice,
        login,
        signup,
        resendConfirmation,
        logout,
        selectOrganization,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return ctx;
}
