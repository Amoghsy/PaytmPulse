import React, { useState, useRef, useEffect } from 'react';
import { FlaskConical, Database, Zap, ChevronDown, Check } from 'lucide-react';

export function DemoMenu({ onSeedData, onSimulateTransaction, isSeeding = false, isSimulating = false }) {
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

  return (
    <div style={{ position: 'relative' }} ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        title="Developer & Demo Tools"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 12px',
          backgroundColor: '#FFFFFF',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          cursor: 'pointer',
          outline: 'none',
          fontSize: '12px',
          fontWeight: 500,
          color: 'var(--color-paytm-navy)',
          boxShadow: 'var(--shadow-xs)',
          transition: 'all var(--transition-fast)'
        }}
      >
        <FlaskConical size={14} color="var(--color-paytm-cyan-dark)" />
        <span>Demo Tools</span>
        <ChevronDown size={13} color="var(--color-text-muted)" />
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            right: 0,
            width: '260px',
            backgroundColor: '#FFFFFF',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-popover)',
            padding: '8px',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            animation: 'toast-in 150ms ease'
          }}
        >
          <div style={{ padding: '6px 8px', fontSize: '11px', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
            Simulation & Seeding
          </div>

          <button
            type="button"
            disabled={isSeeding}
            onClick={() => {
              onSeedData();
              setOpen(false);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 12px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: 'transparent',
              color: 'var(--color-text-primary)',
              cursor: isSeeding ? 'not-allowed' : 'pointer',
              textAlign: 'left',
              width: '100%',
              fontSize: '13px',
              transition: 'background-color var(--transition-fast)'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-bg-page)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <div style={{ width: '28px', height: '28px', borderRadius: '6px', backgroundColor: 'var(--color-paytm-cyan-tint)', color: 'var(--color-text-cyan)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Database size={15} />
            </div>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--color-paytm-navy)' }}>
                {isSeeding ? 'Seeding...' : 'Seed Demo Data'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                Reset & populate sample stores
              </div>
            </div>
          </button>

          <button
            type="button"
            disabled={isSimulating}
            onClick={() => {
              onSimulateTransaction();
              setOpen(false);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 12px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: 'transparent',
              color: 'var(--color-text-primary)',
              cursor: isSimulating ? 'not-allowed' : 'pointer',
              textAlign: 'left',
              width: '100%',
              fontSize: '13px',
              transition: 'background-color var(--transition-fast)'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-bg-page)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <div style={{ width: '28px', height: '28px', borderRadius: '6px', backgroundColor: 'var(--color-success-tint)', color: 'var(--color-success-dark)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Zap size={15} />
            </div>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--color-paytm-navy)' }}>
                {isSimulating ? 'Simulating...' : 'Simulate UPI Payment'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                Emit real-time purchase event
              </div>
            </div>
          </button>
        </div>
      )}
    </div>
  );
}
