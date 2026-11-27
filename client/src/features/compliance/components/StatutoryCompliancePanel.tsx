import React from 'react';
import { GovernmentComplianceReport } from '../../../types/batch';
import {
  ShieldCheck,
  ShieldAlert,
  BookOpen,
  ExternalLink,
} from 'lucide-react';

interface StatutoryCompliancePanelProps {
  compliance?: GovernmentComplianceReport | null;
}

export const StatutoryCompliancePanel: React.FC<StatutoryCompliancePanelProps> = ({ compliance }) => {
  if (!compliance) return null;

  const { overall_government_compliance, findings, hs_codes_evaluated, destination_country } =
    compliance;
  const isCompliant = overall_government_compliance === 'COMPLIANT';

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border-blush)',
        padding: '24px',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '24px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '8px',
              backgroundColor: isCompliant ? 'var(--status-success-bg)' : 'var(--status-error-bg)',
              color: isCompliant ? 'var(--status-success-text)' : 'var(--status-error-text)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {isCompliant ? <ShieldCheck size={22} /> : <ShieldAlert size={22} />}
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: 'var(--text-main)' }}>
              Indian Statutory Export Regulations (DGFT & CBIC)
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Destination: {destination_country || 'Worldwide'} • HS Codes:{' '}
              {hs_codes_evaluated.length > 0 ? hs_codes_evaluated.join(', ') : 'Universal'}
            </span>
          </div>
        </div>

        <span
          style={{
            fontSize: '12px',
            fontWeight: 700,
            padding: '4px 12px',
            borderRadius: '16px',
            backgroundColor: isCompliant ? 'var(--status-success-bg)' : 'var(--status-error-bg)',
            color: isCompliant ? 'var(--status-success-text)' : 'var(--status-error-text)',
            border: `1px solid ${isCompliant ? 'var(--status-success-border)' : 'var(--status-error-border)'}`,
          }}
        >
          {overall_government_compliance}
        </span>
      </div>

      {/* Findings List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {findings.map((f) => {
          const isComp = f.status === 'COMPLIANT';
          const isNonComp = f.status === 'NON_COMPLIANT';

          return (
            <div
              key={f.rule_id}
              style={{
                backgroundColor: isNonComp ? 'var(--status-error-bg)' : 'var(--bg-subtle)',
                border: `1px solid ${isNonComp ? 'var(--status-error-border)' : 'var(--border-subtle)'}`,
                borderRadius: 'var(--radius-sm)',
                padding: '14px 16px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: 'var(--primary-blush)',
                      backgroundColor: 'var(--bg-surface)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      border: '1px solid var(--border-blush)',
                    }}
                  >
                    {f.rule_id}
                  </span>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>
                    {f.rule_title}
                  </span>
                  <span style={{ fontSize: '11px', color: 'var(--text-subtle)' }}>({f.authority})</span>
                </div>

                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '10px',
                    backgroundColor: isComp
                      ? 'var(--status-success-bg)'
                      : isNonComp
                      ? 'var(--status-error-bg)'
                      : 'var(--status-partial-bg)',
                    color: isComp
                      ? 'var(--status-success-text)'
                      : isNonComp
                      ? 'var(--status-error-text)'
                      : 'var(--status-partial-text)',
                    border: `1px solid ${
                      isComp
                        ? 'var(--status-success-border)'
                        : isNonComp
                        ? 'var(--status-error-border)'
                        : 'var(--status-partial-border)'
                    }`,
                  }}
                >
                  {f.status}
                </span>
              </div>

              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                {f.requirement_summary}
              </div>

              <div
                style={{
                  fontSize: '11px',
                  color: 'var(--text-main)',
                  backgroundColor: 'rgba(255, 255, 255, 0.7)',
                  padding: '6px 10px',
                  borderRadius: '4px',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <strong>Evidence:</strong> {f.observed_evidence}
              </div>

              {f.action_required && (
                <div
                  style={{
                    fontSize: '11px',
                    color: 'var(--status-error-text)',
                    backgroundColor: '#ffffff',
                    padding: '6px 10px',
                    borderRadius: '4px',
                    border: '1px solid var(--status-error-border)',
                    marginTop: '6px',
                  }}
                >
                  <strong>Action Required:</strong> {f.action_required}
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '8px', fontSize: '11px', color: 'var(--text-subtle)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <BookOpen size={12} /> {f.policy_document} ({f.para_ref})
                </span>
                {f.source_url && (
                  <a
                    href={f.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '3px',
                      color: 'var(--primary-blush)',
                      textDecoration: 'none',
                    }}
                  >
                    <span>Official Gazette</span>
                    <ExternalLink size={10} />
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
