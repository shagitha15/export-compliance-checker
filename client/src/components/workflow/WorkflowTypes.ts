import { BatchUploadResponse } from '../../types/batch';
import { AgentAnalysisResponse } from '../../features/compliance/types';

export type WorkflowSectionId =
  | 'upload'
  | 'extracted'
  | 'validation'
  | 'policy'
  | 'report';

export type PipelineStageState = 'idle' | 'running' | 'completed' | 'warning' | 'failed';

export interface PipelineStageInfo {
  id:
    | 'upload'
    | 'extraction'
    | 'agent'
    | 'validation'
    | 'policy'
    | 'report';
  label: string;
  status: PipelineStageState;
  detail?: string;
}

export type FinalAuditOutcome = 'PASS' | 'FAIL' | 'PARTIAL';

export interface AuditHistoryEntry {
  batchId: string;
  timestamp: string;
  outcome: FinalAuditOutcome;
  filesCount: number;
  successfulDocs: number;
  failedChecks: number;
  batchResponse: BatchUploadResponse;
  agentResponse: AgentAnalysisResponse | null;
}
