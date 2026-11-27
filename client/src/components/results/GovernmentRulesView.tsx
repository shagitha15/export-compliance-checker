import React, { useState } from 'react';
import { GovernmentComplianceReport } from '../../types/batch';
import {
  ShieldAlert,
  ShieldCheck,
  ExternalLink,
  BookOpen,
  CheckCircle2,
  Info,
} from 'lucide-react';

interface GovernmentRulesViewProps {
  compliance?: GovernmentComplianceReport | null;
}

export const GovernmentRulesView: React.FC<GovernmentRulesViewProps> = ({ compliance }) => {
  const [authorityFilter, setAuthorityFilter] = useState<string>('ALL');

  if (!compliance) {
    return (
      <div
        style={{
          padding: '24px',
          textAlign: 'center',
          backgroundColor: 'var(--bg-subtle)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--text-muted)',
          border: '1px solid var(--border-blush)',
        }}
      >
        No statutory government compliance data available for this batch.
      </div>
    );
  }

  const { overall_government_compliance, summary, findings, hs_codes_evaluated, destination_country } =
    compliance;
  const isCompliant = overall_government_compliance === 'COMPLIANT';

  const authorities = ['ALL', ...Array.from(new Set(findings.map((f) => f.authority)))];

  const filteredFindings = findings.filter(
    (f) => authorityFilter === 'ALL' || f.authority === authorityFilter
  );

  return (
    <div style={{ marginTop: '16px' }}>
      {/* Overall Statutory Compliance Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          borderRadius: 'var(--radius-md)',
          backgroundColor: isCompliant ? 'var(--status-success-bg)' : 'var(--status-error-bg)',
          border: `1px solid ${isCompliant ? 'var(--status-success-border)' : 'var(--status-error-border)'}`,
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {isCompliant ? (
            <ShieldCheck size={26} color="var(--status-success-text)" />
          ) : (
            <ShieldAlert size={26} color="var(--status-error-text)" />
          )}
          <div>
            <h4
              style={{
                margin: 0,
                fontSize: '16px',
                fontWeight: 700,
                color: isCompliant ? 'var(--status-success-text)' : 'var(--status-error-text)',
              }}
            >
              Indian Customs & DGFT Statutory Audit: {overall_government_compliance}
            </h4>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Destination Country: {destination_country || 'Worldwide'} • Evaluated HS Codes:{' '}
              {hs_codes_evaluated && hs_codes_evaluated.length > 0
                ? hs_codes_evaluated.join(', ')
                : 'Universal'}
            </div>
          </div>
        </div>

        {/* Metric summary counters */}
        <div style={{ display: 'flex', gap: '16px', textAlign: 'center' }}>
          <div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--status-success-text)' }}>
              {summary.compliant_count}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>COMPLIANT</div>
          </div>
          <div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--status-error-text)' }}>
              {summary.non_compliant_count}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>NON-COMPLIANT</div>
          </div>
          <div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--status-partial-text)' }}>
              {summary.advisory_count}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>ADVISORY</div>
          </div>
        </div>
      </div>

      {/* Authority Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', flexWrap: 'wrap' }}>
        {authorities.map((auth) => (
          <button
            key={auth}
            type="button"
            onClick={() => setAuthorityFilter(auth)}
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-blush)',
              backgroundColor: authorityFilter === auth ? 'var(--primary-blush)' : 'var(--bg-surface)',
              color: authorityFilter === auth ? '#ffffff' : 'var(--text-muted)',
              cursor: 'pointer',
            }}
          >
            {auth}
          </button>
        ))}
      </div>

      {/* Statutory Findings Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {filteredFindings.map((finding) => {
          const isComp = finding.status === 'COMPLIANT';
          const isNonComp = finding.status === 'NON_COMPLIANT';
          const isAdv = finding.status === 'ADVISORY';

          return (
            <div
              key={finding.rule_id}
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: `1px solid ${isNonComp ? 'var(--status-error-border)' : 'var(--border-blush)'}`,
                borderRadius: 'var(--radius-sm)',
                padding: '14px 18px',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              {/* Finding Title & Status Badge */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: 'var(--primary-blush)',
                      backgroundColor: 'var(--primary-blush-light)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                    }}
                  >
                    {finding.rule_id}
                  </span>
                  <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
                    {finding.rule_title}
                  </span>
                  <span
                    style={{
                      fontSize: '11px',
                      color: 'var(--text-subtle)',
                      backgroundColor: 'var(--bg-subtle)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                    }}
                  >
                    {finding.authority}
                  </span>
                </div>

                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '12px',
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
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  {isComp && <CheckCircle2 size={12} />}
                  {isNonComp && <ShieldAlert size={12} />}
                  {isAdv && <Info size={12} />}
                  {finding.status}
                </span>
              </div>

              {/* Requirement Summary */}
              <p style={{ margin: '0 0 6px 0', fontSize: '13px', color: 'var(--text-muted)' }}>
                {finding.requirement_summary}
              </p>

              {/* Observed Evidence */}
              <div
                style={{
                  padding: '8px 12px',
                  backgroundColor: 'var(--bg-subtle)',
                  borderRadius: '4px',
                  fontSize: '12px',
                  color: 'var(--text-main)',
                  marginTop: '6px',
                }}
              >
                <strong>Observed Evidence:</strong> {finding.observed_evidence}
              </div>

              {/* Required Action if Non-Compliant */}
              {finding.action_required && (
                <div
                  style={{
                    padding: '8px 12px',
                    backgroundColor: 'var(--status-error-bg)',
                    border: '1px solid var(--status-error-border)',
                    borderRadius: '4px',
                    fontSize: '12px',
                    color: 'var(--status-error-text)',
                    marginTop: '8px',
                  }}
                >
                  <strong>Action Required:</strong> {finding.action_required}
                </div>
              )}

              {/* Legal Reference & Citations */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  marginTop: '10px',
                  fontSize: '11px',
                  color: 'var(--text-subtle)',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <BookOpen size={12} /> {finding.policy_document} ({finding.para_ref})
                </span>
                {finding.source_url && (
                  <a
                    href={finding.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      color: 'var(--primary-blush)',
                      textDecoration: 'none',
                    }}
                  >
                    <span>Official Gazette / Portal</span>
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
