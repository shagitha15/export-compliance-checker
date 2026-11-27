import React from 'react';
import { ShieldCheck, LayoutDashboard, LogOut, Home } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export type NavTab = 'compliance' | 'dashboard';

interface NavbarProps {
  title?: string;
  activeTab?: NavTab;
  onTabChange?: (tab: NavTab) => void;
  onHomeClick?: () => void;
  onLogout?: () => void | Promise<void>;
}

export const Navbar: React.FC<NavbarProps> = ({
  title = 'Export Customs Compliance Checker',
  activeTab = 'compliance',
  onTabChange,
  onHomeClick,
  onLogout,
}) => {
  const { user, activeOrg, activeRole, singleUserMode, logout } = useAuth();

  const handleSignOut = () => {
    if (onLogout) {
      void onLogout();
      return;
    }
    void logout();
  };

  return (
    <header
      style={{
        background: 'linear-gradient(90deg, #102A43 0%, #244769 58%, #456B8B 100%)',
        color: '#ffffff',
        padding: '0 24px',
        minHeight: '64px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '10px',
        boxShadow: '0 4px 16px rgba(16, 42, 67, 0.18)',
        borderBottom: '1px solid rgba(159, 186, 208, 0.35)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            backgroundColor: '#456B8B',
            border: '1px solid rgba(159, 186, 208, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#ffffff',
            boxShadow: '0 2px 6px rgba(16, 42, 67, 0.35)',
          }}
        >
          <ShieldCheck size={22} />
        </div>
        <div>
          <h1 style={{ margin: 0, fontSize: '16px', fontWeight: 700, letterSpacing: '-0.01em', color: '#FFFFFF' }}>
            {title}
          </h1>
          <span style={{ fontSize: '11px', color: '#EAF2F8', display: 'block', opacity: 0.9 }}>
            {activeOrg
              ? `${activeOrg.name} (${activeRole})`
              : singleUserMode
              ? 'Single-User Workspace'
              : 'No Active Organization'}{' '}
            • {user?.email}
          </span>
        </div>
      </div>

      {onTabChange && (
        <nav style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 600, flexWrap: 'wrap' }}>
          {onHomeClick && (
            <button
              type="button"
              id="nav-tab-home"
              onClick={onHomeClick}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 12px',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: 'transparent',
                color: '#EAF2F8',
                cursor: 'pointer',
              }}
            >
              <Home size={15} />
              <span>Home</span>
            </button>
          )}
          <button
            type="button"
            id="nav-tab-compliance"
            onClick={() => onTabChange('compliance')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 12px',
              borderRadius: '6px',
              border: activeTab === 'compliance' ? '1px solid rgba(159, 186, 208, 0.65)' : '1px solid transparent',
              backgroundColor: activeTab === 'compliance' ? '#102A43' : 'transparent',
              color: activeTab === 'compliance' ? '#ffffff' : '#EAF2F8',
              cursor: 'pointer',
            }}
          >
            <ShieldCheck size={15} />
            <span>Compliance Workflow</span>
          </button>

          <button
            type="button"
            id="nav-tab-dashboard"
            onClick={() => onTabChange('dashboard')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 12px',
              borderRadius: '6px',
              border: activeTab === 'dashboard' ? '1px solid rgba(159, 186, 208, 0.65)' : '1px solid transparent',
              backgroundColor: activeTab === 'dashboard' ? '#102A43' : 'transparent',
              color: activeTab === 'dashboard' ? '#ffffff' : '#EAF2F8',
              cursor: 'pointer',
            }}
          >
            <LayoutDashboard size={15} />
            <span>Diagnostics</span>
          </button>

          <button
            type="button"
            id="nav-logout-btn"
            onClick={handleSignOut}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              padding: '7px 11px',
              marginLeft: '4px',
              borderRadius: '6px',
              border: '1px solid rgba(234, 242, 248, 0.45)',
              backgroundColor: 'rgba(16, 42, 67, 0.35)',
              color: '#EAF2F8',
              cursor: 'pointer',
              fontSize: '12px',
            }}
          >
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>
        </nav>
      )}
    </header>
  );
};
