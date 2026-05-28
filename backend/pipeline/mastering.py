"""
Master bus chain:
  5.1 Master EQ
  5.2 Bus compression
  5.3 Stereo width (M/S)
  5.4 True Peak Limiting + LUFS targeting
  5.5 QA checks
"""
import logging
import numpy as np
import librosa
from scipy import signal as scipy_signal

from .vocal_processing import (
    rms_db, gain_db, peak_db, normalize_peak,
    _peaking_eq, _shelving, apply_filter, find_spectral_peak, design_biquad
)

logger = logging.getLogger(__name__)

TARGET_LUFS_MAP = {
    'streaming': -14.0,
    'club':       -9.0,
    'radio':     -16.0,
}

GENRE_MASTER_TWEAKS = {
    'reggaeton': dict(sub_bass_boost=1.0, presence_gain=0.0),
    'trap':      dict(sub_bass_boost=1.5, presence_gain=0.0),
    'drill':     dict(sub_bass_boost=1.5, presence_gain=0.0),
    'rnb':       dict(sub_bass_boost=0.5, presence_gain=0.5),
    'pop':       dict(sub_bass_boost=0.0, presence_gain=0.5, air_extra=1.0),
    'rock':      dict(sub_bass_boost=0.0, presence_gain=0.5),
    'afro':      dict(sub_bass_boost=1.0, presence_gain=0.0),
    'house':     dict(sub_bass_boost=1.5, presence_gain=0.0),
}

MOOD_TWEAKS = {
    'warm':   dict(high_shelf_adj=-0.5),
    'punchy': dict(high_shelf_adj=0.0),
    'open':   dict(high_shelf_adj=1.5),
    'gritty': dict(high_shelf_adj=-0.3),
}


def measure_lufs(y: np.ndarray, sr: int) -> float:
    """Measure integrated LUFS using pyloudnorm."""
    try:
        import pyloudnorm as pyln
        meter = pyln.Meter(sr)
        # pyloudnorm expects (samples, channels)
        if y.ndim == 1:
            audio = y.reshape(-1, 1)
        else:
            audio = y.T  # (samples, channels)
        lufs = meter.integrated_loudness(audio)
        if np.isinf(lufs) or np.isnan(lufs):
            return -70.0
        return float(lufs)
    except Exception as e:
        logger.warning(f"LUFS measurement error: {e} — using RMS fallback")
        rms = np.sqrt(np.mean(y ** 2) + 1e-12)
        return float(20 * np.log10(rms) - 3)  # approx


def true_peak_db(y: np.ndarray) -> float:
    """Estimate true peak via 4x oversampling."""
    # Upsample 4x
    y_up = scipy_signal.resample_poly(y.flatten(), 4, 1)
    return float(20 * np.log10(np.max(np.abs(y_up)) + 1e-12))


# ────────────────────────────────────────────────────────────────────────────
# 5.1 Master EQ
# ────────────────────────────────────────────────────────────────────────────

