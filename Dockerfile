# ---- BugBoard Dockerfile ----
# Multi-stage is overkill for a pure-Python app; single stage keeps it simple.

FROM python:3.11-slim

# Metadata
LABEL maintainer="Sarthak Sapkal <PRN: 20240801015>"
LABEL description="BugBoard — Cloud-native issue tracker for CSA3004"

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user for security
RUN groupadd -r bugboard && useradd -r -g bugboard -d /app -s /sbin/nologin bugboard

# Set working directory
WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for SQLite database and give ownership to non-root user
RUN mkdir -p /app/data && chown -R bugboard:bugboard /app

# Switch to non-root user
USER bugboard

# Expose the application port
EXPOSE 5000

# Health check — Kubernetes probes also hit /health but this helps Docker too
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Run with Gunicorn (production WSGI server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
