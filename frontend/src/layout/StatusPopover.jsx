import React, { useState, useRef, useEffect } from 'react';
import { Server, Database, Layers, Radio, CheckCircle2, XCircle, Clock } from 'lucide-react';

export function StatusPopover({ systemHealth, lastUpdated }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (ref.current && !ref.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const allLive = systemHealth?.allLive;
  const timeStr = lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : 'Just now';

  const services = [
    { name: 'FastAPI Backend', icon: Server, ok: systemHealth?.backend, desc: 'Port 8000 • Core Engine' },
    { name: 'PostgreSQL Database', icon: Database, ok: systemHealth?.database, desc: 'Supabase / Local DB' },
    { name: 'Redis Cache & PubSub', icon: Layers, ok: systemHealth?.redis, desc: 'Fast In-Memory State' },
    { name: 'n8n Workflow Automation', icon: Radio, ok: systemHealth?.n8n, desc: 'Port 5678 • Webhooks' }
  ];

  return (
    <div style={{ position: 'relative' }} ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 12px',
          borderRadius: '20px',
          border: `1px solid ${allLive ? 'var(--color-success-border)' : 'var(--color-warning-border)'}`,
          backgroundColor: allLive ? 'var(--color-success-tint)' : 'var(--color-warning-tint)',
          color: allLive ? 'var(--color-success-dark)' : 'var(--color-warning-dark)',
          fontSize: '12px',
          fontWeight: 600,
          cursor: 'pointer',
          outline: 'none',
          transition: 'all var(--transition-fast)'
        }}
      >
        <span
          style={{
            width: '7px',
            height: '7px',
            borderRadius: '50%',
            backgroundColor: allLive ? 'var(--color-success)' : 'var(--color-warning)',
            boxShadow: allLive ? '0 0 0 2px rgba(33, 193, 122, 0.2)' : 'none'
          }}
        />
        {allLive ? 'All systems live' : 'Degraded state'}
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            right: 0,
            width: '280px',
            backgroundColor: '#FFFFFF',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-popover)',
            padding: '16px',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            animation: 'toast-in 150ms ease'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '8px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-paytm-navy)' }}>
              Telemetry Infrastructure
            </span>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '3px' }}>
              <Clock size={11} /> {timeStr}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {services.map((svc, idx) => {
              const Icon = svc.icon;
              return (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ color: 'var(--color-text-secondary)' }}>
                      <Icon size={16} />
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: 500, color: 'var(--color-text-primary)' }}>
                        {svc.name}
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
                        {svc.desc}
                      </div>
                    </div>
                  </div>
                  {svc.ok ? (
                    <CheckCircle2 size={16} color="var(--color-success)" />
                  ) : (
                    <XCircle size={16} color="var(--color-danger)" />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
