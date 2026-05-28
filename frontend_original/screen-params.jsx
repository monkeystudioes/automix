/* ====================================================================
   AutoMix — Screen 3: Parameters
   Genre selector + sliders/toggles
   ==================================================================== */

/* Each genre's "art" is a unique SVG composition — no photos, no clichés.
   Distinct color temperature, geometry and texture per genre. */
function GenreArt({ kind }) {
  switch (kind) {
    case 'reggaeton':
      return (
        <svg viewBox="0 0 120 140" preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
          <defs>
            <radialGradient id="rg-r" cx="0.3" cy="0.2" r="1">
              <stop offset="0%" stopColor="#ff7a3d"/>
              <stop offset="55%" stopColor="#c1265a"/>
              <stop offset="100%" stopColor="#3a0a26"/>
            </radialGradient>
            <pattern id="rg-r-dot" x="0" y="0" width="6" height="6" patternUnits="userSpaceOnUse">
              <circle cx="3" cy="3" r="0.7" fill="rgba(255,235,200,0.18)"/>
            </pattern>
          </defs>
          <rect width="120" height="140" fill="url(#rg-r)"/>
          <rect width="120" height="140" fill="url(#rg-r-dot)"/>
          {/* dembow heart pulse */}
          <path d="M20 90 Q35 75 50 90 Q65 105 80 90 Q95 75 110 90" stroke="rgba(255,220,180,0.45)" strokeWidth="1.2" fill="none"/>
          <path d="M10 105 Q30 88 50 105 Q70 122 90 105 Q105 92 120 105" stroke="rgba(255,220,180,0.22)" strokeWidth="1" fill="none"/>
        </svg>
      );
    case 'trap':
      return (
        <svg viewBox="0 0 120 140" preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
          <defs>
            <linearGradient id="rg-t" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#3b1b6b"/>
              <stop offset="100%" stopColor="#0a0414"/>
            </linearGradient>
          </defs>
          <rect width="120" height="140" fill="url(#rg-t)"/>
          {/* hi-hat divisions */}
          {Array.from({ length: 14 }).map((_, i) => (
            <line key={i} x1={10 + i * 7} y1="25" x2={10 + i * 7} y2={i % 3 === 0 ? 55 : 40} stroke={i % 3 === 0 ? '#a070ff' : 'rgba(160,112,255,0.45)'} strokeWidth="1"/>
          ))}
          {/* sub-bass */}
          <path d="M0 110 Q30 80 60 110 T120 110 L120 140 L0 140 Z" fill="rgba(160,112,255,0.18)"/>
          <path d="M0 122 Q30 102 60 122 T120 122" stroke="#c8a4ff" strokeWidth="1" fill="none"/>
        </svg>
      );
    case 'rnb':
      return (
        <svg viewBox="0 0 120 140" preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
          <defs>
            <linearGradient id="rg-b" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7a496f"/>
              <stop offset="55%" stopColor="#3b3a5e"/>
              <stop offset="100%" stopColor="#11141f"/>
            </linearGradient>
          </defs>
          <rect width="120" height="140" fill="url(#rg-b)"/>
          {/* smoky horizontal bands */}
          {Array.from({ length: 9 }).map((_, i) => (
            <ellipse key={i} cx="60" cy={20 + i * 14} rx={70 - i * 2} ry={3 - i * 0.2} fill="rgba(255,210,230,0.07)"/>
          ))}
          <circle cx="80" cy="55" r="22" fill="rgba(255,170,180,0.12)"/>
          <circle cx="80" cy="55" r="11" fill="rgba(255,200,220,0.18)"/>
        </svg>
      );
    case 'pop':
      return (
        <svg viewBox="0 0 120 140" preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
          <defs>
            <linearGradient id="rg-p" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#ff5fa2"/>
              <stop offset="60%" stopColor="#7c8fff"/>
              <stop offset="100%" stopColor="#3aeeff"/>
            </linearGradient>
          </defs>
          <rect width="120" height="140" fill="url(#rg-p)"/>
          {/* concentric circles */}
          {[8, 18, 30, 44, 60].map((r, i) => (
            <circle key={i} cx="60" cy="70" r={r} stroke="rgba(255,255,255,0.35)" strokeWidth="0.8" fill="none"/>
          ))}
          <circle cx="60" cy="70" r="4" fill="rgba(255,255,255,0.95)"/>
        </svg>
      );
    case 'rock':
      return (
        <svg viewBox="0 0 120 140" preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
          <defs>
            <linearGradient id="rg-k" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3a3a3a"/>
              <stop offset="100%" stopColor="#0a0a0a"/>
            </linearGradient>
            <pattern id="rg-k-grain" x="0" y="0" width="3" height="3" patternUnits="userSpaceOnUse">
              <rect width="1" height="1" fill="rgba(255,255,255,0.06)"/>
            </pattern>
          </defs>
          <rect width="120" height="140" fill="url(#rg-k)"/>
          <rect width="120" height="140" fill="url(#rg-k-grain)"/>
          {/* jagged amp envelope */}
          <polyline points="0,80 10,40 16,75 24,30 32,82 40,45 50,30 58,78 66,38 74,72 84,30 92,80 100,42 110,75 120,50" stroke="#ff3838" strokeWidth="1.5" fill="none"/>
          <polyline points="0,100 12,75 22,95 34,68 46,98 58,70 70,98 82,68 96,95 108,72 120,98" stroke="rgba(255,56,56,0.4)" strokeWidth="1" fill="none"/>
        </svg>
      );
    case 'afro':
      return (
        <svg viewBox="0 0 120 140" preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
          <defs>
            <linearGradient id="rg-a" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#ffd23a"/>
              <stop offset="55%" stopColor="#e7732d"/>
              <stop offset="100%" stopColor="#5a1a08"/>
            </linearGradient>
          </defs>
          <rect width="120" height="140" fill="url(#rg-a)"/>
          {/* polyrhythm waves */}
          {Array.from({ length: 7 }).map((_, i) => (
            <path key={i}
              d={`M0 ${30 + i * 14} Q30 ${15 + i * 14} 60 ${30 + i * 14} T120 ${30 + i * 14}`}
              stroke="rgba(60,20,5,0.45)" strokeWidth="1.1" fill="none"/>
          ))}
        </svg>
      );
    case 'house':
      return (
        <svg viewBox="0 0 120 140" preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
          <defs>
            <linearGradient id="rg-h" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#1e3a4a"/>
              <stop offset="100%" stopColor="#06141c"/>
            </linearGradient>
          </defs>
          <rect width="120" height="140" fill="url(#rg-h)"/>
          {/* four-on-the-floor pulses */}
          {[20, 50, 80, 110].map((y, i) => (
            <circle key={i} cx="60" cy={y} r="22" stroke="rgba(80,210,200,0.5)" strokeWidth="1.2" fill="none"/>
          ))}
          {[20, 50, 80, 110].map((y, i) => (
            <circle key={i} cx="60" cy={y} r="3" fill="#50e0d0"/>
          ))}
        </svg>
      );
    case 'drill':
      return (
        <svg viewBox="0 0 120 140" preserveAspectRatio="xMidYMid slice" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
          <defs>
            <linearGradient id="rg-d" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#3a3036"/>
              <stop offset="100%" stopColor="#0a0808"/>
            </linearGradient>
          </defs>
          <rect width="120" height="140" fill="url(#rg-d)"/>
          {/* sliding 808 lines */}
          <path d="M-5 95 L40 70 L40 100 L80 75 L80 105 L125 80" stroke="#9affa8" strokeWidth="1.4" fill="none"/>
          <path d="M-5 110 L40 90 L40 120 L80 95 L80 125 L125 100" stroke="rgba(154,255,168,0.4)" strokeWidth="1" fill="none"/>
          {/* hihats */}
          {Array.from({ length: 18 }).map((_, i) => (
            <line key={i} x1={8 + i * 6} x2={8 + i * 6} y1="28" y2={i % 2 === 0 ? '40' : '34'} stroke="rgba(154,255,168,0.7)" strokeWidth="0.8"/>
          ))}
        </svg>
      );
    default: return null;
  }
}

