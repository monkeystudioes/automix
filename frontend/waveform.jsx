/* ====================================================================
   AutoMix — Waveform & spectrum primitives
   ==================================================================== */

/* deterministic pseudo-noise so SSR/CSR match without state */
function seeded(seed) {
  let s = seed | 0;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

/* Build a polyline-friendly array of samples shaped like a song:
   - envelope sweeps (intro / verse / chorus dynamics)
   - per-band randomness
   - fade in / out tails */
function buildSamples(count, seed = 1, shape = 'song') {
  const rng = seeded(seed);
  const out = [];
  for (let i = 0; i < count; i++) {
    const t = i / (count - 1);
    let env;
    if (shape === 'vocal') {
      // staggered phrases — gaps + bursts
      const phrase = Math.sin(t * Math.PI * 6) * 0.4 + 0.55;
      const gate = (Math.sin(t * Math.PI * 22) > -0.2) ? 1 : 0.25;
      env = phrase * gate;
    } else if (shape === 'master') {
      // fuller, sustained, slightly compressed
      env = 0.6 + 0.32 * Math.sin(t * Math.PI * 3.2 + 0.4) + 0.12 * Math.sin(t * Math.PI * 9);
      env = Math.min(0.96, env);
    } else {
      // song-shaped: intro low, verse mid, chorus high, drop, outro
      const intro = Math.min(1, t * 6);
      const outro = Math.min(1, (1 - t) * 8);
      const sections =
        0.45 +
        0.35 * Math.sin(t * Math.PI * 2.4) +
        0.18 * Math.sin(t * Math.PI * 7.5);
      env = sections * Math.min(intro, outro);
    }
    const noise = (rng() - 0.5) * 0.7;
    const v = env * (0.55 + 0.45 * rng()) + noise * 0.25;
    out.push(Math.max(-1, Math.min(1, v)));
  }
  return out;
}

/* Bar-style waveform — like a DAW clip view. Renders as a single <svg>. */
function WaveBars({
  width = 800,
  height = 80,
  bars = 140,
  seed = 1,
  shape = 'song',
  color = 'var(--accent)',
  faint = 0.35,
  played = 0,         // 0..1, fraction "played"
  playedColor = null,
}) {
  const samples = React.useMemo(() => buildSamples(bars, seed, shape), [bars, seed, shape]);
  const barW = width / bars;
  const gap = Math.max(1, barW * 0.18);
  const mid = height / 2;
  const cutoff = played * bars;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none"
         style={{ display: 'block', width: '100%', height: '100%' }}>
      {samples.map((s, i) => {
        const h = Math.max(2, Math.abs(s) * (height * 0.92));
        const x = i * barW + gap / 2;
        const y = mid - h / 2;
        const isPlayed = i < cutoff;
        const c = isPlayed && playedColor ? playedColor : color;
        const op = isPlayed ? 1 : faint;
        return <rect key={i} x={x} y={y} width={Math.max(1, barW - gap)} height={h} fill={c} opacity={op} rx="1" />;
      })}
    </svg>
  );
}

/* Continuous-line waveform — like a master / EQ-style curve */
function WaveLine({ width = 800, height = 60, seed = 4, shape = 'master', stroke = 'var(--accent)', fill = null }) {
  const N = 220;
  const samples = React.useMemo(() => buildSamples(N, seed, shape), [seed, shape]);
  const mid = height / 2;
  const pts = samples.map((s, i) => {
    const x = (i / (N - 1)) * width;
    const y = mid - s * (height * 0.42);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const top = `M${pts.join(' L')}`;
  const bottomMirror = samples.slice().reverse().map((s, i) => {
    const x = ((N - 1 - i) / (N - 1)) * width;
    const y = mid + s * (height * 0.42);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const closed = `${top} L${bottomMirror.join(' L')} Z`;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none"
         style={{ display: 'block', width: '100%', height: '100%' }}>
      {fill && <path d={closed} fill={fill} opacity="0.18" />}
      <path d={top} fill="none" stroke={stroke} strokeWidth="1.4" strokeLinejoin="round" strokeLinecap="round" />
      <path d={`M${bottomMirror.join(' L')}`} fill="none" stroke={stroke} strokeWidth="1.4" opacity="0.55" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

/* Animated spectrum analyzer — used in processing screen */
function Spectrum({ bars = 56, seed = 9, running = true }) {
  const [tick, setTick] = React.useState(0);
  React.useEffect(() => {
    if (!running) return;
    let id;
    const loop = () => { setTick(t => t + 1); id = requestAnimationFrame(loop); };
    id = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(id);
  }, [running]);

  const heights = React.useMemo(() => {
    const rng = seeded(seed + tick);
    return Array.from({ length: bars }, (_, i) => {
      // envelope shape: peak in mid-low
      const t = i / (bars - 1);
      const env = 0.85 * Math.exp(-Math.pow((t - 0.32) * 2.0, 2)) + 0.35 * (1 - t);
      const jitter = 0.4 + 0.6 * rng();
      return Math.max(0.06, Math.min(1, env * jitter * 1.1));
    });
  }, [tick, bars, seed]);

  return (
    <div className="spectrum">
      {heights.map((h, i) => (
        <div key={i} className="bar" style={{ height: `${h * 100}%`, opacity: 0.55 + 0.45 * h }} />
      ))}
    </div>
  );
}

/* EQ curve mini-graph — used in result summary */
function EQCurve({ width = 320, height = 130, stroke = 'var(--accent)' }) {
  const pts = [];
  const N = 80;
  for (let i = 0; i < N; i++) {
    const t = i / (N - 1);
    // shape: gentle low shelf cut, presence bump ~3kHz, air lift
    const lowShelf = -0.18 * Math.exp(-Math.pow((t - 0.0) * 3, 2));
    const presence = 0.36 * Math.exp(-Math.pow((t - 0.55) * 4, 2));
    const air      = 0.22 * Math.exp(-Math.pow((t - 0.92) * 6, 2));
    const dip      = -0.12 * Math.exp(-Math.pow((t - 0.30) * 5, 2));
    const y = (lowShelf + presence + air + dip);
    const px = t * width;
    const py = height * 0.55 - y * (height * 0.42);
    pts.push([px, py]);
  }
  const d = 'M' + pts.map(p => p.map(n => n.toFixed(1)).join(',')).join(' L');
  const dArea = d + ` L${width},${height} L0,${height} Z`;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none"
         style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
      <defs>
        <linearGradient id="eqfill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#e3ff87" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#e3ff87" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={dArea} fill="url(#eqfill)" />
      <path d={d} fill="none" stroke={stroke} strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

/* expose */
Object.assign(window, { WaveBars, WaveLine, Spectrum, EQCurve, buildSamples });
