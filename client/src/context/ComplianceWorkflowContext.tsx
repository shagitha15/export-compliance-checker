import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { BatchUploadResponse, SelectedFileItem } from '../types/batch';
import { AgentAnalysisResponse } from '../features/compliance/types';
import { batchService, BatchUploadError } from '../services/batchService';
import { complianceService } from '../services/complianceService';
import { useAuth } from './AuthContext';
import {
  AuditHistoryEntry,
  FinalAuditOutcome,
  PipelineStageInfo,
  WorkflowSectionId,
} from '../components/workflow/WorkflowTypes';

const MAX_FILES = 5;
const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024;
const HISTORY_STORAGE_KEY = 'export_compliance_session_history_v1';

const INITIAL_STAGES: PipelineStageInfo[] = [
  { id: 'upload', label: '1. Document Upload', status: 'idle' },
  { id: 'extraction', label: '2. Gemini AI Extraction', status: 'idle' },
  { id: 'agent', label: '3. LangGraph Agent', status: 'idle' },
  { id: 'validation', label: '4. 16-Rule Validation', status: 'idle' },
  { id: 'policy', label: '5. DGFT & CBIC Policy', status: 'idle' },
  { id: 'report', label: '6. Compliance Report', status: 'idle' },
];

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export function deriveFinalOutcome(
  batch: BatchUploadResponse,
  agent: AgentAnalysisResponse | null
): FinalAuditOutcome {
  const val = agent?.cross_document_validation || batch.cross_document_validation;
  const gov = agent?.government_compliance || batch.government_compliance;
  const fraud = agent?.fraud_analysis;

  if (
    batch.batch_status === 'FAILED' ||
    agent?.overall_compliance_status === 'REJECTED_CUSTOMS_HOLD' ||
    fraud?.overall_risk_level === 'HIGH_RISK' ||
    (val && val.summary.failed > 0) ||
    gov?.overall_government_compliance === 'NON_COMPLIANT'
  ) {
    return 'FAIL';
  }

  if (
    batch.batch_status === 'PARTIAL_SUCCESS' ||
    batch.summary.missing_document_types.length > 0 ||
    batch.documents.some((d) => d.fallback_used) ||
    agent?.overall_compliance_status === 'CONDITIONAL_REMEDIATION_REQUIRED'
  ) {
    return 'PARTIAL';
  }

  return 'PASS';
}

interface ComplianceWorkflowContextValue {
  maxFiles: number;
  activeSection: WorkflowSectionId;
  setActiveSection: React.Dispatch<React.SetStateAction<WorkflowSectionId>>;
  selectedFiles: SelectedFileItem[];
  isRunning: boolean;
  uploadProgress: number;
  progressLabel: string;
  errorMessage: string | null;
  warningMessage: string | null;
  stages: PipelineStageInfo[];
  batchResponse: BatchUploadResponse | null;
  setBatchResponse: React.Dispatch<React.SetStateAction<BatchUploadResponse | null>>;
  agentResponse: AgentAnalysisResponse | null;
  setAgentResponse: React.Dispatch<React.SetStateAction<AgentAnalysisResponse | null>>;
  auditHistory: AuditHistoryEntry[];
  handleAddFiles: (incoming: File[], explicitType?: string) => void;
  handleRemoveFile: (id: string) => void;
  handleChangeType: (id: string, newType: string) => void;
  handleClearAll: () => void;
  handleRunComplianceCheck: (options?: { switchToExtracted?: boolean }) => Promise<boolean>;
}

const ComplianceWorkflowContext = createContext<ComplianceWorkflowContextValue | null>(null);

