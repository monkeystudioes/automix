/* ====================================================================
   AutoMix — Screen 1: Upload (real backend connection)
   ==================================================================== */

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function UploadScreen({ state, setState, sessionId, onNext }) {
  const inst  = state.inst;
  const vocal = state.vocal;
  const bothLoaded = inst.loaded && vocal.loaded;

  const Drop = ({ kind, data, label, channel, accent }) => {
    const [drag, setDrag]       = React.useState(false);
    const [uploading, setUploading] = React.useState(false);
    const [error, setError]     = React.useState(null);

    const handleFile = async (file) => {
      if (!file || !sessionId) return;
      setError(null);
      setUploading(true);

      try {
        const form = new FormData();
        form.append('file', file);

        const base = window.AUTOMIX_API_BASE || '';
        const res = await fetch(`${base}/api/session/${sessionId}/upload/${kind === 'inst' ? 'instrumental' : 'vocal'}`, {
          method: 'POST',
          body: form,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(err.detail || `Error ${res.status}`);
        }

        const data = await res.json();

        setState(s => ({
          ...s,
          [kind]: {
            loaded:   true,
            name:     file.name,
            size:     (file.size / 1024 / 1024).toFixed(1) + ' MB',
            sr:       (data.sample_rate / 1000).toFixed(0) + ' kHz',
            depth:    '24 bit',
            len:      formatTime(data.duration),
            bpm:      data.bpm ? String(data.bpm) : '—',
            key:      data.key || '—',
            file_id:  data.file_id,
          },
        }));
      } catch (e) {
        console.error('Upload error:', e);
        setError(e.message);
      } finally {
        setUploading(false);
      }
    };

    const onDrop = (e) => {
      e.preventDefault();
      setDrag(false);
      handleFile(e.dataTransfer.files?.[0]);
    };

    const onInputChange = (e) => {
      handleFile(e.target.files?.[0]);
    };

    const inputRef = React.useRef(null);

    return (
      <div
        className={`dropzone ${kind} ${data.loaded ? 'loaded' : ''} ${drag ? 'dragover' : ''} ${uploading ? 'uploading' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        onClick={() => !data.loaded && !uploading && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".wav,.aiff,.aif,.flac,.mp3"
          style={{ display: 'none' }}
          onChange={onInputChange}
        />

        <div className="head">
          <div>
            <div className="channel">{channel}</div>
            <div className="name">{label}</div>
          </div>
          <div className="corner-tag">
            {uploading ? '⟳ SUBIENDO…' : data.loaded ? '● LISTO' : '○ VACÍO'}
          </div>
        </div>

        {!data.loaded && !uploading && (
          <div className="body">
            <div className="glyph">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                <path d="M12 4v12m0-12-5 5m5-5 5 5M5 20h14" stroke="currentColor" strokeWidth="1.4"/>
              </svg>
            </div>
            <p>Arrastra tu {kind === 'inst' ? 'instrumental' : 'pista de voz'}<br/>o haz clic para examinar</p>
            <small>WAV · AIFF · FLAC · MP3 — 48kHz/24bit recomendado</small>
            {error && (
              <div style={{ color: '#ff6464', fontFamily: 'var(--mono)', fontSize: 11, marginTop: 8, textAlign: 'center', maxWidth: '80%' }}>
                ⚠ {error}
              </div>
            )}
            <div className="specs">
              <span>MÁX 200MB</span>
              <span>MONO / STEREO</span>
              <span>—:—</span>
            </div>
          </div>
        )}

        {uploading && (
          <div className="body">
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
              <div style={{ width: 40, height: 40, border: '2px solid var(--accent)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }}></div>
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.2em', color: 'var(--text-dim)' }}>
                ANALIZANDO ARCHIVO…
              </div>
            </div>
          </div>
        )}

        {data.loaded && (
          <>
            <div className="dz-wave">
              <WaveBars
                width={520} height={120} bars={120}
                seed={kind === 'inst' ? 17 : 41}
                shape={kind === 'inst' ? 'song' : 'vocal'}
                color={accent}
                faint={0.5}
              />
            </div>
            <div className="dz-meta">
              <div><span className="k">ARCHIVO</span><span className="v" style={{ fontSize: 10, wordBreak: 'break-all' }}>{data.name}</span></div>
              <div><span className="k">DURACIÓN</span><span className="v">{data.len}</span></div>
              <div><span className="k">FORMATO</span><span className="v">{data.sr} / {data.depth}</span></div>
              <div><span className="k">TEMPO</span><span className="v accent">{data.bpm} BPM · {data.key}</span></div>
            </div>
            <div
              style={{ position: 'absolute', top: 12, right: 14, cursor: 'pointer', fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--text-mute)', letterSpacing: '0.15em' }}
              onClick={(e) => { e.stopPropagation(); setState(s => ({ ...s, [kind]: { loaded: false } })); }}
            >
              ✕ QUITAR
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <div className="workspace">
      <aside className="rail">
        <div className="rail-block">
          <div className="rail-label">SESIÓN</div>
          <div style={{ fontFamily: 'var(--display)', fontSize: 22, letterSpacing: '-0.025em', lineHeight: 1.05 }}>
            Sesión sin título<br/>
            <span style={{ color: 'var(--text-mute)', fontSize: 13 }}>#{sessionId}</span>
          </div>
        </div>

        <div className="rail-block">
          <div className="rail-label">DESTINO</div>
          <div className="rail-kv"><span className="k">FORMATO</span><span className="v">WAV 24-BIT</span></div>
          <div className="rail-kv"><span className="k">SAMPLE RATE</span><span className="v">48 kHz</span></div>
          <div className="rail-kv"><span className="k">CANALES</span><span className="v">STEREO</span></div>
          <div className="rail-kv"><span className="k">ENGINE</span><span className="v accent">AUTOMIX v3.2</span></div>
        </div>

        <div className="rail-block">
          <div className="rail-label">FLUJO</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-mute)' }}>
            <div style={{ color: 'var(--accent)' }}>01 → SUBIR PISTAS</div>
            <div>02 → SINCRONIZAR</div>
            <div>03 → PARÁMETROS</div>
            <div>04 → MEZCLA &amp; MASTER</div>
          </div>
        </div>

        <div style={{ marginTop: 'auto', borderTop: '1px solid var(--line)', paddingTop: 14 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.18em', color: 'var(--text-mute)', lineHeight: 1.7 }}>
            CONSEJO — sube las pistas exportadas en seco (sin reverb ni efectos de master) para mejores resultados.
          </div>
        </div>
      </aside>

      <main className="canvas">
        <div className="grain"></div>
        <div className="headline">
          <div>
            <div className="eyebrow">01 / SUBIDA DE PISTAS</div>
            <h1>Carga tu<br/>instrumental <em>y voz.</em></h1>
          </div>
          <div className="sub">
            Dos canales, una mezcla. AutoMix analiza cada pista por separado antes de empezar.
            Acepta archivos sin procesar — sin reverbs, sin master.
          </div>
        </div>

        <div className="dropzones">
          <Drop kind="inst"  data={inst}  label="Instrumental" channel="CANAL A · BEAT" accent="#0044ff" />
          <Drop kind="vocal" data={vocal} label="Voz"          channel="CANAL B · VOX"  accent="#e3ff87" />
        </div>

        <div className="actionbar">
          <div className="left">
            <span>{bothLoaded ? '● 2 PISTAS LISTAS' : `○ ${(inst.loaded ? 1 : 0) + (vocal.loaded ? 1 : 0)} / 2 PISTAS`}</span>
            <span>·</span>
            <span>AUTODETECCIÓN BPM ACTIVA</span>
            {bothLoaded && inst.bpm && vocal.bpm && (
              <>
                <span>·</span>
                <span style={{ color: 'var(--accent)' }}>
                  {inst.bpm === vocal.bpm
                    ? `TEMPOS COMPATIBLES (${inst.bpm} BPM)`
                    : `INST ${inst.bpm} BPM · VOZ ${vocal.bpm} BPM`}
                </span>
              </>
            )}
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn btn-ghost" onClick={() => setState(s => ({ ...s, inst: { loaded: false }, vocal: { loaded: false } }))}>
              Limpiar
            </button>
            <button className="btn" disabled={!bothLoaded} onClick={onNext}>
              Continuar a sincronizar
              <span className="arrow">→</span>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

window.UploadScreen = UploadScreen;
