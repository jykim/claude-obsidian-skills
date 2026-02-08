import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { theme } from '../styles/theme';

interface SlideHeaderProps {
  title: string;
  subtitle?: string;
  color: string;
  delay?: number;
  titleSize?: number;
}

export const SlideHeader: React.FC<SlideHeaderProps> = ({
  title,
  subtitle,
  color,
  delay = theme.animation.slideDelay,
  titleSize = theme.font.title,
}) => {
  const frame = useCurrentFrame();
  const { fadeIn } = theme.animation;

  const titleOpacity = interpolate(frame, [delay, delay + fadeIn], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const titleY = interpolate(frame, [delay, delay + fadeIn], [20, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const subDelay = delay + 8;
  const subOpacity = subtitle
    ? interpolate(frame, [subDelay, subDelay + fadeIn], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      })
    : 0;
  const subY = subtitle
    ? interpolate(frame, [subDelay, subDelay + fadeIn], [20, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      })
    : 0;

  return (
    <div style={{ marginBottom: theme.spacing.sectionGap }}>
      <div
        style={{
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
        }}
      >
        <h1
          style={{
            fontSize: titleSize,
            fontWeight: 700,
            color: theme.colors.text,
            margin: 0,
            lineHeight: 1.2,
          }}
        >
          {title}
        </h1>
        <div
          style={{
            width: 80,
            height: 4,
            backgroundColor: color,
            marginTop: 12,
            borderRadius: 2,
          }}
        />
      </div>
      {subtitle && (
        <div
          style={{
            opacity: subOpacity,
            transform: `translateY(${subY}px)`,
            marginTop: 16,
          }}
        >
          <p
            style={{
              fontSize: theme.font.subtitle,
              color: theme.colors.textMuted,
              margin: 0,
              lineHeight: 1.4,
            }}
          >
            {subtitle}
          </p>
        </div>
      )}
    </div>
  );
};
