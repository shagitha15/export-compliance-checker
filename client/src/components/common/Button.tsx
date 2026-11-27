import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  children,
  style,
  ...props
}) => {
  const getColors = () => {
    switch (variant) {
      case 'primary':
        return {
          bg: 'var(--primary-blush)',
          color: '#ffffff',
          border: 'none',
        };
      case 'danger':
        return {
          bg: 'var(--status-error-bg)',
          color: 'var(--status-error-text)',
          border: '1px solid var(--status-error-border)',
        };
      case 'secondary':
      default:
        return {
          bg: 'var(--bg-surface)',
          color: 'var(--text-main)',
          border: '1px solid var(--border-blush)',
        };
    }
  };

  const colors = getColors();

  return (
    <button
      style={{
        backgroundColor: colors.bg,
        color: colors.color,
        border: colors.border,
        borderRadius: 'var(--radius-sm)',
        padding: '8px 16px',
        fontSize: '14px',
        fontWeight: 600,
        cursor: props.disabled ? 'not-allowed' : 'pointer',
        opacity: props.disabled ? 0.6 : 1,
        transition: 'all 0.2s ease',
        ...style,
      }}
      {...props}
    >
      {children}
    </button>
  );
};
