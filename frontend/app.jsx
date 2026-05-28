/* ====================================================================
   AutoMix — App shell & navigation
   ==================================================================== */

const STEPS = [
  { id: 'upload',  num: '01', label: 'SUBIDA' },
  { id: 'sync',    num: '02', label: 'SINCRONIZAR' },
  { id: 'params',  num: '03', label: 'PARÁMETROS' },
  { id: 'master',  num: '04', label: 'MASTER' },
];

function App() {
  const [sessionId, setSessionId] = React.useState(null);
  const [sessionError, setSessionError] = React.useState(null);

  const [state, setState] = React.useState({
    step: 'upload',
    inst:  { loaded: false },
    vocal: { loaded: false },
    offset: 0,
    params: {
      genre: 'reggaeton',
      presence: 64,
      bass: 72,
      stereo: 48,
      loudness: -14.0,
      target: 'streaming',
      mood: 'warm',
    },
    jobId: null,
    finished: false,
    result: null,
  });

  // Create session on mount
  React.useEffect(() => {
    fetch((window.AUTOMIX_API_BASE || '') + '/api/session', { method: 'POST' })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(d => {
        setSessionId(d.session_id);
      })
      .catch(err => {
        console.error('Session creation failed:', err);
        setSessionError('No se pudo conectar al servidor. ¿Está el backend corriendo?');
      });
  }, []);

  const setStep = (step) => setState(s => ({ ...s, step }));

  const canJump = (id) => {
    if (id === 'upload') return true;
    if (id === 'sync')   return state.inst.loaded && state.vocal.loaded;
    if (id === 'params') return state.inst.loaded && state.vocal.loaded;
    if (id === 'master') return state.inst.loaded && state.vocal.loaded;
    return false;
  };

  const currentIdx = STEPS.findIndex(s => s.id === state.step);

  if (sessionError) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000', flexDirection: 'column', gap: 16, fontFamily: 'monospace' }}>
        <div style={{ color: '#e3ff87', fontSize: 18 }}>⚠ Error de conexión</div>
        <div style={{ color: '#888', fontSize: 13 }}>{sessionError}</div>
        <button onClick={() => window.location.reload()} style={{ marginTop: 12, padding: '10px 20px', background: '#e3ff87', color: '#000', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>
          Reintentar
        </button>
      </div>
    );
  }

  if (!sessionId) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000', flexDirection: 'column', gap: 14 }}>
        <div style={{ width: 36, height: 36, border: '2px solid #e3ff87', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }}></div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <div style={{ color: '#555', fontFamily: 'monospace', fontSize: 11, letterSpacing: '0.2em' }}>INICIANDO SESIÓN…</div>
      </div>
    );
  }

  return (
    <ChromeWindow width="100%" height="100%" url={`automix.studio/session/${sessionId}`}
      tabs={[{ title: `AutoMix — Sesión ${sessionId}` }, { title: 'Pistas de referencia' }, { title: 'docs' }]}
      activeIndex={0}
    >
      <div className="app">
        <header className="topbar">
          <div className="brand">
            <span className="brand-dot"></span>
            AutoMix<sup>v3.2</sup>
          </div>
          <div className="steps">
            {STEPS.map((s, i) => (
              <React.Fragment key={s.id}>
                <div
                  className={`step ${state.step === s.id ? 'active' : ''} ${i < currentIdx ? 'done' : ''}`}
                  onClick={() => canJump(s.id) && setStep(s.id)}
                  style={{ cursor: canJump(s.id) ? 'pointer' : 'not-allowed', opacity: canJump(s.id) ? 1 : 0.4 }}
                >
                  <span className="num">{s.num}</span>
                  <span>{s.label}</span>
                </div>
                {i < STEPS.length - 1 && <span className="step-sep"></span>}
              </React.Fragment>
            ))}
          </div>
          <div className="topbar-right">
            <span className="session-pill">SESIÓN ACTIVA · {sessionId}</span>
            <div style={{ width: 28, height: 28, borderRadius: '50%', background: '#1a1a1c', border: '1px solid var(--line-2)', display: 'grid', placeItems: 'center', fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text-dim)' }}>M</div>
          </div>
        </header>

        {state.step === 'upload' && (
          <UploadScreen state={state} setState={setState} sessionId={sessionId} onNext={() => setStep('sync')} />
        )}
        {state.step === 'sync' && (
          <SyncScreen state={state} setState={setState} onNext={() => setStep('params')} onBack={() => setStep('upload')} />
        )}
        {state.step === 'params' && (
          <ParamsScreen state={state} setState={setState} sessionId={sessionId} onNext={() => setStep('master')} onBack={() => setStep('sync')} />
        )}
        {state.step === 'master' && (
          <ProcessScreen
            state={state} setState={setState}
            sessionId={sessionId}
            onBack={() => { setState(s => ({ ...s, finished: false, jobId: null, result: null })); setStep('params'); }}
            onRestart={() => setState(s => ({ ...s, finished: false, jobId: null, result: null, inst: { loaded: false }, vocal: { loaded: false }, step: 'upload' }))}
          />
        )}
      </div>
    </ChromeWindow>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
