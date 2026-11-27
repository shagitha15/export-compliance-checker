export type OrgRole = 'Admin' | 'Compliance Officer' | 'CHA/Broker' | 'Viewer';

export interface UserInfo {
  user_id: string;
  email: string;
  full_name?: string | null;
}

export interface OrganizationInfo {
  id: string;
  name: string;
  slug?: string | null;
  iec?: string | null;
  gstin?: string | null;
  role: OrgRole;
  status: string;
}

export interface AuthSessionResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserInfo;
  organizations: OrganizationInfo[];
  schema_ready: boolean;
  single_user_mode?: boolean;
  message?: string | null;
}

export interface SignupResponse {
  user: UserInfo;
  email_confirmation_required: boolean;
  session?: AuthSessionResponse | null;
  organizations: OrganizationInfo[];
  schema_ready: boolean;
  single_user_mode?: boolean;
  message: string;
}

export interface OrgMemberInfo {
  id?: string | null;
  organization_id: string;
  user_id: string;
  user_email?: string | null;
  role: OrgRole;
  status: string;
  created_at?: string | null;
}
