import React from 'react';

export function Badge({
  children,
  variant = 'neutral', // 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'brand'
  size = 'md', // 'sm' | 'md'
  dot = false,
  className = '',
  style = {}
}) {
  const variants = {
    success: {
      bg: 'var(--color-success-tint)',
      color: 'var(--color-success-dark)',
      border: 'var(--color-success-border)',
      dotColor: 'var(--color-success)'
    },
    warning: {
      bg: 'var(--color-warning-tint)',
      color: 'var(--color-warning-dark)',
      border: 'var(--color-warning-border)',
      dotColor: 'var(--color-warning)'
    },
    danger: {
      bg: 'var(--color-danger-tint)',
      color: 'var(--color-danger-dark)',
      border: 'var(--color-danger-border)',
      dotColor: 'var(--color-danger)'
    },
    info: {
      bg: 'var(--color-info-tint)',
      color: 'var(--color-text-cyan)',
      border: 'var(--color-info-border)',
      dotColor: 'var(--color-paytm-cyan)'
    },
    brand: {
      bg: 'rgba(0, 46, 110, 0.08)',
      color: 'var(--color-paytm-navy)',
      border: 'rgba(0, 46, 110, 0.2)',
      dotColor: 'var(--color-paytm-navy)'
    },
    neutral: {
      bg: 'var(--color-bg-hover)',
      color: 'var(--color-text-secondary)',
      border: 'var(--color-border)',
      dotColor: 'var(--color-text-muted)'
    }
  };

  const v = variants[variant] || variants.neutral;
  const isSmall = size === 'sm';

  return (
    <span
      className={`paytm-badge ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        padding: isSmall ? '2px 8px' : '3px 10px',
        fontSize: isSmall ? '11px' : '12px',
        fontWeight: 500,
        borderRadius: 'var(--radius-full)',
        backgroundColor: v.bg,
        color: v.color,
        border: `1px solid ${v.border}`,
        lineHeight: 1.3,
        whiteSpace: 'nowrap',
        ...style
      }}
    >
      {dot && (
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: v.dotColor
          }}
        />
      )}
      {children}
    </span>
  );
}

export function SeverityBadge({ severity }) {
  const sev = String(severity || 'LOW').toUpperCase();
  const map = {
    CRITICAL: { variant: 'danger', label: 'Critical' },
    HIGH: { variant: 'warning', label: 'High' },
    MEDIUM: { variant: 'info', label: 'Medium' },
    LOW: { variant: 'neutral', label: 'Low' }
  };
  const config = map[sev] || map.LOW;
  return (
    <Badge variant={config.variant} size="sm" dot>
      {config.label}
    </Badge>
  );
}

export function StatusBadge({ status }) {
  const s = String(status || 'PENDING').toUpperCase();
  const map = {
    APPROVED: { variant: 'success', label: 'Approved' },
    EXECUTED: { variant: 'success', label: 'Executed' },
    PENDING: { variant: 'warning', label: 'Pending Review' },
    REJECTED: { variant: 'danger', label: 'Declined' },
    FAILED: { variant: 'danger', label: 'Failed' },
    ACTIVE: { variant: 'success', label: 'Active' },
    SENT: { variant: 'success', label: 'Delivered' }
  };
  const config = map[s] || { variant: 'neutral', label: s };
  return (
    <Badge variant={config.variant} size="sm" dot>
      {config.label}
    </Badge>
  );
}
