import React from 'react';
import {
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  FileText,
  RotateCcw,
  CheckCircle2,
  ArrowRight,
} from 'lucide-react';
import { AgentAnalysisResponse } from '../types';

interface AgentWorkflowCardProps {
  agentData: AgentAnalysisResponse | null;
  loading: boolean;
  onRunAgent: () => void;
  onDownloadPdf?: () => void;
  downloadingPdf?: boolean;
}

const STAGES = [
  { id: 'DOCUMENT_INPUT', label: '1. Ingestion' },
  { id: 'DOCUMENT_CLASSIFICATION', label: '2. Classification' },
  { id: 'OCR_DATA_EXTRACTION', label: '3. Extraction' },
  { id: 'DOCUMENT_COMPLETENESS', label: '4. Completeness' },
  { id: 'CROSS_DOCUMENT_VALIDATION', label: '5. 16-Rule Audit' },
  { id: 'GOVERNMENT_STATUTORY_VERIFICATION', label: '6. Statutory DGFT' },
  { id: 'FAKE_DOCUMENT_DETECTION', label: '7. Fraud Forensics' },
  { id: 'COMPLIANCE_DECISION', label: '8. AI Decision' },
  { id: 'PDF_REPORT_GENERATION', label: '9. PDF Certificate' },
];