const GENRES = [
  { id: 'reggaeton', name: 'Reggaeton', bpm: '88 — 96 BPM',  tag: 'DEMBOW' },
  { id: 'trap',      name: 'Trap',      bpm: '140 — 160 BPM', tag: '808 / HATS' },
  { id: 'rnb',       name: 'R&B',       bpm: '60 — 90 BPM',   tag: 'SMOOTH' },
  { id: 'pop',       name: 'Pop',       bpm: '100 — 130 BPM', tag: 'RADIO' },
  { id: 'rock',      name: 'Rock',      bpm: '100 — 140 BPM', tag: 'DRIVEN' },
  { id: 'afro',      name: 'Afrobeats', bpm: '100 — 115 BPM', tag: 'POLYRHYTHM' },
  { id: 'house',     name: 'House',     bpm: '120 — 128 BPM', tag: '4 ON FLOOR' },
  { id: 'drill',     name: 'Drill',     bpm: '140 — 150 BPM', tag: 'SLIDE 808' },
];

const KNOBS = [
  { id: 'presence',  name: 'Presencia Vocal',     desc: 'CUERPO Y AIRE EN LA VOZ',     unit: '',     min: 0, max: 100, fmt: v => `${v}` },
  { id: 'bass',      name: 'Peso de Graves',      desc: 'SUB-BASS Y 808 IMPACT',       unit: '',     min: 0, max: 100, fmt: v => `${v}` },
  { id: 'stereo',    name: 'Amplitud Estéreo',    desc: 'IMAGEN L/R DEL MASTER',       unit: '',     min: 0, max: 100, fmt: v => `${v}` },
  { id: 'loudness',  name: 'Objetivo Loudness',   desc: 'LUFS INTEGRADO',              unit: 'LUFS', min: -16, max: -6, fmt: v => `${v.toFixed(1)}` },
];

