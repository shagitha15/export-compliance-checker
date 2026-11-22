// Compliance Feature Module
export interface ComplianceAuditSummary {
  overallStatus: 'PASS' | 'FAIL';
  passedCount: number;
  failedCount: number;
  notApplicableCount: number;
}