export const AgentWorkflowCard: React.FC<AgentWorkflowCardProps> = ({
  agentData,
  loading,
  onRunAgent,
  onDownloadPdf,
  downloadingPdf = false,
}) => {
  if (loading) {
    return (
      <div
        style={{
          padding: '28px',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-blush)',
          boxShadow: 'var(--shadow-sm)',
          marginBottom: '24px',
          textAlign: 'center',
        }}
      >
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: 'var(--primary-blush)', marginBottom: '12px' }}>
          <Sparkles className="animate-spin" size={24} />
          <span style={{ fontSize: '16px', fontWeight: 700 }}>Executing LangGraph AI Agent Workflow...</span>
        </div>
        <p style={{ margin: '0 auto', maxWidth: '500px', fontSize: '13px', color: 'var(--text-muted)' }}>
          Orchestrating multi-document extraction, 16-rule reconciliation, DGFT/CBIC statutory verification, and forensic fraud detection.
        </p>
      </div>
    );
  }

  if (!agentData) {
    return (
      <div
        style={{
          padding: '24px',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-md)',
          border: '1px dashed var(--border-strong)',
          boxShadow: 'var(--shadow-sm)',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <Sparkles size={18} style={{ color: 'var(--primary-blush)' }} />
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--text-main)' }}>
              LangGraph Autonomous Compliance Agent
            </h3>
          </div>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-muted)' }}>
            Execute the unified 8-stage stateful AI agent to audit cross-document consistency, verify statutory laws, and detect document fraud.
          </p>
        </div>
        <button
          type="button"
          onClick={onRunAgent}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 18px',
            fontSize: '13px',
            fontWeight: 700,
            backgroundColor: 'var(--primary-blush)',
            color: '#ffffff',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            boxShadow: '0 2px 8px rgba(184, 50, 83, 0.3)',
          }}
        >
          <Sparkles size={15} /> Run AI Compliance Analysis
        </button>
      </div>
    );
  }

  const status = agentData.overall_compliance_status;
  const isApproved = status === 'APPROVED_FOR_EXPORT';
  const isHold = status === 'REJECTED_CUSTOMS_HOLD';

  const executedStages = new Set(agentData.execution_stages || []);

  const bannerBg = isApproved
    ? 'var(--status-success-bg)'
    : isHold
    ? 'var(--status-error-bg)'
    : 'var(--status-partial-bg)';

  const bannerBorder = isApproved
    ? 'var(--status-success-border)'
    : isHold
    ? 'var(--status-error-border)'
    : 'var(--status-partial-border)';

  const bannerText = isApproved
    ? 'var(--status-success-text)'
    : isHold
    ? 'var(--status-error-text)'
    : 'var(--status-partial-text)';

  const StatusIcon = isApproved ? ShieldCheck : isHold ? ShieldAlert : AlertTriangle;

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-blush)',
        boxShadow: 'var(--shadow-md)',
        marginBottom: '24px',
        overflow: 'hidden',
      }}
      className="fade-in"
    >
      {/* Agent Header Bar */}
      <div
        style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          backgroundColor: 'var(--bg-highlight)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              backgroundColor: 'var(--primary-blush)',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Sparkles size={18} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 800, color: 'var(--text-main)' }}>
                LangGraph Autonomous Compliance Agent
              </h3>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '10px',
                  backgroundColor: 'var(--primary-blush-light)',
                  color: 'var(--primary-blush)',
                }}
              >
                EXEC-{agentData.execution_id.slice(-6).toUpperCase()}
              </span>
            </div>
            <p style={{ margin: '2px 0 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>
              Orchestrated Pipeline • 10 Specialized Nodes • Guardrailed Customs Intelligence
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          {onDownloadPdf && agentData.pdf_report_available && (
            <button
              type="button"
              onClick={onDownloadPdf}
              disabled={downloadingPdf}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--primary-blush)',
                border: '1px solid var(--border-blush)',
                borderRadius: 'var(--radius-sm)',
                cursor: downloadingPdf ? 'not-allowed' : 'pointer',
              }}
            >
              <FileText size={13} /> {downloadingPdf ? 'Downloading...' : 'PDF Audit Certificate'}
            </button>
          )}

          <button
            type="button"
            onClick={onRunAgent}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              backgroundColor: 'var(--primary-blush)',
              color: '#ffffff',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={13} /> Re-Run AI Agent
          </button>
        </div>
      </div>

      {/* Visual Workflow Stage Stepper */}
      <div
        style={{
          padding: '12px 20px',
          backgroundColor: 'var(--bg-subtle)',
          borderBottom: '1px solid var(--border-subtle)',
          overflowX: 'auto',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '760px' }}>
          {STAGES.map((st, idx) => {
            const isCompleted = executedStages.has(st.id) || executedStages.has('COMPLETED');
            return (
              <React.Fragment key={st.id}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    fontSize: '11px',
                    fontWeight: isCompleted ? 700 : 500,
                    color: isCompleted ? 'var(--status-success-text)' : 'var(--text-subtle)',
                    padding: '3px 8px',
                    borderRadius: '12px',
                    backgroundColor: isCompleted ? 'var(--status-success-bg)' : 'transparent',
                    border: isCompleted ? '1px solid var(--status-success-border)' : '1px solid transparent',
                  }}
                >
                  {isCompleted ? <CheckCircle2 size={12} /> : <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--text-subtle)' }} />}
                  <span>{st.label}</span>
                </div>
                {idx < STAGES.length - 1 && (
                  <ArrowRight size={10} style={{ color: 'var(--text-subtle)', flexShrink: 0 }} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      <div style={{ padding: '20px' }}>
        {/* Main Decision Banner */}
        <div
          style={{
            backgroundColor: bannerBg,
            border: `1.5px solid ${bannerBorder}`,
            borderRadius: 'var(--radius-md)',
            padding: '16px 20px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '50%',
                backgroundColor: '#ffffff',
                border: `2px solid ${bannerBorder}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: bannerText,
                flexShrink: 0,
              }}
            >
              <StatusIcon size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <h4 style={{ margin: 0, fontSize: '17px', fontWeight: 800, color: bannerText }}>
                  {isApproved
                    ? 'CUSTOMS CLEARANCE GRANTED: APPROVED FOR EXPORT'
                    : isHold
                    ? 'CUSTOMS EMBARGO: REJECTED UNDER FRAUD HOLD'
                    : 'CONDITIONAL HOLD: REMEDIATION MANDATORY'}
                </h4>
              </div>
              <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: bannerText, opacity: 0.9 }}>
                {isApproved
                  ? 'Consignment fully satisfies all 16 cross-document rules, DGFT/CBIC statutory mandates, and authenticity forensics.'
                  : isHold
                  ? 'Critical tamper signals or identifier checksum forgery detected. Under statutory customs guardrails, automated pass overrides are strictly blocked.'
                  : 'Documentary gaps or field discrepancies require remediation before shipping bills can be registered on ICEGATE.'}
              </p>
            </div>
          </div>

          <div
            style={{
              textAlign: 'right',
              padding: '8px 16px',
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-sm)',
              border: `1px solid ${bannerBorder}`,
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Compliance Rating
            </div>
            <div style={{ fontSize: '22px', fontWeight: 900, color: bannerText }}>
              {agentData.compliance_score.toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Missing Documents Alert Banner */}
        {agentData.summary.missing_documents.length > 0 && (
          <div
            style={{
              padding: '12px 16px',
              backgroundColor: 'var(--status-partial-bg)',
              border: '1px solid var(--status-partial-border)',
              borderRadius: 'var(--radius-sm)',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '13px',
              color: 'var(--status-partial-text)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={16} />
              <span>
                <strong>Missing Canonical Trade Documents:</strong>{' '}
                {agentData.summary.missing_documents.join(', ')}
              </span>
            </div>
            <span style={{ fontSize: '11px', fontWeight: 700, padding: '2px 8px', borderRadius: '4px', backgroundColor: '#ffffff' }}>
              {agentData.summary.missing_documents.length} Missing
            </span>
          </div>
        )}

        {/* Critical Fraud Warning Banner */}
        {agentData.critical_fraud_flag && (
          <div
            style={{
              padding: '12px 16px',
              backgroundColor: 'var(--status-error-bg)',
              border: '1.5px solid var(--status-error-border)',
              borderRadius: 'var(--radius-sm)',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              fontSize: '13px',
              color: 'var(--status-error-text)',
            }}
          >
            <ShieldAlert size={18} />
            <div>
              <strong>CRITICAL FORENSIC TAMPER ALERT:</strong> Document anomalies violate statutory Customs Act 1962 Section 50. Non-overridable hold active.
            </div>
          </div>
        )}

        {/* Multi-Dimensional Audit Metric Cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '12px',
            marginBottom: '20px',
          }}
        >
          <div
            style={{
              padding: '12px 14px',
              backgroundColor: 'var(--bg-subtle)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>Documents Evaluated</div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>
              {agentData.summary.documents_evaluated} / 5
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-subtle)', marginTop: '2px' }}>
              {agentData.summary.missing_documents.length === 0 ? 'Full 5-document set' : `${agentData.summary.missing_documents.length} omitted`}
            </div>
          </div>

          <div
            style={{
              padding: '12px 14px',
              backgroundColor: 'var(--bg-subtle)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>16-Rule Cross Reconciliation</div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>
              {agentData.summary.passed_checks} <span style={{ fontSize: '12px', color: 'var(--status-success-text)' }}>Passed</span> • {agentData.summary.failed_checks} <span style={{ fontSize: '12px', color: 'var(--status-error-text)' }}>Failed</span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-subtle)', marginTop: '2px' }}>
              Multi-document data alignment
            </div>
          </div>

          <div
            style={{
              padding: '12px 14px',
              backgroundColor: 'var(--bg-subtle)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>DGFT / CBIC Statutory Law</div>
            <div
              style={{
                fontSize: '18px',
                fontWeight: 800,
                color: agentData.summary.statutory_compliant ? 'var(--status-success-text)' : 'var(--status-error-text)',
                marginTop: '2px',
              }}
            >
              {agentData.summary.statutory_compliant ? 'Statutory Compliant' : 'Provisions Violated'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-subtle)', marginTop: '2px' }}>
              FTP 2023 & Customs Act Sec 50
            </div>
          </div>

          <div
            style={{
              padding: '12px 14px',
              backgroundColor: 'var(--bg-subtle)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>Authenticity & Risk</div>
            <div
              style={{
                fontSize: '18px',
                fontWeight: 800,
                color: agentData.summary.fraud_risk_level === 'GENUINE' ? 'var(--status-success-text)' : 'var(--status-error-text)',
                marginTop: '2px',
              }}
            >
              {agentData.summary.authenticity_score.toFixed(1)}% • {agentData.summary.fraud_risk_level}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-subtle)', marginTop: '2px' }}>
              Tamper & Mod-36 checksum scan
            </div>
          </div>
        </div>

        {/* AI-Synthesized Reasons & Executive Recommendations */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
          {/* Reasons */}
          <div
            style={{
              padding: '16px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-page)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <h5 style={{ margin: '0 0 10px 0', fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>
              Agent Decision Rationale ({agentData.reasons.length})
            </h5>
            <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.6' }}>
              {agentData.reasons.map((r, i) => (
                <li key={i} style={{ marginBottom: '4px' }}>{r}</li>
              ))}
            </ul>
          </div>

          {/* Actionable Recommendations */}
          <div
            style={{
              padding: '16px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-page)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <h5 style={{ margin: '0 0 10px 0', fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>
              Actionable Remediations for Exporter ({agentData.recommendations.length})
            </h5>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {agentData.recommendations.map((rec, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '8px',
                    fontSize: '12px',
                    color: 'var(--text-main)',
                    lineHeight: '1.5',
                  }}
                >
                  <span
                    style={{
                      flexShrink: 0,
                      width: '18px',
                      height: '18px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--primary-blush-light)',
                      color: 'var(--primary-blush)',
                      fontSize: '10px',
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {i + 1}
                  </span>
                  <span>{rec}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
