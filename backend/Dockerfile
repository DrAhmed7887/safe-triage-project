FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./*.py ./
COPY logic/ ./logic/
COPY jobs/ ./jobs/
COPY fonts/ ./fonts/
# EgyBERT offline matcher is optional — model weights not shipped in production.
# If egybert_model/ has weights, copy them; otherwise skip silently.
COPY egybert_model/ ./egybert_model/

# CRITICAL: Include SNOMED database
COPY umls_cache.db .
RUN chmod 644 umls_cache.db

# EgyBERT precomputation requires PyTorch (not in production requirements).
# The runtime lazy-imports egybert_matcher.py only in offline mode and
# gracefully falls back when torch is missing.
ENV TRANSFORMERS_OFFLINE=1
ENV HF_HUB_OFFLINE=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
