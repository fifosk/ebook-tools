# ebook-tools Backend
# Python 3.10 + FastAPI + FFmpeg + espeak-ng
#
# Build:  docker build -t ebook-tools-backend -f docker/backend/Dockerfile .
# Run:    docker run -d -p 8000:8000 \
#           -v ~/ebook-data/storage:/app/storage \
#           -v ~/ebook-data/config/users:/app/config/users \
#           --env-file ~/ebook-data/.env.docker \
#           ebook-tools-backend

FROM python:3.10-slim-bookworm

# ── System dependencies ──────────────────────────────────────────────
# ffmpeg:           required by pydub for audio format conversion
# espeak-ng:        required by piper-tts for phoneme generation
# libespeak-ng-dev: headers piper needs at build time
# gcc + python3-dev + libc6-dev: C extensions (psutil, bcrypt, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        espeak-ng \
        libespeak-ng-dev \
        gcc \
        python3-dev \
        libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user ────────────────────────────────────────────────────
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -s /bin/bash appuser

WORKDIR /app

# ── Python dependencies (cached layer) ──────────────────────────────
# Copy pyproject.toml and create a minimal stub package so pip can
# resolve the editable install and cache all dependencies.  The real
# source is copied afterwards.
COPY pyproject.toml ./
RUN mkdir -p modules/cli modules/webapi && \
    touch modules/__init__.py modules/cli/__init__.py modules/webapi/__init__.py && \
    echo 'def main(): pass' > modules/cli/main.py && \
    echo 'def main(): pass' > modules/webapi/__main__.py && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e . && \
    rm -rf modules/

# ── Application source ──────────────────────────────────────────────
# Copy modules/ first and re-install editable (deps already cached).
# conf/ and config/ are copied AFTER pip install to avoid setuptools
# flat-layout detection (they're data dirs, not Python packages).
COPY modules/ modules/
RUN pip install --no-cache-dir -e .

COPY conf/ conf/
COPY config/ config/
COPY scripts/ scripts/

# ── Volume mount points ─────────────────────────────────────────────
RUN mkdir -p \
        storage/ebooks storage/covers storage/jobs storage/exports \
        storage/cache storage/library storage/reading_beds \
        storage/bookmarks storage/resume \
        output tmp log && \
    chown -R appuser:appuser /app

# ── Runtime configuration ────────────────────────────────────────────
# EBOOK_API_STATIC_ROOT=""   → disable built-in SPA serving (frontend is separate)
# EBOOK_TTS_BACKEND="gtts"   → macOS 'say' is unavailable in Linux containers
# EBOOK_USE_RAMDISK="false"  → use --tmpfs mount instead
ENV EBOOK_API_STATIC_ROOT="" \
    EBOOK_TTS_BACKEND="gtts" \
    EBOOK_USE_RAMDISK="false" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/_health')" || exit 1

CMD ["python", "-m", "modules.webapi", "--host", "0.0.0.0", "--port", "8000"]
