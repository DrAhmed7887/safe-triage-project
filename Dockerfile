# SAFE-Triage Backend - Google Cloud Run
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure backend directory exists and copy UMLS cache explicitly.
# This makes deploy fail fast if the cache DB is missing from source upload.
RUN mkdir -p /app/backend
COPY backend/umls_cache.db ./backend/umls_cache.db

# Copy backend code
COPY backend/ ./backend/

# Offline semantic matcher assets (used when pre-bundled in source).
RUN if [ -f /app/backend/egybert_model/config.json ] && { [ -f /app/backend/egybert_model/model.safetensors ] || [ -f /app/backend/egybert_model/pytorch_model.bin ]; }; then \
      python /app/backend/precompute_embeddings.py \
        --model-dir /app/backend/egybert_model \
        --embeddings-out /app/backend/keyword_embeddings.pt \
        --index-out /app/backend/keyword_index.json; \
    else \
      echo "EgyBERT model weights not found at build time; semantic offline matcher will be unavailable."; \
    fi

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app/backend:${PYTHONPATH}"
ENV TRANSFORMERS_OFFLINE=1
ENV HF_HUB_OFFLINE=1
ENV PORT=8080

# Expose port (Cloud Run uses 8080 by default)
EXPOSE 8080

# Run the application
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port $PORT"]
