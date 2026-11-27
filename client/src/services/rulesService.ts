import { API_ENDPOINTS } from '../constants/apiEndpoints';
import { authenticatedFetch } from './authService';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

export type RuleSourceType = 'DGFT' | 'CBIC' | 'ICEGATE' | 'RBI' | 'CUSTOMS_SEED';
export type RuleLifecycleStatus = 'active' | 'withdrawn' | 'manual_review' | 'superseded';
export type VerificationStatus = 'verified' | 'manual_review' | 'seed_baseline' | 'withdrawn';
export type OverallSyncStatus = 'success' | 'partial' | 'failed' | 'never_synced';

export interface GovernmentSourceInfo {
  source: 'DGFT' | 'CBIC' | 'ICEGATE';
  label: string;
  portal_url: string;
  last_status: 'success' | 'tls_error' | 'network_error' | 'parse_error' | 'skipped' | 'not_checked';
  last_checked_at: string | null;
  last_error: string | null;
}

export interface SourceSyncOutcome {
  source: 'DGFT' | 'CBIC' | 'ICEGATE';
  source_url: string;
  status: 'success' | 'tls_error' | 'network_error' | 'parse_error' | 'skipped';
  fetched_count: number;
  validated_count: number;
  new_count: number;
  updated_count: number;
  withdrawn_count: number;
  manual_review_count: number;
  error_message: string | null;
  checked_at: string;
}

export interface RuleSyncRunReport {
  sync_id: string;
  started_at: string;
  completed_at: string;
  trigger: 'manual' | 'scheduled' | 'startup';
  overall_status: OverallSyncStatus;
  total_rules: number;
  active_rules: number;
  new_rules_detected: number;
  updated_rules: number;
  withdrawn_rules: number;
  manual_review_rules: number;
  notifications_fetched: number;
  source_outcomes: SourceSyncOutcome[];
  pinecone_upserted: number;
  pinecone_deleted: number;
  message: string;
}

export interface RulesMonitoringOverview {
  last_successful_sync: string | null;
  last_sync_attempt: string | null;
  last_sync_status: OverallSyncStatus;
  last_sync_trigger: string | null;
  scheduler_enabled: boolean;
  scheduler_interval_hours: number;
  next_scheduled_sync: string | null;
  storage_backend: 'supabase' | 'local_registry';
  government_sources: GovernmentSourceInfo[];
  total_rules: number;
  active_rules: number;
  new_rules_detected: number;
  updated_rules: number;
  withdrawn_rules: number;
  manual_review_rules: number;
  recent_sync_runs: RuleSyncRunReport[];
}

export interface GovernmentRuleRecord {
  rule_id: string;
  source: RuleSourceType;
  authority: string;
  notification_number: string;
  policy_document: string;
  para_ref: string;
  rule_title: string;
  rule_text: string;
  applicable_hs_prefixes: string[];
  mandatory_documents: string[];
  severity: string;
  published_date: string | null;
  effective_date: string | null;
  last_verified_at: string | null;
  last_updated_at: string | null;
  source_url: string;
  lifecycle_status: RuleLifecycleStatus;
  verification_status: VerificationStatus;
  validation_notes: string[];
  version: number;
  content_hash: string;
  is_seed_rule: boolean;
}

export interface GovernmentNotificationRecord {
  notification_id: string;
  source: RuleSourceType;
  category: string;
  notification_number: string;
  title: string;
  summary: string;
  published_date: string | null;
  effective_date: string | null;
  source_url: string;
  attachment_url: string | null;
  fetched_at: string;
  last_verified_at: string;
  validation_status: 'validated' | 'manual_review';
  validation_notes: string[];
  is_export_relevant: boolean;
  hs_prefixes: string[];
}

export interface RuleVersionHistoryEntry {
  version_id: string;
  rule_id: string;
  version_number: number;
  change_type: 'new' | 'modified' | 'withdrawn' | 'unchanged' | 'manual_review' | 'approved';
  changed_at: string;
  source: RuleSourceType;
  notification_number: string;
  source_url: string;
  effective_date: string | null;
  summary: string;
}

async function fetchRulesJson<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const response = await authenticatedFetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    },
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload?.detail || payload?.message || `Rules API failed (${response.status})`);
  }
  return payload as T;
}

export const rulesService = {
  getOverview: () => fetchRulesJson<RulesMonitoringOverview>(API_ENDPOINTS.RULES.STATUS),
  listRules: (source?: string) =>
    fetchRulesJson<GovernmentRuleRecord[]>(
      source && source !== 'ALL' ? `${API_ENDPOINTS.RULES.LIST}?source=${encodeURIComponent(source)}` : API_ENDPOINTS.RULES.LIST
    ),
  listNotifications: () =>
    fetchRulesJson<GovernmentNotificationRecord[]>(API_ENDPOINTS.RULES.NOTIFICATIONS),
  listVersions: () =>
    fetchRulesJson<RuleVersionHistoryEntry[]>(API_ENDPOINTS.RULES.VERSIONS),
  syncNow: () =>
    fetchRulesJson<RuleSyncRunReport>(API_ENDPOINTS.RULES.SYNC, { method: 'POST' }),
  approveRule: (ruleId: string) =>
    fetchRulesJson<GovernmentRuleRecord>(API_ENDPOINTS.RULES.APPROVE(ruleId), { method: 'POST' }),
};
