/**
 * Data contracts and types for Task 4: Validation Dashboard, Task 6: Fraud Forensics, and Task 7: LangGraph Agent.
 */

import { CrossDocumentValidationResponse, GovernmentComplianceReport } from '../../types/batch';

export type RuleCategory =
  | 'ALL'
  | 'INVOICE_PO'
  | 'INVOICE_PACKING'
  | 'INVOICE_SHIPPING'
  | 'INVOICE_COO';

export interface RuleCategoryDefinition {
  id: RuleCategory;
  label: string;
  description: string;
  documentPair: string;
}

export const RULE_CATEGORIES: RuleCategoryDefinition[] = [
  {
    id: 'ALL',
    label: 'All 16 Rules',
    description: 'Complete cross-document compliance reconciliation pipeline',
    documentPair: 'All Trade Documents',
  },
  {
    id: 'INVOICE_PO',
    label: 'Invoice ↔ Purchase Order',
    description: 'Invoice numbers, PO numbers, buyer/seller identity, currency, incoterms, and contract valuations',
    documentPair: 'CI ↔ PO',
  },
  {
    id: 'INVOICE_PACKING',
    label: 'Invoice ↔ Packing List',
    description: 'Gross and net weights, total package count, item packaging quantities',
    documentPair: 'CI ↔ PL',
  },
  {
    id: 'INVOICE_SHIPPING',
    label: 'Invoice ↔ Shipping Bill',
    description: 'ICEGATE declaration reference, FOB valuation, declared export currency',
    documentPair: 'CI ↔ SB',
  },
  {
    id: 'INVOICE_COO',
    label: 'Invoice ↔ Certificate of Origin',
    description: 'Invoice reference citation, origin criterion (WO/General), exporter name alignment',
    documentPair: 'CI ↔ COO',
  },
];

export interface ShipmentScenario {
  id: string;
  name: string;
  description: string;
  destination: string;
  expectedStatus: 'PASS' | 'FAIL' | 'PARTIAL';
  documents: Record<string, any>;
}

export interface DiscrepancyDetail {
  checkId: string;
  ruleName: string;
  documentA: string;
  valueA: string | number;
  documentB: string;
  valueB: string | number;
  explanation: string;
  remediationAdvice: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
}

export type FraudRiskLevel = 'GENUINE' | 'SUSPICIOUS' | 'HIGH_RISK';

export type AnomalyCategory =
  | 'METADATA_TAMPERING'
  | 'TYPOGRAPHY_ANOMALY'
  | 'IDENTIFIER_FRAUD'
  | 'NUMERICAL_FORGERY'
  | 'PHYSICAL_ANOMALY'
  | 'TEMPORAL_PARADOX';

export type AnomalySeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface DocumentAnomaly {
  anomaly_id: string;
  category: AnomalyCategory;
  severity: AnomalySeverity;
  rule_name: string;
  description: string;
  evidence: string;
  remediation?: string | null;
  document_type?: string | null;
  field_name?: string | null;
}

export interface DocumentAuthenticityResult {
  document_type: string;
  filename?: string | null;
  authenticity_score: number;
  risk_level: FraudRiskLevel;
  anomalies: DocumentAnomaly[];
}

export interface FraudAnalysisReport {
  audit_id: string;
  audit_timestamp: string;
  overall_authenticity_score: number;
  overall_risk_level: FraudRiskLevel;
  total_anomalies: number;
  critical_anomalies: number;
  anomalies: DocumentAnomaly[];
  document_breakdown: DocumentAuthenticityResult[];
}

export type OverallComplianceDecision =
  | 'APPROVED_FOR_EXPORT'
  | 'CONDITIONAL_REMEDIATION_REQUIRED'
  | 'REJECTED_CUSTOMS_HOLD';

export interface AgentSummary {
  documents_evaluated: number;
  missing_documents: string[];
  passed_checks: number;
  failed_checks: number;
  statutory_compliant: boolean;
  fraud_risk_level: string;
  authenticity_score: number;
}

export interface AgentAnalysisResponse {
  execution_id: string;
  shipment_id: string;
  scenario_title?: string | null;
  overall_compliance_status: OverallComplianceDecision;
  compliance_score: number;
  critical_fraud_flag: boolean;
  summary: AgentSummary;
  reasons: string[];
  recommendations: string[];
  cross_document_validation?: CrossDocumentValidationResponse | null;
  government_compliance?: GovernmentComplianceReport | null;
  fraud_analysis?: FraudAnalysisReport | null;
  pdf_report_available: boolean;
  pdf_report_filename?: string | null;
  execution_stages: string[];
}
