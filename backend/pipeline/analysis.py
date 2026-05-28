"""
BPM and key detection with multi-method fallback.
"""
import logging
import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger(__name__)

GENRE_KEY_PRIORS = {
    # genres where minor keys are vastly more common
    'reggaeton': 'minor',
    'trap':      'minor',
    'drill':     'minor',
    'rnb':       'minor',
    'afro':      'minor',
}

SCALE_PROFILES = {
    'major': np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]),
    'minor': np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]),
}

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def detect_bpm(y: np.ndarray, sr: int, genre: str = None) -> tuple[float, float]:
    """
    Multi-method BPM detection. Returns (bpm, confidence).
    Strategy:
    1. librosa onset_envelope + beat.tempo with prior
    2. tempogram voting
    3. harmonic correction (half/double check)
    """
    methods = []

    # Method 1: onset-based with Gaussian prior around expected genre BPM
    genre_priors = {
        'reggaeton': 92, 'trap': 150, 'drill': 145, 'rnb': 75,
        'pop': 115, 'rock': 120, 'afro': 108, 'house': 124,
    }
    prior_mean = genre_priors.get(genre, 120) if genre else None

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)

    # standard tempo estimate
    tempo_std = librosa.feature.rhythm.tempo(onset_envelope=onset_env, sr=sr)
    if hasattr(tempo_std, '__len__'):
        tempo_std = float(tempo_std[0])
    else:
        tempo_std = float(tempo_std)
    methods.append(tempo_std)

    # with prior if genre known
    if prior_mean:
        try:
            ac = librosa.autocorrelate(onset_env, max_size=sr // 2)
            freqs = librosa.tempo_frequencies(len(ac), sr=sr)
            # weight with gaussian prior
            prior = np.exp(-0.5 * ((freqs - prior_mean) / 20) ** 2)
            weighted = ac * prior
            if weighted.max() > 0:
                best_freq = freqs[np.argmax(weighted)]
                methods.append(float(best_freq))
        except Exception as e:
            logger.debug(f"Prior-weighted tempo failed: {e}")

    # Method 2: tempogram
    try:
        tgram = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr)
        tempo_tgram = librosa.feature.rhythm.tempo(tgram=tgram, sr=sr)
        if hasattr(tempo_tgram, '__len__'):
            tempo_tgram = float(tempo_tgram[0])
        methods.append(float(tempo_tgram))
    except Exception as e:
        logger.debug(f"Tempogram tempo failed: {e}")

    # Vote: most common value within ±5 BPM tolerance
    bpm_raw = float(np.median(methods))

    # Harmonic correction: check if 2x or 0.5x is more likely
    bpm = _resolve_harmonic(bpm_raw, genre)

    confidence = 1.0 - (np.std(methods) / (bpm + 1e-6))
    confidence = float(np.clip(confidence, 0.0, 1.0))

    logger.info(f"BPM detection: raw={bpm_raw:.1f}, corrected={bpm:.1f}, confidence={confidence:.2f}, methods={methods}")
    return round(bpm, 1), confidence


def _resolve_harmonic(bpm: float, genre: str = None) -> float:
    """Check half/double BPM and pick the one that fits genre range."""
    genre_ranges = {
        'reggaeton': (80, 100), 'trap': (130, 165), 'drill': (130, 155),
        'rnb': (60, 95), 'pop': (100, 135), 'rock': (95, 145),
        'afro': (95, 118), 'house': (118, 132),
    }
    if genre and genre in genre_ranges:
        lo, hi = genre_ranges[genre]
        candidates = [bpm, bpm * 2, bpm / 2]
        for c in candidates:
            if lo <= c <= hi:
                return round(c, 1)
    # generic: keep in [60, 200] range
    while bpm < 60:
        bpm *= 2
    while bpm > 200:
        bpm /= 2
    return round(bpm, 1)


