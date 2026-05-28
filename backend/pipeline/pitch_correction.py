"""
Pitch correction (autotune) module.
Uses CREPE for pitch detection + pyrubberband for PSOLA pitch shifting.
"""
import logging
import numpy as np
import librosa
import soundfile as sf
from scipy.signal import medfilt
from .analysis import build_scale_notes, NOTE_NAMES

logger = logging.getLogger(__name__)

GENRE_PARAMS = {
    'reggaeton': dict(attack_ms=20,  strength=0.85, humanize=0.15, allow_blue_notes=True),
    'trap':      dict(attack_ms=40,  strength=0.90, humanize=0.10, allow_blue_notes=True),
    'drill':     dict(attack_ms=40,  strength=0.90, humanize=0.10, allow_blue_notes=True),
    'rnb':       dict(attack_ms=80,  strength=0.70, humanize=0.30, allow_blue_notes=True),
    'pop':       dict(attack_ms=50,  strength=0.80, humanize=0.20, allow_blue_notes=False),
    'rock':      dict(attack_ms=60,  strength=0.75, humanize=0.25, allow_blue_notes=False),
    'afro':      dict(attack_ms=60,  strength=0.78, humanize=0.22, allow_blue_notes=True),
    'house':     dict(attack_ms=50,  strength=0.80, humanize=0.20, allow_blue_notes=False),
}

CORRECTION_THRESHOLD_CENTS = 25.0   # only correct if error > 25 cents
SLIDE_THRESHOLD_CENTS      = 200.0  # if pitch moves > 200 cents in < 100ms, it's a slide
SLIDE_WINDOW_FRAMES        = 6      # ~96ms at 16ms/frame


def hz_to_midi(freq_hz: np.ndarray) -> np.ndarray:
    """Convert Hz to MIDI note number (float)."""
    return 12 * np.log2(np.maximum(freq_hz, 1e-6) / 440.0) + 69


def midi_to_hz(midi: float) -> float:
    return 440.0 * (2 ** ((midi - 69) / 12))


def cents_to_ratio(cents: float) -> float:
    return 2 ** (cents / 1200.0)


def find_nearest_scale_note(midi_pitch: float, scale_notes: list[int]) -> float:
    """Return nearest scale MIDI note (across octaves) to midi_pitch."""
    best = None
    best_dist = float('inf')
    octave_base = int(midi_pitch) // 12
    for octave in range(octave_base - 1, octave_base + 2):
        for pc in scale_notes:
            candidate = octave * 12 + pc
            dist = abs(midi_pitch - candidate)
            if dist < best_dist:
                best_dist = dist
                best = float(candidate)
    return best


def detect_slides(pitch_midi: np.ndarray, confidence: np.ndarray) -> np.ndarray:
    """
    Detect ornamental slides: rapid pitch movement > SLIDE_THRESHOLD_CENTS
    in a short window. Returns boolean mask (True = slide, don't correct).
    """
    is_slide = np.zeros(len(pitch_midi), dtype=bool)
    for i in range(SLIDE_WINDOW_FRAMES, len(pitch_midi)):
        # check only voiced frames
        if confidence[i] < 0.5:
            continue
        window = pitch_midi[max(0, i - SLIDE_WINDOW_FRAMES):i + 1]
        voiced_in_window = window[confidence[max(0, i - SLIDE_WINDOW_FRAMES):i + 1] > 0.5]
        if len(voiced_in_window) >= 2:
            range_cents = (voiced_in_window.max() - voiced_in_window.min()) * 100
            if range_cents > SLIDE_THRESHOLD_CENTS:
                is_slide[max(0, i - SLIDE_WINDOW_FRAMES):i + 1] = True
    return is_slide


def smooth_correction(correction_cents: np.ndarray, attack_ms: float,
                      hop_length: int, sr: int) -> np.ndarray:
    """Apply smoothing to the correction curve to simulate attack time."""
    attack_frames = max(1, int(attack_ms * sr / (hop_length * 1000)))
    kernel = np.ones(attack_frames) / attack_frames
    return np.convolve(correction_cents, kernel, mode='same')


