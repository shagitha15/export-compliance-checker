import React from 'react';
import { SAMPLE_SHIPMENTS } from '../../../services/complianceService';
import { ShipmentScenario } from '../types';
import { Package, Play } from 'lucide-react';

interface ShipmentScenarioSelectorProps {
  selectedScenarioId: string;
  onSelectScenario: (scenario: ShipmentScenario) => void;
  onRunAudit: () => void;
  isLoading: boolean;
}

export const ShipmentScenarioSelector: React.FC<ShipmentScenarioSelectorProps> = ({
  selectedScenarioId,
  onSelectScenario,
  onRunAudit,
  isLoading,
}) => {
  return (
    <div
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border-blush)',
        padding: '20px 24px',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '22px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '280px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: 'var(--primary-blush-light)',
              color: 'var(--primary-blush)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <Package size={20} />
          </div>

          <div style={{ flex: 1 }}>
            <label
              htmlFor="scenario-select"
              style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: 'var(--text-subtle)', textTransform: 'uppercase', marginBottom: '2px' }}
            >
              Select Trade Shipment Scenario
            </label>
            <select
              id="scenario-select"
              value={selectedScenarioId}
              onChange={(e) => {
                const found = SAMPLE_SHIPMENTS.find((s) => s.id === e.target.value);
                if (found) onSelectScenario(found);
              }}
              style={{
                width: '100%',
                maxWidth: '480px',
                padding: '6px 10px',
                fontSize: '13px',
                fontWeight: 600,
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-blush)',
                backgroundColor: 'var(--bg-subtle)',
                color: 'var(--text-main)',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              {SAMPLE_SHIPMENTS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.expectedStatus})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Action Button */}
        <button
          type="button"
          onClick={onRunAudit}
          disabled={isLoading}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 20px',
            fontSize: '14px',
            fontWeight: 700,
            color: '#ffffff',
            backgroundColor: isLoading ? 'var(--text-subtle)' : 'var(--primary-blush)',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            boxShadow: 'var(--shadow-sm)',
            transition: 'all 0.2s ease',
          }}
        >
          <Play size={15} />
          <span>{isLoading ? 'Auditing...' : 'Run Compliance Audit'}</span>
        </button>
      </div>
    </div>
  );
};
