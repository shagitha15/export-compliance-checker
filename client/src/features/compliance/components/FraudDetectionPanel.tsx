import React from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Fingerprint,
  Info,
} from 'lucide-react';
import { FraudAnalysisReport, DocumentAnomaly } from '../types';

interface FraudDetectionPanelProps {
  fraudReport: FraudAnalysisReport | null;
  loading?: boolean;
}

export const FraudDetectionPanel: React.FC<FraudDetectionPanelProps> = ({
  fraudReport,
  loading = false,
}) => {
  if (loading) {
    return (
      <div
        style={{
          padding: '24px',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-blush)',
          boxShadow: 'var(--shadow-sm)',
          marginBottom: '24px',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: '13px',
        }}
      >
        <Fingerprint className="animate-spin" size={24} style={{ margin: '0 auto 8px', color: 'var(--primary-blush)' }} />
        Running digital forensics, tax identifier checksums, and plausibility verification...
      </div>
    );
  }

  if (!fraudReport) return null;

  const score = fraudReport.overall_authenticity_score;
  const risk = fraudReport.overall_risk_level;
  const isGenuine = risk === 'GENUINE';
  const isHighRisk = risk === 'HIGH_RISK';

  const riskBadgeConfig = isGenuine
    ? {
        bg: 'rgba(22, 163, 74, 0.1)',
        border: 'rgba(22, 163, 74, 0.3)',
        text: '#15803d',
        icon: ShieldCheck,
        label: 'GENUINE • LOW RISK',
      }
    : isHighRisk
    ? {
        bg: 'rgba(220, 38, 38, 0.1)',
        border: 'rgba(220, 38, 38, 0.3)',
        text: '#b91c1c',
        icon: ShieldAlert,
        label: 'HIGH FRAUD RISK • ANOMALIES DETECTED',
      }
    : {
        bg: 'rgba(217, 119, 6, 0.1)',
        border: 'rgba(217, 119, 6, 0.3)',
        text: '#b45309',
        icon: AlertTriangle,
        label: 'SUSPICIOUS • AUDIT ADVISED',
      };

  const RiskIcon = riskBadgeConfig.icon;

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return { bg: '#fee2e2', text: '#991b1b', border: '#fca5a5' };
      case 'HIGH':
        return { bg: '#ffedd5', text: '#9a3412', border: '#fdba74' };
      case 'MEDIUM':
        return { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' };
      default:
        return { bg: '#f3f4f6', text: '#374151', border: '#e5e7eb' };
    }
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-blush)',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '24px',
        overflow: 'hidden',
      }}
    >
      {/* Header Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-blush)',
          backgroundColor: 'var(--bg-main)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              backgroundColor: 'var(--primary-blush-light)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--primary-blush)',
            }}
          >
            <Fingerprint size={18} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: 'var(--text-main)' }}>
              Document Authenticity & Tamper Forensics
            </h3>
            <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>
              GSTIN Checksum (Mod-36), Arithmetic Integrity, Weight Law Physics & Temporal Chronology
            </p>
          </div>
        </div>

        {/* Risk Badge & KPI */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '16px',
              backgroundColor: riskBadgeConfig.bg,
              border: `1px solid ${riskBadgeConfig.border}`,
              color: riskBadgeConfig.text,
              fontSize: '12px',
              fontWeight: 700,
              letterSpacing: '0.02em',
            }}
          >
            <RiskIcon size={14} /> {riskBadgeConfig.label}
          </div>

          <div
            style={{
              padding: '4px 12px',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-blush)',
              textAlign: 'center',
            }}
          >
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'block', textTransform: 'uppercase', fontWeight: 600 }}>
              Authenticity
            </span>
            <span style={{ fontSize: '15px', fontWeight: 800, color: riskBadgeConfig.text }}>
              {score}%
            </span>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div style={{ padding: '18px 20px' }}>
        {fraudReport.anomalies.length === 0 ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '14px 16px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'rgba(22, 163, 74, 0.05)',
              border: '1px solid rgba(22, 163, 74, 0.2)',
            }}
          >
            <ShieldCheck size={20} style={{ color: '#16a34a', flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#15803d' }}>
                Zero Tamper Alerts Detected
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                All shipment trade documents exhibit verified digital integrity, valid 15-character GSTIN Mod-36 checksums,
                consistent arithmetic line-item extensions, and plausible physical weight ratios.
              </div>
            </div>
          </div>
        ) : (
          <div>
            <div
              style={{
                fontSize: '12px',
                fontWeight: 700,
                color: isHighRisk ? '#b91c1c' : '#b45309',
                marginBottom: '10px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <AlertTriangle size={14} />
              {fraudReport.anomalies.length} Forensic Anomalies Identified ({fraudReport.critical_anomalies} Critical)
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {fraudReport.anomalies.map((anomaly: DocumentAnomaly) => {
                const badge = getSeverityBadge(anomaly.severity);
                return (
                  <div
                    key={anomaly.anomaly_id}
                    style={{
                      padding: '12px 14px',
                      borderRadius: 'var(--radius-sm)',
                      border: `1px solid ${badge.border}`,
                      backgroundColor: badge.bg,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 800,
                            padding: '2px 8px',
                            borderRadius: '4px',
                            backgroundColor: '#ffffff',
                            color: badge.text,
                            border: `1px solid ${badge.border}`,
                          }}
                        >
                          {anomaly.severity}
                        </span>
                        <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-main)' }}>
                          [{anomaly.anomaly_id}] {anomaly.rule_name}
                        </span>
                      </div>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
                        {anomaly.document_type || 'Shipment Set'}
                      </span>
                    </div>

                    <div style={{ fontSize: '12px', color: 'var(--text-main)', marginTop: '2px' }}>
                      <strong>Observed:</strong> {anomaly.evidence}
                    </div>

                    {anomaly.remediation && (
                      <div
                        style={{
                          fontSize: '11px',
                          color: 'var(--text-muted)',
                          marginTop: '4px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <Info size={12} />
                        <span><strong>Remediation:</strong> {anomaly.remediation}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
