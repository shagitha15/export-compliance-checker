import React from 'react';

interface GlitterParticle {
  id: string;
  angleDeg: number;
  radiusPct: number;
  size: number;
  kind: 'dot' | 'spark';
  tone: 'white' | 'blue' | 'sky';
  delaySec: number;
  durationSec: number;
}

const OUTER_RING_PARTICLES: GlitterParticle[] = [
  { id: 'o1', angleDeg: 0, radiusPct: 47.5, size: 3.1, kind: 'spark', tone: 'white', delaySec: 0.0, durationSec: 2.8 },
  { id: 'o2', angleDeg: 24, radiusPct: 46.8, size: 1.7, kind: 'dot', tone: 'blue', delaySec: 0.6, durationSec: 3.1 },
  { id: 'o3', angleDeg: 50, radiusPct: 48.1, size: 2.4, kind: 'spark', tone: 'sky', delaySec: 1.1, durationSec: 2.5 },
  { id: 'o4', angleDeg: 78, radiusPct: 47.2, size: 1.5, kind: 'dot', tone: 'white', delaySec: 1.7, durationSec: 3.4 },
  { id: 'o5', angleDeg: 105, radiusPct: 48.4, size: 2.9, kind: 'spark', tone: 'blue', delaySec: 0.3, durationSec: 2.9 },
  { id: 'o6', angleDeg: 132, radiusPct: 46.9, size: 1.6, kind: 'dot', tone: 'sky', delaySec: 1.4, durationSec: 3.2 },
  { id: 'o7', angleDeg: 162, radiusPct: 47.7, size: 2.7, kind: 'spark', tone: 'white', delaySec: 0.9, durationSec: 2.6 },
  { id: 'o8', angleDeg: 188, radiusPct: 48.3, size: 1.8, kind: 'dot', tone: 'blue', delaySec: 2.1, durationSec: 3.0 },
  { id: 'o9', angleDeg: 215, radiusPct: 47.1, size: 3.0, kind: 'spark', tone: 'sky', delaySec: 0.4, durationSec: 2.7 },
  { id: 'o10', angleDeg: 244, radiusPct: 48.0, size: 1.5, kind: 'dot', tone: 'white', delaySec: 1.8, durationSec: 3.3 },
  { id: 'o11', angleDeg: 272, radiusPct: 47.4, size: 2.6, kind: 'spark', tone: 'blue', delaySec: 1.0, durationSec: 2.5 },
  { id: 'o12', angleDeg: 300, radiusPct: 48.2, size: 1.7, kind: 'dot', tone: 'sky', delaySec: 2.3, durationSec: 3.1 },
  { id: 'o13', angleDeg: 330, radiusPct: 46.9, size: 2.8, kind: 'spark', tone: 'white', delaySec: 0.7, durationSec: 2.8 },
  { id: 'o14', angleDeg: 348, radiusPct: 47.9, size: 1.4, kind: 'dot', tone: 'blue', delaySec: 1.5, durationSec: 3.4 },
];

const INNER_RING_PARTICLES: GlitterParticle[] = [
  { id: 'i1', angleDeg: 14, radiusPct: 44.2, size: 1.6, kind: 'dot', tone: 'sky', delaySec: 0.2, durationSec: 3.2 },
  { id: 'i2', angleDeg: 46, radiusPct: 43.8, size: 2.3, kind: 'spark', tone: 'white', delaySec: 1.3, durationSec: 2.9 },
  { id: 'i3', angleDeg: 88, radiusPct: 44.5, size: 1.5, kind: 'dot', tone: 'blue', delaySec: 0.8, durationSec: 3.5 },
  { id: 'i4', angleDeg: 126, radiusPct: 43.9, size: 2.4, kind: 'spark', tone: 'sky', delaySec: 1.9, durationSec: 2.6 },
  { id: 'i5', angleDeg: 168, radiusPct: 44.6, size: 1.7, kind: 'dot', tone: 'white', delaySec: 0.5, durationSec: 3.1 },
  { id: 'i6', angleDeg: 204, radiusPct: 44.0, size: 2.5, kind: 'spark', tone: 'blue', delaySec: 1.6, durationSec: 2.8 },
  { id: 'i7', angleDeg: 248, radiusPct: 44.4, size: 1.5, kind: 'dot', tone: 'sky', delaySec: 2.2, durationSec: 3.3 },
  { id: 'i8', angleDeg: 288, radiusPct: 43.8, size: 2.2, kind: 'spark', tone: 'white', delaySec: 0.9, durationSec: 2.7 },
  { id: 'i9', angleDeg: 324, radiusPct: 44.5, size: 1.6, kind: 'dot', tone: 'blue', delaySec: 1.4, durationSec: 3.0 },
];

const TONE_COLOR: Record<GlitterParticle['tone'], string> = {
  white: '#FFFFFF',
  sky: '#BAE6FD',
  blue: '#60A5FA',
};

function toPoint(angleDeg: number, radiusPct: number): { x: number; y: number } {
  const rad = (angleDeg * Math.PI) / 180;
  return {
    x: 100 + radiusPct * 2 * Math.cos(rad),
    y: 100 + radiusPct * 2 * Math.sin(rad),
  };
}

function renderParticles(items: GlitterParticle[]) {
  return items.map((p) => {
    const { x, y } = toPoint(p.angleDeg, p.radiusPct);
    const fill = TONE_COLOR[p.tone];
    const animStyle: React.CSSProperties = {
      transformOrigin: `${x}px ${y}px`,
      animationDelay: `${p.delaySec}s`,
      animationDuration: `${p.durationSec}s`,
    };

    if (p.kind === 'dot') {
      return (
        <circle
          key={p.id}
          cx={x}
          cy={y}
          r={p.size}
          fill={fill}
          className="ecc-glitter-particle"
          style={animStyle}
        />
      );
    }

    const r = p.size * 1.45;
    const inner = p.size * 0.34;
    const d = [
      `M ${x} ${y - r}`,
      `L ${x + inner} ${y - inner}`,
      `L ${x + r} ${y}`,
      `L ${x + inner} ${y + inner}`,
      `L ${x} ${y + r}`,
      `L ${x - inner} ${y + inner}`,
      `L ${x - r} ${y}`,
      `L ${x - inner} ${y - inner}`,
      'Z',
    ].join(' ');

    return (
      <path
        key={p.id}
        d={d}
        fill={fill}
        className="ecc-glitter-particle"
        style={animStyle}
      />
    );
  });
}

export const GlobeGlitterOrbit: React.FC = () => {
  return (
    <div className="ecc-glitter-orbit" aria-hidden="true">
      <svg viewBox="0 0 200 200" className="ecc-glitter-svg">
        <defs>
          <filter id="ecc-glitter-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="0.85" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Subtle circular orbit ring */}
        <circle
          cx="100"
          cy="100"
          r="91"
          fill="none"
          stroke="rgba(147, 197, 253, 0.22)"
          strokeWidth="0.45"
          strokeDasharray="2 3.5"
        />

        {/* Primary clockwise circular glitter orbit */}
        <g className="ecc-glitter-ring-cw" filter="url(#ecc-glitter-glow)">
          {renderParticles(OUTER_RING_PARTICLES)}
        </g>

        {/* Secondary gentle harmonic circular orbit */}
        <g className="ecc-glitter-ring-ccw" filter="url(#ecc-glitter-glow)">
          {renderParticles(INNER_RING_PARTICLES)}
        </g>
      </svg>
    </div>
  );
};
