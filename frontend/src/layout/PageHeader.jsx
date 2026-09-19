import React from 'react';

export function PageHeader({
  title,
  description,
  action,
  tag
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: '16px',
        marginBottom: '24px',
        flexWrap: 'wrap'
      }}
    >
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <h1 style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-paytm-navy)', margin: 0 }}>
            {title}
          </h1>
          {tag && (
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--color-text-cyan)',
                backgroundColor: 'var(--color-paytm-cyan-tint)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-full)'
              }}
            >
              {tag}
            </span>
          )}
        </div>
        {description && (
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', margin: '4px 0 0 0' }}>
            {description}
          </p>
        )}
      </div>

      {action && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {action}
        </div>
      )}
    </div>
  );
}

export default PageHeader;
