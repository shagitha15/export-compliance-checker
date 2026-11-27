export const API_ENDPOINTS = {
  HEALTH: '/health',
  AUTH: {
    SIGNUP: '/auth/signup',
    LOGIN: '/auth/login',
    RESEND_CONFIRMATION: '/auth/resend-confirmation',
    REFRESH: '/auth/refresh',
    LOGOUT: '/auth/logout',
    ME: '/auth/me',
  },
  ORGS: {
    LIST: '/orgs',
    CREATE: '/orgs',
    MEMBERS: (orgId: string) => `/orgs/${encodeURIComponent(orgId)}/members`,
    MEMBER: (orgId: string, userId: string) =>
      `/orgs/${encodeURIComponent(orgId)}/members/${encodeURIComponent(userId)}`,
  },
  AUDITS: {
    LIST: '/audits',
    DETAIL: (batchId: string) => `/audits/${encodeURIComponent(batchId)}`,
    DOCUMENT_SIGNED_URL: (batchId: string, docId: string) =>
      `/audits/${encodeURIComponent(batchId)}/documents/${encodeURIComponent(docId)}/signed-url`,
    REPORT_SIGNED_URL: (batchId: string) =>
      `/audits/${encodeURIComponent(batchId)}/report/signed-url`,
  },
  DOCUMENTS: {
    UPLOAD: '/documents/upload',
    BATCH_UPLOAD: '/documents/batch-upload',
    BATCH_UPLOAD_ALIAS: '/documents/batch',
    EXTRACT: '/documents/extract',
    EXTRACT_SAVED: (filename: string) => `/documents/extract-saved/${encodeURIComponent(filename)}`,
  },
  COMPLIANCE: {
    VALIDATE_DIRECT: '/compliance/validate',
    VALIDATE_STORED: '/compliance/validate-stored',
    VERIFY_RULES: '/compliance/verify-rules',
    AUDIT: '/compliance/audit',
    PDF_REPORT: '/compliance/report/pdf',
  },
  FRAUD: {
    INSPECT: '/fraud/inspect',
    INSPECT_FILE: '/fraud/inspect-file',
  },
  AGENT: {
    ANALYZE: '/agent/analyze',
  },
  RULES: {
    STATUS: '/rules/status',
    LIST: '/rules',
    NOTIFICATIONS: '/rules/notifications',
    VERSIONS: '/rules/versions',
    SYNC: '/rules/sync',
    APPROVE: (ruleId: string) => `/rules/${encodeURIComponent(ruleId)}/approve`,
    WITHDRAW: (ruleId: string) => `/rules/${encodeURIComponent(ruleId)}/withdraw`,
  },
} as const;
