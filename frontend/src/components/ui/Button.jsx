import React from 'react';
import { Loader2 } from 'lucide-react';

export function Button({
  children,
  variant = 'primary', // 'primary' | 'secondary' | 'outline' | 'destructive' | 'whatsapp' | 'ghost'
  size = 'md', // 'sm' | 'md' | 'lg' | 'icon'
  loading = false,
  disabled = false,
  icon: Icon,
  className = '',
  onClick,
  type = 'button',
  ...props
}) {
  const baseStyles = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    fontWeight: 500,
    fontFamily: 'inherit',
    borderRadius: '10px',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.6 : 1,
    transition: 'all 150ms cubic-bezier(0.4, 0, 0.2, 1)',
    border: '1px solid transparent',
    whiteSpace: 'nowrap',
    outline: 'none',
    userSelect: 'none'
  };

  const sizes = {
    sm: { padding: '6px 12px', fontSize: '12px', height: '32px' },
    md: { padding: '8px 16px', fontSize: '14px', height: '40px' },
    lg: { padding: '10px 20px', fontSize: '15px', height: '46px' },
    icon: { padding: '8px', width: '38px', height: '38px', borderRadius: '8px' }
  };

  const variants = {
    primary: {
      backgroundColor: 'var(--color-paytm-cyan)',
      color: '#FFFFFF',
      borderColor: 'var(--color-paytm-cyan)',
      boxShadow: '0 1px 2px rgba(0, 185, 245, 0.2)'
    },
    secondary: {
      backgroundColor: '#FFFFFF',
      color: 'var(--color-paytm-navy)',
      borderColor: 'var(--color-border)',
      boxShadow: 'var(--shadow-xs)'
    },
    outline: {
      backgroundColor: 'transparent',
      color: 'var(--color-paytm-navy)',
      borderColor: 'var(--color-border)'
    },
    destructive: {
      backgroundColor: '#FFFFFF',
      color: 'var(--color-danger)',
      borderColor: 'var(--color-danger-border)'
    },
    whatsapp: {
      backgroundColor: '#25D366',
      color: '#FFFFFF',
      borderColor: '#25D366',
      boxShadow: '0 1px 2px rgba(37, 211, 102, 0.25)'
    },
    ghost: {
      backgroundColor: 'transparent',
      color: 'var(--color-text-secondary)',
      borderColor: 'transparent'
    }
  };

  const combinedStyle = {
    ...baseStyles,
    ...(sizes[size] || sizes.md),
    ...(variants[variant] || variants.primary),
    ...(props.style || {})
  };

  const { style: _ignoredStyle, ...restProps } = props;

  return (
    <button
      type={type}
      style={combinedStyle}
      disabled={disabled || loading}
      onClick={onClick}
      className={`btn-custom btn-${variant} ${className}`}
      {...restProps}
    >
      {loading ? (
        <Loader2 size={size === 'sm' ? 14 : 16} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
      ) : React.isValidElement(Icon) ? (
        Icon
      ) : Icon ? (
        <Icon size={size === 'sm' ? 14 : 16} />
      ) : null}
      {children}
    </button>
  );
}

export default Button;
