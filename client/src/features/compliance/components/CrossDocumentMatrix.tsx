import React, { useState } from 'react';
import { CrossDocumentValidationResponse, CheckResult } from '../../../types/batch';
import { RULE_CATEGORIES, RuleCategory } from '../types';
import {
  CheckCircle2,
  XCircle,
  MinusCircle,
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  AlertCircle,
} from 'lucide-react';

interface CrossDocumentMatrixProps {
  validation?: CrossDocumentValidationResponse | null;
  onSelectDiscrepancy?: (check: CheckResult) => void;
}

export const CrossDocumentMatrix: React.FC<CrossDocumentMatrixProps> = ({
  validation,
  onSelectDiscrepancy,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<RuleCategory>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'FAIL' | 'PASS' | 'NOT_APPLICABLE'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedCheckId, setExpandedCheckId] = useState<string | null>(null);

  if (!validation) return null;

  const { cross_document_results } = validation;

  // Filter checks based on category
  const getCategoryForCheck = (checkId: string): RuleCategory => {
    if (checkId.startsWith('XDOC_INV_PO_') || checkId.startsWith('XDOC_PO_') || checkId.startsWith('XDOC_BUYER_') || checkId.startsWith('XDOC_CURR_') || checkId.startsWith('XDOC_INCO_') || checkId.startsWith('XDOC_TOTAL_VAL_')) {
      return 'INVOICE_PO';
    }
    if (checkId.startsWith('XDOC_WT_') || checkId.startsWith('XDOC_NET_WT_') || checkId.startsWith('XDOC_PKG_COUNT_') || checkId.startsWith('XDOC_ITEM_QTY_')) {
      return 'INVOICE_PACKING';
    }
    if (checkId.startsWith('XDOC_SB_')) {
      return 'INVOICE_SHIPPING';
    }
    if (checkId.startsWith('XDOC_COO_')) {
      return 'INVOICE_COO';
    }
    return 'ALL';
  };

  const filteredResults = cross_document_results.filter((check) => {
    const matchesCategory =
      selectedCategory === 'ALL' || getCategoryForCheck(check.check_id) === selectedCategory;
    const matchesStatus = statusFilter === 'ALL' || check.status === statusFilter;
    const matchesSearch =
      check.rule_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      check.check_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      check.description.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesCategory && matchesStatus && matchesSearch;
  });

  const toggleExpand = (checkId: string) => {
    setExpandedCheckId((prev) => (prev === checkId ? null : checkId));
  };

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
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '20px',
        }}
      >
        <div>
          <h3 style={{ margin: '0 0 4px 0', fontSize: '18px', fontWeight: 700, color: 'var(--text-main)' }}>
            16-Rule Cross-Document Reconciliation Matrix
          </h3>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-muted)' }}>
            Automated trade integrity audit across Commercial Invoice, Packing List, Purchase Order, Shipping Bill, and COO.
          </p>
        </div>

        {/* Search */}
        <div style={{ position: 'relative', minWidth: '220px' }}>
          <Search
            size={14}
            style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-subtle)' }}
          />
          <input
            type="text"
            placeholder="Search 16 rules..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: '8px 12px 8px 32px',
              fontSize: '13px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-blush)',
              backgroundColor: 'var(--bg-subtle)',
              color: 'var(--text-main)',
              width: '100%',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Category Pills */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          overflowX: 'auto',
          paddingBottom: '8px',
          marginBottom: '16px',
        }}
      >
        {RULE_CATEGORIES.map((cat) => {
          const isActive = selectedCategory === cat.id;
          return (
            <button
              key={cat.id}
              type="button"
              onClick={() => setSelectedCategory(cat.id)}
              style={{
                padding: '6px 14px',
                fontSize: '12px',
                fontWeight: 600,
                borderRadius: '20px',
                border: `1px solid ${isActive ? 'var(--primary-blush)' : 'var(--border-blush)'}`,
                backgroundColor: isActive ? 'var(--primary-blush)' : 'var(--bg-subtle)',
                color: isActive ? '#ffffff' : 'var(--text-muted)',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease',
              }}
            >
              {cat.label}
            </button>
          );
        })}
      </div>

      {/* Status Filter Tabs */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '16px',
          fontSize: '12px',
        }}
      >
        <span style={{ color: 'var(--text-subtle)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Filter size={12} /> Status:
        </span>
        {(['ALL', 'FAIL', 'PASS', 'NOT_APPLICABLE'] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatusFilter(s)}
            style={{
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: 600,
              borderRadius: '4px',
              border: '1px solid var(--border-blush)',
              backgroundColor: statusFilter === s ? 'var(--text-main)' : 'transparent',
              color: statusFilter === s ? '#ffffff' : 'var(--text-muted)',
              cursor: 'pointer',
            }}
          >
            {s === 'NOT_APPLICABLE' ? 'NOT APPLICABLE' : s}
          </button>
        ))}
        <span style={{ marginLeft: 'auto', color: 'var(--text-subtle)' }}>
          Showing {filteredResults.length} of {cross_document_results.length} rules
        </span>
      </div>

      {/* Reconciliation Table / Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {filteredResults.map((check) => {
          const isPass = check.status === 'PASS';
          const isFail = check.status === 'FAIL';
          const isNA = check.status === 'NOT_APPLICABLE';
          const isExpanded = expandedCheckId === check.check_id;

          return (
            <div
              key={check.check_id}
              style={{
                backgroundColor: isFail ? 'var(--status-error-bg)' : 'var(--bg-subtle)',
                border: `1px solid ${isFail ? 'var(--status-error-border)' : 'var(--border-subtle)'}`,
                borderRadius: 'var(--radius-sm)',
                padding: '12px 16px',
                transition: 'all 0.2s ease',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                }}
                onClick={() => toggleExpand(check.check_id)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: 0 }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: 'var(--primary-blush)',
                      backgroundColor: 'var(--bg-surface)',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      border: '1px solid var(--border-blush)',
                    }}
                  >
                    {check.check_id}
                  </span>
                  <span
                    style={{
                      fontSize: '13px',
                      fontWeight: 600,
                      color: 'var(--text-main)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {check.rule_name}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
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
                        : 'var(--status-neutral-bg)',
                      color: isPass
                        ? 'var(--status-success-text)'
                        : isFail
                        ? 'var(--status-error-text)'
                        : 'var(--status-neutral-text)',
                      border: `1px solid ${
                        isPass
                          ? 'var(--status-success-border)'
                          : isFail
                          ? 'var(--status-error-border)'
                          : 'var(--status-neutral-border)'
                      }`,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    {isPass && <CheckCircle2 size={12} />}
                    {isFail && <XCircle size={12} />}
                    {isNA && <MinusCircle size={12} />}
                    {check.status}
                  </span>

                  {isExpanded ? <ChevronUp size={16} color="var(--text-subtle)" /> : <ChevronDown size={16} color="var(--text-subtle)" />}
                </div>
              </div>

              {/* Description always visible */}
              <p style={{ margin: '6px 0 0 0', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                {check.description}
              </p>

              {/* Discrepancy details when expanded or failed */}
              {(isExpanded || isFail) && check.discrepancy && (
                <div
                  style={{
                    marginTop: '10px',
                    padding: '10px 14px',
                    backgroundColor: 'rgba(255, 255, 255, 0.8)',
                    borderRadius: '4px',
                    border: '1px solid var(--status-error-border)',
                    fontSize: '12px',
                    color: 'var(--status-error-text)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, marginBottom: '4px' }}>
                    <AlertCircle size={14} /> Customs Discrepancy Detected
                  </div>
                  <div>{check.discrepancy}</div>
                  {onSelectDiscrepancy && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectDiscrepancy(check);
                      }}
                      style={{
                        marginTop: '8px',
                        padding: '4px 10px',
                        fontSize: '11px',
                        fontWeight: 600,
                        backgroundColor: 'var(--primary-blush)',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                      }}
                    >
                      View Remediation & Comparison →
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {filteredResults.length === 0 && (
          <div
            style={{
              padding: '30px',
              textAlign: 'center',
              color: 'var(--text-subtle)',
              fontSize: '13px',
            }}
          >
            No compliance rules matched the selected filter criteria.
          </div>
        )}
      </div>
    </div>
  );
};
