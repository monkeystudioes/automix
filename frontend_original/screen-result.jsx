/* ====================================================================
   AutoMix — Screen 4: Processing → Result
   Two phases: dramatic processing, then a master result view.
   ==================================================================== */

const STAGES = [
  'ANALIZANDO ESPECTRO',
  'DETECTANDO TRANSITORIOS',
  'EQUALIZACIÓN DINÁMICA',
  'COMPRESIÓN MULTIBAND',
  'IMAGEN ESTÉREO',
  'BUS COMPRESSOR',
  'LIMITER MASTER',
  'EXPORTANDO MASTER',
];

function ProcessingView({ params, onDone, onCancel }) {
  const [progress, setProgress] = React.useState(0);
  const [stageIdx, setStageIdx] = React.useState(0);

  React.useEffect(() => {
    const start = performance.now();
    const DURATION = 7200; // ms
    let raf;
    const tick = (t) => {
      const p = Math.min(1, (t - start) / DURATION);
      setProgress(p);
      setStageIdx(Math.min(STAGES.length - 1, Math.floor(p * STAGES.length)));
      if (p < 1) raf = requestAnimationFrame(tick);
      else setTimeout(onDone, 500);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const pct = Math.floor(progress * 100);

  return (
    <div className="proc-shell">
      <div className="grain"></div>
      <div className="proc-stage">
        <div className="proc-title">
          <div className="eyebrow">04 · MEZCLA &amp; MASTER EN CURSO</div>
          <h1>Procesando<br/>tu <em>master.</em></h1>
        </div>

        <div className="proc-percent">
          {String(pct).padStart(2, '0')}<sup>%</sup>
        </div>

        <div style={{ width: '70%', maxWidth: 720, height: 2, background: 'var(--bg-2)', borderRadius: 1, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: 'var(--accent)', boxShadow: '0 0 12px var(--accent)', transition: 'width 0.05s linear' }}></div>
        </div>

        <Spectrum bars={64} seed={11} running={true} />

        <div className="proc-status">
          <div className="dot"></div>
          <span>{STAGES[stageIdx]}</span>
          <span style={{ color: 'var(--text-mute)' }}>·</span>
          <span style={{ color: 'var(--text-mute)' }}>PASO {stageIdx + 1} DE {STAGES.length}</span>
        </div>
      </div>

      <div className="actionbar">
        <div className="left">
          <span>● AUTOMIX v3.2 ENGINE</span>
          <span>·</span>
          <span>OBJETIVO {params.loudness.toFixed(1)} LUFS</span>
          <span>·</span>
          <span>PRESET {(params.genre || 'pop').toUpperCase()}</span>
        </div>
        <button className="btn btn-ghost" onClick={onCancel}>Cancelar</button>
      </div>
    </div>
  );
}

function ResultView({ params, onBack, onRestart }) {
  const [playing, setPlaying] = React.useState(false);
  const [played, setPlayed] = React.useState(0.27);

  React.useEffect(() => {
    if (!playing) return;
    let id;
    const step = () => { setPlayed(p => Math.min(1, p + 0.0015)); id = requestAnimationFrame(step); };
    id = requestAnimationFrame(step);
    return () => cancelAnimationFrame(id);
  }, [playing]);

  const totalSec = 204;
  const cur = Math.floor(played * totalSec);
  const mm = String(Math.floor(cur / 60)).padStart(2, '0');
  const ss = String(cur % 60).padStart(2, '0');

  return (
    <div className="result-shell">
      <main className="result-main">
        <div className="result-hero">
          <div>
            <div className="eyebrow">04 / MASTER LISTO</div>
            <h1>Tu canción,<br/><em>masterizada.</em></h1>
          </div>
          <div className="stamp">
            EXPORTADO 28 MAY 2026<br/>
            AUTOMIX v3.2 · 7.2s<br/>
            <span style={{ color: 'var(--accent)' }}>HASH 9F2A·E13B</span>
          </div>
        </div>

        <div className="result-wave">
          <div className="wave-head">
            <div className="ttl">Master final · midnight_loop_master.wav</div>
            <div className="ttr">
              <span>STEREO</span>
              <span>·</span>
              <span>48 kHz / 24 BIT</span>
              <span>·</span>
              <span style={{ color: 'var(--accent)' }}>{params.loudness.toFixed(1)} LUFS</span>
            </div>
          </div>
          <div className="wave-body">
            <WaveBars width={1100} height={300} bars={210} seed={7} shape="master"
                      color="rgba(255,255,255,0.42)" playedColor="#e3ff87" played={played} faint={0.5} />
            {/* playhead */}
            <div style={{
              position: 'absolute', top: -6, bottom: -6,
              left: `${played * 100}%`,
              width: 2, background: 'var(--accent)', boxShadow: '0 0 12px var(--accent)',
            }}></div>
          </div>
          <div className="result-controls">
            <div className="left">
              <button onClick={() => setPlaying(p => !p)} style={{
                width: 48, height: 48, borderRadius: '50%',
                background: 'var(--accent)', color: '#000',
                display: 'grid', placeItems: 'center',
                boxShadow: '0 0 20px rgba(227,255,135,0.4)',
              }}>
                {playing
                  ? <svg width="18" height="18" viewBox="0 0 18 18"><rect x="4" y="3" width="3" height="12"/><rect x="11" y="3" width="3" height="12"/></svg>
                  : <svg width="18" height="18" viewBox="0 0 18 18"><path d="M5 3 14 9 5 15Z" fill="currentColor"/></svg>
                }
              </button>
              <div className="time">{mm}:{ss}<span style={{ color: 'var(--text-mute)' }}> / 03:24</span></div>
              <button className="tool-btn" title="A/B con original">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <text x="2" y="10" fontFamily="monospace" fontSize="9" fill="currentColor" letterSpacing="-0.5">A/B</text>
                </svg>
              </button>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.18em', color: 'var(--text-mute)' }}>
                {playing ? '▶ REPRODUCIENDO' : '▍ PAUSADO'}
              </div>
            </div>
            <a className="download" href="#" onClick={(e) => e.preventDefault()}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M8 2v9m0 0L4 7m4 4 4-4M3 14h10" stroke="currentColor" strokeWidth="1.6"/>
              </svg>
              Descargar master .WAV
            </a>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 6 }}>
          <button className="btn btn-ghost" onClick={onBack}>← Ajustar parámetros</button>
          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn btn-ghost" onClick={onRestart}>Nueva sesión</button>
            <button className="btn btn-ghost">Exportar stems</button>
            <button className="btn">Compartir<span className="arrow">↗</span></button>
          </div>
        </div>
      </main>

      <aside className="result-side">
        <div>
          <div className="rail-label" style={{ marginBottom: 14 }}>QUÉ SE APLICÓ</div>

          <div className="applied">
            <div className="ttl">
              <h4>Curva EQ</h4>
              <span className="badge">PROCESADA</span>
            </div>
            <div className="eq-card">
              <div className="grid"></div>
              <EQCurve width={360} height={130} />
              <div className="axis">
                <span>20 Hz</span><span>100</span><span>500</span><span>1k</span><span>3k</span><span>8k</span><span>20 kHz</span>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text-mute)', letterSpacing: '0.12em' }}>
              <span>LOW SHELF <span style={{ color: 'var(--accent)' }}>−1.8 dB</span></span>
              <span>3 kHz BUMP <span style={{ color: 'var(--accent)' }}>+2.4 dB</span></span>
              <span>AIR <span style={{ color: 'var(--accent)' }}>+1.6 dB</span></span>
            </div>
          </div>

          <div className="metric-row" style={{ marginTop: 12 }}>
            <div className="metric">
              <div className="k">COMPRESIÓN</div>
              <div className="v">−3.2<small>dB GR</small></div>
            </div>
            <div className="metric">
              <div className="k">LIMITER CEILING</div>
              <div className="v">−1.0<small>dB TP</small></div>
            </div>
            <div className="metric">
              <div className="k">LUFS INTEGRADO</div>
              <div className="v" style={{ color: 'var(--accent)' }}>{params.loudness.toFixed(1)}</div>
            </div>
            <div className="metric">
              <div className="k">RANGO DINÁMICO</div>
              <div className="v">7.4<small>LU</small></div>
            </div>
            <div className="metric">
              <div className="k">CORRELACIÓN</div>
              <div className="v">+0.78</div>
            </div>
            <div className="metric">
              <div className="k">CRESTA</div>
              <div className="v">9.1<small>dB</small></div>
            </div>
          </div>
        </div>

        <div>
          <div className="rail-label" style={{ marginBottom: 12 }}>PRESET</div>
          <div style={{
            border: '1px solid var(--line)', borderRadius: 12, padding: 14,
            background: 'var(--bg-1)',
            fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.1em', color: 'var(--text-dim)',
            lineHeight: 1.8
          }}>
            <div><span style={{ color: 'var(--text-mute)' }}>GÉNERO   </span> {(params.genre || 'pop').toUpperCase()}</div>
            <div><span style={{ color: 'var(--text-mute)' }}>PRESENCIA</span> {params.presence}</div>
            <div><span style={{ color: 'var(--text-mute)' }}>GRAVES   </span> {params.bass}</div>
            <div><span style={{ color: 'var(--text-mute)' }}>ESTÉREO  </span> {params.stereo}</div>
            <div><span style={{ color: 'var(--text-mute)' }}>LOUDNESS </span> {params.loudness.toFixed(1)} LUFS</div>
          </div>
        </div>
      </aside>
    </div>
  );
}

function ProcessScreen({ state, setState, onBack, onRestart }) {
  const [done, setDone] = React.useState(state.finished || false);
  React.useEffect(() => { if (done) setState(s => ({ ...s, finished: true })); }, [done]);

  if (!done) {
    return <ProcessingView params={state.params} onDone={() => setDone(true)} onCancel={onBack} />;
  }
  return <ResultView params={state.params} onBack={onBack} onRestart={onRestart} />;
}

window.ProcessScreen = ProcessScreen;
