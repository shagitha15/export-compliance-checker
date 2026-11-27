import React, { useEffect, useState } from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { GovernmentRulesMonitorSection } from '../components/compliance/GovernmentRulesMonitorSection';
import { healthService } from '../services/healthService';
import { HealthStatus } from '../types/api';
import { CheckCircle2, XCircle } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await healthService.checkHealth();
      setHealth(res.data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to reach API server');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '24px', fontWeight: 800, margin: '0 0 6px 0', color: 'var(--text-main)' }}>
          System Architecture & Service Diagnostics
        </h2>
        <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '14px' }}>
          Real-time trade documentation compliance monitoring, database connectivity, and vector DB status.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        <Card title="Backend Health & Infrastructure" subtitle="FastAPI /api/v1 Connectivity">
          {loading && <p style={{ color: 'var(--text-muted)' }}>Checking backend health...</p>}
          {error && (
            <div
              style={{
                padding: '12px',
                backgroundColor: 'var(--status-error-bg)',
                color: 'var(--status-error-text)',
                border: '1px solid var(--status-error-border)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '13px',
                marginBottom: '14px',
              }}
            >
              <strong>Offline / Error:</strong> {error}
            </div>
          )}
          {health && (
            <div style={{ fontSize: '14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>Backend Status:</span>
                <span
                  style={{
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '4px',
                    backgroundColor:
                      health.status === 'healthy' ? 'var(--status-success-bg)' : 'var(--status-error-bg)',
                    color:
                      health.status === 'healthy' ? 'var(--status-success-text)' : 'var(--status-error-text)',
                  }}
                >
                  {health.status.toUpperCase()}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>API Version:</span>
                <span style={{ fontWeight: 600 }}>{health.version}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Environment:</span>
                <span style={{ fontWeight: 600 }}>{health.environment}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>Supabase PostgreSQL:</span>
                {(() => {
                  const dbConnected = health.components?.database ?? health.database ?? false;
                  return (
                    <span
                      style={{
                        color: dbConnected ? 'var(--status-success-text)' : 'var(--status-error-text)',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      {dbConnected ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                      {dbConnected ? 'CONNECTED' : 'STANDBY / OFFLINE'}
                    </span>
                  );
                })()}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>Pinecone Vector DB:</span>
                {(() => {
                  const vecReady = health.components?.vector_db ?? health.vectorDb ?? false;
                  return (
                    <span
                      style={{
                        color: vecReady ? 'var(--status-success-text)' : 'var(--status-error-text)',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      {vecReady ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                      {vecReady ? 'INITIALIZED' : 'STANDBY'}
                    </span>
                  );
                })()}
              </div>
            </div>
          )}
          <div style={{ marginTop: '20px' }}>
            <Button onClick={fetchHealth} disabled={loading}>
              {loading ? 'Refreshing...' : 'Re-check Status'}
            </Button>
          </div>
        </Card>

        <Card title="5-Document Compliance Engine" subtitle="Statutory Audit Framework">
          <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.8 }}>
            <li>
              <strong>Commercial Invoice (CI):</strong> Mandatory pricing, terms of delivery (Incoterms), exporter GSTIN/IEC, and LUT ARN.
            </li>
            <li>
              <strong>Packing List (PL):</strong> Gross and net weight reconciliation, packaging count, item quantity matching.
            </li>
            <li>
              <strong>Purchase Order (PO):</strong> Buyer contract, purchase order references, item line amount consistency.
            </li>
            <li>
              <strong>Shipping Bill (SB):</strong> ICEGATE customs clearance, port of loading, RITC HS code alignment.
            </li>
            <li>
              <strong>Certificate of Origin (COO):</strong> Trade agreement origin criteria, Chamber of Commerce issuance.
            </li>
          </ul>
        </Card>
      </div>

      <GovernmentRulesMonitorSection />
    </div>
  );
};
