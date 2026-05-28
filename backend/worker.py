"""
Celery worker — AutoMix pipeline tasks.
"""
import logging
import os
import time
import numpy as np
import librosa
import soundfile as sf

from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded

from pipeline.analysis import analyze_file, detect_key, detect_bpm, NOTE_NAMES
from pipeline.vocal_processing import process_vocal
from pipeline.mixing import mix_tracks
from pipeline.mastering import master
from pipeline.export import export_all

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)s %(levelname)s — %(message)s')
logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
UPLOADS_DIR = os.environ.get('UPLOADS_DIR', '/app/uploads')
OUTPUTS_DIR = os.environ.get('OUTPUTS_DIR', '/app/outputs')
TARGET_SR = 48000

celery_app = Celery('automix', broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_expires=86400,  # 24h
    task_soft_time_limit=600,
    task_time_limit=660,
)


def load_and_convert(path: str) -> tuple[np.ndarray, int]:
    """Load any audio file and convert to 48kHz mono float32."""
    y, sr = librosa.load(path, sr=None, mono=True)
    if sr != TARGET_SR:
        y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)
    return y.astype(np.float32), TARGET_SR


def update_state(job_id: str, stage: str, progress: float):
    """Update Celery task state with pipeline progress."""
    celery_app.backend.store_result(
        job_id,
        result={'stage': stage, 'progress': progress, 'status': 'processing'},
        state='PROGRESS',
    )


@celery_app.task(bind=True, name='automix.process')
def process_task(self, job_params: dict) -> dict:
    """
    Full AutoMix pipeline task.
    job_params keys:
      session_id, inst_path, vocal_path,
      genre, presence, bass, stereo, loudness, target, mood,
      offset_ms, no_autotune
    """
    job_id     = self.request.id
    session_id = job_params['session_id']
    t_start    = time.time()

    try:
        # ── Stage 1: Load files ────────────────────────────────────────────
        self.update_state(state='PROGRESS',
                          meta={'stage': 'CARGANDO ARCHIVOS', 'progress': 0.05, 'status': 'processing'})

        inst_path  = job_params['inst_path']
        vocal_path = job_params['vocal_path']

        logger.info(f"[{session_id}] Loading instrumental: {inst_path}")
        y_inst, sr = load_and_convert(inst_path)

        logger.info(f"[{session_id}] Loading vocal: {vocal_path}")
        y_vocal, _  = load_and_convert(vocal_path)

        # ── Stage 2: Analysis ──────────────────────────────────────────────
        self.update_state(state='PROGRESS',
                          meta={'stage': 'ANALIZANDO ESPECTRO', 'progress': 0.10, 'status': 'processing'})

        genre = job_params.get('genre', 'pop')

        bpm, bpm_conf = detect_bpm(y_inst, sr, genre)
        root_note_str, mode, key_conf = detect_key(y_inst, sr, genre)
        root_note_idx = NOTE_NAMES.index(root_note_str) if root_note_str in NOTE_NAMES else 0

        # Estimate vocal SNR
        from pipeline.analysis import estimate_snr
        snr = estimate_snr(y_vocal, sr)
        logger.info(f"[{session_id}] BPM={bpm}, Key={root_note_str} {mode}, SNR={snr:.1f}dB")

        # ── Stage 3: Vocal processing ──────────────────────────────────────
        self.update_state(state='PROGRESS',
                          meta={'stage': 'DETECTANDO TRANSITORIOS', 'progress': 0.18, 'status': 'processing'})

        y_vocal_proc, vocal_stats = process_vocal(
            y=y_vocal,
            sr=sr,
            root_note=root_note_idx,
            mode=mode,
            genre=genre,
            presence_param=float(job_params.get('presence', 50)),
            bpm=bpm,
            snr_db=snr,
            no_autotune=bool(job_params.get('no_autotune', False)),
        )

        self.update_state(state='PROGRESS',
                          meta={'stage': 'EQUALIZACIÓN DINÁMICA', 'progress': 0.45, 'status': 'processing'})

        # ── Stage 4: Mixing ────────────────────────────────────────────────
        mix_stereo, mix_stats = mix_tracks(
            inst=y_inst,
            vocal=y_vocal_proc,
            sr=sr,
            offset_ms=float(job_params.get('offset_ms', 0.0)),
            presence_param=float(job_params.get('presence', 50)),
            use_auto_sync=abs(float(job_params.get('offset_ms', 0.0))) < 10,
        )

        self.update_state(state='PROGRESS',
                          meta={'stage': 'COMPRESIÓN MULTIBAND', 'progress': 0.60, 'status': 'processing'})

        # ── Stage 5: Mastering ─────────────────────────────────────────────
        self.update_state(state='PROGRESS',
                          meta={'stage': 'BUS COMPRESSOR', 'progress': 0.72, 'status': 'processing'})

        mastered, master_report = master(
            mix=mix_stereo,
            sr=sr,
            bass_param=float(job_params.get('bass', 50)),
            presence_param=float(job_params.get('presence', 50)),
            stereo_param=float(job_params.get('stereo', 50)),
            loudness_param=float(job_params.get('loudness', -14.0)),
            target=job_params.get('target', 'streaming'),
            genre=genre,
            mood=job_params.get('mood'),
        )

        self.update_state(state='PROGRESS',
                          meta={'stage': 'LIMITER MASTER', 'progress': 0.88, 'status': 'processing'})

        # ── Stage 6: Export ────────────────────────────────────────────────
        self.update_state(state='PROGRESS',
                          meta={'stage': 'EXPORTANDO MASTER', 'progress': 0.95, 'status': 'processing'})

        t_elapsed = time.time() - t_start

        full_report = {
            'bpm':                       bpm,
            'bpm_confidence':            round(bpm_conf, 3),
            'key':                       f"{root_note_str} {mode}",
            'key_confidence':            round(key_conf, 3),
            'pitch_correction_applied':  vocal_stats.get('pitch_correction_applied', False),
            'pitch_notes_corrected':     vocal_stats.get('pitch_notes_corrected', 0),
            'noise_reduction_applied':   vocal_stats.get('noise_reduction_applied', True),
            'snr_before':                round(snr, 1),
            'lufs_integrated':           master_report['lufs_integrated'],
            'true_peak':                 master_report['true_peak'],
            'true_peak_clippings':       master_report['true_peak_clippings'],
            'stereo_correlation':        master_report['stereo_correlation'],
            'crest_factor':              master_report['crest_factor'],
            'dynamic_range':             master_report['dynamic_range'],
            'qa_warnings':               master_report.get('qa_warnings', []),
            'processing_time_seconds':   round(t_elapsed, 1),
        }

        output_dir = os.path.join(OUTPUTS_DIR, session_id)
        file_paths = export_all(mastered, sr, output_dir, session_id, full_report)

        return {
            'status':   'done',
            'stage':    'EXPORTANDO MASTER',
            'progress': 1.0,
            'report':   full_report,
            'wav_url':  file_paths['wav_url'],
            'mp3_url':  file_paths.get('mp3_url'),
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[{session_id}] Task timed out")
        return {'status': 'error', 'error': 'Processing timed out (>10 min)'}
    except Exception as e:
        logger.exception(f"[{session_id}] Pipeline error: {e}")
        return {'status': 'error', 'error': str(e)}
