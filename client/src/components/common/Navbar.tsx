import React from 'react';

interface NavbarProps {
  title?: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  title = 'Export Customs Documentation Compliance Checker',
}) => {
  return (
    <header style={{ backgroundColor: '#1e293b', color: '#ffffff', padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontSize: '20px' }}>📦</span>
        <h1 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>{title}</h1>
      </div>
      <nav style={{ display: 'flex', gap: '16px', fontSize: '14px' }}>
        <a href="#dashboard" style={{ color: '#94a3b8', textDecoration: 'none' }}>Dashboard</a>
        <a href="#upload" style={{ color: '#94a3b8', textDecoration: 'none' }}>Upload</a>
        <a href="#compliance" style={{ color: '#94a3b8', textDecoration: 'none' }}>Compliance Audit</a>
      </nav>
    </header>
  );
};
