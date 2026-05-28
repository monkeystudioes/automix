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
  // Pre-fill demo data so all screens feel "real" if user jumps around
  const [state, setState] = React.useState({
    step: 'upload',
    inst:  { loaded: false },
    vocal: { loaded: false },
    offset: 42,
    params: {
      genre: 'reggaeton',
      presence: 64,
      bass: 72,
      stereo: 48,
      loudness: -9.5,
      target: 'streaming',
      mood: 'warm',
    },
    finished: false,
  });

  const setStep = (step) => setState(s => ({ ...s, step }));

  // Allow jumping to a step from the indicator only if precondition met
  const canJump = (id) => {
    if (id === 'upload') return true;
    if (id === 'sync')   return state.inst.loaded && state.vocal.loaded;
    if (id === 'params') return state.inst.loaded && state.vocal.loaded;
    if (id === 'master') return state.inst.loaded && state.vocal.loaded;
    return false;
  };

  const currentIdx = STEPS.findIndex(s => s.id === state.step);

  return (
    <ChromeWindow width="100%" height="100%" url="automix.studio/session/A37-K2"
      tabs={[{ title: 'AutoMix — Session A37-K2' }, { title: 'Reference tracks' }, { title: 'docs' }]}
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
            <span className="session-pill">SESIÓN ACTIVA · A37-K2</span>
            <div style={{ width: 28, height: 28, borderRadius: '50%', background: '#1a1a1c', border: '1px solid var(--line-2)', display: 'grid', placeItems: 'center', fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text-dim)' }}>M</div>
          </div>
        </header>

        {state.step === 'upload' && (
          <UploadScreen state={state} setState={setState} onNext={() => setStep('sync')} />
        )}
        {state.step === 'sync' && (
          <SyncScreen state={state} setState={setState} onNext={() => setStep('params')} onBack={() => setStep('upload')} />
        )}
        {state.step === 'params' && (
          <ParamsScreen state={state} setState={setState} onNext={() => setStep('master')} onBack={() => setStep('sync')} />
        )}
        {state.step === 'master' && (
          <ProcessScreen
            state={state} setState={setState}
            onBack={() => { setState(s => ({ ...s, finished: false })); setStep('params'); }}
            onRestart={() => setState(s => ({ ...s, finished: false, inst: { loaded: false }, vocal: { loaded: false }, step: 'upload' }))}
          />
        )}
      </div>
    </ChromeWindow>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
