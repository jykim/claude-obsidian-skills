import React from 'react';

interface TwoColumnProps {
  left: React.ReactNode;
  right: React.ReactNode;
  ratio?: number; // left column ratio 0-1, default 0.5
  gap?: number;
}

export const TwoColumn: React.FC<TwoColumnProps> = ({
  left,
  right,
  ratio = 0.5,
  gap = 60,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        gap,
        flex: 1,
      }}
    >
      <div style={{ flex: ratio }}>{left}</div>
      <div style={{ flex: 1 - ratio }}>{right}</div>
    </div>
  );
};
