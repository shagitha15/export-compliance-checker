import React from 'react';
import { CrossDocumentValidationResponse, GovernmentComplianceReport } from '../../../types/batch';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Percent,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';

interface ComplianceOverviewCardsProps {
  validation?: CrossDocumentValidationResponse | null;
  government?: GovernmentComplianceReport | null;
}

export const ComplianceOverviewCards: React.FC<ComplianceOverviewCardsProps> = ({
  validation,
  government,
}) => {
  if (!validation) return null;

  const { summary, overall_compliance_status } = validation;
  const isPass = overall_compliance_status === 'PASS';

  const applicableChecks = summary.total_checks - summary.not_applicable;
  const passRate =
    applicableChecks > 0 ? Math.round((summary.passed / applicableChecks) * 100) : 100;

  const isGovCompliant = government?.overall_government_compliance === 'COMPLIANT';

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '14px',
        marginBottom: '22px',
      }}
    >
      {/* 1. Overall Status Card */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: `1px solid ${isPass ? 'var(--status-success-border)' : 'var(--status-error-border)'}`,
          borderRadius: 'var(--radius-md)',
          padding: '16px 18px',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>
            Reconciliation
          </span>
          <div
            style={{
              color: isPass ? 'var(--status-success-text)' : 'var(--status-error-text)',
            }}
          >
            {isPass ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
          </div>
        </div>
        <div
          style={{
            fontSize: '22px',
            fontWeight: 800,
            color: isPass ? 'var(--status-success-text)' : 'var(--status-error-text)',
            marginTop: '6px',
          }}
        >
          {overall_compliance_status}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-subtle)', marginTop: '4px' }}>
          {summary.failed === 0 ? 'All applicable rules passed' : `${summary.failed} discrepancy flagged`}
        </div>
      </div>

      {/* 2. Pass Rate % */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-blush)',
          borderRadius: 'var(--radius-md)',
          padding: '16px 18px',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>
            Pass Rate
          </span>
          <div style={{ color: 'var(--primary-blush)' }}>
            <Percent size={18} />
          </div>
        </div>
        <div
          style={{
            fontSize: '22px',
            fontWeight: 800,
            color: 'var(--text-main)',
            marginTop: '6px',
          }}
        >
          {passRate}%
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-subtle)', marginTop: '4px' }}>
          {summary.passed} of {applicableChecks} active checks
        </div>
      </div>

      {/* 3. Passed Checks */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-blush)',
          borderRadius: 'var(--radius-md)',
          padding: '16px 18px',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>
            Passed Checks
          </span>
          <div style={{ color: 'var(--status-success-text)' }}>
            <CheckCircle2 size={18} />
          </div>
        </div>
        <div
          style={{
            fontSize: '22px',
            fontWeight: 800,
            color: 'var(--status-success-text)',
            marginTop: '6px',
          }}
        >
          {summary.passed}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-subtle)', marginTop: '4px' }}>
          Full document integrity confirmed
        </div>
      </div>

      {/* 4. Failed Discrepancies */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-blush)',
          borderRadius: 'var(--radius-md)',
          padding: '16px 18px',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>
            Discrepancies
          </span>
          <div style={{ color: summary.failed > 0 ? 'var(--status-error-text)' : 'var(--text-subtle)' }}>
            <AlertTriangle size={18} />
          </div>
        </div>
        <div
          style={{
            fontSize: '22px',
            fontWeight: 800,
            color: summary.failed > 0 ? 'var(--status-error-text)' : 'var(--text-main)',
            marginTop: '6px',
          }}
        >
          {summary.failed}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-subtle)', marginTop: '4px' }}>
          Requires immediate customs review
        </div>
      </div>

      {/* 5. Statutory Government Compliance */}
      {government && (
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: `1px solid ${isGovCompliant ? 'var(--status-success-border)' : 'var(--status-error-border)'}`,
            borderRadius: 'var(--radius-md)',
            padding: '16px 18px',
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>
              Statutory DGFT/CBIC
            </span>
            <div style={{ color: isGovCompliant ? 'var(--status-success-text)' : 'var(--status-error-text)' }}>
              {isGovCompliant ? <ShieldCheck size={18} /> : <ShieldAlert size={18} />}
            </div>
          </div>
          <div
            style={{
              fontSize: '18px',
              fontWeight: 800,
              color: isGovCompliant ? 'var(--status-success-text)' : 'var(--status-error-text)',
              marginTop: '6px',
            }}
          >
            {government.overall_government_compliance}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-subtle)', marginTop: '4px' }}>
            {government.summary.compliant_count} compliant, {government.summary.advisory_count} advisory
          </div>
        </div>
      )}
    </div>
  );
};
