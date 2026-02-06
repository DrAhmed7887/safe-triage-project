#!/usr/bin/env python3
"""Performance benchmark for SAFE-Triage API."""
import os
import time
import statistics
import requests

URL = os.getenv("BENCHMARK_URL", "https://safe-triage-eciux5h4aq-uc.a.run.app/ai-triage")
REQUESTS = int(os.getenv("BENCHMARK_REQUESTS", "50"))

TEST_CASE = {
    "patient_id": "BENCHMARK",
    "age": 45,
    "gender": "female",
    "chief_complaint_text": "chest pain",
    "vitals": {"hr": 90, "sbp": 130, "dbp": 85, "rr": 18, "temp": 37, "spo2": 97},
    "consciousness": "A",
}


def main():
    times = []
    failures = 0
    for i in range(REQUESTS):
        start = time.time()
        try:
            resp = requests.post(URL, json=TEST_CASE, timeout=10)
            resp.raise_for_status()
            elapsed = time.time() - start
            times.append(elapsed)
        except Exception:
            failures += 1
        if i % 10 == 0:
            print(f"Request {i} complete")

    if not times:
        print("No successful requests.")
        return

    p95 = statistics.quantiles(times, n=20)[18]
    p99 = statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times)

    print("\nPerformance Benchmark")
    print(f"Requests: {REQUESTS} | Success: {len(times)} | Failures: {failures}")
    print(f"Mean: {statistics.mean(times):.3f}s")
    print(f"Median: {statistics.median(times):.3f}s")
    print(f"Std Dev: {statistics.stdev(times):.3f}s" if len(times) > 1 else "Std Dev: 0")
    print(f"Min: {min(times):.3f}s")
    print(f"Max: {max(times):.3f}s")
    print(f"P95: {p95:.3f}s")
    print(f"P99: {p99:.3f}s")


if __name__ == "__main__":
    main()
