import React from 'react';
import { Navbar } from '../components/common/Navbar';

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      <main style={{ flex: 1, maxWidth: '1200px', margin: '0 auto', width: '100%', padding: '24px 16px' }}>
        {children}
      </main>
      <footer
        style={{
          padding: '16px',
          textAlign: 'center',
          fontSize: '13px',
          color: 'var(--text-subtle)',
          borderTop: '1px solid var(--border-blush)',
          backgroundColor: 'var(--bg-surface)',
        }}
      >
        Export Customs Documentation Compliance Checker &copy; 2026
      </footer>
    </div>
  );
};
