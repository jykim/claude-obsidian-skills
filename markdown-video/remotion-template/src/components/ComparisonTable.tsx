import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { theme } from '../styles/theme';

interface ComparisonTableProps {
  headers: string[];
  rows: string[][];
  headerColors?: string[];
  delay?: number;
  fontSize?: number;
}

export const ComparisonTable: React.FC<ComparisonTableProps> = ({
  headers,
  rows,
  headerColors,
  delay = theme.animation.slideDelay + 15,
  fontSize = theme.font.body,
}) => {
  const frame = useCurrentFrame();
  const { fadeIn, stagger } = theme.animation;
  const colCount = headers.length;

  const headerOpacity = interpolate(frame, [delay, delay + fadeIn], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        width: '100%',
        borderRadius: 12,
        overflow: 'hidden',
        border: `1px solid ${theme.colors.surfaceLight}`,
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: 'flex',
          opacity: headerOpacity,
        }}
      >
        {headers.map((header, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              padding: '18px 24px',
              backgroundColor: headerColors?.[i] || theme.colors.surfaceLight,
              fontSize: fontSize - 2,
              fontWeight: 700,
              color: theme.colors.text,
              textAlign: 'center',
              borderRight:
                i < colCount - 1
                  ? `1px solid ${theme.colors.background}`
                  : 'none',
            }}
          >
            {header}
          </div>
        ))}
      </div>

      {/* Data rows */}
      {rows.map((row, rowIdx) => {
        const rowDelay = delay + fadeIn + rowIdx * stagger;
        const rowOpacity = interpolate(
          frame,
          [rowDelay, rowDelay + fadeIn],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );
        const rowY = interpolate(
          frame,
          [rowDelay, rowDelay + fadeIn],
          [12, 0],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );

        return (
          <div
            key={rowIdx}
            style={{
              display: 'flex',
              opacity: rowOpacity,
              transform: `translateY(${rowY}px)`,
              borderTop: `1px solid ${theme.colors.surfaceLight}`,
            }}
          >
            {row.map((cell, cellIdx) => (
              <div
                key={cellIdx}
                style={{
                  flex: 1,
                  padding: '14px 24px',
                  fontSize: fontSize - 4,
                  color: theme.colors.text,
                  lineHeight: 1.5,
                  backgroundColor:
                    rowIdx % 2 === 0
                      ? theme.colors.surface
                      : 'transparent',
                  borderRight:
                    cellIdx < colCount - 1
                      ? `1px solid ${theme.colors.surfaceLight}`
                      : 'none',
                }}
              >
                {cell}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
};
