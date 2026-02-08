import React from 'react';
import { Composition } from 'remotion';
import { SlidesVideo } from './Video';
import { slides } from './data/slides';
import { theme } from './styles/theme';

const totalDurationFrames = slides.reduce(
  (sum, s) => sum + s.durationSec * theme.fps,
  0
);

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="__COMPOSITION_ID__"
      component={SlidesVideo}
      durationInFrames={totalDurationFrames}
      fps={theme.fps}
      width={theme.width}
      height={theme.height}
    />
  );
};
