import React from 'react';
import { PackageOpen } from 'lucide-react';
import { Button } from './Button';

export function EmptyState({
  icon: Icon = PackageOpen,
  title = 'No records found',
  description = 'There is no data available for this view at the moment.',
  action,
  actionLabel,
  onAction,
  actionLoading = false,
  style = {}
}) {
  return (
    <div
      style={{
        padding: '40px 20px',
        textAlign: 'center',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '12px',
        ...style
      }}
    >
      <div
        style={{
          width: '52px',
          height: '52px',
          borderRadius: '50%',
          backgroundColor: 'var(--color-bg-page)',
          border: '1px solid var(--color-border)',
          color: 'var(--color-text-muted)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        <Icon size={24} />
      </div>
      <div>
        <h4 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-paytm-navy)', margin: '0 0 4px 0' }}>
          {title}
        </h4>
        <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', maxWidth: '360px', margin: '0 auto' }}>
          {description}
        </p>
      </div>
      {action ? (
        <div style={{ marginTop: '8px' }}>{action}</div>
      ) : actionLabel && onAction ? (
        <div style={{ marginTop: '8px' }}>
          <Button variant="secondary" size="sm" onClick={onAction} loading={actionLoading}>
            {actionLabel}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

export default EmptyState;