export const ComplianceWorkflowProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { activeOrg, activeRole, canWrite, singleUserMode } = useAuth();
  const [activeSection, setActiveSection] = useState<WorkflowSectionId>('upload');
  const [selectedFiles, setSelectedFiles] = useState<SelectedFileItem[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState('Uploading documents...');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [warningMessage, setWarningMessage] = useState<string | null>(null);

  const [stages, setStages] = useState<PipelineStageInfo[]>(INITIAL_STAGES);
  const [batchResponse, setBatchResponse] = useState<BatchUploadResponse | null>(null);
  const [agentResponse, setAgentResponse] = useState<AgentAnalysisResponse | null>(null);
  const [auditHistory, setAuditHistory] = useState<AuditHistoryEntry[]>(() => {
    try {
      const raw = sessionStorage.getItem(HISTORY_STORAGE_KEY);
      return raw ? (JSON.parse(raw) as AuditHistoryEntry[]) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      sessionStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(auditHistory.slice(0, 10)));
    } catch {
      // Ignore storage quota errors
    }
  }, [auditHistory]);

  const handleAddFiles = useCallback((incoming: File[], explicitType?: string) => {
    setErrorMessage(null);
    setWarningMessage(null);

    setSelectedFiles((prev) => {
      const filteredPrev = explicitType
        ? prev.filter((item) => item.documentType !== explicitType)
        : prev;

      const slotsLeft = MAX_FILES - filteredPrev.length;
      if (slotsLeft <= 0) {
        setWarningMessage(
          `Maximum ${MAX_FILES} documents permitted per compliance check. Remove a file first.`
        );
        return prev;
      }

      const slice = incoming.slice(0, slotsLeft);
      if (incoming.length > slotsLeft) {
        setWarningMessage(`Only the first ${slotsLeft} file(s) were added (max ${MAX_FILES}).`);
      }

      const additions: SelectedFileItem[] = slice.map((file) => {
        let validationError: string | null = null;
        if (!file.name.toLowerCase().endsWith('.pdf')) {
          validationError = 'Invalid format: only .pdf documents are accepted.';
        } else if (file.size === 0) {
          validationError = 'File is empty (0 bytes).';
        } else if (file.size > MAX_FILE_SIZE_BYTES) {
          validationError = `File exceeds 25 MB limit (${formatFileSize(file.size)}).`;
        }

        return {
          id: `doc_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          file,
          documentType: explicitType || 'Auto-Detect',
          sizeFormatted: formatFileSize(file.size),
          sizeBytes: file.size,
          validationError,
        };
      });

      return [...filteredPrev, ...additions];
    });
  }, []);

  const handleRemoveFile = useCallback((id: string) => {
    setSelectedFiles((prev) => prev.filter((item) => item.id !== id));
    setErrorMessage(null);
  }, []);

  const handleChangeType = useCallback((id: string, newType: string) => {
    setSelectedFiles((prev) =>
      prev.map((item) => (item.id === id ? { ...item, documentType: newType } : item))
    );
  }, []);

  const handleClearAll = useCallback(() => {
    setSelectedFiles([]);
    setErrorMessage(null);
    setWarningMessage(null);
  }, []);

  const handleRunComplianceCheck = useCallback(
    async (options?: { switchToExtracted?: boolean }): Promise<boolean> => {
      const switchToExtracted = options?.switchToExtracted ?? true;

      if (!singleUserMode && !activeOrg) {
        setErrorMessage('Organization context is required when Single-User Mode is disabled.');
        return false;
      }
      if (!singleUserMode && !canWrite) {
        setErrorMessage(
          `Role "${activeRole}" has read-only access and cannot upload or trigger new audits.`
        );
        return false;
      }
      if (selectedFiles.length === 0) {
        setErrorMessage('Please select at least 1 PDF document before running the compliance check.');
        return false;
      }

      setIsRunning(true);
      setErrorMessage(null);
      setWarningMessage(null);
      setUploadProgress(5);
      setProgressLabel('Uploading PDF documents via multipart/form-data...');

      setStages([
        { id: 'upload', label: '1. Document Upload', status: 'running' },
        { id: 'extraction', label: '2. Gemini AI Extraction', status: 'running' },
        { id: 'agent', label: '3. LangGraph Agent', status: 'idle' },
        { id: 'validation', label: '4. 16-Rule Validation', status: 'idle' },
        { id: 'policy', label: '5. DGFT & CBIC Policy', status: 'idle' },
        { id: 'report', label: '6. Compliance Report', status: 'idle' },
      ]);

      try {
        const files = selectedFiles.map((f) => f.file);
        const docTypes = selectedFiles.map((f) => f.documentType);

        const batchRes = await batchService.uploadBatch(files, docTypes, (pct, lbl) => {
          setUploadProgress(pct);
          if (lbl) setProgressLabel(lbl);
        });

        setBatchResponse(batchRes);
        const anyFallback = batchRes.documents.some((d) => d.fallback_used);
        const anySuccess = batchRes.summary.successful_count > 0;

        if (!anySuccess) {
          setStages([
            { id: 'upload', label: '1. Document Upload', status: 'completed' },
            {
              id: 'extraction',
              label: '2. Gemini AI Extraction',
              status: 'failed',
              detail: 'No valid documents extracted',
            },
            { id: 'agent', label: '3. LangGraph Agent', status: 'failed' },
            { id: 'validation', label: '4. 16-Rule Validation', status: 'failed' },
            { id: 'policy', label: '5. DGFT & CBIC Policy', status: 'failed' },
            {
              id: 'report',
              label: '6. Compliance Report',
              status: 'warning',
              detail: 'Failed-batch report ready',
            },
          ]);
          setAgentResponse(null);
          if (switchToExtracted) {
            setActiveSection('extracted');
          }
          return true;
        }

        setStages([
          { id: 'upload', label: '1. Document Upload', status: 'completed' },
          {
            id: 'extraction',
            label: '2. Gemini AI Extraction',
            status: anyFallback ? 'warning' : 'completed',
            detail: anyFallback ? 'PyMuPDF fallback used on >=1 doc' : 'Gemini AI',
          },
          { id: 'agent', label: '3. LangGraph Agent', status: 'running' },
          { id: 'validation', label: '4. 16-Rule Validation', status: 'running' },
          { id: 'policy', label: '5. DGFT & CBIC Policy', status: 'running' },
          { id: 'report', label: '6. Compliance Report', status: 'idle' },
        ]);

        setProgressLabel('Executing LangGraph Agent, 16-Rule Audit & DGFT/CBIC Policy Verification...');
        setUploadProgress(88);

        const extractedMap: Record<string, any> = {};
        for (const d of batchRes.documents) {
          if (d.status === 'SUCCESS' && d.document_type && d.extracted_data) {
            extractedMap[d.document_type] = d.extracted_data;
          }
        }

        let agentRes: AgentAnalysisResponse | null = null;
        try {
          agentRes = await complianceService.analyzeDocumentsWithAgent(
            extractedMap,
            batchRes.batch_id,
            `Exporter Audit (${batchRes.batch_id})`
          );
          setAgentResponse(agentRes);
        } catch (agentErr: any) {
          setWarningMessage(
            `Batch extraction succeeded, but LangGraph agent endpoint reported an error: ${agentErr.message}`
          );
        }

        const finalVal = agentRes?.cross_document_validation || batchRes.cross_document_validation;
        const finalGov = agentRes?.government_compliance || batchRes.government_compliance;
        const outcome = deriveFinalOutcome(batchRes, agentRes);

        setStages([
          { id: 'upload', label: '1. Document Upload', status: 'completed' },
          {
            id: 'extraction',
            label: '2. Gemini AI Extraction',
            status: anyFallback ? 'warning' : 'completed',
          },
          {
            id: 'agent',
            label: '3. LangGraph Agent',
            status: agentRes ? 'completed' : 'warning',
          },
          {
            id: 'validation',
            label: '4. 16-Rule Validation',
            status: finalVal
              ? finalVal.summary.failed > 0
                ? 'warning'
                : 'completed'
              : 'failed',
          },
          {
            id: 'policy',
            label: '5. DGFT & CBIC Policy',
            status: finalGov
              ? finalGov.overall_government_compliance === 'NON_COMPLIANT'
                ? 'warning'
                : 'completed'
              : 'failed',
          },
          { id: 'report', label: '6. Compliance Report', status: 'completed' },
        ]);

        setUploadProgress(100);

        const historyEntry: AuditHistoryEntry = {
          batchId: batchRes.batch_id,
          timestamp: batchRes.timestamp,
          outcome,
          filesCount: batchRes.summary.total_files_received,
          successfulDocs: batchRes.summary.successful_count,
          failedChecks: finalVal ? finalVal.summary.failed : 0,
          batchResponse: batchRes,
          agentResponse: agentRes,
        };
        setAuditHistory((prev) => [
          historyEntry,
          ...prev.filter((h) => h.batchId !== batchRes.batch_id),
        ]);
        if (switchToExtracted) {
          setActiveSection('extracted');
        }
        return true;
      } catch (err: any) {
        const msg =
          err instanceof BatchUploadError
            ? err.message
            : err.message || 'Unable to connect to backend server.';
        setErrorMessage(msg);
        setStages([
          { id: 'upload', label: '1. Document Upload', status: 'failed' },
          { id: 'extraction', label: '2. Gemini AI Extraction', status: 'idle' },
          { id: 'agent', label: '3. LangGraph Agent', status: 'idle' },
          { id: 'validation', label: '4. 16-Rule Validation', status: 'idle' },
          { id: 'policy', label: '5. DGFT & CBIC Policy', status: 'idle' },
          { id: 'report', label: '6. Compliance Report', status: 'idle' },
        ]);
        return false;
      } finally {
        setIsRunning(false);
      }
    },
    [activeOrg, activeRole, canWrite, selectedFiles, singleUserMode]
  );

  return (
    <ComplianceWorkflowContext.Provider
      value={{
        maxFiles: MAX_FILES,
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
      }}
    >
      {children}
    </ComplianceWorkflowContext.Provider>
  );
};

export function useComplianceWorkflow(): ComplianceWorkflowContextValue {
  const ctx = useContext(ComplianceWorkflowContext);
  if (!ctx) {
    throw new Error('useComplianceWorkflow must be used inside ComplianceWorkflowProvider');
  }
  return ctx;
}
