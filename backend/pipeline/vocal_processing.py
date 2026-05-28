"""
Full vocal processing chain:
  3.1 Noise reduction
  3.2 Pitch correction (autotune)
  3.3 De-essing
  3.4 EQ (vocal curve)
  3.5 Compression (1176 → LA-2A)
  3.6 Reverb
"""
import logging
import numpy as np
import librosa
import soundfile as sf
from scipy import signal as scipy_signal

from .pitch_correction import correct_pitch
from .analysis import NOTE_NAMES

logger = logging.getLogger(__name__)

TARGET_SR = 48000


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def rms_db(y: np.ndarray) -> float:
    rms = np.sqrt(np.mean(y ** 2) + 1e-12)
    return 20 * np.log10(rms + 1e-12)


def peak_db(y: np.ndarray) -> float:
    return 20 * np.log10(np.max(np.abs(y)) + 1e-12)


def normalize_peak(y: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    """Normalize so peak = ceiling_db. Never clips."""
    pk = np.max(np.abs(y))
    if pk < 1e-9:
        return y
    target = 10 ** (ceiling_db / 20)
    return y * (target / pk)


def gain_db(y: np.ndarray, db: float) -> np.ndarray:
    return y * (10 ** (db / 20))


def design_biquad(filter_type: str, freq: float, sr: int,
                  gain_db_val: float = 0.0, q: float = 0.707) -> tuple:
    """
    Design IIR biquad filter coefficients using scipy.
    filter_type: 'high_pass', 'low_pass', 'low_shelf', 'high_shelf', 'peak', 'notch'
    Returns (b, a) arrays for scipy.signal.lfilter.
    """
    nyq = sr / 2.0
    w0 = freq / nyq  # normalized [0, 1)

    if filter_type == 'high_pass':
        b, a = scipy_signal.butter(2, w0, btype='high')
    elif filter_type == 'low_pass':
        b, a = scipy_signal.butter(2, w0, btype='low')
    elif filter_type == 'low_shelf':
        A = 10 ** (gain_db_val / 40)
        b, a = scipy_signal.iirpeak(w0, q) if gain_db_val > 0 else scipy_signal.iirnotch(w0, q)
        # Proper shelf: use bilinear transform
        b, a = _shelving(freq, sr, gain_db_val, shelf_type='low', q=q)
    elif filter_type == 'high_shelf':
        b, a = _shelving(freq, sr, gain_db_val, shelf_type='high', q=q)
    elif filter_type == 'peak':
        b, a = _peaking_eq(freq, sr, gain_db_val, q)
    elif filter_type == 'notch':
        b, a = scipy_signal.iirnotch(w0, q)
    else:
        raise ValueError(f"Unknown filter type: {filter_type}")
    return b, a


def _shelving(freq: float, sr: int, gain_db_val: float,
              shelf_type: str = 'low', q: float = 0.707):
    """Analog-prototype shelving filter via bilinear transform."""
    A = 10 ** (gain_db_val / 40.0)
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / (2 * q)

    if shelf_type == 'low':
        b0 =  A * ((A + 1) - (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha)
        b1 =  2 * A * ((A - 1) - (A + 1) * np.cos(w0))
        b2 =  A * ((A + 1) - (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha)
        a0 =       (A + 1) + (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha
        a1 = -2 *      ((A - 1) + (A + 1) * np.cos(w0))
        a2 =           (A + 1) + (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha
    else:  # high shelf
        b0 =  A * ((A + 1) + (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha)
        b1 = -2 * A * ((A - 1) + (A + 1) * np.cos(w0))
        b2 =  A * ((A + 1) + (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha)
        a0 =       (A + 1) - (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha
        a1 =  2 *      ((A - 1) - (A + 1) * np.cos(w0))
        a2 =           (A + 1) - (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha

    b = np.array([b0, b1, b2]) / a0
    a = np.array([a0, a1, a2]) / a0
    return b, a


def _peaking_eq(freq: float, sr: int, gain_db_val: float, q: float = 2.0):
    """Peaking EQ biquad."""
    A = 10 ** (gain_db_val / 40.0)
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / (2 * q)

    b0 =  1 + alpha * A
    b1 = -2 * np.cos(w0)
    b2 =  1 - alpha * A
    a0 =  1 + alpha / A
    a1 = -2 * np.cos(w0)
    a2 =  1 - alpha / A

    b = np.array([b0, b1, b2]) / a0
    a = np.array([a0, a1, a2]) / a0
    return b, a


def apply_filter(y: np.ndarray, b, a) -> np.ndarray:
    return scipy_signal.lfilter(b, a, y).astype(np.float32)


def find_spectral_peak(y: np.ndarray, sr: int, f_low: float, f_high: float) -> float:
    """Find frequency with peak energy in a given band."""
    freqs = np.fft.rfftfreq(len(y), d=1.0 / sr)
    spectrum = np.abs(np.fft.rfft(y)) ** 2
    mask = (freqs >= f_low) & (freqs <= f_high)
    if not np.any(mask):
        return (f_low + f_high) / 2
    peak_idx = np.argmax(spectrum[mask])
    return float(freqs[mask][peak_idx])


# ────────────────────────────────────────────────────────────────────────────
# 3.1 Noise Reduction
# ────────────────────────────────────────────────────────────────────────────

def noise_reduce(y: np.ndarray, sr: int, snr_db: float = 30.0) -> np.ndarray:
    """
    Neural denoising via DeepFilterNet (Apache 2.0).
    Falls back to spectral subtraction if not available.
    """
    aggressive = snr_db < 20.0
    strength = 0.7 if aggressive else 0.55

    try:
        from df.enhance import enhance, init_df, load_audio, save_audio
        import tempfile, os, soundfile as sf_inner

        model, df_state, _ = init_df()
        # DeepFilterNet expects 48kHz
        y_48 = librosa.resample(y, orig_sr=sr, target_sr=48000) if sr != 48000 else y

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_in:
            sf_inner.write(tmp_in.name, y_48, 48000, subtype='FLOAT')
            in_path = tmp_in.name

        audio, _ = load_audio(in_path, sr=df_state.sr())
        enhanced = enhance(model, df_state, audio)

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_out:
            save_audio(tmp_out.name, enhanced, df_state.sr())
            y_clean, _ = librosa.load(tmp_out.name, sr=sr, mono=True)

        os.unlink(in_path)
        os.unlink(tmp_out.name)

        # Second pass for very noisy audio
        if snr_db < 15:
            y_clean = _spectral_subtract(y_clean, sr, strength=0.4)

        logger.info("DeepFilterNet noise reduction applied")
        return y_clean.astype(np.float32)

    except Exception as e:
        logger.warning(f"DeepFilterNet unavailable ({e}), using spectral subtraction")
        return _spectral_subtract(y, sr, strength=strength)


def _spectral_subtract(y: np.ndarray, sr: int, strength: float = 0.6) -> np.ndarray:
    """Spectral subtraction using noise estimate from first 0.5s."""
    n_fft = 2048
    hop = 512
    n_noise = min(int(0.5 * sr), len(y) // 4)

    # Estimate noise spectrum from silence
    noise_stft = librosa.stft(y[:n_noise], n_fft=n_fft, hop_length=hop)
    noise_power = np.mean(np.abs(noise_stft) ** 2, axis=1, keepdims=True)

    # Full signal STFT
    D = librosa.stft(y, n_fft=n_fft, hop_length=hop)
    power = np.abs(D) ** 2
    phase = np.angle(D)

    # Subtract noise power, floor at 0
    clean_power = np.maximum(power - strength * noise_power, power * 0.01)
    D_clean = np.sqrt(clean_power) * np.exp(1j * phase)

    y_clean = librosa.istft(D_clean, hop_length=hop, length=len(y))
    return y_clean.astype(np.float32)


# ────────────────────────────────────────────────────────────────────────────
# 3.3 De-essing
# ────────────────────────────────────────────────────────────────────────────

def deess(y: np.ndarray, sr: int, ratio: float = 3.0) -> np.ndarray:
    """
    Frequency-selective de-esser targeting 5kHz-10kHz.
    Detects sibilance energy above threshold and applies dynamic reduction.
    """
    n_fft = 2048
    hop = 512

    D = librosa.stft(y, n_fft=n_fft, hop_length=hop)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    sib_mask = (freqs >= 5000) & (freqs <= 10000)
    full_power = np.mean(np.abs(D) ** 2, axis=0)
    sib_power  = np.mean(np.abs(D[sib_mask, :]) ** 2, axis=0)

    # Dynamic threshold: mean + 6dB
    sib_mean = np.mean(sib_power) + 1e-12
    threshold = sib_mean * (10 ** (6 / 10))

    # Gain reduction where sibilance exceeds threshold
    gain = np.ones(D.shape[1])
    over_thresh = sib_power > threshold
    if np.any(over_thresh):
        excess = sib_power[over_thresh] / threshold
        gain[over_thresh] = 1.0 / (excess ** ((ratio - 1) / ratio))
        gain = np.clip(gain, 0.5, 1.0)

    # Apply only to sibilant frequencies
    D_out = D.copy()
    D_out[sib_mask, :] *= gain[np.newaxis, :]

    y_out = librosa.istft(D_out, hop_length=hop, length=len(y))
    return y_out.astype(np.float32)


# ────────────────────────────────────────────────────────────────────────────
# 3.4 Vocal EQ
# ────────────────────────────────────────────────────────────────────────────

GENRE_EQ_TWEAKS = {
    'reggaeton': dict(hp_freq=150, presence_gain_extra=1.5, air_gain=1.0),
    'trap':      dict(hp_freq=150, presence_gain_extra=1.5, air_gain=0.8),
    'rnb':       dict(hp_freq=80,  presence_gain_extra=0.0, air_gain=1.0, warmth_boost=1.0),
    'pop':       dict(hp_freq=80,  presence_gain_extra=0.5, air_gain=2.0),
    'rock':      dict(hp_freq=100, presence_gain_extra=0.5, air_gain=1.0),
    'afro':      dict(hp_freq=80,  presence_gain_extra=0.5, air_gain=1.5),
    'house':     dict(hp_freq=80,  presence_gain_extra=0.5, air_gain=1.5),
    'drill':     dict(hp_freq=150, presence_gain_extra=1.5, air_gain=0.8),
}


def eq_vocal(y: np.ndarray, sr: int,
             presence_param: float = 50.0,
             genre: str = 'pop') -> np.ndarray:
    """
    Apply vocal EQ chain per spec.
    presence_param: 0-100 controls 2.5-3.5kHz boost amount.
    """
    tweaks = GENRE_EQ_TWEAKS.get(genre, GENRE_EQ_TWEAKS['pop'])
    in_db = rms_db(y)

    # 1. High-pass (remove rumble)
    hp_freq = tweaks.get('hp_freq', 80)
    b, a = design_biquad('high_pass', hp_freq, sr)
    y = apply_filter(y, b, a)

    # 2. Low shelf cut (boominess at 200Hz)
    b, a = _shelving(200, sr, gain_db_val=-2.0, shelf_type='low', q=0.7)
    y = apply_filter(y, b, a)

    # 3. Auto-notch for boxiness (300-500Hz)
    boxy_freq = find_spectral_peak(y, sr, 300, 500)
    b, a = _peaking_eq(boxy_freq, sr, gain_db_val=-3.0, q=3.0)
    y = apply_filter(y, b, a)
    logger.debug(f"Vocal EQ: auto-notch at {boxy_freq:.0f} Hz")

    # 4. Presence boost (2.5-3.5kHz)
    presence_gain = 1.0 + (presence_param / 100.0) * 4.0 + tweaks.get('presence_gain_extra', 0)
    b, a = _peaking_eq(3000, sr, gain_db_val=presence_gain, q=1.2)
    y = apply_filter(y, b, a)

    # 5. De-harsh check (4-6kHz)
    harsh_freq = find_spectral_peak(y, sr, 4000, 6000)
    harsh_level = rms_db(
        scipy_signal.sosfilt(
            scipy_signal.butter(4, [4000 / (sr / 2), 6000 / (sr / 2)], btype='band', output='sos'),
            y
        )
    )
    ref_level = rms_db(y)
    if harsh_level > ref_level + 3:
        b, a = _peaking_eq(harsh_freq, sr, gain_db_val=-2.0, q=2.5)
        y = apply_filter(y, b, a)
        logger.debug(f"Vocal EQ: de-harsh at {harsh_freq:.0f} Hz")

    # 6. Air (10-16kHz high shelf)
    air_gain = 1.5 + tweaks.get('air_gain', 0.0)
    b, a = _shelving(12000, sr, gain_db_val=air_gain, shelf_type='high', q=0.7)
    y = apply_filter(y, b, a)

    # 7. High cut at 18kHz
    b, a = scipy_signal.butter(3, 18000 / (sr / 2), btype='low')
    y = apply_filter(y, b, a)

    # Warmth boost for RnB
    if tweaks.get('warmth_boost', 0):
        b, a = _peaking_eq(800, sr, gain_db_val=tweaks['warmth_boost'], q=1.0)
        y = apply_filter(y, b, a)

    # Gain-stage: restore pre-EQ level
    out_db = rms_db(y)
    if abs(out_db - in_db) > 0.5:
        y = gain_db(y, in_db - out_db)

    return y.astype(np.float32)


# ────────────────────────────────────────────────────────────────────────────
# 3.5 Vocal Compression (1176 → LA-2A)
# ────────────────────────────────────────────────────────────────────────────

def compress(y: np.ndarray, sr: int,
             attack_ms: float, release_ms: float,
             ratio: float, threshold_rms_db: float = -18.0) -> np.ndarray:
    """Simple feed-forward RMS compressor."""
    attack_coef  = np.exp(-1.0 / (sr * attack_ms / 1000.0))
    release_coef = np.exp(-1.0 / (sr * release_ms / 1000.0))

    rms_window = int(sr * 0.01)  # 10ms RMS
    gain_reduction = np.ones(len(y))
    envelope = 0.0

    for i in range(len(y)):
        x = float(y[i])
        power = x * x
        if power > envelope:
            envelope = attack_coef * envelope + (1 - attack_coef) * power
        else:
            envelope = release_coef * envelope + (1 - release_coef) * power

        rms = np.sqrt(max(envelope, 1e-12))
        rms_dB = 20 * np.log10(rms + 1e-12)

        if rms_dB > threshold_rms_db:
            excess = rms_dB - threshold_rms_db
            gr = excess * (1.0 - 1.0 / ratio)
            gain_reduction[i] = 10 ** (-gr / 20.0)

    # Clamp gain reduction to max -6dB
    gain_reduction = np.maximum(gain_reduction, 10 ** (-6 / 20))

    y_out = y * gain_reduction

    # Auto makeup gain: restore average level
    makeup = rms_db(y) - rms_db(y_out)
    y_out = gain_db(y_out, makeup)

    return y_out.astype(np.float32)


def compress_vocal(y: np.ndarray, sr: int) -> np.ndarray:
    """Two-stage vocal compression: 1176 + LA-2A."""
    in_db = rms_db(y)

    # Stage 1: 1176 (fast, transients)
    y = compress(y, sr, attack_ms=0.5, release_ms=40, ratio=4.0, threshold_rms_db=-18.0)
    logger.debug(f"After 1176: {rms_db(y):.1f} dBFS RMS")

    # Stage 2: LA-2A (slow, body)
    y = compress(y, sr, attack_ms=10.0, release_ms=200, ratio=3.0, threshold_rms_db=-12.0)
    logger.debug(f"After LA-2A: {rms_db(y):.1f} dBFS RMS")

    # Verify RMS is in target range [-18, -12]
    out_db = rms_db(y)
    if out_db < -18:
        y = gain_db(y, -18 - out_db)
    elif out_db > -12:
        y = gain_db(y, -12 - out_db + 1)

    return y.astype(np.float32)


# ────────────────────────────────────────────────────────────────────────────
# 3.6 Vocal Reverb
# ────────────────────────────────────────────────────────────────────────────

GENRE_REVERB = {
    'reggaeton': dict(decay=1.0, wet=0.18, room=0.35),
    'trap':      dict(decay=1.5, wet=0.22, room=0.40),
    'drill':     dict(decay=1.5, wet=0.22, room=0.40),
    'rnb':       dict(decay=1.4, wet=0.20, room=0.38),
    'pop':       dict(decay=0.9, wet=0.15, room=0.30),
    'rock':      dict(decay=1.1, wet=0.16, room=0.35),
    'afro':      dict(decay=1.0, wet=0.16, room=0.32),
    'house':     dict(decay=1.2, wet=0.18, room=0.35),
}


def add_reverb(y: np.ndarray, sr: int, bpm: float = 120, genre: str = 'pop') -> np.ndarray:
    """
    Add subtle room reverb using pedalboard or synthetic IR.
    Pre-delay is BPM-synced.
    """
    params = GENRE_REVERB.get(genre, GENRE_REVERB['pop'])
    pre_delay_ms = (60000 / bpm) * 0.25  # one quarter-note quarter
    pre_delay_samples = int(pre_delay_ms * sr / 1000)

    try:
        from pedalboard import Pedalboard, Reverb

        board = Pedalboard([
            Reverb(
                room_size=params['room'],
                damping=0.7,
                wet_level=params['wet'],
                dry_level=1.0 - params['wet'],
                width=0.5,
            )
        ])
        y_padded = np.pad(y, (pre_delay_samples, 0))
        y_wet = board(y_padded, sr)
        y_wet = y_wet[:len(y)]

        # High-cut on reverb tail (8kHz) to not compete with direct voice
        b, a = scipy_signal.butter(3, 8000 / (sr / 2), btype='low')
        y_rev_only = y_wet - y
        y_rev_only = scipy_signal.lfilter(b, a, y_rev_only)
        y_out = y + y_rev_only

    except ImportError:
        logger.warning("pedalboard not available — using simple convolution reverb")
        y_out = _simple_reverb(y, sr, decay=params['decay'], wet=params['wet'],
                               pre_delay_samples=pre_delay_samples)

    return y_out.astype(np.float32)


def _simple_reverb(y: np.ndarray, sr: int,
                   decay: float, wet: float,
                   pre_delay_samples: int) -> np.ndarray:
    """Synthetic exponential-decay IR reverb."""
    ir_len = int(decay * sr)
    t = np.arange(ir_len) / sr
    ir = np.random.randn(ir_len) * np.exp(-t / (decay * 0.5))
    ir[0] = 1.0  # direct component

    from scipy.signal import fftconvolve
    y_conv = fftconvolve(y, ir)[:len(y)]
    y_conv = y_conv / (np.max(np.abs(y_conv)) + 1e-9)

    pre_y = np.pad(y, (pre_delay_samples, 0))[:len(y)]
    return (y * (1 - wet) + pre_y * wet * 0.3 + y_conv * wet * 0.7).astype(np.float32)


# ────────────────────────────────────────────────────────────────────────────
# Main entry point
# ────────────────────────────────────────────────────────────────────────────

def process_vocal(
    y: np.ndarray,
    sr: int,
    root_note: int,
    mode: str,
    genre: str = 'pop',
    presence_param: float = 50.0,
    bpm: float = 120.0,
    snr_db: float = 30.0,
    no_autotune: bool = False,
) -> tuple[np.ndarray, dict]:
    """
    Full vocal processing chain. Returns (processed_audio, stats_dict).
    """
    stats = {}
    logger.info(f"Vocal processing start — RMS: {rms_db(y):.1f} dBFS")

    # 3.1 Noise reduction
    y = noise_reduce(y, sr, snr_db=snr_db)
    stats['noise_reduction_applied'] = True
    logger.info(f"After noise reduction — RMS: {rms_db(y):.1f} dBFS")

    # Safety: prevent clipping before next step
    y = normalize_peak(y, ceiling_db=-1.0)

    # 3.2 Pitch correction
    y, pitch_stats = correct_pitch(y, sr, root_note, mode, genre=genre, no_autotune=no_autotune)
    stats.update(pitch_stats)
    logger.info(f"After pitch correction — RMS: {rms_db(y):.1f} dBFS")

    y = normalize_peak(y, ceiling_db=-1.0)

    # 3.3 De-essing
    y = deess(y, sr)
    logger.info(f"After de-essing — RMS: {rms_db(y):.1f} dBFS")

    # 3.4 Vocal EQ
    y = eq_vocal(y, sr, presence_param=presence_param, genre=genre)
    logger.info(f"After vocal EQ — RMS: {rms_db(y):.1f} dBFS")

    y = normalize_peak(y, ceiling_db=-1.0)

    # 3.5 Compression
    y = compress_vocal(y, sr)
    logger.info(f"After compression — RMS: {rms_db(y):.1f} dBFS")

    # 3.6 Reverb
    y = add_reverb(y, sr, bpm=bpm, genre=genre)
    logger.info(f"After reverb — RMS: {rms_db(y):.1f} dBFS")

    y = normalize_peak(y, ceiling_db=-1.5)

    return y.astype(np.float32), stats
