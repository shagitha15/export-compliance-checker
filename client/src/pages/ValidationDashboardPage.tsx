import React, { useState, useEffect } from 'react';
import { CrossDocumentValidationResponse, GovernmentComplianceReport, CheckResult } from '../types/batch';
import { complianceService, SAMPLE_SHIPMENTS } from '../services/complianceService';
import { ShipmentScenario, FraudAnalysisReport, AgentAnalysisResponse } from '../features/compliance/types';
import { ComplianceOverviewCards } from '../features/compliance/components/ComplianceOverviewCards';
import { CrossDocumentMatrix } from '../features/compliance/components/CrossDocumentMatrix';
import { DiscrepancyInspector } from '../features/compliance/components/DiscrepancyInspector';
import { StatutoryCompliancePanel } from '../features/compliance/components/StatutoryCompliancePanel';
import { ShipmentScenarioSelector } from '../features/compliance/components/ShipmentScenarioSelector';
import { FraudDetectionPanel } from '../features/compliance/components/FraudDetectionPanel';
import { AgentWorkflowCard } from '../features/compliance/components/AgentWorkflowCard';
import {
  Download,
  RotateCcw,
  Sparkles,
  FileText,
} from 'lucide-react';

export const ValidationDashboardPage: React.FC = () => {
  const [selectedScenario, setSelectedScenario] = useState<ShipmentScenario>(SAMPLE_SHIPMENTS[0]);
  const [validationData, setValidationData] = useState<CrossDocumentValidationResponse | null>(null);
  const [governmentData, setGovernmentData] = useState<GovernmentComplianceReport | null>(null);
  const [fraudData, setFraudData] = useState<FraudAnalysisReport | null>(null);
  const [agentData, setAgentData] = useState<AgentAnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [agentLoading, setAgentLoading] = useState<boolean>(false);
  const [downloadingPdf, setDownloadingPdf] = useState<boolean>(false);
  const [selectedDiscrepancy, setSelectedDiscrepancy] = useState<CheckResult | null>(null);

  const executeAudit = async (scenario: ShipmentScenario) => {
    setLoading(true);
    setSelectedDiscrepancy(null);

    try {
      const [valRes, govRes, fraudRes, agentRes] = await Promise.all([
        complianceService.validateDocuments(scenario.documents),
        complianceService.verifyGovernmentRules(scenario.documents),
        complianceService.inspectFraud(scenario.documents),
        complianceService.analyzeWithAgent(scenario),
      ]);
      setValidationData(valRes);
      setGovernmentData(govRes);
      setFraudData(fraudRes);
      setAgentData(agentRes);
    } catch (err) {
      console.error('Audit execution error:', err);
    } finally {
      setLoading(false);
    }
  };

  const executeAgentWorkflow = async () => {
    setAgentLoading(true);
    try {
      const res = await complianceService.analyzeWithAgent(selectedScenario);
      setAgentData(res);
      if (res.cross_document_validation) setValidationData(res.cross_document_validation);
      if (res.government_compliance) setGovernmentData(res.government_compliance);
      if (res.fraud_analysis) setFraudData(res.fraud_analysis);
    } catch (err) {
      console.error('Agent workflow execution error:', err);
    } finally {
      setAgentLoading(false);
    }
  };

  useEffect(() => {
    executeAudit(selectedScenario);
  }, [selectedScenario]);

  const handleExportJson = () => {
    if (!validationData) return;
    const exportPayload = {
      scenario: selectedScenario.name,
      exportedAt: new Date().toISOString(),
      agentAnalysis: agentData,
      crossDocumentValidation: validationData,
      governmentCompliance: governmentData,
      fraudAndAuthenticity: fraudData,
    };
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(exportPayload, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `compliance_audit_${selectedScenario.id}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleDownloadPdf = async () => {
    if (!validationData) return;
    setDownloadingPdf(true);
    try {
      await complianceService.downloadPdfReport(selectedScenario, validationData, governmentData);
    } catch (err: any) {
      console.error('PDF generation error:', err);
      alert(`Could not generate PDF: ${err.message || 'Server error'}`);
    } finally {
      setDownloadingPdf(false);
    }
  };

  const discrepancies = validationData?.cross_document_results.filter((c) => c.status === 'FAIL') || [];

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto' }} className="fade-in">
      {/* Page Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        <div>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'var(--primary-blush-light)',
              color: 'var(--primary-blush)',
              padding: '3px 10px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700,
              marginBottom: '6px',
            }}
          >
            <Sparkles size={12} /> Indian Customs Two-Stage Compliance Engine
          </div>
          <h2
            style={{
              margin: 0,
              fontSize: '24px',
              fontWeight: 800,
              color: 'var(--text-main)',
              letterSpacing: '-0.02em',
            }}
          >
            Customs Validation & Reconciliation Dashboard
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
            16-rule multi-document consistency auditing, field-level discrepancy analysis, and statutory DGFT & CBIC verification.
          </p>
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            onClick={executeAgentWorkflow}
            disabled={loading || agentLoading}
            id="run-ai-agent-btn"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              fontSize: '13px',
              fontWeight: 700,
              backgroundColor: 'var(--primary-blush-light)',
              color: 'var(--primary-blush)',
              border: '1px solid var(--border-blush)',
              borderRadius: 'var(--radius-sm)',
              cursor: loading || agentLoading ? 'not-allowed' : 'pointer',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <Sparkles size={14} /> {agentLoading ? 'Agent Running...' : 'Run AI Agent'}
          </button>

          <button
            type="button"
            onClick={() => executeAudit(selectedScenario)}
            disabled={loading || agentLoading}
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
              cursor: loading || agentLoading ? 'not-allowed' : 'pointer',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <RotateCcw size={14} /> Re-Audit
          </button>

          <button
            type="button"
            onClick={handleExportJson}
            disabled={!validationData || loading}
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
              cursor: !validationData || loading ? 'not-allowed' : 'pointer',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <Download size={14} /> Export JSON
          </button>

          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={!validationData || loading || downloadingPdf}
            id="download-pdf-report-btn"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              fontSize: '13px',
              fontWeight: 600,
              backgroundColor: 'var(--primary-blush)',
              color: '#ffffff',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              cursor: !validationData || loading || downloadingPdf ? 'not-allowed' : 'pointer',
              boxShadow: '0 2px 6px rgba(184, 50, 83, 0.25)',
              transition: 'opacity 0.2s ease',
              opacity: !validationData || loading || downloadingPdf ? 0.6 : 1,
            }}
          >
            <FileText size={14} /> {downloadingPdf ? 'Generating PDF...' : 'Download PDF Report'}
          </button>
        </div>
      </div>

      {/* Shipment Scenario Selector */}
      <ShipmentScenarioSelector
        selectedScenarioId={selectedScenario.id}
        onSelectScenario={(s) => setSelectedScenario(s)}
        onRunAudit={() => executeAudit(selectedScenario)}
        isLoading={loading}
      />

      {/* LangGraph Autonomous Compliance Agent Workflow Card (Task 7) */}
      <AgentWorkflowCard
        agentData={agentData}
        loading={agentLoading}
        onRunAgent={executeAgentWorkflow}
        onDownloadPdf={handleDownloadPdf}
        downloadingPdf={downloadingPdf}
      />

      {/* Overview Metric Cards */}
      <ComplianceOverviewCards validation={validationData} government={governmentData} />

      {/* Fraud & Document Authenticity Forensics Panel (Task 6) */}
      <FraudDetectionPanel fraudReport={fraudData} loading={loading} />

      {/* Discrepancy Remediation Inspector (Shows if discrepancies exist) */}
      <DiscrepancyInspector
        discrepancies={selectedDiscrepancy ? [selectedDiscrepancy] : discrepancies}
        onDismiss={() => setSelectedDiscrepancy(null)}
      />

      {/* 16-Rule Cross-Document Matrix */}
      <CrossDocumentMatrix
        validation={validationData}
        onSelectDiscrepancy={(check) => setSelectedDiscrepancy(check)}
      />

      {/* Statutory Regulatory Panel */}
      <StatutoryCompliancePanel compliance={governmentData} />
    </div>
  );
};