function ParamsScreen({ state, setState, onNext, onBack }) {
  const params = state.params;
  const setParam = (k, v) => setState(s => ({ ...s, params: { ...s.params, [k]: v } }));
  const selected = GENRES.find(g => g.id === params.genre) || GENRES[0];

  const Slider = ({ knob }) => {
    const trackRef = React.useRef(null);
    const val = params[knob.id];
    const range = knob.max - knob.min;
    const pct = ((val - knob.min) / range) * 100;
    const onDown = (e) => {
      const move = (ev) => {
        const rect = trackRef.current.getBoundingClientRect();
        const p = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
        const newVal = knob.min + p * range;
        const stepped = knob.unit === 'LUFS' ? Math.round(newVal * 10) / 10 : Math.round(newVal);
        setParam(knob.id, stepped);
      };
      const up = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', up);
      move(e);
    };
    return (
      <div className="knob">
        <div className="top">
          <div className="name">{knob.name}</div>
          <div className="val">{knob.fmt(val)}{knob.unit ? ` ${knob.unit}` : ''}</div>
        </div>
        <div className="desc">{knob.desc}</div>
        <div className="track" ref={trackRef} onPointerDown={onDown}>
          <div className="fill" style={{ width: `${pct}%` }}></div>
          <div className="thumb" style={{ left: `${pct}%` }}></div>
        </div>
        <div className="scale">
          <span>{knob.min}{knob.unit ? ` ${knob.unit}` : ''}</span>
          <span>{knob.max}{knob.unit ? ` ${knob.unit}` : ''}</span>
        </div>
      </div>
    );
  };

  const TARGETS = [
    { id: 'streaming', label: 'STREAMING (-14 LUFS)' },
    { id: 'club',      label: 'CLUB / FESTIVAL' },
    { id: 'radio',     label: 'RADIO' },
    { id: 'reference', label: 'REFERENCIA PERSONALIZADA' },
  ];

  const MOODS = [
    { id: 'warm',     label: 'CÁLIDO' },
    { id: 'punchy',   label: 'PUNCHY' },
    { id: 'open',     label: 'AÉREO' },
    { id: 'gritty',   label: 'CRUDO' },
  ];

  return (
    <div className="params-shell">
      <main className="params-main">
        <div className="headline" style={{ padding: 0, marginBottom: 24 }}>
          <div>
            <div className="eyebrow">03 / PARÁMETROS DE MEZCLA</div>
            <h1>¿Cómo<br/>debe <em>sonar?</em></h1>
          </div>
          <div className="sub">
            Elige una estética de género y ajusta los cuatro controles maestros.
            AutoMix interpreta tus elecciones como un ingeniero — no como un preset.
          </div>
        </div>

        <div>
          <div className="section-title">
            <h2>Género</h2>
            <div className="meta">SELECCIONA 1 · MARCA EL CARÁCTER DE LA CADENA</div>
          </div>
          <div className="genres">
            {GENRES.map(g => (
              <div key={g.id} className={`genre-card ${params.genre === g.id ? 'selected' : ''}`} onClick={() => setParam('genre', g.id)}>
                <div className="art"><GenreArt kind={g.id} /></div>
                <div className="vignette"></div>
                <div className="tag">{g.tag}</div>
                <div className="check">
                  {params.genre === g.id && (
                    <svg width="10" height="10" viewBox="0 0 10 10"><path d="m2 5 2 2 4-4" stroke="currentColor" strokeWidth="1.6" fill="none"/></svg>
                  )}
                </div>
                <div className="label">
                  <div className="name">{g.name}</div>
                  <div className="bpm">{g.bpm}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="section-title">
            <h2>Controles maestros</h2>
            <div className="meta">4 PARÁMETROS · ARRASTRA PARA AJUSTAR</div>
          </div>
          <div className="knobs">
            {KNOBS.map(k => <Slider key={k.id} knob={k} />)}
          </div>
        </div>

        <div style={{ marginTop: 22 }}>
          <div className="section-title">
            <h2>Objetivo</h2>
            <div className="meta">DESTINO DEL MASTER</div>
          </div>
          <div className="toggle-row" style={{ marginBottom: 16 }}>
            {TARGETS.map(t => (
              <div key={t.id} className={`toggle ${params.target === t.id ? 'active' : ''}`} onClick={() => setParam('target', t.id)}>
                {t.label}
              </div>
            ))}
          </div>
          <div className="section-title" style={{ marginTop: 18 }}>
            <h2 style={{ fontSize: 18 }}>Mood</h2>
            <div className="meta">CARÁCTER TONAL · OPCIONAL</div>
          </div>
          <div className="toggle-row">
            {MOODS.map(m => (
              <div key={m.id} className={`toggle ${params.mood === m.id ? 'active' : ''}`} onClick={() => setParam('mood', params.mood === m.id ? null : m.id)}>
                {m.label}
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 32, paddingTop: 18, borderTop: '1px solid var(--line)' }}>
          <button className="btn btn-ghost" onClick={onBack}>← Sincronización</button>
          <button className="btn" onClick={onNext}>
            Mezclar &amp; masterizar<span className="arrow">→</span>
          </button>
        </div>
      </main>

      <aside className="params-sidebar">
        <div>
          <div className="rail-label" style={{ marginBottom: 12 }}>SELECCIÓN ACTIVA</div>
          <div className="summary-card" style={{ position: 'relative', overflow: 'hidden', padding: 0 }}>
            <div style={{ position: 'relative', height: 130 }}>
              <GenreArt kind={selected.id} />
              <div className="vignette" style={{ position: 'absolute', inset: 0 }}></div>
              <div style={{ position: 'absolute', left: 14, bottom: 12, right: 14 }}>
                <div style={{ fontFamily: 'var(--display)', fontSize: 26, color: '#fff', letterSpacing: '-0.025em', fontWeight: 600 }}>{selected.name}</div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'rgba(255,255,255,0.8)', letterSpacing: '0.18em' }}>{selected.bpm} · {selected.tag}</div>
              </div>
            </div>
            <div style={{ padding: 18 }}>
              <div className="summary-row"><span className="k">PRESENCIA</span><span className="v accent">{params.presence}</span></div>
              <div className="summary-row"><span className="k">GRAVES</span><span className="v accent">{params.bass}</span></div>
              <div className="summary-row"><span className="k">ESTÉREO</span><span className="v accent">{params.stereo}</span></div>
              <div className="summary-row"><span className="k">LOUDNESS</span><span className="v accent">{params.loudness.toFixed(1)} LUFS</span></div>
              <div className="summary-row"><span className="k">OBJETIVO</span><span className="v">{(TARGETS.find(t => t.id === params.target) || TARGETS[0]).label}</span></div>
              {params.mood && <div className="summary-row"><span className="k">MOOD</span><span className="v">{(MOODS.find(m => m.id === params.mood) || {}).label}</span></div>}
            </div>
          </div>
        </div>

        <div>
          <div className="rail-label" style={{ marginBottom: 12 }}>CADENA APROXIMADA</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[
              ['01', 'CORRECCIÓN DE FASE'],
              ['02', 'EQ SUSTRACTIVO'],
              ['03', 'COMPRESIÓN MULTIBAND'],
              ['04', 'PRESENCIA VOCAL'],
              ['05', 'SATURACIÓN ARMÓNICA'],
              ['06', 'STEREO IMAGER'],
              ['07', 'BUS COMPRESSOR'],
              ['08', 'LIMITER MASTER'],
            ].map(([n, l]) => (
              <div key={n} style={{
                display: 'flex', justifyContent: 'space-between',
                padding: '8px 12px',
                border: '1px solid var(--line)',
                borderRadius: 6,
                fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)'
              }}>
                <span style={{ color: 'var(--text-mute)' }}>{n}</span>
                <span>{l}</span>
              </div>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}

window.ParamsScreen = ParamsScreen;
