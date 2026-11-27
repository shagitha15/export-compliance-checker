import React, { useState } from 'react';
import { CrossDocumentValidationResponse } from '../../types/batch';
import { CheckCircle2, XCircle, AlertTriangle, MinusCircle, Search } from 'lucide-react';

interface CrossValidationSectionProps {
  validation?: CrossDocumentValidationResponse | null;
  onGoToUpload: () => void;
}

type DisplayStatus = 'Match' | 'Mismatch' | 'Missing' | 'Not Applicable';

interface UnifiedRuleRow {
  id: string;
  stage: 'Stage 1: Intra-Document' | 'Stage 2: Cross-Document';
  ruleName: string;
  documentsInvolved: string[];
  fieldName: string;
  status: DisplayStatus;
  rawStatus: string;
  expectedValue?: any;
  observedValues?: Record<string, any>;
  explanation: string;
}

function classifyRuleStatus(
  rawStatus: string,
  message: string,
  checkIdOrName: string
): DisplayStatus {
  const upper = (rawStatus || '').toUpperCase();
  if (upper === 'PASS') return 'Match';
  if (upper === 'FAIL') {
    if (
      checkIdOrName.includes('mandatory_fields') ||
      message.toLowerCase().includes('missing essential') ||
      message.toLowerCase().includes('missing packing list')
    ) {
      return 'Missing';
    }
    return 'Mismatch';
  }
  if (
    message.toLowerCase().includes('missing') ||
    message.toLowerCase().includes('omitted')
  ) {
    return 'Missing';
  }
  return 'Not Applicable';
}

