import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { theme } from '../styles/theme';

interface BadgeProps {
  text: string;
  variant: 'success' | 'danger' | 'info' | 'muted';
  delay?: number;
}

const variantColors: Record<BadgeProps['variant'], string> = {
  success: theme.colors.success,
  danger: theme.colors.danger,
  info: theme.colors.accent,
  muted: theme.colors.textMuted,
};

export const Badge: React.FC<BadgeProps> = ({
  text,
  variant,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [delay, delay + theme.animation.fadeIn], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const color = variantColors[variant];

  return (
    <span
      style={{
        opacity,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 16px',
        borderRadius: 20,
        border: `2px solid ${color}`,
        backgroundColor: `${color}18`,
        fontSize: theme.font.badge,
        fontWeight: 600,
        color,
        lineHeight: 1.4,
      }}
    >
      {text}
    </span>
  );
};
