import React from 'react';

export function Card({
  children,
  title,
  subtitle,
  action,
  icon: Icon,
  className = '',
  style = {},
  noPadding = false,
  ...props
}) {
  return (
    <div
      className={`paytm-card ${className}`}
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-xs)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        ...style
      }}
      {...props}
    >
      {(title || subtitle || action || Icon) && (
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--color-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {Icon && (
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  backgroundColor: 'var(--color-paytm-cyan-tint)',
                  color: 'var(--color-text-cyan)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <Icon size={18} />
              </div>
            )}
            <div>
              {title && (
                <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-paytm-navy)', margin: 0 }}>
                  {title}
                </h3>
              )}
              {subtitle && (
                <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', margin: '2px 0 0 0' }}>
                  {subtitle}
                </p>
              )}
            </div>
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div
        style={{
          padding: noPadding ? '0' : '20px',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
          height: '100%',
          overflow: noPadding ? 'hidden' : 'visible'
        }}
      >
        {children}
      </div>
    </div>
  );
}

export default Card;
