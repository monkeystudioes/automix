/* ====================================================================
   AutoMix — Screen 2: Sync editor (mini-DAW)
   ==================================================================== */

function SyncScreen({ state, setState, onNext, onBack }) {
  const [offset, setOffset] = React.useState(state.offset ?? 42); // px offset of vocal
  const [zoom, setZoom] = React.useState(1.0);
  const [playing, setPlaying] = React.useState(false);
  const [playhead, setPlayhead] = React.useState(0.18); // 0..1
  const arenaRef = React.useRef(null);
  const dragRef = React.useRef(null);
  const [beats, setBeats] = React.useState(true);

  // play tick
  React.useEffect(() => {
    if (!playing) return;
    let id;
    const step = () => {
      setPlayhead(p => p + 0.0014);
      id = requestAnimationFrame(step);
    };
    id = requestAnimationFrame(step);
    return () => cancelAnimationFrame(id);
  }, [playing]);
  React.useEffect(() => { if (playhead > 1) { setPlayhead(0); setPlaying(false); } }, [playhead]);

  // commit offset to global state on next/back
  React.useEffect(() => { setState(s => ({ ...s, offset })); }, [offset]);

  const beatSize = 56 * zoom;

  const startDrag = (e) => {
    dragRef.current = { startX: e.clientX, startOff: offset };
    window.addEventListener('pointermove', onDrag);
    window.addEventListener('pointerup', endDrag);
  };
  const onDrag = (e) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.startX;
    setOffset(dragRef.current.startOff + dx);
  };
  const endDrag = () => {
    dragRef.current = null;
    window.removeEventListener('pointermove', onDrag);
    window.removeEventListener('pointerup', endDrag);
  };

  // convert px offset → ms (assume 120 BPM, beat = 500ms, beatSize px = 500ms)
  const offsetMs = Math.round((offset / beatSize) * 500);
  const offsetSign = offsetMs >= 0 ? '+' : '−';

  const seconds = Math.floor(playhead * 204); // ~3:24 in seconds
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
  const ss = String(seconds % 60).padStart(2, '0');
  const fr = String(Math.floor((playhead * 204 - seconds) * 24)).padStart(2, '0');

  return (
    <div className="sync-shell">
      <div className="sync-toolbar">
        <div className="left">
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.2em', color: 'var(--text-mute)' }}>02 · SINCRONIZAR</div>
          <div style={{ width: 1, height: 22, background: 'var(--line-2)' }}></div>
          <div style={{ fontFamily: 'var(--display)', fontSize: 18, letterSpacing: '-0.025em' }}>
            Alinea la voz<span style={{ color: 'var(--text-mute)' }}> al beat</span>
          </div>
        </div>
        <div className="right">
          <div className="tool-group">
            <button className="tool-btn" onClick={() => setZoom(z => Math.max(0.5, z - 0.25))} title="Zoom out">
              <svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 7h8" stroke="currentColor" strokeWidth="1.4"/></svg>
            </button>
            <div className="zoom-readout">{Math.round(zoom * 100)}%</div>
            <button className="tool-btn" onClick={() => setZoom(z => Math.min(3, z + 0.25))} title="Zoom in">
              <svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 7h8M7 3v8" stroke="currentColor" strokeWidth="1.4"/></svg>
            </button>
          </div>
          <button className={`tool-btn ${beats ? 'active' : ''}`} onClick={() => setBeats(b => !b)} title="Snap to beats">
            <svg width="14" height="14" viewBox="0 0 14 14"><path d="M2 11h2V5H2v6Zm3 0h2V2H5v9Zm3 0h2V7H8v4Zm3 0h2V4h-2v7Z" fill="currentColor"/></svg>
          </button>
          <button className="tool-btn" title="Auto-align">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="m3 7 2 2 6-6" stroke="currentColor" strokeWidth="1.4"/>
            </svg>
          </button>
          <button className="btn-ghost" style={{ padding: '8px 14px', borderRadius: 8, fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.18em', border: '1px solid var(--line-2)' }} onClick={() => setOffset(0)}>
            RESET OFFSET
          </button>
        </div>
      </div>

      <div className="sync-arena" ref={arenaRef}>
        {/* ruler */}
        <div className="sync-ruler">
          {Array.from({ length: 16 }).map((_, i) => (
            <div key={i} className={`tick ${i % 4 === 0 ? 'bar' : ''}`}>
              <span>{i % 4 === 0 ? `${(i / 4) + 1}` : `.${(i % 4) + 1}`}</span>
            </div>
          ))}
        </div>

        {/* lane: instrumental */}
        <div className="lane inst" style={{ '--beat': `${beatSize}px` }}>
          <div className={`beats ${beats ? 'strong' : ''}`}></div>
          <div className="lane-label">
            <div className="dot"></div>
            <div>
              <div className="name">INST — midnight_loop_120bpm.wav</div>
              <div className="sub">120 BPM · F MIN · ANCLA</div>
            </div>
          </div>
          <div className="clip inst" style={{ left: 0, width: '100%' }}>
            <div className="clip-fill">
              <WaveBars width={1200} height={140} bars={170} seed={17} shape="song" color="#3a7bff" faint={0.85} />
            </div>
            <div className="grip">ANCLADO</div>
          </div>
        </div>

        {/* lane: vocal, draggable */}
        <div className="lane vocal" style={{ '--beat': `${beatSize}px` }}>
          <div className={`beats ${beats ? 'strong' : ''}`}></div>
          <div className="lane-label">
            <div className="dot"></div>
            <div>
              <div className="name">VOX — verse_take_07.wav</div>
              <div className="sub">ARRASTRA PARA ALINEAR · OFFSET {offsetSign}{Math.abs(offsetMs)} ms</div>
            </div>
          </div>
          <div
            className="clip vocal"
            style={{ left: offset, width: '94%' }}
            onPointerDown={startDrag}
          >
            <div className="clip-fill">
              <WaveBars width={1100} height={140} bars={150} seed={41} shape="vocal" color="#e3ff87" faint={0.85} />
            </div>
            <div className="handle l"></div>
            <div className="handle r"></div>
            <div className="grip">DRAG</div>
          </div>
          <div className="offset-chip">{offsetSign}{Math.abs(offsetMs)} ms · {offsetSign}{(Math.abs(offsetMs) / 500 * 100).toFixed(1)} BEATS</div>
        </div>

        {/* playhead */}
        <div className="playhead" style={{ left: `calc(36px + ${playhead * 100}% * 0.94)` }}></div>
      </div>

      <div className="transport">
        <div className="controls">
          <button className="tool-btn" title="Rewind" onClick={() => setPlayhead(0)}>
            <svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 2v10M12 2 5 7l7 5V2Z" fill="currentColor"/></svg>
          </button>
          <button className="play-btn" onClick={() => setPlaying(p => !p)}>
            {playing ? (
              <svg width="20" height="20" viewBox="0 0 20 20"><rect x="5" y="4" width="3.5" height="12" rx="0.5"/><rect x="11.5" y="4" width="3.5" height="12" rx="0.5"/></svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 20 20"><path d="M6 4 16 10 6 16Z" fill="currentColor"/></svg>
            )}
          </button>
          <button className="tool-btn" title="Loop">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 5a3 3 0 0 1 3-3h5l-1.5-1.5M12 9a3 3 0 0 1-3 3H4l1.5 1.5" stroke="currentColor" strokeWidth="1.4"/></svg>
          </button>
        </div>

        <div className="time">
          {mm}:{ss}<small>:{fr} / 03:24</small>
        </div>

        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          {/* Mini level meters */}
          <div style={{ display: 'flex', gap: 8 }}>
            {['L', 'R'].map(ch => (
              <div key={ch} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '0.18em', color: 'var(--text-mute)' }}>{ch}</div>
                <div style={{ width: 80, height: 6, background: 'var(--bg-1)', borderRadius: 3, overflow: 'hidden', border: '1px solid var(--line)' }}>
                  <div style={{ width: ch === 'L' ? '62%' : '58%', height: '100%', background: 'linear-gradient(90deg, var(--accent), #ff6464)' }}></div>
                </div>
              </div>
            ))}
          </div>
          <button className="btn btn-ghost" onClick={onBack}>← Atrás</button>
          <button className="btn" onClick={onNext}>Parámetros<span className="arrow">→</span></button>
        </div>
      </div>
    </div>
  );
}

window.SyncScreen = SyncScreen;
