import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { theme } from '../styles/theme';

interface NumberedFlowProps {
  steps: string[];
  delay?: number;
  color?: string;
}

export const NumberedFlow: React.FC<NumberedFlowProps> = ({
  steps,
  delay = theme.animation.slideDelay + 15,
  color = theme.colors.accent,
}) => {
  const frame = useCurrentFrame();
  const { fadeIn, stagger } = theme.animation;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {steps.map((step, i) => {
        const itemDelay = delay + i * stagger;
        const opacity = interpolate(
          frame,
          [itemDelay, itemDelay + fadeIn],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );
        const translateX = interpolate(
          frame,
          [itemDelay, itemDelay + fadeIn],
          [20, 0],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );

        return (
          <React.Fragment key={i}>
            <div
              style={{
                opacity,
                transform: `translateX(${translateX}px)`,
                display: 'flex',
                alignItems: 'center',
                gap: 20,
              }}
            >
              {/* Number circle */}
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: '50%',
                  backgroundColor: color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: theme.font.badge,
                  fontWeight: 700,
                  color: '#fff',
                  flexShrink: 0,
                }}
              >
                {i + 1}
              </div>
              <span
                style={{
                  fontSize: theme.font.body - 2,
                  color: theme.colors.text,
                  lineHeight: 1.4,
                }}
              >
                {step}
              </span>
            </div>

            {/* Connector line */}
            {i < steps.length - 1 && (
              <div
                style={{
                  opacity: opacity * 0.4,
                  width: 2,
                  height: 16,
                  backgroundColor: color,
                  marginLeft: 19,
                }}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
