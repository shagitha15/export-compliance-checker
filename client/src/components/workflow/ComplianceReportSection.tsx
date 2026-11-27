import React, { useState } from 'react';
import { BatchUploadResponse } from '../../types/batch';
import { AgentAnalysisResponse } from '../../features/compliance/types';
import { batchService } from '../../services/batchService';
import { AuditHistoryEntry, FinalAuditOutcome } from './WorkflowTypes';
import { FraudDetectionPanel } from '../../features/compliance/components/FraudDetectionPanel';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileDown,
  Download,
  History,
} from 'lucide-react';

interface ComplianceReportSectionProps {
  batchResponse: BatchUploadResponse | null;
  agentResponse: AgentAnalysisResponse | null;
  outcome: FinalAuditOutcome | null;
  auditHistory: AuditHistoryEntry[];
  onSelectHistoryEntry: (entry: AuditHistoryEntry) => void;
  onGoToUpload: () => void;
}

export const ComplianceReportSection: React.FC<ComplianceReportSectionProps> = ({
  batchResponse,
  agentResponse,
  outcome,
  auditHistory,
  onSelectHistoryEntry,
  onGoToUpload,
}) => {
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  if (!batchResponse || !outcome) {
    return (
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-blush)',
          borderRadius: 'var(--radius-lg)',
          padding: '32px',
          textAlign: 'center',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <p style={{ margin: '0 0 14px 0', color: 'var(--text-muted)', fontSize: '14px' }}>
          No completed compliance report yet. Upload documents and start compliance verification to generate your final report.
        </p>
        <button
          type="button"
          onClick={onGoToUpload}
          style={{
            padding: '9px 18px',
            fontSize: '13px',
            fontWeight: 700,
            backgroundColor: '#102A43',
            color: '#ffffff',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
          }}
        >
          Go to Upload Documents
        </button>
      </div>
    );
  }

  const val = agentResponse?.cross_document_validation || batchResponse.cross_document_validation;
  const gov = agentResponse?.government_compliance || batchResponse.government_compliance;
  const fraud = agentResponse?.fraud_analysis || null;

  const isPass = outcome === 'PASS';
  const isFail = outcome === 'FAIL';

  const discrepancies = (val?.cross_document_results || []).filter((c) => c.status === 'FAIL');
  const intraDiscrepancies = (val?.intra_document_results || []).filter((c) => c.status === 'FAIL');
  const nonCompliantPolicies = (gov?.findings || []).filter((f) => f.status === 'NON_COMPLIANT');

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    setPdfError(null);
    try {
      const mergedBatch: BatchUploadResponse = {
        ...batchResponse,
        cross_document_validation: val || batchResponse.cross_document_validation,
        government_compliance: gov || batchResponse.government_compliance,
      };
      await batchService.downloadBatchPdfReport(mergedBatch, fraud);
    } catch (err: any) {
      setPdfError(err.message || 'Failed to generate PDF report.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleExportJson = () => {
    const payload = {
      batch_id: batchResponse.batch_id,
      timestamp: batchResponse.timestamp,
      final_outcome: outcome,
      batch_result: batchResponse,
      langgraph_agent_analysis: agentResponse,
    };
    const dataUrl =
      'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(payload, null, 2));
    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = `compliance_report_${batchResponse.batch_id}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
      {/* Final Outcome Banner */}
      <div
        style={{
          padding: '22px 24px',
          borderRadius: 'var(--radius-lg)',
          backgroundColor: isPass
            ? 'var(--status-success-bg)'
            : isFail
            ? 'var(--status-error-bg)'
            : 'var(--status-partial-bg)',
          border: `1px solid ${
            isPass
              ? 'var(--status-success-border)'
              : isFail
              ? 'var(--status-error-border)'
              : 'var(--status-partial-border)'
          }`,
          boxShadow: 'var(--shadow-md)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '46px',
                height: '46px',
                borderRadius: '50%',
                backgroundColor: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: isPass
                  ? 'var(--status-success-text)'
                  : isFail
                  ? 'var(--status-error-text)'
                  : 'var(--status-partial-text)',
              }}
            >
              {isPass && <CheckCircle2 size={26} />}
              {isFail && <XCircle size={26} />}
              {!isPass && !isFail && <AlertTriangle size={26} />}
            </div>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Final Compliance Audit Result
              </div>
              <h3
                style={{
                  margin: '2px 0 0 0',
                  fontSize: '22px',
                  fontWeight: 800,
                  color: isPass
                    ? 'var(--status-success-text)'
                    : isFail
                    ? 'var(--status-error-text)'
                    : 'var(--status-partial-text)',
                }}
              >
                FINAL RESULT: {outcome}
              </h3>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Batch {batchResponse.batch_id} • {batchResponse.summary.successful_count}/
                {batchResponse.summary.total_files_received} files extracted
                {agentResponse
                  ? ` • LangGraph Decision: ${agentResponse.overall_compliance_status} (${agentResponse.compliance_score.toFixed(1)}%)`
                  : ''}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button
              type="button"
              id="report-export-json-btn"
              onClick={handleExportJson}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '9px 16px',
                fontSize: '13px',
                fontWeight: 600,
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-main)',
                border: '1px solid var(--border-blush)',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
              }}
            >
              <Download size={15} /> Export JSON
            </button>

            <button
              type="button"
              id="report-download-pdf-btn"
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '9px 18px',
                fontSize: '13px',
                fontWeight: 700,
                backgroundColor: 'var(--primary-blush)',
                color: '#ffffff',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                cursor: downloadingPdf ? 'not-allowed' : 'pointer',
                opacity: downloadingPdf ? 0.7 : 1,
              }}
            >
              <FileDown size={15} /> {downloadingPdf ? 'Generating PDF...' : 'Download PDF Report'}
            </button>
          </div>
        </div>

        {pdfError && (
          <div
            style={{
              marginTop: '12px',
              padding: '10px 14px',
              backgroundColor: 'var(--status-error-bg)',
              border: '1px solid var(--status-error-border)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--status-error-text)',
              fontSize: '13px',
            }}
          >
            <strong>PDF Error:</strong> {pdfError}
          </div>
        )}
      </div>

      {/* Summary Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
          gap: '12px',
        }}
      >
        <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-blush)', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>Validation Checks</div>
          <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
            {val ? `${val.summary.passed} Pass / ${val.summary.failed} Fail` : 'Not Run'}
          </div>
        </div>
        <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-blush)', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>DGFT &amp; CBIC Policy</div>
          <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
            {gov ? gov.overall_government_compliance : 'Not Evaluated'}
          </div>
        </div>
        <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-blush)', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>Missing Documents</div>
          <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
            {batchResponse.summary.missing_document_types.length}
          </div>
        </div>
        <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-blush)', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>Authenticity Score</div>
          <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
            {fraud ? `${fraud.overall_authenticity_score.toFixed(1)}% (${fraud.overall_risk_level})` : 'Not Run'}
          </div>
        </div>
      </div>

      {/* Detected Discrepancies & Policy Violations */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-blush)',
          borderRadius: 'var(--radius-lg)',
          padding: '20px 24px',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <h4 style={{ margin: '0 0 12px 0', fontSize: '15px', fontWeight: 700, color: 'var(--text-main)' }}>
          Detected Discrepancies &amp; Compliance Findings
        </h4>

        {discrepancies.length === 0 && intraDiscrepancies.length === 0 && nonCompliantPolicies.length === 0 ? (
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--status-success-text)' }}>
            No cross-document discrepancies or statutory policy violations detected in evaluated documents.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {intraDiscrepancies.map((d, i) => (
              <div
                key={`intra_${i}`}
                style={{
                  padding: '10px 12px',
                  backgroundColor: 'var(--status-error-bg)',
                  border: '1px solid var(--status-error-border)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12.5px',
                  color: 'var(--status-error-text)',
                }}
              >
                <strong>[{d.document_type}] {d.check_name}:</strong> {d.message}
              </div>
            ))}
            {discrepancies.map((d) => (
              <div
                key={d.check_id}
                style={{
                  padding: '10px 12px',
                  backgroundColor: 'var(--status-error-bg)',
                  border: '1px solid var(--status-error-border)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12.5px',
                  color: 'var(--status-error-text)',
                }}
              >
                <strong>[{d.check_id}] {d.rule_name}:</strong> {d.discrepancy || d.message}
              </div>
            ))}
            {nonCompliantPolicies.map((p) => (
              <div
                key={p.rule_id}
                style={{
                  padding: '10px 12px',
                  backgroundColor: 'var(--status-error-bg)',
                  border: '1px solid var(--status-error-border)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12.5px',
                  color: 'var(--status-error-text)',
                }}
              >
                <strong>[{p.rule_id} • {p.authority}] {p.rule_title}:</strong> {p.observed_evidence}
              </div>
            ))}
          </div>
        )}

        {agentResponse && agentResponse.recommendations.length > 0 && (
          <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
            <h5 style={{ margin: '0 0 8px 0', fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>
              LangGraph Agent Recommendations ({agentResponse.recommendations.length})
            </h5>
            <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12.5px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
              {agentResponse.recommendations.map((r, idx) => (
                <li key={idx}>{r}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {fraud && <FraudDetectionPanel fraudReport={fraud} loading={false} />}

      {/* Session Audit History */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-blush)',
          borderRadius: 'var(--radius-lg)',
          padding: '18px 22px',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
          <History size={16} color="var(--primary-blush)" />
          <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: 'var(--text-main)' }}>
            Session Audit History ({auditHistory.length})
          </h4>
        </div>
        {auditHistory.length === 0 ? (
          <p style={{ margin: 0, fontSize: '12.5px', color: 'var(--text-muted)' }}>
            No prior audits recorded in this session.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {auditHistory.map((item) => (
              <div
                key={item.batchId}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '8px',
                  padding: '8px 12px',
                  backgroundColor:
                    item.batchId === batchResponse.batch_id ? 'var(--bg-highlight)' : 'var(--bg-subtle)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12.5px',
                }}
              >
                <div>
                  <strong>{item.batchId}</strong> • {new Date(item.timestamp).toLocaleString()} •{' '}
                  {item.successfulDocs}/{item.filesCount} docs • Outcome: <strong>{item.outcome}</strong>
                </div>
                {item.batchId !== batchResponse.batch_id && (
                  <button
                    type="button"
                    onClick={() => onSelectHistoryEntry(item)}
                    style={{
                      padding: '4px 10px',
                      fontSize: '11.5px',
                      fontWeight: 600,
                      backgroundColor: 'var(--bg-surface)',
                      color: 'var(--primary-blush)',
                      border: '1px solid var(--border-blush)',
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                  >
                    Load Audit
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