def detect_key(y: np.ndarray, sr: int, genre: str = None) -> tuple[str, str, float]:
    """
    Key detection via chromagram + Krumhansl-Schmuckler profiles.
    Returns (note, mode, confidence).
    """
    # Harmonic-percussive separation to get cleaner chromagram
    y_harm, _ = librosa.effects.hpss(y)

    chroma = librosa.feature.chroma_cqt(y=y_harm, sr=sr, bins_per_octave=36)
    chroma_mean = chroma.mean(axis=1)  # shape (12,)

    best_corr = -np.inf
    best_note = 0
    best_mode = 'major'

    for mode, profile in SCALE_PROFILES.items():
        for shift in range(12):
            rotated = np.roll(profile, shift)
            corr = np.corrcoef(chroma_mean, rotated)[0, 1]
            if corr > best_corr:
                best_corr = corr
                best_note = shift
                best_mode = mode

    # Apply genre prior to disambiguate major/minor
    if genre and genre in GENRE_KEY_PRIORS:
        preferred_mode = GENRE_KEY_PRIORS[genre]
        # re-run forcing preferred mode
        best_corr_genre = -np.inf
        best_note_genre = 0
        profile = SCALE_PROFILES[preferred_mode]
        for shift in range(12):
            rotated = np.roll(profile, shift)
            corr = np.corrcoef(chroma_mean, rotated)[0, 1]
            if corr > best_corr_genre:
                best_corr_genre = corr
                best_note_genre = shift
        # Use genre-biased result if it's within 0.05 correlation of best
        if best_corr_genre >= best_corr - 0.05:
            best_note = best_note_genre
            best_mode = preferred_mode
            best_corr = best_corr_genre

    note_name = NOTE_NAMES[best_note]
    confidence = float(np.clip((best_corr + 1) / 2, 0.0, 1.0))

    key_str = f"{note_name} {'major' if best_mode == 'major' else 'minor'}"
    logger.info(f"Key detection: {key_str}, confidence={confidence:.2f}")
    return note_name, best_mode, confidence


def build_scale_notes(root_note: int, mode: str) -> list[int]:
    """
    Build list of MIDI semitone offsets for a given key.
    root_note: 0=C, 1=C#, ...11=B
    Returns sorted list of semitones (0-11) in the scale.
    """
    major_intervals = [0, 2, 4, 5, 7, 9, 11]
    minor_intervals = [0, 2, 3, 5, 7, 8, 10]
    # Blue notes for urban genres
    blue_intervals  = [0, 2, 3, 4, 5, 7, 9, 10]  # minor pentatonic + chromatic passing

    intervals = major_intervals if mode == 'major' else minor_intervals
    scale = [(root_note + i) % 12 for i in intervals]
    return sorted(set(scale))


def estimate_snr(y: np.ndarray, sr: int) -> float:
    """Estimate SNR by comparing first 0.5s silence to signal body."""
    n_silent = int(0.5 * sr)
    if len(y) < n_silent * 3:
        return 30.0  # assume clean for very short clips

    noise_power = np.mean(y[:n_silent] ** 2) + 1e-12
    signal_power = np.mean(y[n_silent:] ** 2) + 1e-12

    if signal_power <= noise_power:
        return 6.0
    snr_db = 10 * np.log10(signal_power / noise_power)
    return float(np.clip(snr_db, 0, 80))


def analyze_file(path: str, genre: str = None) -> dict:
    """Full analysis of an audio file. Returns dict with all metadata."""
    y, sr = librosa.load(path, sr=None, mono=True)

    bpm, bpm_conf = detect_bpm(y, sr, genre)
    root, mode, key_conf = detect_key(y, sr, genre)
    snr = estimate_snr(y, sr)
    duration = len(y) / sr

    return {
        'bpm': bpm,
        'bpm_confidence': bpm_conf,
        'key': f"{root} {mode}",
        'key_root': root,
        'key_mode': mode,
        'key_confidence': key_conf,
        'duration': duration,
        'sample_rate': sr,
        'snr_db': snr,
    }
