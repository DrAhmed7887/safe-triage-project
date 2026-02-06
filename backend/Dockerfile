FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./*.py ./
COPY logic/ ./logic/
COPY jobs/ ./jobs/
COPY fonts/ ./fonts/

# CRITICAL: Include SNOMED database
COPY umls_cache.db .
RUN chmod 644 umls_cache.db

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
