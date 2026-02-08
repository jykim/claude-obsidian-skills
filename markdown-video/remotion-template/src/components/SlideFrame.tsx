import React from 'react';
import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { theme } from '../styles/theme';
import { fontFamily } from '../styles/fonts';

interface SlideFrameProps {
  audio: string;
  partColor: number;
  children: React.ReactNode;
}

export const SlideFrame: React.FC<SlideFrameProps> = ({
  audio,
  partColor,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const fadeInDuration = Math.round(fps * 0.6);
  const fadeOutDuration = Math.round(fps * 0.6);

  const opacity = interpolate(
    frame,
    [0, fadeInDuration, durationInFrames - fadeOutDuration, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const color = theme.colors.parts[partColor] || theme.colors.accent;
  const barWidth = interpolate(
    frame,
    [0, fadeInDuration * 2],
    [0, 100],
    { extrapolateRight: 'clamp' }
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        fontFamily,
      }}
    >
      <AbsoluteFill
        style={{
          opacity,
          padding: `${theme.spacing.pagePy}px ${theme.spacing.pagePx}px`,
        }}
      >
        {children}
      </AbsoluteFill>

      {/* Bottom accent bar */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          width: `${barWidth}%`,
          height: 4,
          backgroundColor: color,
          opacity: opacity * 0.8,
        }}
      />

      <Audio src={staticFile(audio)} />
    </AbsoluteFill>
  );
};
