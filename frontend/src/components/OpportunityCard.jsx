import React from 'react';
import { Sparkles, ArrowRight, TrendingUp, Package, Users, Tag } from 'lucide-react';
import { Button } from './ui/Button';
import { formatINR } from './KpiCard';

export function OpportunityCard({
  opportunity,
  onAct,
  loading = false,
  style = {}
}) {
  const type = opportunity.type || opportunity.opportunity_type || 'GENERAL';
  const title = opportunity.title || opportunity.headline || 'Business Growth Action';
  const description = opportunity.description || opportunity.rationale || opportunity.reason || '';
  const impactVal = opportunity.estimated_gain || opportunity.estimated_impact || opportunity.value || 0;

  const iconMap = {
    STOCKOUT_PREVENTION: Package,
    CROSS_SELL: Tag,
    CUSTOMER_WINBACK: Users,
    PROMOTION: TrendingUp,
    GENERAL: Sparkles
  };

  const Icon = iconMap[type] || Sparkles;

  return (
    <div
      style={{
        padding: '16px',
        backgroundColor: '#FFFFFF',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '12px',
        transition: 'border-color var(--transition-fast), box-shadow var(--transition-fast)',
        ...style
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
        <div
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            backgroundColor: 'var(--color-paytm-cyan-tint)',
            color: 'var(--color-text-cyan)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}
        >
          <Icon size={18} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
            <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-paytm-navy)', margin: 0 }}>
              {title}
            </h4>
            {impactVal > 0 && (
              <span
                style={{
                  fontSize: '12px',
                  fontWeight: 700,
                  color: 'var(--color-success-dark)',
                  backgroundColor: 'var(--color-success-tint)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  whiteSpace: 'nowrap'
                }}
              >
                +{formatINR(impactVal)}
              </span>
            )}
          </div>
          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', margin: '4px 0 0 0', lineHeight: 1.4 }}>
            {description}
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '4px' }}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onAct && onAct(opportunity)}
          loading={loading}
          style={{ fontSize: '12px', height: '30px' }}
        >
          Act on this <ArrowRight size={12} />
        </Button>
      </div>
    </div>
  );
}

export default OpportunityCard;
