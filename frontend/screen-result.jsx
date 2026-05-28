/* ====================================================================
   AutoMix — Screen 4: Processing → Result (real backend polling)
   ==================================================================== */

const STAGES = [
  'CARGANDO ARCHIVOS',
  'ANALIZANDO ESPECTRO',
  'DETECTANDO TRANSITORIOS',
  'EQUALIZACIÓN DINÁMICA',
  'COMPRESIÓN MULTIBAND',
  'IMAGEN ESTÉREO',
  'BUS COMPRESSOR',
  'LIMITER MASTER',
  'EXPORTANDO MASTER',
];

function ProcessingView({ params, sessionId, jobId, onDone, onError, onCancel }) {
  const [progress, setProgress] = React.useState(0);
  const [stageIdx, setStageIdx] = React.useState(0);
  const [stageLabel, setStageLabel] = React.useState(STAGES[0]);

  React.useEffect(() => {
    if (!sessionId || !jobId) return;
    let stopped = false;

    const poll = async () => {
      if (stopped) return;
      try {
        const base = window.AUTOMIX_API_BASE || '';
        const res = await fetch(`${base}/api/session/${sessionId}/job/${jobId}/status`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (data.status === 'done') {
          setProgress(1);
          setStageIdx(STAGES.length - 1);
          setStageLabel('EXPORTANDO MASTER');
          setTimeout(() => onDone(data.result), 600);
          return;
        }
        if (data.status === 'error') {
          onError(data.error || 'Error desconocido');
          return;
        }

        // processing or queued
        const p = data.progress || 0;
        setProgress(p);

        // Map stage label
        const label = data.stage || STAGES[Math.floor(p * STAGES.length)];
        setStageLabel(label);
        const idx = STAGES.indexOf(label);
        setStageIdx(idx >= 0 ? idx : Math.floor(p * STAGES.length));

        if (!stopped) setTimeout(poll, 800);
      } catch (e) {
        console.error('Poll error:', e);
        if (!stopped) setTimeout(poll, 2000);
      }
    };

    poll();
    return () => { stopped = true; };
  }, [sessionId, jobId]);

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
          <div style={{ width: `${pct}%`, height: '100%', background: 'var(--accent)', boxShadow: '0 0 12px var(--accent)', transition: 'width 0.3s ease' }}></div>
        </div>

        <Spectrum bars={64} seed={11} running={true} />

        <div className="proc-status">
          <div className="dot"></div>
          <span>{stageLabel}</span>
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

function ResultView({ params, result, onBack, onRestart }) {
  const [playing, setPlaying] = React.useState(false);
  const [played, setPlayed]   = React.useState(0);
  const report = result?.report || {};

  React.useEffect(() => {
    if (!playing) return;
    let id;
    const step = () => { setPlayed(p => Math.min(1, p + 0.0015)); id = requestAnimationFrame(step); };
    id = requestAnimationFrame(step);
    return () => cancelAnimationFrame(id);
  }, [playing]);

  const totalSec = report.processing_time_seconds ? 204 : 204;
  const cur = Math.floor(played * totalSec);
  const mm  = String(Math.floor(cur / 60)).padStart(2, '0');
  const ss  = String(cur % 60).padStart(2, '0');

  const wavUrl = result?.wav_url;
  const mp3Url = result?.mp3_url;

  return (
    <div className="result-shell">
      <main className="result-main">
        <div className="result-hero">
          <div>
            <div className="eyebrow">04 / MASTER LISTO</div>
            <h1>Tu canción,<br/><em>masterizada.</em></h1>
          </div>
          <div className="stamp">
            EXPORTADO {new Date().toLocaleDateString('es-ES', { day:'2-digit', month:'short', year:'numeric' }).toUpperCase()}<br/>
            AUTOMIX v3.2 · {report.processing_time_seconds || '—'}s<br/>
            <span style={{ color: 'var(--accent)' }}>
              {report.bpm ? `${report.bpm} BPM · ${report.key}` : ''}
            </span>
          </div>
        </div>

        <div className="result-wave">
          <div className="wave-head">
            <div className="ttl">Master final</div>
            <div className="ttr">
              <span>STEREO</span>
              <span>·</span>
              <span>48 kHz / 24 BIT</span>
              <span>·</span>
              <span style={{ color: 'var(--accent)' }}>
                {report.lufs_integrated != null ? `${report.lufs_integrated.toFixed(1)} LUFS` : `${params.loudness.toFixed(1)} LUFS`}
              </span>
            </div>
          </div>
          <div className="wave-body">
            <WaveBars width={1100} height={300} bars={210} seed={7} shape="master"
                      color="rgba(255,255,255,0.42)" playedColor="#e3ff87" played={played} faint={0.5} />
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
              <div className="time">{mm}:{ss}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.18em', color: 'var(--text-mute)' }}>
                {playing ? '▶ REPRODUCIENDO' : '▍ PAUSADO'}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              {mp3Url && (
                <a className="download" href={mp3Url} download style={{ padding: '12px 18px', borderRadius: 999, background: 'var(--bg-1)', color: 'var(--text)', border: '1px solid var(--line-2)', display: 'inline-flex', alignItems: 'center', gap: 8, fontFamily: 'var(--display)', fontSize: 13, textDecoration: 'none' }}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 2v9m0 0L4 7m4 4 4-4M3 14h10" stroke="currentColor" strokeWidth="1.6"/></svg>
                  MP3
                </a>
              )}
              {wavUrl ? (
                <a className="download" href={wavUrl} download style={{ display: 'inline-flex', alignItems: 'center', gap: 12, padding: '16px 22px', borderRadius: 999, background: 'var(--accent)', color: '#000', fontFamily: 'var(--display)', fontSize: 15, fontWeight: 500, letterSpacing: '-0.01em', textDecoration: 'none' }}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2v9m0 0L4 7m4 4 4-4M3 14h10" stroke="currentColor" strokeWidth="1.6"/></svg>
                  Descargar master .WAV
                </a>
              ) : (
                <button className="download" style={{ display: 'inline-flex', alignItems: 'center', gap: 12, padding: '16px 22px', borderRadius: 999, background: 'var(--bg-1)', color: 'var(--text-mute)', border: '1px solid var(--line)', cursor: 'not-allowed' }} disabled>
                  Archivo no disponible
                </button>
              )}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 6 }}>
          <button className="btn btn-ghost" onClick={onBack}>← Ajustar parámetros</button>
          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn btn-ghost" onClick={onRestart}>Nueva sesión</button>
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
            {report.bpm && (
              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text-mute)', letterSpacing: '0.12em' }}>
                <span>BPM <span style={{ color: 'var(--accent)' }}>{report.bpm}</span></span>
                <span>KEY <span style={{ color: 'var(--accent)' }}>{report.key}</span></span>
                <span>AUTOTUNE <span style={{ color: 'var(--accent)' }}>{report.pitch_correction_applied ? 'ON' : 'OFF'}</span></span>
              </div>
            )}
          </div>

          <div className="metric-row" style={{ marginTop: 12 }}>
            <div className="metric">
              <div className="k">CORRECCIÓN PITCH</div>
              <div className="v">{report.pitch_notes_corrected ?? '—'}<small> frames</small></div>
            </div>
            <div className="metric">
              <div className="k">LIMITER CEILING</div>
              <div className="v">{report.true_peak != null ? report.true_peak.toFixed(1) : '—'}<small>dBTP</small></div>
            </div>
            <div className="metric">
              <div className="k">LUFS INTEGRADO</div>
              <div className="v" style={{ color: 'var(--accent)' }}>
                {report.lufs_integrated != null ? report.lufs_integrated.toFixed(1) : params.loudness.toFixed(1)}
              </div>
            </div>
            <div className="metric">
              <div className="k">RANGO DINÁMICO</div>
              <div className="v">{report.dynamic_range != null ? report.dynamic_range.toFixed(1) : '—'}<small>LU</small></div>
            </div>
            <div className="metric">
              <div className="k">CORRELACIÓN</div>
              <div className="v">{report.stereo_correlation != null ? `+${report.stereo_correlation.toFixed(2)}` : '—'}</div>
            </div>
            <div className="metric">
              <div className="k">CRESTA</div>
              <div className="v">{report.crest_factor != null ? report.crest_factor.toFixed(1) : '—'}<small>dB</small></div>
            </div>
          </div>

          {report.qa_warnings?.length > 0 && (
            <div style={{ marginTop: 12, padding: 12, border: '1px solid rgba(255,100,100,0.3)', borderRadius: 10, background: 'rgba(255,50,50,0.05)' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.18em', color: 'rgba(255,100,100,0.8)', marginBottom: 6 }}>AVISOS QA</div>
              {report.qa_warnings.map((w, i) => (
                <div key={i} style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text-dim)', padding: '3px 0' }}>⚠ {w}</div>
              ))}
            </div>
          )}
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
            {params.mood && <div><span style={{ color: 'var(--text-mute)' }}>MOOD     </span> {params.mood.toUpperCase()}</div>}
          </div>
        </div>
      </aside>
    </div>
  );
}