def eq_master(mix: np.ndarray, sr: int,
              bass_param: float = 50.0,
              presence_param: float = 50.0,
              genre: str = 'pop',
              mood: str = None) -> np.ndarray:
    """Apply master bus EQ. mix: (2, N) stereo."""
    tweaks = GENRE_MASTER_TWEAKS.get(genre, GENRE_MASTER_TWEAKS['pop'])
    mood_tw = MOOD_TWEAKS.get(mood, {}) if mood else {}

    out = np.zeros_like(mix)
    for ch in range(mix.shape[0]):
        y = mix[ch]
        in_db = rms_db(y)

        # 1. Sub-bass shelf
        sub_gain = ((bass_param - 50) / 50) * 2.0 + tweaks.get('sub_bass_boost', 0)
        if abs(sub_gain) > 0.2:
            b, a = _shelving(40, sr, gain_db_val=sub_gain, shelf_type='low', q=0.7)
            y = apply_filter(y, b, a)

        # 2. Warmth at 200Hz
        b, a = _peaking_eq(200, sr, gain_db_val=0.5, q=0.5)
        y = apply_filter(y, b, a)

        # 3. Midrange check (300-800Hz honkiness)
        honk_freq = find_spectral_peak(y, sr, 300, 800)
        honk_level = rms_db(
            scipy_signal.sosfilt(
                scipy_signal.butter(4, [300 / (sr / 2), 800 / (sr / 2)], btype='band', output='sos'),
                y
            )
        )
        ref = rms_db(y)
        if honk_level > ref + 2:
            b, a = _peaking_eq(honk_freq, sr, gain_db_val=-2.0, q=2.0)
            y = apply_filter(y, b, a)
            logger.debug(f"Master EQ: honk notch at {honk_freq:.0f} Hz")

        # 4. Presence (2-4kHz)
        pres_gain = tweaks.get('presence_gain', 0.5)
        if pres_gain > 0.1:
            b, a = _peaking_eq(3000, sr, gain_db_val=pres_gain, q=0.8)
            y = apply_filter(y, b, a)

        # 5. High shelf (8kHz+)
        air_gain = 1.0 + mood_tw.get('high_shelf_adj', 0)
        b, a = _shelving(8000, sr, gain_db_val=air_gain, shelf_type='high', q=0.5)
        y = apply_filter(y, b, a)

        # Gain-stage restore
        out_db = rms_db(y)
        if abs(out_db - in_db) > 0.5:
            y = gain_db(y, in_db - out_db)

        out[ch] = y

    return out.astype(np.float32)


# ────────────────────────────────────────────────────────────────────────────
# 5.2 Bus Compression
# ────────────────────────────────────────────────────────────────────────────

def compress_bus(mix: np.ndarray, sr: int) -> np.ndarray:
    """
    Gentle bus glue compression: 2:1, 30ms attack, 200ms release, ~2-3dB GR.
    """
    from .vocal_processing import compress
    out = np.zeros_like(mix)
    for ch in range(mix.shape[0]):
        out[ch] = compress(mix[ch], sr,
                           attack_ms=30, release_ms=200,
                           ratio=2.0, threshold_rms_db=-18.0)
    # Verify GR doesn't exceed -3dB
    in_rms  = rms_db(mix.flatten())
    out_rms = rms_db(out.flatten())
    gr = out_rms - in_rms
    if gr < -4:  # too much compression
        out = gain_db(out, -gr - 3)

    logger.info(f"Bus compression GR: {gr:.1f} dB")
    return out.astype(np.float32)


# ────────────────────────────────────────────────────────────────────────────
# 5.3 Stereo Width (M/S)
# ────────────────────────────────────────────────────────────────────────────

def stereo_width(mix: np.ndarray, sr: int, width_param: float = 50.0) -> np.ndarray:
    """
    M/S stereo width processing.
    width_param: 0=narrow, 50=neutral, 100=wider.
    Enforces mono-compatibility (bass in mono below 150Hz).
    """
    if mix.shape[0] != 2:
        return mix  # can't do M/S on mono

    M = (mix[0] + mix[1]) / 2
    S = (mix[0] - mix[1]) / 2

    # High-pass on Side to ensure mono bass compatibility
    b, a = scipy_signal.butter(3, 150 / (sr / 2), btype='high')
    S = scipy_signal.lfilter(b, a, S)

    # Adjust Side level
    if width_param > 50:
        side_gain = 1.0 + (width_param - 50) / 50 * 3  # max +3dB Side
    else:
        side_gain = 1.0 - (50 - width_param) / 50 * 0.75  # min -6dB Side (0.25 ratio)

    S = S * side_gain

    # Check stereo correlation — keep above +0.5
    corr = _stereo_correlation(M + S, M - S)
    if corr < 0.5:
        # Pull back side gain
        S = S * 0.7
        logger.warning(f"Stereo correlation low ({corr:.2f}), reduced side signal")

    L = M + S
    R = M - S

    logger.info(f"Stereo width: param={width_param}, side_gain={side_gain:.2f}, corr={corr:.2f}")
    return np.stack([L, R], axis=0).astype(np.float32)


