import React from 'react';
import {
  deriveFinalOutcome,
  useComplianceWorkflow,
} from '../context/ComplianceWorkflowContext';
import { UploadDocumentsSection } from '../components/workflow/UploadDocumentsSection';
import { ExtractedDataSection } from '../components/workflow/ExtractedDataSection';
import { CrossValidationSection } from '../components/workflow/CrossValidationSection';
import { PolicyVerificationSection } from '../components/workflow/PolicyVerificationSection';
import { ComplianceReportSection } from '../components/workflow/ComplianceReportSection';
import { WorkflowSectionId } from '../components/workflow/WorkflowTypes';
import {
  UploadCloud,
  FileSearch,
  Scale,
  ShieldCheck,
  FileCheck2,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  RotateCcw,
  LucideIcon,
} from 'lucide-react';

interface ComplianceWorkflowPageProps {
  activeStep?: WorkflowSectionId;
  onSelectStep?: (step: WorkflowSectionId) => void;
}

interface StepMeta {
  id: WorkflowSectionId;
  stepNumber: number;
  title: string;
  shortLabel: string;
  subtitle: string;
  icon: LucideIcon;
}

const STEP_ORDER: StepMeta[] = [
  {
    id: 'upload',
    stepNumber: 1,
    title: 'Upload Documents',
    shortLabel: 'Upload Documents',
    subtitle:
      'Upload up to five export customs PDF documents for automated OCR scanning, Gemini AI schema extraction, and verification.',
    icon: UploadCloud,
  },
  {
    id: 'extracted',
    stepNumber: 2,
    title: 'Extracted Data',
    shortLabel: 'Extracted Data',
    subtitle:
      'Review structured trade fields parsed from each uploaded PDF document along with extraction provenance and missing-field alerts.',
    icon: FileSearch,
  },
  {
    id: 'validation',
    stepNumber: 3,
    title: 'Cross-Document Validation',
    shortLabel: 'Cross-Document Validation',
    subtitle:
      'Inspect two-stage deterministic reconciliation across quantities, HS codes, currencies, weights, invoice numbers, and commercial totals.',
    icon: Scale,
  },
  {
    id: 'policy',
    stepNumber: 4,
    title: 'DGFT & CBIC Policy Verification',
    shortLabel: 'DGFT & CBIC Policy',
    subtitle:
      'Verify export compliance against DGFT Foreign Trade Policy 2023, Customs Act 1962, GST Rule 96A LUT, RBI FEMA, and SCOMET controls.',
    icon: ShieldCheck,
  },
  {
    id: 'report',
    stepNumber: 5,
    title: 'Compliance Report',
    shortLabel: 'Compliance Report',
    subtitle:
      'Review the final customs clearance determination, forensic authenticity breakdown, remediation steps, and A4 PDF Compliance Certificate.',
    icon: FileCheck2,
  },
];

