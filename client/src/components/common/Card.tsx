import React from 'react';

interface CardProps {
  title: string;
  children: React.ReactNode;
  subtitle?: string;
  style?: React.CSSProperties;
}

export const Card: React.FC<CardProps> = ({ title, subtitle, children, style }) => {
  return (
    <div
      style={{
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--border-blush)',
        borderRadius: 'var(--radius-md)',
        padding: '22px',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '16px',
        ...style,
      }}
    >
      <h3 style={{ margin: '0 0 4px 0', fontSize: '16px', fontWeight: 700, color: 'var(--text-main)' }}>
        {title}
      </h3>
      {subtitle && (
        <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: 'var(--text-muted)' }}>
          {subtitle}
        </p>
      )}
      <div>{children}</div>
    </div>
  );
};
