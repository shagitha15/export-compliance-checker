import React, { useState } from 'react';
import { CrossDocumentValidationResponse } from '../../types/batch';
import {
  CheckCircle2,
  XCircle,
  MinusCircle,
  AlertTriangle,
  Search,
} from 'lucide-react';

interface CrossDocumentViewProps {
  validation?: CrossDocumentValidationResponse | null;
}

export const CrossDocumentView: React.FC<CrossDocumentViewProps> = ({ validation }) => {
  const [filter, setFilter] = useState<'ALL' | 'FAIL' | 'PASS' | 'NOT_APPLICABLE'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  if (!validation) {
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
        No cross-document validation data available for this batch.
      </div>
    );
  }

  const { overall_compliance_status, summary, cross_document_results, documents_missing } =
    validation;
  const isOverallPass = overall_compliance_status === 'PASS';

  const filteredChecks = cross_document_results.filter((check) => {
    const isCheckNA = check.status === 'NOT APPLICABLE' || check.status === 'NOT_APPLICABLE';
    const matchesFilter =
      filter === 'ALL' || (filter === 'NOT_APPLICABLE' ? isCheckNA : check.status === filter);
    const q = searchQuery.toLowerCase();
    const detailText = (check.description || check.message || '').toLowerCase();
    const matchesSearch =
      check.rule_name.toLowerCase().includes(q) ||
      check.check_id.toLowerCase().includes(q) ||
      detailText.includes(q);
    return matchesFilter && matchesSearch;
  });

  return (
    <div style={{ marginTop: '16px' }}>
      {/* Overall Status Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          borderRadius: 'var(--radius-md)',
          backgroundColor: isOverallPass ? 'var(--status-success-bg)' : 'var(--status-error-bg)',
          border: `1px solid ${isOverallPass ? 'var(--status-success-border)' : 'var(--status-error-border)'}`,
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {isOverallPass ? (
            <CheckCircle2 size={24} color="var(--status-success-text)" />
          ) : (
            <XCircle size={24} color="var(--status-error-text)" />
          )}
          <div>
            <h4
              style={{
                margin: 0,
                fontSize: '16px',
                fontWeight: 700,
                color: isOverallPass ? 'var(--status-success-text)' : 'var(--status-error-text)',
              }}
            >
              Cross-Document Reconciliation: {overall_compliance_status}
            </h4>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Audit ID: {validation.audit_id} • Evaluated at {new Date(validation.audit_timestamp).toLocaleTimeString()}
            </div>
          </div>
        </div>

        {/* Metrics summary */}
        <div style={{ display: 'flex', gap: '16px', textAlign: 'center' }}>
          <div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--status-success-text)' }}>
              {summary.passed}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>PASSED</div>
          </div>
          <div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--status-error-text)' }}>
              {summary.failed}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>FAILED</div>
          </div>
          <div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-subtle)' }}>
              {summary.not_applicable}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>N/A</div>
          </div>
        </div>
      </div>

      {/* Missing documents callout if any */}
      {documents_missing && documents_missing.length > 0 && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: 'var(--status-partial-bg)',
            border: '1px solid var(--status-partial-border)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '13px',
            color: 'var(--status-partial-text)',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <AlertTriangle size={16} />
          <span>
            <strong>Omitted Trade Documents:</strong>{' '}
            {documents_missing.join(', ')}. Rules depending on these documents evaluated to NOT APPLICABLE.
          </span>
        </div>
      )}

      {/* Filter and Search Controls */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '14px',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', gap: '8px' }}>
          {(['ALL', 'FAIL', 'PASS', 'NOT_APPLICABLE'] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setFilter(s)}
              style={{
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-blush)',
                backgroundColor: filter === s ? 'var(--primary-blush)' : 'var(--bg-surface)',
                color: filter === s ? '#ffffff' : 'var(--text-muted)',
                cursor: 'pointer',
              }}
            >
              {s === 'NOT_APPLICABLE' ? 'N/A' : s}
            </button>
          ))}
        </div>

        <div style={{ position: 'relative', minWidth: '220px' }}>
          <Search
            size={14}
            style={{ position: 'absolute', left: '10px', top: '9px', color: 'var(--text-subtle)' }}
          />
          <input
            type="text"
            placeholder="Search checks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: '6px 10px 6px 30px',
              fontSize: '13px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-blush)',
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-main)',
              width: '100%',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Rules Evaluation List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {filteredChecks.map((check) => {
          const isPass = check.status === 'PASS';
          const isFail = check.status === 'FAIL';
          const isWarn = check.status === 'WARNING';
          const isNA = check.status === 'NOT APPLICABLE' || check.status === 'NOT_APPLICABLE';
          const explanation = check.description || check.message || '';

          return (
            <div
              key={check.check_id}
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: `1px solid ${
                  isFail
                    ? 'var(--status-error-border)'
                    : isWarn
                    ? 'var(--status-partial-border)'
                    : 'var(--border-blush)'
                }`,
                borderRadius: 'var(--radius-sm)',
                padding: '12px 16px',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
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
                    {check.check_id}
                  </span>
                  <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
                    {check.rule_name}
                  </span>
                  {check.documents_involved && check.documents_involved.length > 0 && (
                    <span style={{ fontSize: '11px', color: 'var(--text-subtle)' }}>
                      ({check.documents_involved.join(' vs ')})
                    </span>
                  )}
                </div>

                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '12px',
                    backgroundColor: isPass
                      ? 'var(--status-success-bg)'
                      : isFail
                      ? 'var(--status-error-bg)'
                      : isWarn
                      ? 'var(--status-partial-bg)'
                      : 'var(--status-neutral-bg)',
                    color: isPass
                      ? 'var(--status-success-text)'
                      : isFail
                      ? 'var(--status-error-text)'
                      : isWarn
                      ? 'var(--status-partial-text)'
                      : 'var(--status-neutral-text)',
                    border: `1px solid ${
                      isPass
                        ? 'var(--status-success-border)'
                        : isFail
                        ? 'var(--status-error-border)'
                        : isWarn
                        ? 'var(--status-partial-border)'
                        : 'var(--status-neutral-border)'
                    }`,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  {isPass && <CheckCircle2 size={12} />}
                  {isFail && <XCircle size={12} />}
                  {isWarn && <AlertTriangle size={12} />}
                  {isNA && <MinusCircle size={12} />}
                  {check.status}
                </span>
              </div>

              {explanation && (
                <p style={{ margin: '6px 0 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
                  {explanation}
                </p>
              )}

              {check.discrepancy && (
                <div
                  style={{
                    marginTop: '8px',
                    padding: '8px 12px',
                    backgroundColor: 'var(--status-error-bg)',
                    border: '1px solid var(--status-error-border)',
                    borderRadius: '4px',
                    fontSize: '12px',
                    color: 'var(--status-error-text)',
                  }}
                >
                  <strong>Discrepancy:</strong>{' '}
                  {typeof check.discrepancy === 'string'
                    ? check.discrepancy
                    : JSON.stringify(check.discrepancy)}
                </div>
              )}
            </div>
          );
        })}

        {filteredChecks.length === 0 && (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-subtle)' }}>
            No checks matching current filter/search.
          </div>
        )}
      </div>
    </div>
  );
};
