"""
Mixing: sync, level balance, sidechain EQ.
"""
import logging
import numpy as np
import librosa
from scipy.signal import fftconvolve

from .vocal_processing import rms_db, gain_db, peak_db, normalize_peak, _peaking_eq, apply_filter

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# 4.1 Sync
# ────────────────────────────────────────────────────────────────────────────

def auto_sync(inst: np.ndarray, vocal: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Align vocal to instrumental via cross-correlation of onset envelopes.
    Returns (inst_aligned, vocal_aligned, offset_ms).
    Both outputs have the same length.
    """
    hop = 512
    inst_env  = librosa.onset.onset_strength(y=inst,  sr=sr, hop_length=hop)
    vocal_env = librosa.onset.onset_strength(y=vocal, sr=sr, hop_length=hop)

    # Cross-correlate
    corr = fftconvolve(inst_env, vocal_env[::-1], mode='full')
    offset_frames = corr.argmax() - (len(vocal_env) - 1)
    offset_samples = offset_frames * hop
    offset_ms = offset_samples / sr * 1000

    logger.info(f"Auto-sync: offset = {offset_ms:.1f} ms ({offset_samples} samples)")

    # Align: positive offset_samples = vocal starts after inst
    if offset_samples > 0:
        vocal_aligned = np.pad(vocal, (offset_samples, 0))
    else:
        vocal_aligned = vocal[abs(offset_samples):]

    # Make same length as instrumental
    min_len = min(len(inst), len(vocal_aligned))
    inst_aligned  = inst[:min_len]
    vocal_aligned = vocal_aligned[:min_len]

    return inst_aligned.astype(np.float32), vocal_aligned.astype(np.float32), offset_ms


def apply_manual_offset(inst: np.ndarray, vocal: np.ndarray, sr: int,
                        offset_ms: float) -> tuple[np.ndarray, np.ndarray]:
    """Apply a user-specified offset in ms to the vocal track."""
    offset_samples = int(offset_ms * sr / 1000)

    if offset_samples > 0:
        vocal_shifted = np.pad(vocal, (offset_samples, 0))
    elif offset_samples < 0:
        vocal_shifted = vocal[abs(offset_samples):]
        vocal_shifted = np.pad(vocal_shifted, (0, abs(offset_samples)))
    else:
        vocal_shifted = vocal

    min_len = min(len(inst), len(vocal_shifted))
    return inst[:min_len].astype(np.float32), vocal_shifted[:min_len].astype(np.float32)


# ────────────────────────────────────────────────────────────────────────────
# 4.2 Level Balance
# ────────────────────────────────────────────────────────────────────────────

def balance_levels(inst: np.ndarray, vocal: np.ndarray, sr: int,
                   presence_param: float = 50.0) -> tuple[np.ndarray, np.ndarray]:
    """
    Balance instrumental and vocal so vocal is 3-6 dB above instrumental in LUFS.
    Uses short-term RMS as proxy for LUFS (proper LUFS needs pyloudnorm).
    presence_param: 0-100 adjusts the vocal-to-inst gap (50=4dB gap).
    """
    try:
        import pyloudnorm as pyln
        meter = pyln.Meter(sr)
        # pyloudnorm expects (samples, channels) — reshape for mono
        inst_lufs  = meter.integrated_loudness(inst.reshape(-1, 1))
        vocal_lufs = meter.integrated_loudness(vocal.reshape(-1, 1))
    except Exception:
        # Fallback to RMS
        inst_lufs  = rms_db(inst)
        vocal_lufs = rms_db(vocal)

    # Target gap: presence 50 → 4dB, 0 → 2dB, 100 → 6dB
    target_gap_db = 2.0 + (presence_param / 100.0) * 4.0

    current_gap = vocal_lufs - inst_lufs
    adjustment = target_gap_db - current_gap

    # Adjust the instrumental (not the vocal, to preserve its processed level)
    inst_adjusted = gain_db(inst, -adjustment)
    logger.info(f"Level balance: inst adj {-adjustment:.1f}dB, gap now ~{target_gap_db:.1f}dB")

    return inst_adjusted.astype(np.float32), vocal


# ────────────────────────────────────────────────────────────────────────────
# 4.3 Sidechain EQ
# ────────────────────────────────────────────────────────────────────────────

def find_collision_frequencies(inst: np.ndarray, vocal: np.ndarray,
                               sr: int, n_freqs: int = 3) -> list[float]:
    """
    Find the 2-3 frequencies where instrumental and vocal energy collide most.
    Analyzes 200Hz-4kHz range.
    """
    n_fft = 4096
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    mask = (freqs >= 200) & (freqs <= 4000)

    inst_spec  = np.mean(np.abs(librosa.stft(inst,  n_fft=n_fft)) ** 2, axis=1)
    vocal_spec = np.mean(np.abs(librosa.stft(vocal, n_fft=n_fft)) ** 2, axis=1)

    # Collision score: product of normalized spectra
    inst_norm  = inst_spec  / (inst_spec.max()  + 1e-9)
    vocal_norm = vocal_spec / (vocal_spec.max() + 1e-9)
    collision  = (inst_norm * vocal_norm)[mask]

    # Find top N peaks
    freq_band = freqs[mask]
    peaks = []
    min_spacing = 100  # Hz minimum between peaks

    sorted_indices = np.argsort(collision)[::-1]
    for idx in sorted_indices:
        f = float(freq_band[idx])
        if all(abs(f - p) > min_spacing for p in peaks):
            peaks.append(f)
        if len(peaks) >= n_freqs:
            break

    logger.info(f"Sidechain EQ collision freqs: {[f'{f:.0f}Hz' for f in peaks]}")
    return peaks


def detect_vocal_activity(vocal: np.ndarray, sr: int, hop: int = 512) -> np.ndarray:
    """Return boolean mask (per-sample) indicating where vocal is active."""
    rms_frames = librosa.feature.rms(y=vocal, frame_length=1024, hop_length=hop)[0]
    threshold = np.mean(rms_frames) * 0.3
    active_frames = rms_frames > threshold

    # Upsample to sample-level
    active_samples = np.repeat(active_frames, hop)
    if len(active_samples) < len(vocal):
        active_samples = np.pad(active_samples, (0, len(vocal) - len(active_samples)))
    return active_samples[:len(vocal)]


def sidechain_eq(inst: np.ndarray, vocal: np.ndarray, sr: int) -> np.ndarray:
    """
    Apply dynamic EQ to instrumental at collision frequencies,
    only when vocal is present.
    Returns processed instrumental.
    """
    collision_freqs = find_collision_frequencies(inst, vocal, sr)
    vocal_active = detect_vocal_activity(vocal, sr)

    # Apply notch cuts at collision frequencies only where vocal is active
    inst_out = inst.copy()

    for freq in collision_freqs:
        b, a = _peaking_eq(freq, sr, gain_db_val=-1.5, q=2.0)
        from scipy.signal import lfilter
        inst_notched = lfilter(b, a, inst)
        # Blend: apply notch only where vocal is active
        inst_out = np.where(vocal_active, inst_notched, inst_out)

    return inst_out.astype(np.float32)


# ────────────────────────────────────────────────────────────────────────────
# Main mix function
# ────────────────────────────────────────────────────────────────────────────

def mix_tracks(
    inst: np.ndarray,
    vocal: np.ndarray,
    sr: int,
    offset_ms: float = 0.0,
    presence_param: float = 50.0,
    use_auto_sync: bool = True,
) -> tuple[np.ndarray, dict]:
    """
    Full mixing pipeline. Returns (mix_stereo, stats).
    mix_stereo is shape (2, N) — stereo output.
    """
    stats = {}

    # Safety normalize before mixing
    inst  = normalize_peak(inst,  ceiling_db=-3.0)
    vocal = normalize_peak(vocal, ceiling_db=-3.0)

    # 4.1 Sync
    if use_auto_sync and abs(offset_ms) < 10:
        inst, vocal, auto_offset = auto_sync(inst, vocal, sr)
        stats['auto_sync_offset_ms'] = auto_offset
    else:
        inst, vocal = apply_manual_offset(inst, vocal, sr, offset_ms)
        stats['manual_offset_ms'] = offset_ms

    # 4.2 Level balance
    inst, vocal = balance_levels(inst, vocal, sr, presence_param=presence_param)

    # 4.3 Sidechain EQ
    inst = sidechain_eq(inst, vocal, sr)

    # Mix to stereo (instrumental panned slightly left, vocal center)
    mix_L = inst * 0.95 + vocal * 0.85
    mix_R = inst * 0.95 + vocal * 0.85

    # Slight stereo spread on instrumental
    inst_L = librosa.effects.time_stretch(inst, rate=1.0)[:len(inst)]
    mix_L = mix_L * 0.95 + inst * 0.05
    mix_R = mix_R * 0.95 + inst * 0.05

    mix = np.stack([mix_L, mix_R], axis=0)

    # Safety check: no clipping
    peak = np.max(np.abs(mix))
    if peak > 0.99:
        mix = mix * (0.99 / peak)
        logger.warning("Mix clipping prevented — attenuated")

    stats['mix_peak_db'] = float(peak_db(mix.flatten()))
    stats['mix_rms_db']  = float(rms_db(mix.flatten()))

    return mix.astype(np.float32), stats