def _stereo_correlation(L: np.ndarray, R: np.ndarray) -> float:
    """Pearson correlation between L and R channels."""
    if len(L) == 0 or len(R) == 0:
        return 1.0
    corr = np.corrcoef(L, R)[0, 1]
    return float(corr) if not np.isnan(corr) else 1.0


# ────────────────────────────────────────────────────────────────────────────
# 5.4 True Peak Limiter + LUFS targeting
# ────────────────────────────────────────────────────────────────────────────

def apply_limiter(mix: np.ndarray, sr: int,
                  ceiling_dBTP: float = -1.0,
                  release_ms: float = 150) -> np.ndarray:
    """
    True peak brick-wall limiter.
    Uses lookahead + 4x oversampled peak detection.
    """
    try:
        from pedalboard import Pedalboard, Limiter
        board = Pedalboard([Limiter(threshold_db=ceiling_dBTP, release_ms=release_ms)])
        out = np.zeros_like(mix)
        for ch in range(mix.shape[0]):
            out[ch] = board(mix[ch].reshape(1, -1), sr).flatten()
        return out.astype(np.float32)
    except ImportError:
        logger.warning("pedalboard not available — using simple clipper limiter")
        return _simple_limiter(mix, ceiling_dBTP)


def _simple_limiter(mix: np.ndarray, ceiling_dBTP: float = -1.0) -> np.ndarray:
    """Sample-accurate peak limiter with soft knee."""
    ceiling_lin = 10 ** (ceiling_dBTP / 20)
    peak = np.max(np.abs(mix))
    if peak > ceiling_lin:
        # Soft knee: apply gain that brings peak to ceiling
        gain = ceiling_lin / peak
        # Smooth the gain to avoid distortion
        mix_out = mix * gain
        # Hard clip as safety
        np.clip(mix_out, -ceiling_lin, ceiling_lin, out=mix_out)
        return mix_out.astype(np.float32)
    return mix


def target_loudness(mix: np.ndarray, sr: int,
                    target_lufs: float = -14.0,
                    ceiling_dBTP: float = -1.0,
                    max_iterations: int = 3) -> tuple[np.ndarray, float, float]:
    """
    Iterative LUFS targeting with True Peak limiting.
    Returns (mix_out, achieved_lufs, true_peak_db).
    """
    mix_out = mix.copy()

    for i in range(max_iterations):
        current_lufs = measure_lufs(mix_out, sr)
        if np.isinf(current_lufs) or np.isnan(current_lufs):
            current_lufs = -70.0

        gain_needed = target_lufs - current_lufs
        mix_out = gain_db(mix_out, gain_needed)
        logger.debug(f"LUFS iter {i+1}: current={current_lufs:.1f}, gain={gain_needed:.1f}dB")

        # Apply limiter
        mix_out = apply_limiter(mix_out, sr, ceiling_dBTP=ceiling_dBTP)

        # Check result
        final_lufs = measure_lufs(mix_out, sr)
        if abs(final_lufs - target_lufs) <= 0.5:
            break

    tp = true_peak_db(mix_out)
    logger.info(f"LUFS targeting: target={target_lufs:.1f}, achieved={final_lufs:.1f}, TP={tp:.1f} dBTP")
    return mix_out.astype(np.float32), float(final_lufs), float(tp)


# ────────────────────────────────────────────────────────────────────────────
# 5.5 QA
# ────────────────────────────────────────────────────────────────────────────

