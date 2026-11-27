import React from 'react';
import { ComplianceWorkflowPage } from '../pages/ComplianceWorkflowPage';
import { DashboardPage } from '../pages/DashboardPage';
import { NavTab } from '../components/common/Navbar';
import { WorkflowSectionId } from '../components/workflow/WorkflowTypes';

interface AppRoutesProps {
  activeTab: NavTab;
  activeStep: WorkflowSectionId;
  onSelectStep: (step: WorkflowSectionId) => void;
  onNavigate?: (tab: NavTab) => void;
}

export const AppRoutes: React.FC<AppRoutesProps> = ({
  activeTab,
  activeStep,
  onSelectStep,
}) => {
  if (activeTab === 'dashboard') {
    return <DashboardPage />;
  }
  return <ComplianceWorkflowPage activeStep={activeStep} onSelectStep={onSelectStep} />;
};
