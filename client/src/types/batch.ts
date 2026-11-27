/**
 * TypeScript Data Contracts for 5-Document Batch Upload and Compliance Ingestion.
 * Aligned with server/schemas/batch.py, server/schemas/validation.py, and server/schemas/compliance.py.
 */

export type BatchProcessingStatus = 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED';
export type DocumentItemStatus = 'SUCCESS' | 'FAILED' | 'DUPLICATE' | 'SKIPPED';
export type ValidationStatus = 'PASS' | 'FAIL' | 'WARNING' | 'NOT APPLICABLE' | 'NOT_APPLICABLE';
export type RegulatoryComplianceStatus = 'COMPLIANT' | 'NON_COMPLIANT' | 'ADVISORY';

export interface BatchDocumentItem {
  original_filename: string;
  saved_filename?: string | null;
  document_type?: string | null;
  status: DocumentItemStatus;
  file_size_bytes: number;
  extraction_method?: string | null;
  fallback_used?: boolean;
  warning?: string | null;
  extracted_data?: Record<string, any> | null;
  error?: string | null;
  error_code?: string | null;
}

export interface BatchProcessingSummary {
  total_files_received: number;
  successful_count: number;
  failed_count: number;
  duplicate_count: number;
  detected_document_types: string[];
  missing_document_types: string[];
}

export interface CheckResult {
  check_id: string;
  rule_name: string;
  description: string;
  message?: string;
  documents_involved?: string[];
  field_name?: string;
  expected_value?: any;
  observed_values?: Record<string, any>;
  status: ValidationStatus;
  discrepancy?: any;
  stage?: string;
}

export interface IntraDocumentCheckResult {
  document_type: string;
  check_id?: string;
  check_name?: string;
  rule_name?: string;
  status: ValidationStatus;
  message?: string;
  discrepancy?: string | null;
}

export interface ValidationSummary {
  total_checks: number;
  passed: number;
  failed: number;
  not_applicable: number;
}

export interface CrossDocumentValidationResponse {
  audit_id: string;
  audit_timestamp: string;
  documents_evaluated: string[];
  documents_missing: string[];
  overall_compliance_status: ValidationStatus;
  summary: ValidationSummary;
  intra_document_results: IntraDocumentCheckResult[];
  cross_document_results: CheckResult[];
}

export interface RegulatoryFinding {
  rule_id: string;
  rule_title: string;
  authority: string;
  policy_document: string;
  para_ref: string;
  source_url?: string;
  status: RegulatoryComplianceStatus;
  requirement_summary: string;
  observed_evidence: string;
  action_required?: string | null;
}

export interface GovernmentComplianceSummary {
  total_rules_evaluated: number;
  compliant_count: number;
  non_compliant_count: number;
  advisory_count: number;
}

export interface GovernmentComplianceReport {
  audit_id: string;
  audit_timestamp: string;
  hs_codes_evaluated: string[];
  destination_country?: string | null;
  overall_government_compliance: RegulatoryComplianceStatus;
  summary: GovernmentComplianceSummary;
  findings: RegulatoryFinding[];
}

export interface BatchUploadResponse {
  batch_id: string;
  timestamp: string;
  batch_status: BatchProcessingStatus;
  summary: BatchProcessingSummary;
  documents: BatchDocumentItem[];
  cross_document_validation?: CrossDocumentValidationResponse | null;
  government_compliance?: GovernmentComplianceReport | null;
}

export interface SelectedFileItem {
  id: string;
  file: File;
  documentType: string; // 'Auto-Detect' or one of the 5 canonical types
  sizeFormatted: string;
  sizeBytes: number;
  validationError?: string | null;
}
