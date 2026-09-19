import React from 'react';

export function RfmDonut({ segmentsData }) {
  // Extract segments counts from backend segments_summary or direct keys
  const summary = segmentsData?.segments_summary || segmentsData || {};
  const highValue = summary.HIGH_VALUE || summary.high_value?.length || summary.high_value_count || 0;
  const active = (summary.ACTIVE || 0) + (summary.FREQUENT || 0) + (summary.NEW || 0) || summary.active?.length || summary.active_count || 0;
  const atRisk = summary.AT_RISK || summary.at_risk?.length || summary.at_risk_count || 0;
  const inactive = summary.INACTIVE || summary.inactive?.length || summary.inactive_count || 0;

  const total = segmentsData?.total_customers ?? (highValue + active + atRisk + inactive);
  const displayTotal = total > 0 ? total : 0;
  const divisor = total > 0 ? total : 1;

  const segments = [
    { label: 'High Value', count: highValue, color: '#002E6E', pct: total > 0 ? Math.round((highValue / divisor) * 100) : 0 },
    { label: 'Active & New', count: active, color: '#00B9F5', pct: total > 0 ? Math.round((active / divisor) * 100) : 0 },
    { label: 'At Risk', count: atRisk, color: '#F5A623', pct: total > 0 ? Math.round((atRisk / divisor) * 100) : 0 },
    { label: 'Inactive', count: inactive, color: '#94A3B8', pct: total > 0 ? Math.round((inactive / divisor) * 100) : 0 }
  ];

  // Calculate SVG Donut Strokes
  const size = 160;
  const strokeWidth = 24;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let cumulativePercent = 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
      {/* SVG Donut */}
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
          {segments.map((seg, idx) => {
            const strokeDasharray = `${(seg.pct / 100) * circumference} ${circumference}`;
            const strokeDashoffset = -((cumulativePercent / 100) * circumference);
            cumulativePercent += seg.pct;

            return (
              <circle
                key={idx}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="transparent"
                stroke={seg.color}
                strokeWidth={strokeWidth}
                strokeDasharray={strokeDasharray}
                strokeDashoffset={strokeDashoffset}
                style={{ transition: 'stroke-dasharray 0.5s ease' }}
              />
            );
          })}
        </svg>
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none'
          }}
        >
          <span style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-paytm-navy)' }}>
            {displayTotal}
          </span>
          <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>
            Customers
          </span>
        </div>
      </div>

      {/* 4-Item Legend */}
      <div style={{ width: '100%', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px 16px' }}>
        {segments.map((seg, idx) => (
          <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '3px',
                backgroundColor: seg.color,
                flexShrink: 0
              }}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--color-text-primary)' }}>
                  {seg.label}
                </span>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-paytm-navy)' }}>
                  {seg.count}
                </span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                {seg.pct}% of base
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default RfmDonut;