def correct_pitch(
    y: np.ndarray,
    sr: int,
    root_note: int,
    mode: str,
    genre: str = 'pop',
    no_autotune: bool = False,
) -> tuple[np.ndarray, dict]:
    """
    Apply pitch correction to vocal audio.

    Returns:
        corrected audio (np.ndarray, same length as input)
        stats dict
    """
    if no_autotune:
        return y, {'pitch_correction_applied': False, 'pitch_notes_corrected': 0}

    params = GENRE_PARAMS.get(genre, GENRE_PARAMS['pop'])
    scale_notes = build_scale_notes(root_note, mode)

    # CREPE requires 16kHz mono
    y_16k = librosa.resample(y, orig_sr=sr, target_sr=16000) if sr != 16000 else y

    try:
        import crepe
        hop_length_16k = 256
        time, frequency, confidence, _ = crepe.predict(
            y_16k, 16000,
            model_capacity='full',
            step_size=int(hop_length_16k / 16000 * 1000),  # ms
            viterbi=True,
            verbose=0,
        )
        logger.info(f"CREPE pitch detection: {len(frequency)} frames")
    except ImportError:
        logger.warning("CREPE not available — using librosa pyin fallback")
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'),
            sr=sr, hop_length=512,
        )
        frequency = np.where(voiced_flag, f0, 0.0)
        confidence = voiced_probs
        time = np.arange(len(frequency)) * 512 / sr

    # Convert to MIDI
    voiced_mask = (confidence >= 0.6) & (frequency > 0)
    pitch_midi = np.zeros(len(frequency))
    pitch_midi[voiced_mask] = hz_to_midi(frequency[voiced_mask])

    # Detect slides (protect from correction)
    is_slide = detect_slides(pitch_midi, confidence)

    # Compute per-frame correction in cents
    correction_cents = np.zeros(len(frequency))
    frames_corrected = 0

    for i in range(len(frequency)):
        if not voiced_mask[i] or is_slide[i]:
            continue
        midi_p = pitch_midi[i]
        target_midi = find_nearest_scale_note(midi_p, scale_notes)
        if target_midi is None:
            continue
        error_cents = (target_midi - midi_p) * 100.0
        if abs(error_cents) < CORRECTION_THRESHOLD_CENTS:
            continue
        # Apply humanize: don't correct 100%
        correction_cents[i] = error_cents * params['strength'] * (1.0 - params['humanize'] * 0.5)
        frames_corrected += 1

    # Smooth correction curve to simulate attack time
    correction_cents = smooth_correction(
        correction_cents, params['attack_ms'],
        hop_length=512, sr=sr
    )

    # Apply pitch shift frame by frame using pyrubberband
    y_corrected = _apply_pitch_shift_frames(y, sr, correction_cents, time)

    stats = {
        'pitch_correction_applied': True,
        'pitch_notes_corrected': frames_corrected,
    }
    logger.info(f"Pitch correction: {frames_corrected} frames corrected")
    return y_corrected, stats


def _apply_pitch_shift_frames(
    y: np.ndarray, sr: int,
    correction_cents: np.ndarray,
    time_axis: np.ndarray,
) -> np.ndarray:
    """
    Apply variable pitch shift using pyrubberband (PSOLA, preserves formants).
    Falls back to librosa pitch_shift if rubberband not available.
    """
    try:
        import pyrubberband as pyrb

        # Build per-sample pitch ratio array
        n_samples = len(y)
        sample_times = np.arange(n_samples) / sr

        # Interpolate correction_cents to sample-level
        if len(time_axis) > 1:
            cents_per_sample = np.interp(sample_times, time_axis, correction_cents)
        else:
            cents_per_sample = np.zeros(n_samples)

        # pyrubberband pitch_shift works on segments — apply in chunks with crossfade
        CHUNK_SAMPLES = sr // 2  # 0.5s chunks
        overlap = sr // 20        # 50ms overlap for crossfade
        output = np.zeros(n_samples)
        fade_in  = np.linspace(0, 1, overlap)
        fade_out = np.linspace(1, 0, overlap)

        pos = 0
        while pos < n_samples:
            end = min(pos + CHUNK_SAMPLES, n_samples)
            chunk = y[pos:end]
            chunk_cents = np.mean(cents_per_sample[pos:end])
            n_semitones = chunk_cents / 100.0

            if abs(n_semitones) > 0.1:
                chunk_shifted = pyrb.pitch_shift(
                    chunk, sr, n_semitones,
                    rbargs={'--formant': '', '--fine': ''},
                )
                # Ensure same length
                if len(chunk_shifted) > len(chunk):
                    chunk_shifted = chunk_shifted[:len(chunk)]
                elif len(chunk_shifted) < len(chunk):
                    chunk_shifted = np.pad(chunk_shifted, (0, len(chunk) - len(chunk_shifted)))
            else:
                chunk_shifted = chunk

            # Crossfade with previous
            if pos > 0 and len(chunk_shifted) >= overlap:
                chunk_shifted[:overlap] *= fade_in
                output[pos:pos + overlap] *= fade_out
                output[pos:pos + overlap] += chunk_shifted[:overlap]
                output[pos + overlap:end] = chunk_shifted[overlap:]
            else:
                output[pos:end] = chunk_shifted

            pos = end

        return output.astype(np.float32)

    except ImportError:
        logger.warning("pyrubberband not available — using librosa pitch_shift (no formant preservation)")
        # Apply a single global shift (less precise but functional)
        mean_cents = float(np.mean(correction_cents[correction_cents != 0])) if np.any(correction_cents != 0) else 0
        if abs(mean_cents) < 0.5:
            return y
        return librosa.effects.pitch_shift(y, sr=sr, n_steps=mean_cents / 100.0)
