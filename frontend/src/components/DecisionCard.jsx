import React, { useState } from 'react';
import { Target, Check, X, MessageSquare, ChevronDown, ChevronUp, AlertCircle, ShieldCheck } from 'lucide-react';
import { Button } from './ui/Button';
import { StatusBadge } from './ui/Badge';
import { formatINR } from './KpiCard';

export function DecisionCard({
  decision,
  onApprove,
  onReject,
  onSendWhatsApp,
  approvingId,
  rejectingId,
  alertingId,
  activeMerchant
}) {
  const [showPayload, setShowPayload] = useState(false);

  const id = decision.id;
  const rawTitle = decision.title || 'Next Best Action Recommendation';
  const title = rawTitle.replace(/:\s*None/gi, '').replace(/:\s*null/gi, '').trim();
  const actionType = decision.action_type || decision.type || 'RESTOCK_PRODUCT';
  const reason = decision.reason || decision.description || decision.rationale || 'AI suggested action based on store telemetry';
  const impact = decision.estimated_impact?.value || decision.expected_impact_val || decision.impact || 0;
  const impactLabel = decision.estimated_impact?.type || 'ESTIMATED REVENUE GAIN';
  const confidence = decision.confidence ? Math.round(decision.confidence * 100) : 92;
  const status = decision.status || 'PENDING_APPROVAL';
  const params = decision.parameters || decision.payload;
  const lang = activeMerchant?.language || activeMerchant?.preferred_language || 'Hindi';

  const statusStr = String(status).toUpperCase();
  const isPending = statusStr.includes('PENDING') || statusStr === 'GENERATED' || statusStr === 'NEW';
  const isApproved = statusStr.includes('APPROV') || statusStr === 'EXECUTED';
  const isRejected = statusStr.includes('REJECT') || statusStr.includes('DECLIN');

  return (
    <div
      style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: '20px',
        boxShadow: 'var(--shadow-xs)',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        transition: 'all var(--transition-fast)'
      }}
    >
      {/* Top Row: Type, Title, Confidence & Status */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              backgroundColor: 'var(--color-paytm-cyan-tint)',
              color: 'var(--color-text-cyan)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}
          >
            <Target size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-paytm-navy)', margin: 0 }}>
                {title}
              </h3>
              <StatusBadge status={status} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-paytm-cyan-dark)' }}>
                {String(actionType).replace(/_/g, ' ')}
              </span>
              <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>•</span>
              <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <ShieldCheck size={13} color="var(--color-success)" /> {confidence}% confidence
              </span>
            </div>
          </div>
        </div>

        {impact > 0 && (
          <div
            style={{
              textAlign: 'right',
              padding: '6px 12px',
              backgroundColor: 'var(--color-success-tint)',
              border: '1px solid var(--color-success-border)',
              borderRadius: '8px',
              flexShrink: 0
            }}
          >
            <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-success-dark)' }}>
              +{formatINR(impact)}
            </div>
            <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-success-dark)', textTransform: 'uppercase' }}>
              {impactLabel}
            </div>
          </div>
        )}
      </div>

      {/* Rationale */}
      <div
        style={{
          padding: '12px 14px',
          backgroundColor: 'var(--color-bg-subtle)',
          borderRadius: '8px',
          borderLeft: '3px solid var(--color-paytm-cyan)'
        }}
      >
        <p style={{ fontSize: '13px', color: 'var(--color-text-primary)', margin: 0, lineHeight: 1.4 }}>
          <strong>AI Rationale:</strong> {reason}
        </p>
      </div>

      {/* Expandable Parameters / Payload */}
      {params && Object.keys(params).length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowPayload(!showPayload)}
            style={{
              background: 'none',
              border: 'none',
              padding: 0,
              fontSize: '12px',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            {showPayload ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            {showPayload ? 'Hide Action Payload' : 'View Action Payload Parameters'}
          </button>
          {showPayload && (
            <pre
              style={{
                marginTop: '8px',
                padding: '10px 12px',
                backgroundColor: 'var(--color-bg-page)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                fontSize: '11px',
                color: 'var(--color-text-primary)',
                fontFamily: 'monospace',
                overflowX: 'auto'
              }}
            >
              {JSON.stringify(params, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* Action Buttons (Strictly Right-Aligned with Clear Hierarchy & Vibrant Contrast) */}
      {isPending ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: '12px',
            paddingTop: '12px',
            borderTop: '1px solid var(--color-border-subtle)',
            flexWrap: 'wrap'
          }}
        >
          <Button
            variant="destructive"
            size="sm"
            onClick={() => onReject && onReject(id)}
            loading={rejectingId === id}
            icon={X}
            style={{ fontWeight: 600 }}
          >
            Decline Action
          </Button>

          <Button
            variant="whatsapp"
            size="sm"
            onClick={() => onSendWhatsApp && onSendWhatsApp(id)}
            loading={alertingId === id}
            icon={MessageSquare}
            style={{ fontWeight: 600 }}
          >
            Send WhatsApp Alert ({lang})
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => onApprove && onApprove(id)}
            loading={approvingId === id}
            icon={Check}
            style={{
              backgroundColor: 'var(--color-paytm-navy)',
              borderColor: 'var(--color-paytm-navy)',
              fontWeight: 600
            }}
          >
            Approve & Execute via Paytm
          </Button>
        </div>
      ) : (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingTop: '10px',
            borderTop: '1px solid var(--color-border-subtle)',
            fontSize: '12px',
            color: 'var(--color-text-secondary)'
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {isApproved ? (
              <span style={{ color: 'var(--color-success)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Check size={14} /> Action Approved & Executed
              </span>
            ) : isRejected ? (
              <span style={{ color: 'var(--color-danger)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                <X size={14} /> Action Declined
              </span>
            ) : (
              <span>Status: {status}</span>
            )}
          </span>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => onSendWhatsApp && onSendWhatsApp(id)}
            loading={alertingId === id}
            icon={MessageSquare}
            style={{ fontSize: '12px' }}
          >
            Resend WhatsApp ({lang})
          </Button>
        </div>
      )}
    </div>
  );
}

export default DecisionCard;
