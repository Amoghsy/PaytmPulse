import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

export function formatINR(amount) {
  if (amount === null || amount === undefined || isNaN(amount)) return '₹0';
  const num = Math.round(Number(amount));
  return '₹' + num.toLocaleString('en-IN');
}

export function KpiCard({
  title,
  value,
  caption,
  trend, // { value: '+12.4%', isPositive: true }
  icon: Icon,
  isCurrency = false,
  loading = false,
  style = {}
}) {
  const displayValue = isCurrency ? formatINR(value) : (value !== null && value !== undefined ? Number(value).toLocaleString('en-IN') : '0');

  return (
    <div
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: '20px',
        boxShadow: 'var(--shadow-xs)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        minHeight: '124px',
        transition: 'transform var(--transition-fast), box-shadow var(--transition-fast)',
        ...style
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>
          {title}
        </span>
        {Icon && (
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: 'var(--color-paytm-cyan-tint)',
              color: 'var(--color-text-cyan)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <Icon size={18} />
          </div>
        )}
      </div>

      <div>
        <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--color-paytm-navy)', lineHeight: 1.2 }}>
          {loading ? '...' : displayValue}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
          {trend && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '2px',
                fontSize: '11px',
                fontWeight: 600,
                color: trend.isPositive !== false ? 'var(--color-success-dark)' : 'var(--color-danger-dark)',
                backgroundColor: trend.isPositive !== false ? 'var(--color-success-tint)' : 'var(--color-danger-tint)',
                padding: '1px 6px',
                borderRadius: '4px'
              }}
            >
              {trend.isPositive !== false ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              {trend.value}
            </span>
          )}
          {caption && (
            <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
              {caption}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default KpiCard;
