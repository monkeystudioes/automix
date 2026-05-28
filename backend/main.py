"""
AutoMix FastAPI backend.
"""
import logging
import os
import random
import string
import time
import uuid
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipeline.analysis import analyze_file
from worker import celery_app, process_task

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)s %(levelname)s — %(message)s')
logger = logging.getLogger(__name__)

UPLOADS_DIR = os.environ.get('UPLOADS_DIR', '/app/uploads')
OUTPUTS_DIR = os.environ.get('OUTPUTS_DIR', '/app/outputs')
TARGET_SR   = 48000
MAX_FILE_MB = 200

app = FastAPI(title='AutoMix API', version='3.2.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# In-memory session store (use Redis in production for multi-instance)
sessions: dict[str, dict] = {}


def _session_id() -> str:
    letters = random.choices(string.ascii_uppercase, k=3)
    digits  = random.choices(string.digits,  k=2)
    return ''.join(letters) + '-' + ''.join(digits)


def _save_upload(upload: UploadFile, dest_dir: str, file_id: str) -> str:
    """Save uploaded file, returning the path."""
    os.makedirs(dest_dir, exist_ok=True)
    ext = Path(upload.filename).suffix.lower() or '.wav'
    path = os.path.join(dest_dir, f"{file_id}{ext}")
    with open(path, 'wb') as f:
        f.write(upload.file.read())
    return path


def _to_wav_48k(src_path: str) -> str:
    """Convert any audio to WAV 48kHz 24-bit, return new path."""
    dest = src_path.rsplit('.', 1)[0] + '_48k.wav'
    if os.path.exists(dest):
        return dest
    y, sr = librosa.load(src_path, sr=None, mono=True)
    if sr != TARGET_SR:
        y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)
    sf.write(dest, y, TARGET_SR, subtype='PCM_24')
    return dest


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.post('/api/session')
async def create_session():
    sid = _session_id()
    sessions[sid] = {'created': time.time(), 'files': {}}
    logger.info(f"Session created: {sid}")
    return {'session_id': sid}


@app.post('/api/session/{session_id}/upload/{kind}')
async def upload_file(session_id: str, kind: str, file: UploadFile = File(...)):
    """kind = 'instrumental' or 'vocal'"""
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    if kind not in ('instrumental', 'vocal'):
        raise HTTPException(400, 'kind must be instrumental or vocal')

    # Size check
    content = await file.read()
    size_mb = len(content) / 1e6
    if size_mb > MAX_FILE_MB:
        raise HTTPException(413, f'File too large ({size_mb:.1f} MB, max {MAX_FILE_MB} MB)')

    # Reset to start of stream
    file.file.seek(0)

    file_id = f"{session_id}_{kind}_{uuid.uuid4().hex[:8]}"
    dest_dir = os.path.join(UPLOADS_DIR, session_id)
    raw_path = _save_upload(file, dest_dir, file_id)

    # Convert to 48kHz WAV for processing
    wav_path = _to_wav_48k(raw_path)

    # Analyze
    analysis = analyze_file(wav_path)

    sessions[session_id]['files'][kind] = {
        'file_id':  file_id,
        'raw_path': raw_path,
        'wav_path': wav_path,
        **analysis,
    }

    response = {
        'file_id':    file_id,
        'duration':   round(analysis['duration'], 2),
        'sample_rate': TARGET_SR,
        'snr_db':     round(analysis['snr_db'], 1),
    }
    if kind == 'instrumental':
        response.update({
            'bpm': analysis['bpm'],
            'key': analysis['key'],
        })
    else:
        response.update({
            'detected_noise_level': analysis['snr_db'],
            'estimated_quality':    'studio' if analysis['snr_db'] > 25 else 'mobile',
        })

    logger.info(f"[{session_id}] {kind} uploaded: {analysis}")
    return response


class ProcessParams(BaseModel):
    genre:       str   = 'pop'
    presence:    float = 50.0
    bass:        float = 50.0
    stereo:      float = 50.0
    loudness:    float = -14.0
    target:      str   = 'streaming'
    mood:        str   = None
    offset_ms:   float = 0.0
    no_autotune: bool  = False


@app.post('/api/session/{session_id}/process')
async def start_process(session_id: str, params: ProcessParams):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')

    files = sessions[session_id].get('files', {})
    if 'instrumental' not in files or 'vocal' not in files:
        raise HTTPException(400, 'Both instrumental and vocal must be uploaded first')

    job_params = {
        'session_id': session_id,
        'inst_path':  files['instrumental']['wav_path'],
        'vocal_path': files['vocal']['wav_path'],
        **params.model_dump(),
    }

    task = process_task.apply_async(args=[job_params])
    sessions[session_id]['job_id'] = task.id

    logger.info(f"[{session_id}] Process started — job_id={task.id}")
    return {'job_id': task.id}


@app.get('/api/session/{session_id}/job/{job_id}/status')
async def job_status(session_id: str, job_id: str):
    result = celery_app.AsyncResult(job_id)

    if result.state == 'PENDING':
        return {'status': 'queued', 'stage': 'EN COLA', 'progress': 0.0}

    if result.state == 'PROGRESS':
        meta = result.info or {}
        return {
            'status':   'processing',
            'stage':    meta.get('stage', ''),
            'progress': meta.get('progress', 0.0),
        }

    if result.state == 'SUCCESS':
        data = result.result or {}
        if data.get('status') == 'error':
            return {'status': 'error', 'error': data.get('error', 'Unknown error')}
        return {
            'status':   'done',
            'stage':    'EXPORTANDO MASTER',
            'progress': 1.0,
            'result':   {
                'wav_url': data.get('wav_url'),
                'mp3_url': data.get('mp3_url'),
                'report':  data.get('report', {}),
            },
        }

    if result.state == 'FAILURE':
        return {'status': 'error', 'error': str(result.result)}

    return {'status': result.state.lower(), 'stage': '', 'progress': 0.0}


@app.get('/api/session/{session_id}/result')
async def get_result(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, 'Session not found')
    job_id = sessions[session_id].get('job_id')
    if not job_id:
        raise HTTPException(404, 'No job found for session')
    return await job_status(session_id, job_id)


@app.get('/api/files/{filename}')
async def serve_file(filename: str):
    """Serve output files (WAV, MP3, JSON)."""
    # Security: strip path traversal
    filename = Path(filename).name
    session_id = filename.split('_')[0] + '-' + filename.split('_')[1] if '-' in filename else filename.rsplit('_', 2)[0]

    # Try session-specific folder first
    path = os.path.join(OUTPUTS_DIR, session_id, filename)
    if not os.path.exists(path):
        # Flat fallback
        path = os.path.join(OUTPUTS_DIR, filename)

    if not os.path.exists(path):
        raise HTTPException(404, f'File not found: {filename}')

    return FileResponse(path)


# Serve frontend static files (in production / Docker build)
frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
if os.path.isdir(frontend_dir):
    app.mount('/static', StaticFiles(directory=frontend_dir), name='static')

    @app.get('/')
    async def serve_index():
        index = os.path.join(frontend_dir, 'index.html')
        if os.path.exists(index):
            return FileResponse(index)
        raise HTTPException(404, 'Frontend not found')
