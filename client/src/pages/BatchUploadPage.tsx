import React, { useState } from 'react';
import { BatchUploadResponse } from '../types/batch';
import { BatchUploader } from '../components/upload/BatchUploader';
import { BatchResultsView } from '../components/results/BatchResultsView';
import { Sparkles } from 'lucide-react';

interface BatchUploadPageProps {
  onNavigateToDashboard?: () => void;
}

export const BatchUploadPage: React.FC<BatchUploadPageProps> = ({ onNavigateToDashboard }) => {
  const [batchResult, setBatchResult] = useState<BatchUploadResponse | null>(null);

  const handleBatchComplete = (response: BatchUploadResponse) => {
    setBatchResult(response);
  };

  const handleReset = () => {
    setBatchResult(null);
  };

  return (
    <div>
      {/* Header Introduction */}
      <div style={{ marginBottom: '28px', textAlign: 'center' }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'var(--primary-blush-light)',
            color: 'var(--primary-blush)',
            padding: '4px 12px',
            borderRadius: '16px',
            fontSize: '12px',
            fontWeight: 600,
            marginBottom: '10px',
          }}
        >
          <Sparkles size={14} /> AI-Powered Customs Clearance & Regulatory Verification
        </div>
        <h2
          style={{
            fontSize: '26px',
            fontWeight: 800,
            color: 'var(--text-main)',
            margin: '0 0 8px 0',
            letterSpacing: '-0.02em',
          }}
        >
          5-Document Batch Customs Audit
        </h2>
        <p
          style={{
            color: 'var(--text-muted)',
            margin: '0 auto',
            maxWidth: '640px',
            fontSize: '14px',
            lineHeight: 1.5,
          }}
        >
          Upload up to 5 export trade documents in a single batch. Automated PyMuPDF OCR, Gemini 2.5 structured
          extraction, 16-point cross-document reconciliation, and Indian Customs statutory compliance screening.
        </p>
      </div>

      {/* Main Workflow: Upload or Results */}
      {!batchResult ? (
        <BatchUploader onBatchComplete={handleBatchComplete} />
      ) : (
        <BatchResultsView
          response={batchResult}
          onReset={handleReset}
          onNavigateToDashboard={onNavigateToDashboard}
        />
      )}
    </div>
  );
};
