import React from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

export function ToastContainer({ toasts = [], onCloseToast, onRemove }) {
  if (!toasts || !toasts.length) return null;

  const handleClose = onCloseToast || onRemove;

  const icons = {
    success: { icon: CheckCircle2, color: 'var(--color-success)', bg: 'var(--color-success-tint)', border: 'var(--color-success-border)' },
    warning: { icon: AlertTriangle, color: 'var(--color-warning)', bg: 'var(--color-warning-tint)', border: 'var(--color-warning-border)' },
    error: { icon: AlertCircle, color: 'var(--color-danger)', bg: 'var(--color-danger-tint)', border: 'var(--color-danger-border)' },
    info: { icon: Info, color: 'var(--color-paytm-cyan)', bg: 'var(--color-info-tint)', border: 'var(--color-info-border)' }
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 99999,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        maxWidth: '420px',
        width: 'calc(100% - 48px)',
        pointerEvents: 'none'
      }}
    >
      {toasts.map(toast => {
        const conf = icons[toast.type] || icons.info;
        const Icon = conf.icon;
        return (
          <div
            key={toast.id}
            style={{
              pointerEvents: 'auto',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              padding: '12px 16px',
              backgroundColor: '#FFFFFF',
              border: `1px solid ${conf.border}`,
              borderLeft: `4px solid ${conf.color}`,
              borderRadius: '10px',
              boxShadow: 'var(--shadow-lg)',
              animation: 'fadeIn 200ms ease'
            }}
          >
            <div style={{ color: conf.color, marginTop: '2px', flexShrink: 0 }}>
              <Icon size={18} />
            </div>
            <div style={{ flex: 1, fontSize: '13px', color: 'var(--color-text-primary)', lineHeight: 1.4 }}>
              {toast.message}
            </div>
            {handleClose && (
              <button
                type="button"
                onClick={() => handleClose(toast.id)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-text-muted)',
                  cursor: 'pointer',
                  padding: '2px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <X size={14} />
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default ToastContainer;
