import React from 'react';
import { CheckResult } from '../../../types/batch';
import {
  ShieldAlert,
  Check,
  HelpCircle,
} from 'lucide-react';

interface DiscrepancyInspectorProps {
  discrepancies: CheckResult[];
  onDismiss?: () => void;
}

export const DiscrepancyInspector: React.FC<DiscrepancyInspectorProps> = ({
  discrepancies,
}) => {
  if (!discrepancies || discrepancies.length === 0) {
    return (
      <div
        style={{
          backgroundColor: 'var(--status-success-bg)',
          border: '1px solid var(--status-success-border)',
          borderRadius: 'var(--radius-lg)',
          padding: '24px',
          textAlign: 'center',
          color: 'var(--status-success-text)',
          marginBottom: '24px',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div
          style={{
            width: '42px',
            height: '42px',
            borderRadius: '50%',
            backgroundColor: '#ffffff',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '10px',
            color: 'var(--status-success-text)',
          }}
        >
          <Check size={22} />
        </div>
        <h4 style={{ margin: '0 0 4px 0', fontSize: '16px', fontWeight: 700 }}>
          Zero Cross-Document Discrepancies
        </h4>
        <p style={{ margin: 0, fontSize: '13px', opacity: 0.9 }}>
          All evaluated trade documents strictly reconcile across values, currencies, quantities, weights, and entity identifiers.
        </p>
      </div>
    );
  }

  const getRemediationAdvice = (checkId: string): string => {
    switch (checkId) {
      case 'XDOC_TOTAL_VAL_006':
        return 'Reconcile contract pricing. If invoice reflects agreed modifications, obtain a revised buyer Purchase Order amendment or formal contract addendum before customs filing.';
      case 'XDOC_CURR_004':
        return 'Align currency codes across Commercial Invoice and Purchase Order. Indian Customs requires valuation in the precise currency declared on the shipping bill.';
      case 'XDOC_WT_007':
        return 'Re-weigh consignment packages. Update Packing List gross weights or re-issue Commercial Invoice so tare and gross weights match within acceptable customs tolerance (<1%).';
      case 'XDOC_INCO_005':
        return 'Harmonize Incoterms 2020 (e.g. FOB vs CIF). Freight and insurance declarations on the Shipping Bill depend strictly on the agreed terms of delivery.';
      case 'XDOC_SB_INV_011':
        return 'File an amendment under Section 149 of the Customs Act 1962 on ICEGATE to correct the cited Commercial Invoice number before cargo assessment.';
      default:
        return 'Review the cited trade documents and align all data fields before filing export declarations with Customs authorities.';
    }
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--status-error-border)',
        padding: '24px',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '24px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
        <div
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            backgroundColor: 'var(--status-error-bg)',
            color: 'var(--status-error-text)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <ShieldAlert size={20} />
        </div>
        <div>
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--status-error-text)' }}>
            Active Discrepancies Requiring Remediation ({discrepancies.length})
          </h3>
          <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>
            Field discrepancies will trigger ICEGATE assessment queries, duty re-calculation, or cargo examination holds.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {discrepancies.map((d, idx) => (
          <div
            key={d.check_id || idx}
            style={{
              padding: '16px',
              backgroundColor: 'var(--status-error-bg)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--status-error-border)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  backgroundColor: '#ffffff',
                  color: 'var(--status-error-text)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  border: '1px solid var(--status-error-border)',
                }}
              >
                {d.check_id}
              </span>
              <strong style={{ fontSize: '14px', color: 'var(--status-error-text)' }}>
                {d.rule_name}
              </strong>
            </div>

            <div style={{ fontSize: '13px', color: 'var(--text-main)', marginBottom: '10px' }}>
              <strong>Observed Discrepancy:</strong> {d.discrepancy || d.description}
            </div>

            {/* Recommended Customs Action */}
            <div
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-blush)',
                fontSize: '12px',
                color: 'var(--text-main)',
              }}
            >
              <div style={{ fontWeight: 600, color: 'var(--primary-blush)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <HelpCircle size={14} /> Customs Remediation Procedure:
              </div>
              <div style={{ lineHeight: 1.5 }}>
                {getRemediationAdvice(d.check_id)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
