import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { theme } from '../styles/theme';

interface BulletListProps {
  items: string[];
  delay?: number;
  color?: string;
  fontSize?: number;
}

export const BulletList: React.FC<BulletListProps> = ({
  items,
  delay = theme.animation.slideDelay + 15,
  color = theme.colors.accent,
  fontSize = theme.font.body,
}) => {
  const frame = useCurrentFrame();
  const { fadeIn, stagger } = theme.animation;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.itemGap }}>
      {items.map((item, i) => {
        const itemDelay = delay + i * stagger;
        const opacity = interpolate(frame, [itemDelay, itemDelay + fadeIn], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        const translateY = interpolate(frame, [itemDelay, itemDelay + fadeIn], [20, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });

        return (
          <div
            key={i}
            style={{
              opacity,
              transform: `translateY(${translateY}px)`,
              display: 'flex',
              alignItems: 'flex-start',
              gap: 16,
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: color,
                marginTop: Math.round(fontSize * 0.4),
                flexShrink: 0,
              }}
            />
            <span
              style={{
                fontSize,
                color: theme.colors.text,
                lineHeight: 1.5,
              }}
            >
              {item}
            </span>
          </div>
        );
      })}
    </div>
  );
};
