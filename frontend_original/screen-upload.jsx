/* ====================================================================
   AutoMix — Screen 1: Upload
   ==================================================================== */

function UploadScreen({ state, setState, onNext }) {
  const inst = state.inst;
  const vocal = state.vocal;
  const bothLoaded = inst.loaded && vocal.loaded;

  const Drop = ({ kind, data, label, channel, accent }) => {
    const [drag, setDrag] = React.useState(false);

    const handleFile = (file) => {
      // Simulated metadata
      const sample = {
        loaded: true,
        name: file?.name || (kind === 'inst' ? 'midnight_loop_120bpm.wav' : 'verse_take_07.wav'),
        size: file ? Math.round(file.size / 1024 / 1024 * 10) / 10 + ' MB' : (kind === 'inst' ? '34.2 MB' : '12.7 MB'),
        sr: '48 kHz',
        depth: '24 bit',
        len: kind === 'inst' ? '3:24' : '3:18',
        bpm: kind === 'inst' ? '120' : '120',
        key: kind === 'inst' ? 'F min' : 'F min',
      };
      setState(s => ({ ...s, [kind]: sample }));
    };

    return (
      <div
        className={`dropzone ${kind} ${data.loaded ? 'loaded' : ''} ${drag ? 'dragover' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handleFile(e.dataTransfer.files?.[0]); }}
        onClick={() => !data.loaded && handleFile(null)}
      >
        <div className="head">
          <div>
            <div className="channel">{channel}</div>
            <div className="name">{label}</div>
          </div>
          <div className="corner-tag">
            {data.loaded ? '● READY' : '○ EMPTY'}
          </div>
        </div>

        {!data.loaded && (
          <div className="body">
            <div className="glyph">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                <path d="M12 4v12m0-12-5 5m5-5 5 5M5 20h14" stroke="currentColor" strokeWidth="1.4"/>
              </svg>
            </div>
            <p>Arrastra tu {kind === 'inst' ? 'instrumental' : 'pista de voz'}<br/>o haz clic para examinar</p>
            <small>WAV · AIFF · FLAC — 48kHz / 24bit recomendado</small>
            <div className="specs">
              <span>MAX 200MB</span>
              <span>MONO / STEREO</span>
              <span>—:—:—</span>
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
              <div><span className="k">ARCHIVO</span><span className="v">{data.name}</span></div>
              <div><span className="k">DURACIÓN</span><span className="v">{data.len}</span></div>
              <div><span className="k">FORMATO</span><span className="v">{data.sr} / {data.depth}</span></div>
              <div><span className="k">TEMPO</span><span className="v accent">{data.bpm} BPM · {data.key}</span></div>
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
            <span style={{ color: 'var(--text-mute)', fontSize: 13 }}>#A37-K2</span>
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
            {bothLoaded && <><span>·</span><span style={{ color: 'var(--accent)' }}>TEMPOS COMPATIBLES (120 BPM)</span></>}
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn btn-ghost" onClick={() => setState(s => ({ ...s, inst: { loaded: false }, vocal: { loaded: false } }))}>Limpiar</button>
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
