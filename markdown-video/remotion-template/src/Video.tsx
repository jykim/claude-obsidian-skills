import React from 'react';
import { Sequence } from 'remotion';
import { sceneMap } from './scenes';
import { slides } from './data/slides';
import { theme } from './styles/theme';

export const SlidesVideo: React.FC = () => {
  let currentFrame = 0;

  return (
    <>
      {slides.map((slide) => {
        const durationInFrames = slide.durationSec * theme.fps;
        const from = currentFrame;
        currentFrame += durationInFrames;

        const SceneComponent = sceneMap[slide.id];
        if (!SceneComponent) return null;

        return (
          <Sequence
            key={slide.id}
            from={from}
            durationInFrames={durationInFrames}
            name={`${slide.id}. ${slide.title}`}
          >
            <SceneComponent slide={slide} />
          </Sequence>
        );
      })}
    </>
  );
};
