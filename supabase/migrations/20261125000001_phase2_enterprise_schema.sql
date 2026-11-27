-- ============================================================================
-- Phase 2: Enterprise SaaS Multi-Tenant Schema, RBAC, RLS & Private Storage
-- Project: Export Customs Documentation Compliance Checker
-- Safe & Idempotent: Preserves existing `public.customs_documents` table & data.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Organizations
CREATE TABLE IF NOT EXISTS public.organizations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    slug text UNIQUE NOT NULL,
    iec text,
    gstin text,
    created_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 2. Organization Memberships & RBAC Roles
CREATE TABLE IF NOT EXISTS public.organization_memberships (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    user_email text,
    role text NOT NULL CHECK (role IN ('Admin', 'Compliance Officer', 'CHA/Broker', 'Viewer')),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'invited', 'suspended')),
    invited_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_memberships_user_id ON public.organization_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_org_memberships_org_id ON public.organization_memberships(organization_id);

-- 3. Preserve existing `customs_documents` rows and add optional tenant scoping
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'customs_documents'
    ) THEN
        ALTER TABLE public.customs_documents
            ADD COLUMN IF NOT EXISTS organization_id uuid REFERENCES public.organizations(id) ON DELETE SET NULL;
        ALTER TABLE public.customs_documents
            ADD COLUMN IF NOT EXISTS created_by uuid REFERENCES auth.users(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_customs_documents_org_id ON public.customs_documents(organization_id);
    END IF;
END $$;

-- 4. Audit Batches
CREATE TABLE IF NOT EXISTS public.audit_batches (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id text UNIQUE NOT NULL,
    organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    created_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
    shipment_ref text,
    batch_status text NOT NULL,
    overall_outcome text CHECK (overall_outcome IN ('PASS', 'FAIL', 'PARTIAL')),
    compliance_score numeric(5,2),
    authenticity_score numeric(5,2),
    total_files integer NOT NULL DEFAULT 0,
    successful_files integer NOT NULL DEFAULT 0,
    failed_files integer NOT NULL DEFAULT 0,
    duplicate_files integer NOT NULL DEFAULT 0,
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    cross_document_validation jsonb,
    government_compliance jsonb,
    fraud_analysis jsonb,
    agent_analysis jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_batches_org_created ON public.audit_batches(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_batches_batch_id ON public.audit_batches(batch_id);

-- 5. Batch Documents (Linked to Private Storage)
CREATE TABLE IF NOT EXISTS public.batch_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id uuid NOT NULL REFERENCES public.audit_batches(id) ON DELETE CASCADE,
    organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    uploaded_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
    original_filename text NOT NULL,
    saved_filename text,
    storage_bucket text NOT NULL DEFAULT 'customs-documents',
    storage_path text,
    sha256_hash text,
    file_size_bytes bigint NOT NULL DEFAULT 0,
    document_type text,
    processing_status text NOT NULL,
    extraction_method text,
    fallback_used boolean NOT NULL DEFAULT false,
    warning text,
    error_code text,
    error_message text,
    extracted_data jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_batch_documents_batch_id ON public.batch_documents(batch_id);
CREATE INDEX IF NOT EXISTS idx_batch_documents_org_id ON public.batch_documents(organization_id);

-- 6. Audit Findings
CREATE TABLE IF NOT EXISTS public.audit_findings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id uuid NOT NULL REFERENCES public.audit_batches(id) ON DELETE CASCADE,
    organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    stage text NOT NULL,
    rule_id text NOT NULL,
    rule_name text NOT NULL,
    authority text,
    document_type text,
    field_name text,
    status text NOT NULL,
    severity text,
    expected_value text,
    observed_value jsonb,
    message text,
    remediation text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_findings_batch_id ON public.audit_findings(batch_id);
CREATE INDEX IF NOT EXISTS idx_audit_findings_org_id ON public.audit_findings(organization_id);

-- 7. Compliance Reports
CREATE TABLE IF NOT EXISTS public.compliance_reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id uuid NOT NULL REFERENCES public.audit_batches(id) ON DELETE CASCADE,
    organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    generated_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
    report_filename text NOT NULL,
    storage_bucket text NOT NULL DEFAULT 'customs-documents',
    storage_path text NOT NULL,
    file_size_bytes bigint NOT NULL DEFAULT 0,
    overall_outcome text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_compliance_reports_batch_id ON public.compliance_reports(batch_id);
CREATE INDEX IF NOT EXISTS idx_compliance_reports_org_id ON public.compliance_reports(organization_id);

-- ============================================================================
-- 8. Helper Function & Strict Organization-Level Row Level Security (RLS)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.user_has_org_role(
    target_org_id uuid,
    allowed_roles text[] DEFAULT ARRAY['Admin', 'Compliance Officer', 'CHA/Broker', 'Viewer']
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.organization_memberships m
        WHERE m.organization_id = target_org_id
          AND m.user_id = auth.uid()
          AND m.status = 'active'
          AND m.role = ANY(allowed_roles)
    );
$$;

ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organization_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.batch_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.compliance_reports ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'customs_documents'
    ) THEN
        ALTER TABLE public.customs_documents ENABLE ROW LEVEL SECURITY;
    END IF;
END $$;

-- Organizations Policies
DROP POLICY IF EXISTS org_select_member ON public.organizations;
CREATE POLICY org_select_member ON public.organizations
    FOR SELECT USING (
        created_by = auth.uid() OR public.user_has_org_role(id)
    );

DROP POLICY IF EXISTS org_insert_authenticated ON public.organizations;
CREATE POLICY org_insert_authenticated ON public.organizations
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL AND created_by = auth.uid());

DROP POLICY IF EXISTS org_update_admin ON public.organizations;
CREATE POLICY org_update_admin ON public.organizations
    FOR UPDATE USING (public.user_has_org_role(id, ARRAY['Admin']));

-- Membership Policies
DROP POLICY IF EXISTS membership_select_org ON public.organization_memberships;
CREATE POLICY membership_select_org ON public.organization_memberships
    FOR SELECT USING (
        user_id = auth.uid() OR public.user_has_org_role(organization_id)
    );

DROP POLICY IF EXISTS membership_insert_admin ON public.organization_memberships;
CREATE POLICY membership_insert_admin ON public.organization_memberships
    FOR INSERT WITH CHECK (
        public.user_has_org_role(organization_id, ARRAY['Admin'])
    );

DROP POLICY IF EXISTS membership_update_admin ON public.organization_memberships;
CREATE POLICY membership_update_admin ON public.organization_memberships
    FOR UPDATE USING (
        public.user_has_org_role(organization_id, ARRAY['Admin'])
    );

DROP POLICY IF EXISTS membership_delete_admin ON public.organization_memberships;
CREATE POLICY membership_delete_admin ON public.organization_memberships
    FOR DELETE USING (
        public.user_has_org_role(organization_id, ARRAY['Admin'])
    );

-- Audit Batches Policies
DROP POLICY IF EXISTS batches_select_org ON public.audit_batches;
CREATE POLICY batches_select_org ON public.audit_batches
    FOR SELECT USING (public.user_has_org_role(organization_id));

DROP POLICY IF EXISTS batches_insert_writer ON public.audit_batches;
CREATE POLICY batches_insert_writer ON public.audit_batches
    FOR INSERT WITH CHECK (
        public.user_has_org_role(organization_id, ARRAY['Admin', 'Compliance Officer', 'CHA/Broker'])
    );

DROP POLICY IF EXISTS batches_update_writer ON public.audit_batches;
CREATE POLICY batches_update_writer ON public.audit_batches
    FOR UPDATE USING (
        public.user_has_org_role(organization_id, ARRAY['Admin', 'Compliance Officer', 'CHA/Broker'])
    );

-- Batch Documents Policies
DROP POLICY IF EXISTS docs_select_org ON public.batch_documents;
CREATE POLICY docs_select_org ON public.batch_documents
    FOR SELECT USING (public.user_has_org_role(organization_id));

DROP POLICY IF EXISTS docs_insert_writer ON public.batch_documents;
CREATE POLICY docs_insert_writer ON public.batch_documents
    FOR INSERT WITH CHECK (
        public.user_has_org_role(organization_id, ARRAY['Admin', 'Compliance Officer', 'CHA/Broker'])
    );

-- Audit Findings Policies
DROP POLICY IF EXISTS findings_select_org ON public.audit_findings;
CREATE POLICY findings_select_org ON public.audit_findings
    FOR SELECT USING (public.user_has_org_role(organization_id));

DROP POLICY IF EXISTS findings_insert_writer ON public.audit_findings;
CREATE POLICY findings_insert_writer ON public.audit_findings
    FOR INSERT WITH CHECK (
        public.user_has_org_role(organization_id, ARRAY['Admin', 'Compliance Officer', 'CHA/Broker'])
    );

-- Compliance Reports Policies
DROP POLICY IF EXISTS reports_select_org ON public.compliance_reports;
CREATE POLICY reports_select_org ON public.compliance_reports
    FOR SELECT USING (public.user_has_org_role(organization_id));

DROP POLICY IF EXISTS reports_insert_writer ON public.compliance_reports;
CREATE POLICY reports_insert_writer ON public.compliance_reports
    FOR INSERT WITH CHECK (
        public.user_has_org_role(organization_id, ARRAY['Admin', 'Compliance Officer', 'CHA/Broker'])
    );

-- Legacy customs_documents RLS
DROP POLICY IF EXISTS legacy_docs_select_org ON public.customs_documents;
CREATE POLICY legacy_docs_select_org ON public.customs_documents
    FOR SELECT USING (
        organization_id IS NOT NULL AND public.user_has_org_role(organization_id)
    );

-- ============================================================================
-- 9. Private Storage Bucket & Organization-Scoped Object Policies
-- ============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'customs-documents',
    'customs-documents',
    false,
    26214400,
    ARRAY['application/pdf']
)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    file_size_limit = 26214400;

DROP POLICY IF EXISTS storage_select_org ON storage.objects;
CREATE POLICY storage_select_org ON storage.objects
    FOR SELECT USING (
        bucket_id = 'customs-documents'
        AND (storage.foldername(name))[1] ~* '^[0-9a-f-]{36}$'
        AND public.user_has_org_role(((storage.foldername(name))[1])::uuid)
    );

DROP POLICY IF EXISTS storage_insert_org ON storage.objects;
CREATE POLICY storage_insert_org ON storage.objects
    FOR INSERT WITH CHECK (
        bucket_id = 'customs-documents'
        AND (storage.foldername(name))[1] ~* '^[0-9a-f-]{36}$'
        AND public.user_has_org_role(
            ((storage.foldername(name))[1])::uuid,
            ARRAY['Admin', 'Compliance Officer', 'CHA/Broker']
        )
    );
