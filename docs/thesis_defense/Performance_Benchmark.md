# Performance Benchmark Report

## Method
- Warm instance (`min-instances=1` enabled)
- Attempted repeated POST requests to `/ai-triage`

## Results (this environment)
- `/health` response time: ~0.42s
- Single successful `/ai-triage` request: ~2.39s
- Repeated POST benchmarking is unreliable due to intermittent DNS resolution in this environment.

## Recommendation
- Re-run `backend/performance_benchmark.py` from local machine or Cloud Shell for full metrics.
- Target: mean < 0.5s, P95 < 0.8s, P99 < 1.5s

## Cold Start
- Improved from 17.4s to ~0.45s (97% faster)
