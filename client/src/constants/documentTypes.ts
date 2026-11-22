export const DOCUMENT_TYPES = [
  'Commercial Invoice',
  'Packing List',
  'Purchase Order',
  'Shipping Bill',
  'Certificate of Origin',
] as const;

export type DocumentType = typeof DOCUMENT_TYPES[number];
