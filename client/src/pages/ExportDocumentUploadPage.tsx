import React from 'react';
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  FileCheck2,
  FolderUp,
} from 'lucide-react';
import { UploadDocumentsSection } from '../components/workflow/UploadDocumentsSection';
import {
  deriveFinalOutcome,
  useComplianceWorkflow,
} from '../context/ComplianceWorkflowContext';

interface ExportDocumentUploadPageProps {
  onBackToDashboard: () => void;
  onViewResultsInDashboard: () => void;
}

export const ExportDocumentUploadPage: React.FC<ExportDocumentUploadPageProps> = ({
  onBackToDashboard,
  onViewResultsInDashboard,
}) => {
  const {
    maxFiles,
    selectedFiles,
    isRunning,
    uploadProgress,
    progressLabel,
    errorMessage,
    warningMessage,
    stages,
    batchResponse,
    agentResponse,
    handleAddFiles,
    handleRemoveFile,
    handleChangeType,
    handleClearAll,
    handleRunComplianceCheck,
  } = useComplianceWorkflow();

  const onRunUpload = async () => {
    await handleRunComplianceCheck({ switchToExtracted: false });
  };

  const finalOutcome = batchResponse ? deriveFinalOutcome(batchResponse, agentResponse) : null;
  const readyCount = selectedFiles.filter((f) => !f.validationError).length;

  return (
    <div style={{ maxWidth: '1080px', margin: '0 auto' }} className="fade-in">
      {/* Compact Verification Workspace Header (Distinct from Landing Hero) */}
      <div
        style={{
          marginBottom: '18px',
          padding: '18px 24px',
          borderRadius: '14px',
          backgroundColor: '#FFFFFF',
          border: '1px solid #C5D7E8',
          boxShadow: '0 6px 20px rgba(16, 42, 67, 0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '11px',
              background: 'linear-gradient(135deg, #102A43 0%, #456B8B 100%)',
              color: '#FFFFFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <FolderUp size={22} />
          </div>
          <div>
            <h1
              style={{
                margin: 0,
                fontSize: '23px',
                fontWeight: 800,
                color: '#102A43',
                letterSpacing: '-0.02em',
                lineHeight: 1.2,
              }}
            >
              Export Document Upload
            </h1>
            <p style={{ margin: '4px 0 0 0', fontSize: '13.5px', color: '#456B8B' }}>
              Upload your export documents for AI-powered compliance verification.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span
            style={{
              fontSize: '12px',
              fontWeight: 700,
              color: readyCount > 0 ? '#0D9488' : '#1E3A5F',
              backgroundColor: readyCount > 0 ? '#E6F4F1' : '#EAF2F8',
              border: `1px solid ${readyCount > 0 ? '#99D5CE' : '#C5D7E8'}`,
              padding: '6px 12px',
              borderRadius: '999px',
            }}
          >
            Batch Queue: {readyCount}/{maxFiles} PDFs
          </span>

          <button
            type="button"
            id="upload-back-dashboard-btn"
            onClick={onBackToDashboard}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 14px',
              fontSize: '12.5px',
              fontWeight: 600,
              color: '#102A43',
              backgroundColor: '#EAF2F8',
              border: '1px solid #9FBAD0',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            <ArrowLeft size={14} />
            <span>Back to Dashboard</span>
          </button>
        </div>
      </div>

      {/* Main Drag & Drop Workspace + 5 Document Cards */}
      <UploadDocumentsSection
        selectedFiles={selectedFiles}
        onAddFiles={handleAddFiles}
        onRemoveFile={handleRemoveFile}
        onChangeType={handleChangeType}
        onClearAll={handleClearAll}
        onRunComplianceCheck={onRunUpload}
        isRunning={isRunning}
        uploadProgress={uploadProgress}
        progressLabel={progressLabel}
        errorMessage={errorMessage}
        warningMessage={warningMessage}
        maxFiles={maxFiles}
        showSectionHeader={false}
      />

      {/* Completed Verification Summary & Handoff to Full Dashboard */}
      {batchResponse && finalOutcome && !isRunning && (
        <div
          id="upload-completed-summary"
          style={{
            marginTop: '18px',
            padding: '18px 22px',
            borderRadius: '14px',
            backgroundColor: '#FFFFFF',
            border: '1px solid #0D9488',
            boxShadow: '0 8px 24px rgba(16, 42, 67, 0.09)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '10px',
                backgroundColor: '#E6F4F1',
                color: '#0D9488',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid #99D5CE',
              }}
            >
              <FileCheck2 size={20} />
            </div>
            <div>
              <div style={{ fontSize: '14.5px', fontWeight: 700, color: '#102A43' }}>
                Verification Complete — Outcome: {finalOutcome}
              </div>
              <div style={{ fontSize: '12.5px', color: '#456B8B', marginTop: '2px' }}>
                Batch {batchResponse.batch_id} • {batchResponse.summary.successful_count}/
                {batchResponse.summary.total_files_received} document(s) extracted
                {agentResponse
                  ? ` • LangGraph Score: ${agentResponse.compliance_score.toFixed(1)}%`
                  : ''}
              </div>
            </div>
          </div>

          <button
            type="button"
            id="upload-view-dashboard-btn"
            className="ecc-btn-verify"
            onClick={onViewResultsInDashboard}
          >
            <span>Open Full Compliance Report</span>
            <ArrowRight size={15} />
          </button>
        </div>
      )}

      {/* Compact Pipeline Telemetry Bar */}
      <div
        style={{
          marginTop: '18px',
          backgroundColor: 'rgba(255, 255, 255, 0.92)',
          border: '1px solid #C5D7E8',
          borderRadius: '12px',
          padding: '10px 14px',
          overflowX: 'auto',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '820px' }}>
          {stages.map((st, i) => {
            const bg =
              st.status === 'completed'
                ? '#E6F4F1'
                : st.status === 'warning'
                ? '#FEF7E6'
                : st.status === 'failed'
                ? '#FEF2F2'
                : st.status === 'running'
                ? '#1E3A5F'
                : '#EAF2F8';
            const fg =
              st.status === 'completed'
                ? '#0D9488'
                : st.status === 'warning'
                ? '#8A5A00'
                : st.status === 'failed'
                ? '#991B1B'
                : st.status === 'running'
                ? '#FFFFFF'
                : '#456B8B';

            return (
              <React.Fragment key={st.id}>
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '4px 10px',
                    borderRadius: '14px',
                    fontSize: '11.5px',
                    fontWeight: 600,
                    backgroundColor: bg,
                    color: fg,
                    border: '1px solid #C5D7E8',
                  }}
                >
                  {st.status === 'completed' && <CheckCircle2 size={12} />}
                  {st.status === 'warning' && <AlertTriangle size={12} />}
                  {st.status === 'failed' && <XCircle size={12} />}
                  {st.status === 'running' && <Loader2 size={12} />}
                  <span>{st.label}</span>
                </div>
                {i < stages.length - 1 && <ArrowRight size={12} color="#456B8B" />}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};
