import React, { useState } from 'react';
import { Zap, AlertTriangle, TrendingDown, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { SeverityBadge } from './ui/Badge';

export function formatRelativeTime(dateInput) {
  if (!dateInput) return 'Just now';
  const d = new Date(dateInput);
  if (isNaN(d.getTime())) return 'Recently';
  const diffSec = Math.floor((new Date() - d) / 1000);
  if (diffSec < 60) return 'Just now';
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

export function EventItem({ event, onSelect, isSelected = false }) {
  const [expanded, setExpanded] = useState(false);

  const eventType = event.event_type || event.type || 'SYSTEM_EVENT';
  const severity = event.severity || 'LOW';
  const summary = event.summary || event.description || event.message || 'Business Telemetry Update';
  const timestamp = event.created_at || event.timestamp;
  const payload = event.payload || event.parameters;

  const getIcon = () => {
    if (eventType.includes('SPIKE')) return <Zap size={16} color="#00B9F5" />;
    if (eventType.includes('STOCK') || eventType.includes('DECLINE')) return <AlertTriangle size={16} color="#F5A623" />;
    if (eventType.includes('DECLINE')) return <TrendingDown size={16} color="#F0475B" />;
    return <CheckCircle size={16} color="#21C17A" />;
  };

  return (
    <div
      onClick={() => onSelect && onSelect(event)}
      style={{
        padding: '12px 16px',
        backgroundColor: isSelected ? 'var(--color-bg-hover)' : '#FFFFFF',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        cursor: onSelect ? 'pointer' : 'default',
        transition: 'background-color var(--transition-fast)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              backgroundColor: 'var(--color-bg-page)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}
          >
            {getIcon()}
          </div>
          <div>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-paytm-navy)' }}>
              {eventType.replace(/_/g, ' ')}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <SeverityBadge severity={severity} />
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
            {formatRelativeTime(timestamp)}
          </span>
        </div>
      </div>

      <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', margin: '8px 0 0 36px', lineHeight: 1.4 }}>
        {summary}
      </p>

      {payload && Object.keys(payload).length > 0 && (
        <div style={{ marginTop: '8px', marginLeft: '36px' }}>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            style={{
              background: 'none',
              border: 'none',
              padding: 0,
              fontSize: '11px',
              color: 'var(--color-paytm-cyan-dark)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {expanded ? 'Hide payload' : 'Inspect payload'}
          </button>
          {expanded && (
            <pre
              style={{
                marginTop: '6px',
                padding: '8px 10px',
                backgroundColor: 'var(--color-bg-subtle)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                fontSize: '11px',
                color: 'var(--color-text-primary)',
                overflowX: 'auto',
                fontFamily: 'monospace'
              }}
            >
              {JSON.stringify(payload, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

export default EventItem;