export const ComplianceWorkflowPage: React.FC<ComplianceWorkflowPageProps> = ({
  activeStep,
  onSelectStep,
}) => {
  const {
    maxFiles,
    activeSection,
    setActiveSection,
    selectedFiles,
    isRunning,
    uploadProgress,
    progressLabel,
    errorMessage,
    warningMessage,
    stages,
    batchResponse,
    setBatchResponse,
    agentResponse,
    setAgentResponse,
    auditHistory,
    handleAddFiles,
    handleRemoveFile,
    handleChangeType,
    handleClearAll,
    handleRunComplianceCheck,
  } = useComplianceWorkflow();

  const currentStepId = activeStep || activeSection;
  const currentIndex = Math.max(
    0,
    STEP_ORDER.findIndex((s) => s.id === currentStepId)
  );
  const currentMeta = STEP_ORDER[currentIndex];
  const prevMeta = currentIndex > 0 ? STEP_ORDER[currentIndex - 1] : null;
  const nextMeta = currentIndex < STEP_ORDER.length - 1 ? STEP_ORDER[currentIndex + 1] : null;

  const goToStep = (step: WorkflowSectionId) => {
    setActiveSection(step);
    if (onSelectStep) {
      onSelectStep(step);
    }
  };

  const finalVal = agentResponse?.cross_document_validation || batchResponse?.cross_document_validation;
  const finalGov = agentResponse?.government_compliance || batchResponse?.government_compliance;
  const finalOutcome = batchResponse ? deriveFinalOutcome(batchResponse, agentResponse) : null;

  const getStepStatus = (
    stepId: WorkflowSectionId
  ): 'current' | 'completed' | 'warning' | 'failed' | 'running' | 'pending' => {
    if (stepId === currentStepId) return 'current';

    if (stepId === 'upload') {
      if (isRunning) return 'running';
      if (batchResponse) return 'completed';
      return 'pending';
    }
    if (stepId === 'extracted') {
      const stage = stages.find((s) => s.id === 'extraction');
      if (stage?.status === 'running') return 'running';
      if (stage?.status === 'failed') return 'failed';
      if (stage?.status === 'warning') return 'warning';
      if (batchResponse) return 'completed';
      return 'pending';
    }
    if (stepId === 'validation') {
      const stage = stages.find((s) => s.id === 'validation');
      if (stage?.status === 'running') return 'running';
      if (stage?.status === 'failed') return 'failed';
      if (finalVal) return finalVal.summary.failed > 0 ? 'warning' : 'completed';
      return 'pending';
    }
    if (stepId === 'policy') {
      const stage = stages.find((s) => s.id === 'policy');
      if (stage?.status === 'running') return 'running';
      if (stage?.status === 'failed') return 'failed';
      if (finalGov) {
        return finalGov.overall_government_compliance === 'NON_COMPLIANT' ? 'warning' : 'completed';
      }
      return 'pending';
    }
    if (stepId === 'report') {
      if (batchResponse && finalOutcome) {
        return finalOutcome === 'FAIL' ? 'warning' : 'completed';
      }
      return 'pending';
    }
    return 'pending';
  };

  const renderPageKpiBadge = () => {
    if (currentStepId === 'upload') {
      const ready = selectedFiles.filter((f) => !f.validationError).length;
      return (
        <div
          style={{
            padding: '8px 14px',
            borderRadius: '10px',
            backgroundColor: ready > 0 ? '#E6F4F1' : '#EAF2F8',
            border: `1px solid ${ready > 0 ? '#99D5CE' : '#9FBAD0'}`,
            color: ready > 0 ? '#0D9488' : '#102A43',
            fontSize: '12.5px',
            fontWeight: 700,
          }}
        >
          Queue: {ready} / {maxFiles} PDF(s)
        </div>
      );
    }
    if (currentStepId === 'extracted') {
      const total = batchResponse?.documents.length || 0;
      const ok = batchResponse?.summary.successful_count || 0;
      return (
        <div
          style={{
            padding: '8px 14px',
            borderRadius: '10px',
            backgroundColor: total > 0 ? '#E6F4F1' : '#EAF2F8',
            border: `1px solid ${total > 0 ? '#99D5CE' : '#9FBAD0'}`,
            color: total > 0 ? '#0D9488' : '#456B8B',
            fontSize: '12.5px',
            fontWeight: 700,
          }}
        >
          {total > 0 ? `${ok} / ${total} Documents Extracted` : 'Awaiting Upload'}
        </div>
      );
    }
    if (currentStepId === 'validation') {
      return (
        <div
          style={{
            padding: '8px 14px',
            borderRadius: '10px',
            backgroundColor: finalVal ? (finalVal.summary.failed > 0 ? '#FEF7E6' : '#E6F4F1') : '#EAF2F8',
            border: `1px solid ${finalVal ? (finalVal.summary.failed > 0 ? '#F2D388' : '#99D5CE') : '#9FBAD0'}`,
            color: finalVal ? (finalVal.summary.failed > 0 ? '#8A5A00' : '#0D9488') : '#456B8B',
            fontSize: '12.5px',
            fontWeight: 700,
          }}
        >
          {finalVal
            ? `${finalVal.summary.passed} Match • ${finalVal.summary.failed} Mismatch`
            : 'Not Evaluated Yet'}
        </div>
      );
    }
    if (currentStepId === 'policy') {
      return (
        <div
          style={{
            padding: '8px 14px',
            borderRadius: '10px',
            backgroundColor: finalGov
              ? finalGov.overall_government_compliance === 'COMPLIANT'
                ? '#E6F4F1'
                : '#FEF2F2'
              : '#EAF2F8',
            border: `1px solid ${
              finalGov
                ? finalGov.overall_government_compliance === 'COMPLIANT'
                  ? '#99D5CE'
                  : '#FECACA'
                : '#9FBAD0'
            }`,
            color: finalGov
              ? finalGov.overall_government_compliance === 'COMPLIANT'
                ? '#0D9488'
                : '#991B1B'
              : '#456B8B',
            fontSize: '12.5px',
            fontWeight: 700,
          }}
        >
          {finalGov ? finalGov.overall_government_compliance : 'Awaiting Verification'}
        </div>
      );
    }
    return (
      <div
        style={{
          padding: '8px 14px',
          borderRadius: '10px',
          backgroundColor:
            finalOutcome === 'PASS'
              ? '#E6F4F1'
              : finalOutcome === 'FAIL'
              ? '#FEF2F2'
              : finalOutcome === 'PARTIAL'
              ? '#FEF7E6'
              : '#EAF2F8',
          border: '1px solid #9FBAD0',
          color:
            finalOutcome === 'PASS'
              ? '#0D9488'
              : finalOutcome === 'FAIL'
              ? '#991B1B'
              : finalOutcome === 'PARTIAL'
              ? '#8A5A00'
              : '#456B8B',
          fontSize: '12.5px',
          fontWeight: 700,
        }}
      >
        {finalOutcome ? `Decision: ${finalOutcome}` : 'Report Pending'}
      </div>
    );
  };

  const PageIcon = currentMeta.icon;

  return (
    <div style={{ maxWidth: '1120px', margin: '0 auto' }} className="fade-in">
      {/* Persistent 5-Step Enterprise Stepper */}
      <nav
        aria-label="Compliance Verification Steps"
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #C5D7E8',
          borderRadius: '14px',
          padding: '10px 12px',
          boxShadow: '0 4px 16px rgba(16, 42, 67, 0.06)',
          marginBottom: '18px',
          overflowX: 'auto',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(5, minmax(150px, 1fr))',
            gap: '8px',
            minWidth: '780px',
          }}
        >
          {STEP_ORDER.map((step) => {
            const status = getStepStatus(step.id);
            const isCurrent = status === 'current';
            const isCompleted = status === 'completed';
            const isWarning = status === 'warning';
            const isFailed = status === 'failed';
            const isStepRunning = status === 'running';

            const bg = isCurrent
              ? 'linear-gradient(135deg, #102A43 0%, #1E3A5F 100%)'
              : isCompleted
              ? '#F2FAF8'
              : isWarning
              ? '#FEF7E6'
              : isFailed
              ? '#FEF2F2'
              : '#EAF2F8';
            const border = isCurrent
              ? '#102A43'
              : isCompleted
              ? '#99D5CE'
              : isWarning
              ? '#F2D388'
              : isFailed
              ? '#FECACA'
              : '#C5D7E8';
            const titleColor = isCurrent ? '#FFFFFF' : '#102A43';
            const subColor = isCurrent
              ? '#9FBAD0'
              : isCompleted
              ? '#0D9488'
              : isWarning
              ? '#8A5A00'
              : isFailed
              ? '#991B1B'
              : '#456B8B';

            const statusLabel = isCurrent
              ? 'Active Step'
              : isStepRunning
              ? 'Running...'
              : isCompleted
              ? 'Completed'
              : isWarning
              ? 'Review Needed'
              : isFailed
              ? 'Failed'
              : 'Pending';

            return (
              <button
                key={step.id}
                type="button"
                id={`workflow-step-${step.id}`}
                aria-current={isCurrent ? 'step' : undefined}
                onClick={() => goToStep(step.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '9px 12px',
                  borderRadius: '10px',
                  border: `1px solid ${border}`,
                  background: bg,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                  boxShadow: isCurrent ? '0 4px 12px rgba(16, 42, 67, 0.22)' : 'none',
                }}
              >
                <div
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    fontSize: '12px',
                    fontWeight: 800,
                    backgroundColor: isCurrent
                      ? 'rgba(255, 255, 255, 0.16)'
                      : isCompleted
                      ? '#0D9488'
                      : '#FFFFFF',
                    color: isCurrent || isCompleted ? '#FFFFFF' : '#102A43',
                    border: isCurrent || isCompleted ? 'none' : '1px solid #9FBAD0',
                  }}
                >
                  {isStepRunning ? (
                    <Loader2 size={14} />
                  ) : isCompleted ? (
                    <CheckCircle2 size={15} />
                  ) : isWarning ? (
                    <AlertTriangle size={14} color="#8A5A00" />
                  ) : isFailed ? (
                    <XCircle size={14} color="#991B1B" />
                  ) : (
                    step.stepNumber
                  )}
                </div>

                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: '12px',
                      fontWeight: 700,
                      color: titleColor,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {step.shortLabel}
                  </div>
                  <div style={{ fontSize: '10.5px', fontWeight: 600, color: subColor }}>
                    {statusLabel}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Dedicated Page Header Banner */}
      <div
        style={{
          marginBottom: '20px',
          padding: '22px 26px',
          borderRadius: '16px',
          background: 'linear-gradient(125deg, #FFFFFF 0%, #EAF2F8 62%, #9FBAD0 100%)',
          border: '1px solid #9FBAD0',
          boxShadow: '0 8px 24px rgba(16, 42, 67, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', flex: 1, minWidth: '260px' }}>
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #102A43 0%, #1E3A5F 100%)',
              color: '#FFFFFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              boxShadow: '0 6px 14px rgba(16, 42, 67, 0.18)',
            }}
          >
            <PageIcon size={22} />
          </div>
          <div>
            <div
              style={{
                display: 'inline-block',
                fontSize: '11px',
                fontWeight: 800,
                textTransform: 'uppercase',
                letterSpacing: '0.07em',
                color: '#456B8B',
                marginBottom: '4px',
              }}
            >
              Step {currentMeta.stepNumber} of {STEP_ORDER.length} • Export Compliance Workflow
            </div>
            <h1
              style={{
                margin: 0,
                fontSize: '26px',
                fontWeight: 800,
                color: '#102A43',
                letterSpacing: '-0.02em',
                lineHeight: 1.2,
              }}
            >
              {currentMeta.title}
            </h1>
            <p style={{ margin: '6px 0 0 0', fontSize: '13.5px', color: '#1E3A5F', maxWidth: '680px', lineHeight: 1.5 }}>
              {currentMeta.subtitle}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {renderPageKpiBadge()}
        </div>
      </div>

      {/* Dedicated Single-Step Page View */}
      <div>
        {currentStepId === 'upload' && (
          <UploadDocumentsSection
            selectedFiles={selectedFiles}
            onAddFiles={handleAddFiles}
            onRemoveFile={handleRemoveFile}
            onChangeType={handleChangeType}
            onClearAll={handleClearAll}
            onRunComplianceCheck={async () => {
              const ok = await handleRunComplianceCheck({ switchToExtracted: true });
              if (ok) {
                goToStep('extracted');
              }
            }}
            isRunning={isRunning}
            uploadProgress={uploadProgress}
            progressLabel={progressLabel}
            errorMessage={errorMessage}
            warningMessage={warningMessage}
            maxFiles={maxFiles}
            showSectionHeader={false}
          />
        )}

        {currentStepId === 'extracted' && (
          <ExtractedDataSection
            documents={batchResponse?.documents || []}
            onGoToUpload={() => goToStep('upload')}
          />
        )}

        {currentStepId === 'validation' && (
          <CrossValidationSection
            validation={finalVal}
            onGoToUpload={() => goToStep('upload')}
          />
        )}

        {currentStepId === 'policy' && (
          <PolicyVerificationSection
            compliance={finalGov}
            onGoToUpload={() => goToStep('upload')}
          />
        )}

        {currentStepId === 'report' && (
          <ComplianceReportSection
            batchResponse={batchResponse}
            agentResponse={agentResponse}
            outcome={finalOutcome}
            auditHistory={auditHistory}
            onSelectHistoryEntry={(entry) => {
              setBatchResponse(entry.batchResponse);
              setAgentResponse(entry.agentResponse);
            }}
            onGoToUpload={() => goToStep('upload')}
          />
        )}
      </div>

      {/* Persistent Previous / Next Step Navigation Footer */}
      <div
        style={{
          marginTop: '22px',
          padding: '14px 20px',
          backgroundColor: '#FFFFFF',
          border: '1px solid #C5D7E8',
          borderRadius: '14px',
          boxShadow: '0 4px 16px rgba(16, 42, 67, 0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          {prevMeta ? (
            <button
              type="button"
              id="step-prev-btn"
              onClick={() => goToStep(prevMeta.id)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '7px',
                padding: '9px 16px',
                fontSize: '13px',
                fontWeight: 600,
                color: '#102A43',
                backgroundColor: '#EAF2F8',
                border: '1px solid #9FBAD0',
                borderRadius: '8px',
                cursor: 'pointer',
              }}
            >
              <ArrowLeft size={15} />
              <span>Previous: {prevMeta.shortLabel}</span>
            </button>
          ) : (
            <span style={{ fontSize: '12.5px', color: '#456B8B', fontWeight: 500 }}>
              Upload files above, or advance directly to inspect results.
            </span>
          )}
        </div>

        <div style={{ fontSize: '12px', fontWeight: 700, color: '#456B8B' }}>
          Step {currentMeta.stepNumber} of {STEP_ORDER.length}
        </div>

        <div>
          {nextMeta ? (
            <button
              type="button"
              id="step-next-btn"
              onClick={() => goToStep(nextMeta.id)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '7px',
                padding: '9px 18px',
                fontSize: '13px',
                fontWeight: 700,
                color: '#FFFFFF',
                background: 'linear-gradient(135deg, #102A43 0%, #1E3A5F 100%)',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                boxShadow: '0 4px 12px rgba(16, 42, 67, 0.18)',
              }}
            >
              <span>Next: {nextMeta.shortLabel}</span>
              <ArrowRight size={15} />
            </button>
          ) : (
            <button
              type="button"
              id="step-restart-btn"
              onClick={() => goToStep('upload')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '7px',
                padding: '9px 18px',
                fontSize: '13px',
                fontWeight: 700,
                color: '#FFFFFF',
                background: 'linear-gradient(135deg, #102A43 0%, #1E3A5F 100%)',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                boxShadow: '0 4px 12px rgba(16, 42, 67, 0.18)',
              }}
            >
              <RotateCcw size={14} />
              <span>Back to Upload Documents</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
