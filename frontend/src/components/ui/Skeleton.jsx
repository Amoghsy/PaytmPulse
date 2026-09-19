import React from 'react';

export function Skeleton({
  width = '100%',
  height = '20px',
  borderRadius = 'var(--radius-sm)',
  className = '',
  style = {}
}) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{
        width,
        height,
        borderRadius,
        ...style
      }}
    />
  );
}

export function CardSkeleton({ lines = 3 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px' }}>
      <Skeleton width="40%" height="24px" />
      <Skeleton width="100%" height="16px" />
      {lines > 2 && <Skeleton width="80%" height="16px" />}
      {lines > 3 && <Skeleton width="60%" height="16px" />}
    </div>
  );
}

export default Skeleton;
