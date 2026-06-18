FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by Pillow/pillow-heif
RUN apt-get update && apt-get install -y --no-install-recommends \
    libheif-dev \
    libde265-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "web:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
