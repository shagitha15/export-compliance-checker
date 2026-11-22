// Document Intelligence Feature Module
export interface DocumentIntelligenceData {
  documentType: string;
  confidence: number;
  extractedFields: Record<string, unknown>;
}
