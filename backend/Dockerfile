FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./*.py ./
COPY logic/ ./logic/
COPY jobs/ ./jobs/
COPY fonts/ ./fonts/
COPY egybert_model/ ./egybert_model/

# CRITICAL: Include SNOMED database
COPY umls_cache.db .
RUN chmod 644 umls_cache.db

# Build-time embedding generation (offline runtime).
RUN if [ -f ./egybert_model/config.json ] && { [ -f ./egybert_model/model.safetensors ] || [ -f ./egybert_model/pytorch_model.bin ]; }; then \
      python precompute_embeddings.py \
        --model-dir ./egybert_model \
        --embeddings-out ./keyword_embeddings.pt \
        --index-out ./keyword_index.json; \
    else \
      echo "EgyBERT model weights missing; semantic offline matcher disabled."; \
    fi

ENV TRANSFORMERS_OFFLINE=1
ENV HF_HUB_OFFLINE=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
