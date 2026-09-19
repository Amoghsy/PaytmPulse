import React, { useState } from 'react';
import { Target, CheckCircle2, XCircle, Clock, Sparkles, AlertCircle, RefreshCw } from 'lucide-react';
import { PageHeader } from '../layout/PageHeader';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { DecisionCard } from '../components/DecisionCard';
import { EmptyState } from '../components/ui/EmptyState';
import { StatusBadge } from '../components/ui/Badge';
import { formatINR } from '../components/KpiCard';

export function Decisions({
  pendingDecisions = [],
  decisionHistory = [],
  activeMerchant,
  onGenerateDecision,
  isGenerating = false,
  onApproveDecision,
  onRejectDecision,
  onSendWhatsAppAlert,
  approvingId,
  rejectingId,
  alertingId,
  onRefresh
}) {
  const [historyTab, setHistoryTab] = useState('ALL'); // 'ALL' | 'APPROVED' | 'REJECTED' | 'EXECUTED'
  const lang = activeMerchant?.language || activeMerchant?.preferred_language || 'Kannada';

  const filteredHistory = decisionHistory.filter(dec => {
    if (historyTab === 'ALL') return true;
    const s = String(dec.status || '').toUpperCase();
    return s === historyTab;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <PageHeader
        title="Next Best Actions & Decision Engine"
        description="Phase 6 multi-factor scored candidate actions awaiting merchant approval"
        tag="Paytm Decision Engine"
        action={
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Button
              variant="outline"
              size="sm"
              icon={RefreshCw}
              onClick={onRefresh}
            >
              Refresh
            </Button>
            <Button
              variant="primary"
              size="md"
              icon={Target}
              onClick={onGenerateDecision}
              loading={isGenerating}
            >
              Generate Next Best Action
            </Button>
          </div>
        }
      />

      {/* SECTION 1: Pending Decisions Awaiting Approval */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-paytm-navy)', margin: 0 }}>
              Pending Authorization
            </h2>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: '#FFFFFF',
                backgroundColor: pendingDecisions.length > 0 ? 'var(--color-danger)' : 'var(--color-text-muted)',
                padding: '2px 8px',
                borderRadius: '10px'
              }}
            >
              {pendingDecisions.length}
            </span>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
            Actions require merchant consent before automated dispatch
          </span>
        </div>

        {pendingDecisions.length === 0 ? (
          <Card>
            <EmptyState
              icon={CheckCircle2}
              title="All caught up! No pending actions."
              description="Click 'Generate Next Best Action' to evaluate live inventory depletion, sales spikes, or customer winbacks."
              actionLabel="Generate Next Best Action"
              onAction={onGenerateDecision}
              actionLoading={isGenerating}
            />
          </Card>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {pendingDecisions.map(decision => (
              <DecisionCard
                key={decision.id}
                decision={decision}
                onApprove={onApproveDecision}
                onReject={onRejectDecision}
                onSendWhatsApp={onSendWhatsAppAlert}
                approvingId={approvingId}
                rejectingId={rejectingId}
                alertingId={alertingId}
                activeMerchant={activeMerchant}
              />
            ))}
          </div>
        )}
      </div>

      {/* SECTION 2: Decision History Log with Tabs */}
      <div style={{ marginTop: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '12px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-paytm-navy)', margin: 0 }}>
            Decision History & Audit Trail
          </h2>

          {/* Sub-tabs */}
          <div
            style={{
              display: 'inline-flex',
              padding: '3px',
              backgroundColor: 'var(--color-bg-page)',
              border: '1px solid var(--color-border)',
              borderRadius: '8px',
              gap: '2px'
            }}
          >
            {['ALL', 'APPROVED', 'REJECTED', 'EXECUTED'].map(tab => (
              <button
                key={tab}
                type="button"
                onClick={() => setHistoryTab(tab)}
                style={{
                  padding: '4px 12px',
                  fontSize: '12px',
                  fontWeight: 500,
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  backgroundColor: historyTab === tab ? '#FFFFFF' : 'transparent',
                  color: historyTab === tab ? 'var(--color-paytm-navy)' : 'var(--color-text-secondary)',
                  boxShadow: historyTab === tab ? 'var(--shadow-xs)' : 'none',
                  transition: 'all 150ms ease'
                }}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        <Card noPadding>
          {filteredHistory.length === 0 ? (
            <div style={{ padding: '32px' }}>
              <EmptyState
                icon={Clock}
                title="No historical decisions"
                description="Decisions you approve or decline will appear in this audit log."
              />
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ backgroundColor: 'var(--color-bg-page)', borderBottom: '1px solid var(--color-border)' }}>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Recommendation</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Action Type</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Impact</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Confidence</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Status</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredHistory.map((rec, idx) => (
                    <tr
                      key={rec.id || idx}
                      style={{
                        borderBottom: '1px solid var(--color-border-subtle)',
                        backgroundColor: idx % 2 === 0 ? '#FFFFFF' : 'var(--color-bg-subtle)'
                      }}
                    >
                      <td style={{ padding: '12px 16px', fontWeight: 500, color: 'var(--color-paytm-navy)' }}>
                        {rec.title}
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary)' }}>
                        {rec.type?.replace(/_/g, ' ') || 'STOCK REORDER'}
                      </td>
                      <td style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--color-success-dark)' }}>
                        {rec.expected_impact ? rec.expected_impact : '₹1,500'}
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary)' }}>
                        {rec.confidence ? `${Math.round(rec.confidence * 100)}%` : '92%'}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <StatusBadge status={rec.status} />
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--color-text-muted)', fontSize: '12px' }}>
                        {rec.created_at ? new Date(rec.created_at).toLocaleDateString() : 'Today'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

export default Decisions;