function ErrorView({ error, onBack }) {
  return (
    <div className="proc-shell">
      <div className="proc-stage">
        <div className="proc-title">
          <div className="eyebrow">ERROR DE PROCESAMIENTO</div>
          <h1>Algo salió<br/><em>mal.</em></h1>
        </div>
        <div style={{ fontFamily: 'var(--mono)', fontSize: 13, color: '#ff6464', maxWidth: 600, textAlign: 'center', lineHeight: 1.6 }}>
          {error}
        </div>
      </div>
      <div className="actionbar">
        <div className="left"><span style={{ color: '#ff6464' }}>● ERROR</span></div>
        <button className="btn btn-ghost" onClick={onBack}>← Volver a parámetros</button>
      </div>
    </div>
  );
}

function ProcessScreen({ state, setState, sessionId, onBack, onRestart }) {
  const [done, setDone]   = React.useState(state.finished || false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (done) setState(s => ({ ...s, finished: true }));
  }, [done]);

  if (error) {
    return <ErrorView error={error} onBack={onBack} />;
  }

  if (!done) {
    return (
      <ProcessingView
        params={state.params}
        sessionId={sessionId}
        jobId={state.jobId}
        onDone={(result) => { setState(s => ({ ...s, result })); setDone(true); }}
        onError={(err) => setError(err)}
        onCancel={onBack}
      />
    );
  }

  return (
    <ResultView
      params={state.params}
      result={state.result}
      onBack={onBack}
      onRestart={onRestart}
    />
  );
}

window.ProcessScreen = ProcessScreen;
