export const DOCUMENT_TYPES = [
  'Commercial Invoice',
  'Packing List',
  'Bill of Lading',
  'Shipping Bill',
  'Certificate of Origin',
  'Purchase Order',
] as const;

export type DocumentType = typeof DOCUMENT_TYPES[number];

export interface ExporterSlotDefinition {
  type: DocumentType;
  shortCode: string;
  description: string;
}

export const EXPORTER_DOCUMENT_SLOTS: ExporterSlotDefinition[] = [
  {
    type: 'Commercial Invoice',
    shortCode: 'CI',
    description: 'Invoice number, exporter/importer, HS codes, currency, Incoterms & total value',
  },
  {
    type: 'Packing List',
    shortCode: 'PL',
    description: 'Package counts, net weight, gross weight, dimensions & invoice reference',
  },
  {
    type: 'Bill of Lading',
    shortCode: 'BL',
    description: 'B/L number, vessel/voyage, ports of loading/discharge, shipper & weight',
  },
  {
    type: 'Shipping Bill',
    shortCode: 'SB',
    description: 'ICEGATE shipping bill no., port code, RITC HS code & FOB valuation',
  },
  {
    type: 'Certificate of Origin',
    shortCode: 'COO',
    description: 'Certificate no., origin criterion, chamber endorsement & invoice reference',
  },
];
