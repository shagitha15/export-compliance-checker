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
      <footer style={{ padding: '16px', textAlign: 'center', fontSize: '13px', color: '#94a3b8', borderTop: '1px solid #e2e8f0' }}>
        Export Customs Documentation Compliance Checker &copy; 2026
      </footer>
    </div>
  );
};
