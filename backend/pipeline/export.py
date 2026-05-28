"""
Export: WAV 24-bit/48kHz, MP3 320kbps, JSON report.
"""
import json
import logging
import os
import time
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

TARGET_SR = 48000


def export_wav(mix: np.ndarray, sr: int, path: str) -> None:
    """Export 24-bit / 48kHz WAV."""
    # Ensure stereo (2, N) → (N, 2)
    if mix.ndim == 1:
        audio = np.stack([mix, mix], axis=1)
    elif mix.shape[0] == 2:
        audio = mix.T  # (N, 2)
    else:
        audio = mix

    # Clip safety: never exceed ±1.0
    np.clip(audio, -1.0, 1.0, out=audio)

    sf.write(path, audio, sr, subtype='PCM_24')
    logger.info(f"WAV exported: {path} ({os.path.getsize(path) / 1e6:.1f} MB)")


def export_mp3(wav_path: str, mp3_path: str, bitrate: str = '320k') -> bool:
    """Convert WAV to MP3 320kbps using pydub (requires ffmpeg)."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_wav(wav_path)
        audio.export(mp3_path, format='mp3', bitrate=bitrate)
        logger.info(f"MP3 exported: {mp3_path}")
        return True
    except Exception as e:
        logger.warning(f"MP3 export failed: {e}")
        return False


def export_report(report: dict, path: str) -> None:
    """Write JSON analysis/processing report."""
    with open(path, 'w') as f:
        json.dump(report, f, indent=2)
    logger.info(f"Report written: {path}")


def export_all(
    mix: np.ndarray,
    sr: int,
    output_dir: str,
    session_id: str,
    report: dict,
) -> dict:
    """
    Export WAV + MP3 + JSON to output_dir.
    Returns dict with file paths/URLs.
    """
    os.makedirs(output_dir, exist_ok=True)

    wav_path  = os.path.join(output_dir, f"{session_id}_master.wav")
    mp3_path  = os.path.join(output_dir, f"{session_id}_master.mp3")
    json_path = os.path.join(output_dir, f"{session_id}_report.json")

    export_wav(mix, sr, wav_path)
    mp3_ok = export_mp3(wav_path, mp3_path)
    export_report(report, json_path)

    return {
        'wav_path':  wav_path,
        'mp3_path':  mp3_path if mp3_ok else None,
        'json_path': json_path,
        'wav_url':   f"/api/files/{session_id}_master.wav",
        'mp3_url':   f"/api/files/{session_id}_master.mp3" if mp3_ok else None,
    }
