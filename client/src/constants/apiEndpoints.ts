export const API_ENDPOINTS = {
  HEALTH: '/health',
  DOCUMENTS: {
    UPLOAD: '/documents/upload',
    LIST: '/documents',
    GET_BY_ID: (id: string) => `/documents/${id}`,
  },
  COMPLIANCE: {
    VALIDATE_DIRECT: '/compliance/validate',
    VALIDATE_STORED: '/compliance/validate-stored',
  },
  REGULATIONS: {
    SEARCH: '/regulations/search',
    VERIFY_SHIPMENT: '/regulations/verify',
  },
} as const;
