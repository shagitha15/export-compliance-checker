import React, { useState, useEffect, useMemo } from 'react';
import { BatchUploadResponse } from '../../types/batch';
import { FraudAnalysisReport } from '../../features/compliance/types';
import { complianceService } from '../../services/complianceService';
import { batchService } from '../../services/batchService';
import { DocumentCard } from './DocumentCard';
import { CrossDocumentView } from './CrossDocumentView';
import { GovernmentRulesView } from './GovernmentRulesView';
import { FraudDetectionPanel } from '../../features/compliance/components/FraudDetectionPanel';
import {
  Layers,
  Scale,
  ShieldCheck,
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  XCircle,
  FileDown,
  LayoutDashboard,
  ShieldAlert,
} from 'lucide-react';

interface BatchResultsViewProps {
  response: BatchUploadResponse;
  onReset: () => void;
  onNavigateToDashboard?: () => void;
}

export const BatchResultsView: React.FC<BatchResultsViewProps> = ({
  response,
  onReset,
  onNavigateToDashboard,
}) => {
  const [activeTab, setActiveTab] = useState<
    'documents' | 'cross_validation' | 'government_rules' | 'fraud_forensics'
  >('documents');
  const [fraudReport, setFraudReport] = useState<FraudAnalysisReport | null>(null);
  const [fraudLoading, setFraudLoading] = useState<boolean>(false);
  const [downloadingPdf, setDownloadingPdf] = useState<boolean>(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  const {
    batch_id,
    timestamp,
    batch_status,
    summary,
    documents,
    cross_document_validation,
    government_compliance,
  } = response;

  const extractedDocsMap = useMemo(() => {
    const map: Record<string, any> = {};
    for (const doc of documents) {
      if (doc.status === 'SUCCESS' && doc.document_type && doc.extracted_data) {
        map[doc.document_type] = doc.extracted_data;
      }
    }
    return map;
  }, [documents]);

  useEffect(() => {
    let active = true;
    if (Object.keys(extractedDocsMap).length === 0) {
      setFraudReport(null);
      return;
    }

    setFraudLoading(true);
    complianceService
      .inspectFraud(extractedDocsMap)
      .then((res) => {
        if (active) setFraudReport(res);
      })
      .catch(() => {
        if (active) setFraudReport(null);
      })
      .finally(() => {
        if (active) setFraudLoading(false);
      });

    return () => {
      active = false;
    };
  }, [extractedDocsMap]);

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    setPdfError(null);
    try {
      await batchService.downloadBatchPdfReport(response, fraudReport);
    } catch (err: any) {
      setPdfError(err.message || 'Unable to generate PDF compliance report.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const isSuccess = batch_status === 'SUCCESS';
  const isPartial = batch_status === 'PARTIAL_SUCCESS';
  const isFailed = batch_status === 'FAILED';

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto' }} className="fade-in">
      {/* Top Banner */}
      <div
        style={{
          padding: '24px',
          borderRadius: 'var(--radius-lg)',
          backgroundColor: isSuccess
            ? 'var(--status-success-bg)'
            : isPartial
            ? 'var(--status-partial-bg)'
            : 'var(--status-error-bg)',
          border: `1px solid ${
            isSuccess
              ? 'var(--status-success-border)'
              : isPartial
              ? 'var(--status-partial-border)'
              : 'var(--status-error-border)'
          }`,
          boxShadow: 'var(--shadow-md)',
          marginBottom: '24px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                backgroundColor: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: isSuccess
                  ? 'var(--status-success-text)'
                  : isPartial
                  ? 'var(--status-partial-text)'
                  : 'var(--status-error-text)',
                boxShadow: '0 2px 6px rgba(0,0,0,0.06)',
              }}
            >
              {isSuccess && <CheckCircle size={28} />}
              {isPartial && <AlertTriangle size={28} />}
              {isFailed && <XCircle size={28} />}
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <h3
                  style={{
                    margin: 0,
                    fontSize: '20px',
                    fontWeight: 700,
                    color: isSuccess
                      ? 'var(--status-success-text)'
                      : isPartial
                      ? 'var(--status-partial-text)'
                      : 'var(--status-error-text)',
                  }}
                >
                  Batch Ingestion: {batch_status.replace('_', ' ')}
                </h3>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    backgroundColor: 'rgba(0,0,0,0.06)',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    color: 'var(--text-main)',
                  }}
                >
                  {batch_id}
                </span>
              </div>

              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Completed at {new Date(timestamp).toLocaleString()} • {summary.successful_count} of{' '}
                {summary.total_files_received} documents successfully parsed
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              id="batch-download-pdf-btn"
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 16px',
                fontSize: '14px',
                fontWeight: 600,
                backgroundColor: 'var(--primary-blush)',
                color: '#ffffff',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                cursor: downloadingPdf ? 'not-allowed' : 'pointer',
                opacity: downloadingPdf ? 0.7 : 1,
                boxShadow: '0 2px 6px rgba(184, 50, 83, 0.25)',
              }}
            >
              <FileDown size={15} /> {downloadingPdf ? 'Generating PDF...' : 'Download PDF Report'}
            </button>

            {onNavigateToDashboard && (
              <button
                type="button"
                id="batch-open-dashboard-btn"
                onClick={onNavigateToDashboard}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 14px',
                  fontSize: '13px',
                  fontWeight: 600,
                  backgroundColor: 'var(--bg-surface)',
                  color: 'var(--text-main)',
                  border: '1px solid var(--border-blush)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  boxShadow: 'var(--shadow-sm)',
                }}
              >
                <LayoutDashboard size={15} /> Validation Dashboard
              </button>
            )}

            <button
              type="button"
              onClick={onReset}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 16px',
                fontSize: '14px',
                fontWeight: 600,
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--primary-blush)',
                border: '1px solid var(--border-blush)',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <RotateCcw size={15} /> Upload Another Batch
            </button>
          </div>
        </div>

        {pdfError && (
          <div
            style={{
              marginTop: '12px',
              padding: '10px 14px',
              backgroundColor: 'var(--status-error-bg)',
              border: '1px solid var(--status-error-border)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--status-error-text)',
              fontSize: '13px',
            }}
          >
            <strong>PDF Export Error:</strong> {pdfError}
          </div>
        )}

        {/* Metrics Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
            gap: '12px',
            marginTop: '20px',
            paddingTop: '16px',
            borderTop: '1px solid rgba(0,0,0,0.06)',
          }}
        >
          <div style={{ backgroundColor: 'rgba(255,255,255,0.7)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Files Received</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-main)' }}>
              {summary.total_files_received}
            </div>
          </div>

          <div style={{ backgroundColor: 'rgba(255,255,255,0.7)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: '12px', color: 'var(--status-success-text)' }}>Successful</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--status-success-text)' }}>
              {summary.successful_count}
            </div>
          </div>

          <div style={{ backgroundColor: 'rgba(255,255,255,0.7)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: '12px', color: 'var(--status-error-text)' }}>Failed</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--status-error-text)' }}>
              {summary.failed_count}
            </div>
          </div>

          <div style={{ backgroundColor: 'rgba(255,255,255,0.7)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: '12px', color: 'var(--status-partial-text)' }}>Duplicates</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--status-partial-text)' }}>
              {summary.duplicate_count}
            </div>
          </div>
        </div>

        {/* Document Categories Detected vs Missing */}
        <div style={{ marginTop: '16px', fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div>
            <strong style={{ color: 'var(--text-main)' }}>Detected Types: </strong>
            {summary.detected_document_types.length > 0 ? (
              summary.detected_document_types.map((type) => (
                <span
                  key={type}
                  style={{
                    display: 'inline-block',
                    backgroundColor: 'var(--bg-surface)',
                    color: 'var(--primary-blush)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    marginRight: '6px',
                    fontWeight: 600,
                    border: '1px solid var(--border-blush)',
                  }}
                >
                  ✓ {type}
                </span>
              ))
            ) : (
              <span style={{ color: 'var(--text-muted)' }}>None</span>
            )}
          </div>

          {summary.missing_document_types.length > 0 && (
            <div>
              <strong style={{ color: 'var(--text-muted)' }}>Missing Types: </strong>
              {summary.missing_document_types.map((type) => (
                <span
                  key={type}
                  style={{
                    display: 'inline-block',
                    backgroundColor: 'rgba(0,0,0,0.04)',
                    color: 'var(--text-subtle)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    marginRight: '6px',
                  }}
                >
                  - {type}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-blush)',
          marginBottom: '20px',
          gap: '8px',
          flexWrap: 'wrap',
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab('documents')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 18px',
            fontSize: '14px',
            fontWeight: 600,
            border: 'none',
            borderBottom: `2px solid ${
              activeTab === 'documents' ? 'var(--primary-blush)' : 'transparent'
            }`,
            backgroundColor: 'transparent',
            color: activeTab === 'documents' ? 'var(--primary-blush)' : 'var(--text-muted)',
            cursor: 'pointer',
          }}
        >
          <Layers size={16} /> Processed Documents ({documents.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('cross_validation')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 18px',
            fontSize: '14px',
            fontWeight: 600,
            border: 'none',
            borderBottom: `2px solid ${
              activeTab === 'cross_validation' ? 'var(--primary-blush)' : 'transparent'
            }`,
            backgroundColor: 'transparent',
            color:
              activeTab === 'cross_validation' ? 'var(--primary-blush)' : 'var(--text-muted)',
            cursor: 'pointer',
          }}
        >
          <Scale size={16} /> Cross-Document Reconciliation (16 Rules)
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('government_rules')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 18px',
            fontSize: '14px',
            fontWeight: 600,
            border: 'none',
            borderBottom: `2px solid ${
              activeTab === 'government_rules' ? 'var(--primary-blush)' : 'transparent'
            }`,
            backgroundColor: 'transparent',
            color:
              activeTab === 'government_rules' ? 'var(--primary-blush)' : 'var(--text-muted)',
            cursor: 'pointer',
          }}
        >
          <ShieldCheck size={16} /> Statutory Indian Export Regulations
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('fraud_forensics')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 18px',
            fontSize: '14px',
            fontWeight: 600,
            border: 'none',
            borderBottom: `2px solid ${
              activeTab === 'fraud_forensics' ? 'var(--primary-blush)' : 'transparent'
            }`,
            backgroundColor: 'transparent',
            color:
              activeTab === 'fraud_forensics' ? 'var(--primary-blush)' : 'var(--text-muted)',
            cursor: 'pointer',
          }}
        >
          <ShieldAlert size={16} /> Fake Document Detection
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'documents' && (
        <div>
          {documents.map((doc, idx) => (
            <DocumentCard
              key={doc.saved_filename || `${doc.original_filename}_${idx}`}
              document={doc}
              index={idx}
            />
          ))}
        </div>
      )}

      {activeTab === 'cross_validation' && (
        <CrossDocumentView validation={cross_document_validation} />
      )}

      {activeTab === 'government_rules' && (
        <GovernmentRulesView compliance={government_compliance} />
      )}

      {activeTab === 'fraud_forensics' && (
        <FraudDetectionPanel fraudReport={fraudReport} loading={fraudLoading} />
      )}
    </div>
  );
};
