import React, { useEffect, useState } from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { healthService } from '../services/healthService';
import { HealthStatus } from '../types/api';

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
        <h2 style={{ fontSize: '24px', fontWeight: 700, margin: '0 0 8px 0' }}>Compliance Dashboard</h2>
        <p style={{ color: '#64748b', margin: 0 }}>
          Real-time trade documentation compliance monitoring, OCR extraction, and statutory verification.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
        <Card title="System Architecture & Backend Health" subtitle="FastAPI /api/v1 Connectivity">
          {loading && <p style={{ color: '#64748b' }}>Checking backend health...</p>}
          {error && (
            <div style={{ padding: '12px', backgroundColor: '#fee2e2', color: '#991b1b', borderRadius: '6px', fontSize: '14px', marginBottom: '12px' }}>
              <strong>Offline / Error:</strong> {error}
            </div>
          )}
          {health && (
            <div style={{ fontSize: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span>Backend Status:</span>
                <strong style={{ color: health.status === 'healthy' ? '#16a34a' : '#ea580c' }}>
                  {health.status.toUpperCase()}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span>API Version:</span>
                <span>{health.version}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span>Environment:</span>
                <span>{health.environment}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span>Supabase PostgreSQL:</span>
                <span style={{ color: health.database ? '#16a34a' : '#dc2626' }}>
                  {health.database ? 'CONNECTED' : 'DISCONNECTED'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Pinecone Vector DB:</span>
                <span style={{ color: health.vectorDb ? '#16a34a' : '#dc2626' }}>
                  {health.vectorDb ? 'INITIALIZED' : 'STANDBY'}
                </span>
              </div>
            </div>
          )}
          <div style={{ marginTop: '16px' }}>
            <Button onClick={fetchHealth} disabled={loading}>
              {loading ? 'Refreshing...' : 'Re-check Status'}
            </Button>
          </div>
        </Card>

        <Card title="Documents Monitored" subtitle="Standard Trade Document Categories">
          <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '14px', color: '#334155' }}>
            <li style={{ marginBottom: '6px' }}>Commercial Invoice (CI)</li>
            <li style={{ marginBottom: '6px' }}>Packing List (PL)</li>
            <li style={{ marginBottom: '6px' }}>Purchase Order (PO)</li>
            <li style={{ marginBottom: '6px' }}>Shipping Bill (SB)</li>
            <li>Certificate of Origin (COO)</li>
          </ul>
        </Card>
      </div>
    </div>
  );
};
