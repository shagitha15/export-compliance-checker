import React from 'react';
import { GovernmentComplianceReport } from '../../types/batch';
import { GovernmentRulesView } from '../results/GovernmentRulesView';
import { GovernmentRulesMonitorSection } from '../compliance/GovernmentRulesMonitorSection';

interface PolicyVerificationSectionProps {
  compliance?: GovernmentComplianceReport | null;
  onGoToUpload: () => void;
}

export const PolicyVerificationSection: React.FC<PolicyVerificationSectionProps> = ({
  compliance,
  onGoToUpload,
}) => {
  if (!compliance) {
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
          No DGFT &amp; CBIC statutory policy verification results available yet. Upload documents and start compliance verification first.
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

  return (
    <div className="fade-in">
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-blush)',
          borderRadius: 'var(--radius-lg)',
          padding: '16px 22px',
          boxShadow: 'var(--shadow-sm)',
          marginBottom: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: '16.5px', fontWeight: 700, color: '#102A43' }}>
            Statutory Regulation Evaluation
          </h3>
          <p style={{ margin: '3px 0 0 0', fontSize: '12.5px', color: '#456B8B' }}>
            DGFT FTP 2023 · ITC-HS Schedule 2 · CBIC Customs Act 1962 · RBI FEMA • Audit ID: {compliance.audit_id}
          </p>
        </div>
      </div>

      <GovernmentRulesView compliance={compliance} />
      <GovernmentRulesMonitorSection />
    </div>
  );
};
