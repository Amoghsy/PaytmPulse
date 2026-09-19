import React, { useState } from 'react';
import { Zap, Filter, RefreshCw, X, Radio } from 'lucide-react';
import { PageHeader } from '../layout/PageHeader';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { EventItem, formatRelativeTime } from '../components/EventItem';
import { SeverityBadge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';

export function LiveEvents({ events = [], onRefresh, isRefreshing = false, onSimulatePayment }) {
  const [filterSeverity, setFilterSeverity] = useState('ALL'); // 'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'
  const [selectedEvent, setSelectedEvent] = useState(null);

  const filteredEvents = events.filter(evt => {
    if (filterSeverity === 'ALL') return true;
    const sev = String(evt.severity || 'LOW').toUpperCase();
    return sev === filterSeverity;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <PageHeader
        title="Live Events Stream"
        description="Real-time Phase 3 event ingestion, anomaly detections, and demand spike alerts"
        tag="Live Telemetry"
        action={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Button
              variant="outline"
              size="sm"
              icon={Zap}
              onClick={onSimulatePayment}
            >
              Simulate Live Event
            </Button>
            <Button
              variant="secondary"
              size="sm"
              icon={RefreshCw}
              onClick={onRefresh}
              loading={isRefreshing}
            >
              Refresh
            </Button>
          </div>
        }
      />

      {/* Filter Chips Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Filter size={14} /> Filter Severity:
          </span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => (
            <button
              key={sev}
              type="button"
              onClick={() => setFilterSeverity(sev)}
              style={{
                padding: '4px 12px',
                fontSize: '12px',
                fontWeight: 500,
                borderRadius: 'var(--radius-full)',
                border: filterSeverity === sev ? '1px solid var(--color-paytm-cyan)' : '1px solid var(--color-border)',
                backgroundColor: filterSeverity === sev ? 'var(--color-paytm-cyan-tint)' : '#FFFFFF',
                color: filterSeverity === sev ? 'var(--color-paytm-navy)' : 'var(--color-text-secondary)',
                cursor: 'pointer',
                transition: 'all var(--transition-fast)'
              }}
            >
              {sev}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--color-text-muted)' }}>
          <span className="live-indicator-dot" /> Streaming live from PostgreSQL / Redis PubSub
        </div>
      </div>

      {/* Main Grid: Events Timeline + Detail Drawer */}
      <div className="grid grid-12">
        <div className={selectedEvent ? 'col-7' : 'col-12'}>
          {filteredEvents.length === 0 ? (
            <Card>
              <EmptyState
                icon={Zap}
                title="No events matching filter"
                description="Simulate a new transaction or trigger live anomalies to view streaming telemetry."
                actionLabel="Simulate Live Payment"
                onAction={onSimulatePayment}
              />
            </Card>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {filteredEvents.map((evt, idx) => (
                <EventItem
                  key={evt.id || idx}
                  event={evt}
                  onSelect={(e) => setSelectedEvent(e)}
                  isSelected={selectedEvent?.id === evt.id}
                />
              ))}
            </div>
          )}
        </div>

        {/* Selected Event Payload Detail Drawer */}
        {selectedEvent && (
          <div className="col-5">
            <Card
              title="Event Telemetry Details"
              subtitle={`ID: ${selectedEvent.id ? selectedEvent.id.slice(0, 8) + '...' : 'Event Record'}`}
              action={
                <button
                  type="button"
                  onClick={() => setSelectedEvent(null)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
                >
                  <X size={18} />
                </button>
              }
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>Event Type</div>
                  <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-paytm-navy)' }}>
                    {selectedEvent.event_type || selectedEvent.type}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '16px' }}>
                  <div>
                    <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>Severity</div>
                    <SeverityBadge severity={selectedEvent.severity} />
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>Recorded</div>
                    <span style={{ fontSize: '13px', color: 'var(--color-text-primary)' }}>
                      {formatRelativeTime(selectedEvent.created_at || selectedEvent.timestamp)}
                    </span>
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>Summary</div>
                  <div style={{ fontSize: '13px', color: 'var(--color-text-primary)', lineHeight: 1.4 }}>
                    {selectedEvent.summary || selectedEvent.description || 'Live anomaly event payload.'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>Raw Payload</div>
                  <pre
                    style={{
                      padding: '12px',
                      backgroundColor: 'var(--color-bg-page)',
                      border: '1px solid var(--color-border)',
                      borderRadius: '8px',
                      fontSize: '11px',
                      fontFamily: 'monospace',
                      color: 'var(--color-text-primary)',
                      overflowX: 'auto',
                      maxHeight: '260px'
                    }}
                  >
                    {JSON.stringify(selectedEvent.payload || selectedEvent.parameters || selectedEvent, null, 2)}
                  </pre>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

export default LiveEvents;
