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
  const bg = variant === 'primary' ? '#2563eb' : variant === 'danger' ? '#ef4444' : '#64748b';
  return (
    <button
      style={{
        backgroundColor: bg,
        color: '#ffffff',
        border: 'none',
        borderRadius: '6px',
        padding: '8px 16px',
        fontSize: '14px',
        fontWeight: 500,
        cursor: 'pointer',
        ...style,
      }}
      {...props}
    >
      {children}
    </button>
  );
};
