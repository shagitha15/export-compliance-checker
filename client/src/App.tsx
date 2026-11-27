import React, { Component, ErrorInfo, ReactNode, useCallback, useEffect, useRef, useState } from 'react';
import { Navbar, NavTab } from './components/common/Navbar';
import { AppRoutes } from './routes/AppRoutes';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ComplianceWorkflowProvider, useComplianceWorkflow } from './context/ComplianceWorkflowContext';
import { AuthScreen } from './components/auth/AuthScreen';
import { LandingPage } from './components/landing/LandingPage';
import { WorkflowSectionId } from './components/workflow/WorkflowTypes';

type AppRoutePath =
  | '/'
  | '/login'
  | '/dashboard'
  | '/dashboard/upload'
  | '/dashboard/extracted-data'
  | '/dashboard/cross-validation'
  | '/dashboard/policy-verification'
  | '/dashboard/compliance-report';

const STEP_TO_ROUTE: Record<WorkflowSectionId, AppRoutePath> = {
  upload: '/dashboard/upload',
  extracted: '/dashboard/extracted-data',
  validation: '/dashboard/cross-validation',
  policy: '/dashboard/policy-verification',
  report: '/dashboard/compliance-report',
};

const ROUTE_TO_STEP: Partial<Record<AppRoutePath, WorkflowSectionId>> = {
  '/dashboard/upload': 'upload',
  '/dashboard/extracted-data': 'extracted',
  '/dashboard/cross-validation': 'validation',
  '/dashboard/policy-verification': 'policy',
  '/dashboard/compliance-report': 'report',
};

function normalizeRoutePath(pathname: string): AppRoutePath {
  const clean = (pathname || '/').replace(/\/+$/, '') || '/';
  if (clean === '/login') return '/login';
  if (clean === '/dashboard') return '/dashboard';
  if (clean === '/dashboard/upload') return '/dashboard/upload';
  if (clean === '/dashboard/extracted-data') return '/dashboard/extracted-data';
  if (clean === '/dashboard/cross-validation') return '/dashboard/cross-validation';
  if (clean === '/dashboard/policy-verification') return '/dashboard/policy-verification';
  if (clean === '/dashboard/compliance-report') return '/dashboard/compliance-report';
  return '/';
}

interface ErrorBoundaryState {
  hasError: boolean;
  errorMessage: string;
}

class AppErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, errorMessage: '' };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, errorMessage: error?.message || 'Unexpected rendering error.' };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('React render error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
            backgroundColor: '#F8FAFC',
            color: '#1E293B',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            textAlign: 'center',
          }}
        >
          <h2 style={{ margin: '0 0 8px 0', color: '#102A43' }}>
            EXPORT CUSTOMS COMPLIANCE
          </h2>
          <p style={{ margin: '0 0 16px 0', color: '#475569', maxWidth: '480px', fontSize: '14px' }}>
            The page encountered a rendering error: {this.state.errorMessage}
          </p>
          <button
            type="button"
            onClick={() => {
              this.setState({ hasError: false, errorMessage: '' });
              if (typeof window !== 'undefined') {
                window.history.replaceState({}, '', '/');
                window.location.reload();
              }
            }}
            style={{
              padding: '10px 20px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: '#0D9488',
              color: '#ffffff',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Reload Home Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const AppShell: React.FC = () => {
  const { user, loading, logout } = useAuth();
  const { activeSection, setActiveSection } = useComplianceWorkflow();
  const [activeTab, setActiveTab] = useState<NavTab>('compliance');
  const [routePath, setRoutePath] = useState<AppRoutePath>(() =>
    typeof window !== 'undefined' ? normalizeRoutePath(window.location.pathname) : '/'
  );
  const [authInitialMode, setAuthInitialMode] = useState<'login' | 'signup'>('login');
  const isLoggingOutRef = useRef(false);

  const navigate = useCallback((target: AppRoutePath, replace = false) => {
    setRoutePath(target);
    if (typeof window !== 'undefined') {
      const current = normalizeRoutePath(window.location.pathname);
      if (current !== target) {
        if (replace) {
          window.history.replaceState({}, '', target);
        } else {
          window.history.pushState({}, '', target);
        }
        window.scrollTo(0, 0);
      }
    }
  }, []);

  const handleSelectStep = useCallback(
    (step: WorkflowSectionId) => {
      setActiveSection(step);
      setActiveTab('compliance');
      navigate(STEP_TO_ROUTE[step]);
    },
    [navigate, setActiveSection]
  );

  // Keep workflow context activeSection synced when user navigates via URL or browser Back/Forward
  useEffect(() => {
    const matchedStep = ROUTE_TO_STEP[routePath];
    if (matchedStep && matchedStep !== activeSection) {
      setActiveSection(matchedStep);
    }
  }, [routePath, activeSection, setActiveSection]);

  const handleLogout = useCallback(async () => {
    isLoggingOutRef.current = true;
    navigate('/', true);
    try {
      await logout();
    } finally {
      isLoggingOutRef.current = false;
    }
  }, [logout, navigate]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const onPopState = () => {
      setRoutePath(normalizeRoutePath(window.location.pathname));
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  // Redirect authenticated users from /login -> active workflow step page cleanly
  useEffect(() => {
    if (user && routePath === '/login') {
      navigate(STEP_TO_ROUTE[activeSection], true);
    }
  }, [user, routePath, activeSection, navigate]);

  // Redirect unauthenticated or expired sessions on any /dashboard* route -> /login cleanly (unless logging out to "/")
  useEffect(() => {
    if (!loading && !user && routePath.startsWith('/dashboard') && !isLoggingOutRef.current) {
      navigate('/login', true);
    }
  }, [loading, user, routePath, navigate]);

  // Always render LandingPage immediately on "/" regardless of session verification delay
  if (routePath === '/') {
    const targetDashboard = STEP_TO_ROUTE[activeSection];
    return (
      <LandingPage
        isAuthenticated={Boolean(user)}
        onLoginClick={() => {
          if (user) {
            navigate(targetDashboard);
          } else {
            setAuthInitialMode('login');
            navigate('/login');
          }
        }}
        onGetStartedClick={() => {
          if (user) {
            navigate(targetDashboard);
          } else {
            setAuthInitialMode('login');
            navigate('/login');
          }
        }}
        onOpenDashboard={() => navigate(targetDashboard)}
      />
    );
  }

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#F8FAFC',
          color: '#475569',
          fontSize: '14px',
        }}
      >
        Verifying session...
      </div>
    );
  }

  if (!user || routePath === '/login') {
    return (
      <AuthScreen
        initialMode={authInitialMode}
        onBackToHome={() => navigate('/')}
      />
    );
  }

  const resolvedStep: WorkflowSectionId = ROUTE_TO_STEP[routePath] || activeSection;

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#EAF2F8',
        backgroundImage: 'linear-gradient(180deg, #EAF2F8 0%, #DCE8F3 50%, #9FBAD0 100%)',
      }}
    >
      <Navbar
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          if (tab === 'compliance') {
            navigate(STEP_TO_ROUTE[activeSection]);
          } else {
            navigate('/dashboard');
          }
        }}
        onHomeClick={() => navigate('/')}
        onLogout={handleLogout}
      />
      <main style={{ flex: 1, maxWidth: '1200px', margin: '0 auto', width: '100%', padding: '24px 16px' }}>
        <AppRoutes
          activeTab={activeTab}
          activeStep={resolvedStep}
          onSelectStep={handleSelectStep}
          onNavigate={setActiveTab}
        />
      </main>
      <footer
        style={{
          padding: '16px',
          textAlign: 'center',
          fontSize: '13px',
          color: '#EAF2F8',
          borderTop: '1px solid rgba(159, 186, 208, 0.28)',
          backgroundColor: '#102A43',
        }}
      >
        Export Customs Documentation Compliance Checker &copy; 2026
      </footer>
    </div>
  );
};

export function App() {
  return (
    <AppErrorBoundary>
      <AuthProvider>
        <ComplianceWorkflowProvider>
          <AppShell />
        </ComplianceWorkflowProvider>
      </AuthProvider>
    </AppErrorBoundary>
  );
}

export default App;
