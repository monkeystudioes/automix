FROM python:3.11-slim

# System deps: ffmpeg for audio format conversion + rubberband for pitch shift
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    librubberband-dev \
    rubberband-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional heavy deps (comment out if not needed to speed up build)
# RUN pip install --no-cache-dir crepe torch torchaudio deepfilternet

COPY . .

RUN mkdir -p /app/uploads /app/outputs

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
