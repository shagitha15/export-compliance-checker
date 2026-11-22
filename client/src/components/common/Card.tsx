import React from 'react';

interface CardProps {
  title: string;
  children: React.ReactNode;
  subtitle?: string;
}

export const Card: React.FC<CardProps> = ({ title, subtitle, children }) => {
  return (
    <div style={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', marginBottom: '16px' }}>
      <h3 style={{ margin: '0 0 4px 0', fontSize: '16px', color: '#0f172a' }}>{title}</h3>
      {subtitle && <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: '#64748b' }}>{subtitle}</p>}
      <div>{children}</div>
    </div>
  );
};