export const CrossValidationSection: React.FC<CrossValidationSectionProps> = ({
  validation,
  onGoToUpload,
}) => {
  const [statusFilter, setStatusFilter] = useState<'ALL' | DisplayStatus>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  if (!validation) {
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
          No cross-document validation results yet. Upload documents and run the compliance check first.
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

  const unifiedRows: UnifiedRuleRow[] = [
    ...(validation.intra_document_results || []).map((r, idx) => {
      const msg = r.message || r.discrepancy || '';
      const name = r.rule_name || r.check_name || `Intra-Document Check #${idx + 1}`;
      return {
        id: r.check_id || `INTRA_${idx + 1}_${r.document_type.replace(/\s+/g, '_').toUpperCase()}`,
        stage: 'Stage 1: Intra-Document' as const,
        ruleName: `${r.document_type}: ${name.replace(/_/g, ' ')}`,
        documentsInvolved: [r.document_type],
        fieldName: r.check_name || 'internal_integrity',
        status: classifyRuleStatus(r.status, msg, name),
        rawStatus: r.status,
        explanation: msg,
      };
    }),
    ...(validation.cross_document_results || []).map((c) => {
      const msg = c.discrepancy || c.message || c.description || '';
      return {
        id: c.check_id,
        stage: 'Stage 2: Cross-Document' as const,
        ruleName: c.rule_name,
        documentsInvolved: c.documents_involved || [],
        fieldName: c.field_name || 'cross_document_field',
        status: classifyRuleStatus(c.status, msg, c.check_id),
        rawStatus: c.status,
        expectedValue: c.expected_value,
        observedValues: c.observed_values,
        explanation: msg,
      };
    }),
  ];

  const matchCount = unifiedRows.filter((r) => r.status === 'Match').length;
  const mismatchCount = unifiedRows.filter((r) => r.status === 'Mismatch').length;
  const missingCount = unifiedRows.filter((r) => r.status === 'Missing').length;
  const naCount = unifiedRows.filter((r) => r.status === 'Not Applicable').length;

  const filtered = unifiedRows.filter((row) => {
    const matchesStatus = statusFilter === 'ALL' || row.status === statusFilter;
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      row.id.toLowerCase().includes(q) ||
      row.ruleName.toLowerCase().includes(q) ||
      row.fieldName.toLowerCase().includes(q) ||
      row.documentsInvolved.join(' ').toLowerCase().includes(q) ||
      row.explanation.toLowerCase().includes(q);
    return matchesStatus && matchesSearch;
  });

  const badgeColors = (status: DisplayStatus) => {
    if (status === 'Match') {
      return {
        bg: 'var(--status-success-bg)',
        border: 'var(--status-success-border)',
        text: 'var(--status-success-text)',
        icon: <CheckCircle2 size={12} />,
      };
    }
    if (status === 'Mismatch') {
      return {
        bg: 'var(--status-error-bg)',
        border: 'var(--status-error-border)',
        text: 'var(--status-error-text)',
        icon: <XCircle size={12} />,
      };
    }
    if (status === 'Missing') {
      return {
        bg: 'var(--status-partial-bg)',
        border: 'var(--status-partial-border)',
        text: 'var(--status-partial-text)',
        icon: <AlertTriangle size={12} />,
      };
    }
    return {
      bg: 'var(--status-neutral-bg)',
      border: 'var(--status-neutral-border)',
      text: 'var(--status-neutral-text)',
      icon: <MinusCircle size={12} />,
    };
  };

  return (
    <div className="fade-in">
      {/* Header & Summary Card */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-blush)',
          borderRadius: 'var(--radius-lg)',
          padding: '20px 24px',
          boxShadow: 'var(--shadow-sm)',
          marginBottom: '18px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 700, color: '#102A43' }}>
              Reconciliation Summary ({unifiedRows.length} Evaluated Rules)
            </h3>
            <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#456B8B' }}>
              Stage 1 intra-document math &amp; Stage 2 cross-document comparisons • Audit ID: {validation.audit_id}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '14px', textAlign: 'center' }}>
            <div>
              <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--status-success-text)' }}>{matchCount}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Match</div>
            </div>
            <div>
              <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--status-error-text)' }}>{mismatchCount}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Mismatch</div>
            </div>
            <div>
              <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--status-partial-text)' }}>{missingCount}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Missing</div>
            </div>
            <div>
              <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-subtle)' }}>{naCount}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>N/A</div>
            </div>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div
          style={{
            marginTop: '16px',
            paddingTop: '14px',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '10px',
          }}
        >
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {(['ALL', 'Mismatch', 'Missing', 'Match', 'Not Applicable'] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setStatusFilter(s)}
                style={{
                  padding: '5px 12px',
                  fontSize: '12px',
                  fontWeight: 600,
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-blush)',
                  backgroundColor: statusFilter === s ? 'var(--primary-blush)' : 'var(--bg-subtle)',
                  color: statusFilter === s ? '#ffffff' : 'var(--text-muted)',
                  cursor: 'pointer',
                }}
              >
                {s}
              </button>
            ))}
          </div>

          <div style={{ position: 'relative', minWidth: '220px' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '9px', color: 'var(--text-subtle)' }} />
            <input
              type="text"
              placeholder="Search rules, fields, documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                padding: '6px 10px 6px 30px',
                fontSize: '12.5px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-blush)',
                backgroundColor: 'var(--bg-subtle)',
                color: 'var(--text-main)',
                width: '100%',
              }}
            />
          </div>
        </div>
      </div>

      {/* Rule Rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {filtered.map((row) => {
          const style = badgeColors(row.status);
          const observedEntries = row.observedValues ? Object.entries(row.observedValues) : [];

          return (
            <div
              key={row.id}
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: `1px solid ${row.status === 'Mismatch' ? 'var(--status-error-border)' : 'var(--border-blush)'}`,
                borderRadius: 'var(--radius-md)',
                padding: '14px 18px',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: 'var(--primary-blush)',
                      backgroundColor: 'var(--primary-blush-light)',
                      padding: '2px 7px',
                      borderRadius: '4px',
                    }}
                  >
                    {row.id}
                  </span>
                  <strong style={{ fontSize: '14px', color: 'var(--text-main)' }}>{row.ruleName}</strong>
                  <span style={{ fontSize: '11px', color: 'var(--text-subtle)' }}>
                    • {row.stage}
                  </span>
                </div>

                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '3px 10px',
                    borderRadius: '12px',
                    backgroundColor: style.bg,
                    color: style.text,
                    border: `1px solid ${style.border}`,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  {style.icon} {row.status}
                </span>
              </div>

              <div style={{ marginTop: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
                <strong>Documents:</strong> {row.documentsInvolved.join(', ') || 'N/A'} &nbsp;|&nbsp;{' '}
                <strong>Field:</strong> <code>{row.fieldName}</code>
              </div>

              <p style={{ margin: '6px 0 0 0', fontSize: '13px', color: 'var(--text-main)' }}>
                {row.explanation}
              </p>

              {(row.expectedValue !== undefined && row.expectedValue !== null) || observedEntries.length > 0 ? (
                <div
                  style={{
                    marginTop: '10px',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                  }}
                >
                  {row.expectedValue !== undefined && row.expectedValue !== null && (
                    <div>
                      <strong>Expected / Benchmark Value:</strong>{' '}
                      {typeof row.expectedValue === 'object'
                        ? JSON.stringify(row.expectedValue)
                        : String(row.expectedValue)}
                    </div>
                  )}
                  {observedEntries.length > 0 && (
                    <div>
                      <strong>Detected Values by Document:</strong>{' '}
                      {observedEntries
                        .map(
                          ([docName, val]) =>
                            `${docName}: ${typeof val === 'object' ? JSON.stringify(val) : String(val)}`
                        )
                        .join(' | ')}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
};
