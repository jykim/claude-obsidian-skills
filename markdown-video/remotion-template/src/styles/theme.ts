export const theme = {
  colors: {
    background: '#0a1628',
    text: '#e8edf5',
    textMuted: '#8892a4',
    accent: '#4a9eff',
    surface: '#131f35',
    surfaceLight: '#1a2a45',
    success: '#2ecc71',
    danger: '#e74c3c',
    parts: {
      0: '#9b59b6', // purple
      1: '#3498db', // blue
      2: '#e67e22', // orange
      3: '#e74c3c', // red
      4: '#2ecc71', // green
      5: '#e74c3c', // red
      6: '#2ecc71', // green
    } as Record<number, string>,
  },
  font: {
    title: 64,
    subtitle: 36,
    body: 28,
    small: 22,
    badge: 20,
  },
  spacing: {
    pagePx: 100,
    pagePy: 80,
    sectionGap: 40,
    itemGap: 20,
  },
  animation: {
    fadeIn: 15, // frames
    stagger: 8, // frames between items
    slideDelay: 10, // initial delay before content appears
  },
  fps: 30,
  width: 1920,
  height: 1080,
} as const;
