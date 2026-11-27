-- Government Regulatory Rule Monitoring, Version History & Sync Telemetry Schema
-- Supports live DGFT / CBIC / ICEGATE notifications, immutable audit versions, and approval tracking.

CREATE TABLE IF NOT EXISTS public.regulatory_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    authority TEXT NOT NULL,
    notification_number TEXT NOT NULL DEFAULT 'Statutory Baseline',
    policy_document TEXT NOT NULL,
    para_ref TEXT NOT NULL DEFAULT 'Official Notice',
    rule_title TEXT NOT NULL,
    rule_text TEXT NOT NULL,
    applicable_hs_prefixes JSONB NOT NULL DEFAULT '["ALL"]'::jsonb,
    mandatory_documents JSONB NOT NULL DEFAULT '[]'::jsonb,
    severity TEXT NOT NULL DEFAULT 'MEDIUM',
    published_date TEXT,
    effective_date TEXT,
    last_verified_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_url TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL DEFAULT 'active',
    verification_status TEXT NOT NULL DEFAULT 'seed_baseline',
    validation_notes JSONB NOT NULL DEFAULT '[]'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    content_hash TEXT NOT NULL,
    is_seed_rule BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_regulatory_rules_source ON public.regulatory_rules(source);
CREATE INDEX IF NOT EXISTS idx_regulatory_rules_status ON public.regulatory_rules(lifecycle_status, verification_status);

CREATE TABLE IF NOT EXISTS public.regulatory_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    notification_number TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    published_date TEXT,
    effective_date TEXT,
    source_url TEXT NOT NULL,
    attachment_url TEXT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content_hash TEXT NOT NULL,
    validation_status TEXT NOT NULL DEFAULT 'validated',
    validation_notes JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_export_relevant BOOLEAN NOT NULL DEFAULT TRUE,
    hs_prefixes JSONB NOT NULL DEFAULT '["ALL"]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_reg_notifications_source_date ON public.regulatory_notifications(source, fetched_at DESC);

CREATE TABLE IF NOT EXISTS public.regulatory_rule_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id TEXT NOT NULL UNIQUE,
    rule_id TEXT NOT NULL REFERENCES public.regulatory_rules(rule_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    change_type TEXT NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source TEXT NOT NULL,
    notification_number TEXT NOT NULL,
    source_url TEXT NOT NULL,
    effective_date TEXT,
    summary TEXT NOT NULL,
    previous_state JSONB,
    new_state JSONB
);

CREATE INDEX IF NOT EXISTS idx_reg_rule_versions_rule_id ON public.regulatory_rule_versions(rule_id, changed_at DESC);

CREATE TABLE IF NOT EXISTS public.regulatory_rule_sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sync_id TEXT NOT NULL UNIQUE,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    trigger TEXT NOT NULL,
    overall_status TEXT NOT NULL,
    total_rules INTEGER NOT NULL DEFAULT 0,
    active_rules INTEGER NOT NULL DEFAULT 0,
    new_rules_detected INTEGER NOT NULL DEFAULT 0,
    updated_rules INTEGER NOT NULL DEFAULT 0,
    withdrawn_rules INTEGER NOT NULL DEFAULT 0,
    manual_review_rules INTEGER NOT NULL DEFAULT 0,
    notifications_fetched INTEGER NOT NULL DEFAULT 0,
    source_outcomes JSONB NOT NULL DEFAULT '[]'::jsonb,
    pinecone_upserted INTEGER NOT NULL DEFAULT 0,
    pinecone_deleted INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_reg_sync_logs_completed ON public.regulatory_rule_sync_logs(completed_at DESC);

ALTER TABLE public.regulatory_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.regulatory_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.regulatory_rule_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.regulatory_rule_sync_logs ENABLE ROW LEVEL SECURITY;