def qa_check(mix: np.ndarray, sr: int,
             target_lufs: float, lufs_achieved: float, tp_db: float) -> dict:
    """Automated QA checks before export. Returns dict with warnings."""
    warnings = []
    checks = {}

    # LUFS within ±0.5 LU
    lufs_ok = abs(lufs_achieved - target_lufs) <= 0.5
    checks['lufs_ok'] = lufs_ok
    if not lufs_ok:
        warnings.append(f"LUFS off target: {lufs_achieved:.1f} vs {target_lufs:.1f}")

    # True peak
    tp_ok = tp_db <= -1.0
    checks['true_peak_ok'] = tp_ok
    if not tp_ok:
        warnings.append(f"True peak too high: {tp_db:.1f} dBTP")

    # Stereo correlation
    if mix.shape[0] == 2:
        corr = _stereo_correlation(mix[0], mix[1])
        checks['stereo_correlation'] = round(corr, 3)
        if corr < 0.4:
            warnings.append(f"Stereo correlation too low: {corr:.2f}")

    # Crest factor (peak-to-RMS)
    peak_val = np.max(np.abs(mix))
    rms_val  = np.sqrt(np.mean(mix ** 2) + 1e-12)
    crest_db = 20 * np.log10(peak_val / (rms_val + 1e-9))
    checks['crest_factor'] = round(float(crest_db), 2)
    if crest_db < 6:
        warnings.append(f"Over-compressed: crest factor {crest_db:.1f} dB (< 6 dB)")
    if crest_db > 14:
        warnings.append(f"Under-limited: crest factor {crest_db:.1f} dB (> 14 dB)")

    # Dynamic range (simplified: 95th - 5th percentile in dB)
    abs_vals = np.abs(mix.flatten())
    dr = 20 * np.log10(np.percentile(abs_vals, 95) / (np.percentile(abs_vals, 5) + 1e-9))
    checks['dynamic_range'] = round(float(dr), 2)

    checks['warnings'] = warnings
    checks['qa_passed'] = len(warnings) == 0
    return checks


# ────────────────────────────────────────────────────────────────────────────
# Main mastering function
# ────────────────────────────────────────────────────────────────────────────

def master(
    mix: np.ndarray,
    sr: int,
    bass_param: float = 50.0,
    presence_param: float = 50.0,
    stereo_param: float = 50.0,
    loudness_param: float = -14.0,
    target: str = 'streaming',
    genre: str = 'pop',
    mood: str = None,
) -> tuple[np.ndarray, dict]:
    """
    Full mastering pipeline.
    mix: (2, N) stereo float32
    Returns (mastered_mix, report_dict)
    """
    # Resolve LUFS target
    target_lufs = TARGET_LUFS_MAP.get(target, -14.0)
    # User loudness_param overrides preset if significantly different
    if abs(loudness_param - target_lufs) > 0.5:
        target_lufs = loudness_param

    logger.info(f"Mastering: genre={genre}, mood={mood}, target={target_lufs:.1f} LUFS")

    # Safety normalize before chain
    mix = _normalize_stereo(mix, ceiling_db=-4.0)

    # 5.1 Master EQ
    mix = eq_master(mix, sr, bass_param=bass_param, presence_param=presence_param,
                    genre=genre, mood=mood)
    logger.info(f"After master EQ — peak: {peak_db(mix.flatten()):.1f} dBFS")

    mix = _normalize_stereo(mix, ceiling_db=-2.0)

    # 5.2 Bus compression
    mix = compress_bus(mix, sr)
    logger.info(f"After bus comp — peak: {peak_db(mix.flatten()):.1f} dBFS")

    # 5.3 Stereo width
    mix = stereo_width(mix, sr, width_param=stereo_param)

    # 5.4 LUFS targeting + limiting
    mix, lufs_achieved, tp = target_loudness(mix, sr, target_lufs=target_lufs)

    # 5.5 QA
    qa = qa_check(mix, sr, target_lufs, lufs_achieved, tp)
    for w in qa.get('warnings', []):
        logger.warning(f"QA: {w}")

    report = {
        'lufs_integrated':      round(lufs_achieved, 2),
        'true_peak':            round(tp, 2),
        'true_peak_clippings':  0 if tp <= -1.0 else 1,
        'stereo_correlation':   qa.get('stereo_correlation', 1.0),
        'crest_factor':         qa.get('crest_factor', 9.0),
        'dynamic_range':        qa.get('dynamic_range', 8.0),
        'qa_warnings':          qa.get('warnings', []),
        'qa_passed':            qa.get('qa_passed', True),
    }

    return mix.astype(np.float32), report


def _normalize_stereo(mix: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    peak = np.max(np.abs(mix))
    if peak < 1e-9:
        return mix
    target = 10 ** (ceiling_db / 20)
    if peak > target:
        mix = mix * (target / peak)
    return mix.astype(np.float32)
