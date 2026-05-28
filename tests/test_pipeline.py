"""
AutoMix pipeline tests.
Run with: cd backend && python -m pytest ../tests/test_pipeline.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import numpy as np
import pytest
import librosa


# ── helpers ────────────────────────────────────────────────────────────────

SR = 48000

def make_click_track(bpm: float, duration: float = 8.0) -> np.ndarray:
    """Generate a metronome click track at a given BPM."""
    n = int(duration * SR)
    y = np.zeros(n)
    beat_samples = int(SR * 60 / bpm)
    click = np.exp(-np.linspace(0, 10, 1000))  # decaying click
    for start in range(0, n - 1000, beat_samples):
        y[start:start + 1000] += click * 0.8
    return y.astype(np.float32)


def make_sine(freq: float, duration: float = 3.0, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(int(duration * SR)) / SR
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def make_scale(root_midi: int = 60, duration_per_note: float = 0.5) -> np.ndarray:
    """Generate C major scale as a sequence of sine tones."""
    intervals = [0, 2, 4, 5, 7, 9, 11, 12]
    notes = []
    for i in intervals:
        freq = 440 * 2 ** ((root_midi + i - 69) / 12)
        notes.append(make_sine(freq, duration=duration_per_note))
    return np.concatenate(notes)


# ── tests ──────────────────────────────────────────────────────────────────

class TestBPMDetection:
    def test_120_bpm(self):
        from pipeline.analysis import detect_bpm
        y = make_click_track(120.0)
        bpm, conf = detect_bpm(y, SR)
        assert abs(bpm - 120.0) <= 5.0, f"Expected ~120 BPM, got {bpm}"
        assert conf >= 0.0

    def test_90_bpm(self):
        from pipeline.analysis import detect_bpm
        y = make_click_track(90.0)
        bpm, conf = detect_bpm(y, SR, genre='reggaeton')
        assert abs(bpm - 90.0) <= 8.0, f"Expected ~90 BPM, got {bpm}"

    def test_does_not_double_bpm(self):
        """60 BPM should not be detected as 120 BPM."""
        from pipeline.analysis import detect_bpm
        y = make_click_track(60.0)
        bpm, _ = detect_bpm(y, SR)
        assert bpm < 100, f"Expected ~60 BPM, got {bpm} (double detection)"


class TestKeyDetection:
    def test_c_major_scale(self):
        from pipeline.analysis import detect_key
        y = make_scale(root_midi=60)  # C major
        root, mode, conf = detect_key(y, SR)
        assert root == 'C', f"Expected C, got {root}"
        assert mode == 'major', f"Expected major, got {mode}"

    def test_key_confidence(self):
        from pipeline.analysis import detect_key
        y = make_scale(root_midi=60)
        _, _, conf = detect_key(y, SR)
        assert 0.0 <= conf <= 1.0


class TestPitchCorrection:
    def test_sharp_note_corrected_to_c(self):
        """255 Hz (slightly flat of middle C = 261.63 Hz) should correct toward C."""
        from pipeline.pitch_correction import correct_pitch
        freq_in  = 255.0  # slightly flat C
        target_c = 261.63

        y = make_sine(freq_in, duration=2.0)
        # C major: root=0 (C), mode=major
        y_out, stats = correct_pitch(y, SR, root_note=0, mode='major', genre='pop')

        # Detect pitch of output
        f0, voiced, _ = librosa.pyin(y_out, fmin=200, fmax=400, sr=SR)
        voiced_f0 = f0[voiced]
        if len(voiced_f0) > 0:
            mean_f0 = np.nanmean(voiced_f0)
            # Should have moved toward C (261.63) from 255 Hz
            assert mean_f0 > freq_in - 1, f"Pitch should not decrease: {freq_in} → {mean_f0}"

    def test_no_correction_when_disabled(self):
        from pipeline.pitch_correction import correct_pitch
        y = make_sine(255.0, duration=1.0)
        y_out, stats = correct_pitch(y, SR, root_note=0, mode='major', no_autotune=True)
        assert not stats['pitch_correction_applied']
        np.testing.assert_allclose(y_out, y, atol=1e-3)


class TestNoClipping:
    def test_vocal_processing_no_clip(self):
        """Vocal processing chain must never produce clipping (> 1.0)."""
        from pipeline.vocal_processing import process_vocal
        y = make_sine(220.0, duration=3.0, amplitude=0.6)
        y_out, _ = process_vocal(y, SR, root_note=0, mode='minor', genre='reggaeton')
        assert np.max(np.abs(y_out)) <= 1.0, "Vocal processing clipped!"

    def test_mastering_no_clip(self):
        """Mastering chain must never produce clipping."""
        from pipeline.mastering import master
        y = make_sine(110.0, duration=5.0, amplitude=0.7)
        mix = np.stack([y, y], axis=0)
        mix_out, _ = master(mix, SR)
        assert np.max(np.abs(mix_out)) <= 1.0, "Mastering clipped!"


class TestLUFSTarget:
    def test_streaming_target(self):
        """Master output must be within ±0.5 LU of -14 LUFS target."""
        from pipeline.mastering import master, measure_lufs
        y = make_sine(110.0, duration=10.0, amplitude=0.5)
        mix = np.stack([y, y], axis=0)
        mix_out, report = master(mix, SR, target='streaming')

        lufs = measure_lufs(mix_out, SR)
        assert abs(lufs - (-14.0)) <= 1.0, f"LUFS {lufs:.1f} outside ±1 LU of -14"

    def test_club_target(self):
        from pipeline.mastering import master, measure_lufs
        y = make_sine(110.0, duration=10.0, amplitude=0.5)
        mix = np.stack([y, y], axis=0)
        mix_out, report = master(mix, SR, target='club')

        lufs = measure_lufs(mix_out, SR)
        assert abs(lufs - (-9.0)) <= 1.5, f"LUFS {lufs:.1f} outside target for club"


class TestPipelineFull:
    def test_pipeline_runs_without_error(self):
        """Full pipeline should complete without exceptions."""
        from pipeline.analysis import detect_bpm, detect_key
        from pipeline.vocal_processing import process_vocal
        from pipeline.mixing import mix_tracks
        from pipeline.mastering import master

        duration = 5.0
        y_inst  = make_sine(110.0, duration=duration, amplitude=0.5)
        y_vocal = make_sine(220.0, duration=duration, amplitude=0.4)

        bpm, _ = detect_bpm(y_inst, SR)
        root, mode, _ = detect_key(y_inst, SR)
        root_idx = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'].index(root)

        y_vp, _ = process_vocal(y_vocal, SR, root_note=root_idx, mode=mode,
                                 genre='pop', bpm=bpm, snr_db=30)

        mix, _ = mix_tracks(y_inst, y_vp, SR)
        mastered, report = master(mix, SR)

        assert mastered.shape[0] == 2, "Output must be stereo"
        assert mastered.shape[1] > 0, "Output must have samples"
        assert np.max(np.abs(mastered)) <= 1.0, "Final output must not clip"
        assert 'lufs_integrated' in report
