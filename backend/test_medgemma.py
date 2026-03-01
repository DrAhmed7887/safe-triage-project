#!/usr/bin/env python3
"""Test MedGemma 1.5-4B integration end-to-end."""

from __future__ import annotations

import asyncio

from medgemma_batch_qa import MedGemmaBatchQA
from medgemma_client import MedGemmaClient


async def test_medgemma_connection() -> bool:
    print("\n" + "=" * 70)
    print("TEST 1: MedGemma 1.5-4B Connection Test")
    print("=" * 70 + "\n")
    try:
        client = MedGemmaClient()
        ok = client.test_connection()
    except Exception as exc:
        print(f"❌ Connection setup failed: {exc}")
        return False

    if ok:
        print("✅ MedGemma 1.5-4B API is accessible")
    else:
        print("❌ MedGemma 1.5-4B API connection failed")
    return ok


async def test_batch_analysis() -> bool:
    print("\n" + "=" * 70)
    print("TEST 2: Batch Analysis with Real Cases")
    print("=" * 70 + "\n")
    qa = MedGemmaBatchQA()
    results = await qa.run_hourly_review()
    if results.get("status") == "success":
        print("✅ Batch analysis successful")
        print(f"   Cases: {results.get('cases_reviewed', 0)}")
        print(f"   Flagged: {results.get('cases_flagged', 0)}")
        print(f"   Critical: {results.get('critical_flags', 0)}")
        return True
    if results.get("status") == "no_cases":
        print("✅ No recent cases to review (service working)")
        return True
    print(f"❌ Batch analysis failed: {results.get('error')}")
    return False


async def test_alert_system() -> bool:
    print("\n" + "=" * 70)
    print("TEST 3: Alert System Test")
    print("=" * 70 + "\n")
    from medgemma_alerts import send_disaster_alert

    test_case = {
        "case_id": "TEST-001",
        "concerning_pattern": "Silent MI Risk",
        "confidence": 0.95,
        "reasoning": "Test alert only",
        "recommended_action": "ECG + Troponin",
        "esi_recommendation": 2,
    }
    try:
        result = await send_disaster_alert(test_case)
        print(f"Alert result: {result}")
        if result.get("push") or result.get("email") or result.get("queued"):
            print("✅ Alert dispatch pathway working")
            return True
        print("❌ Alert dispatch returned no channels")
        return False
    except Exception as exc:
        print(f"❌ Alert failed: {exc}")
        return False


async def run_all_tests() -> int:
    print("\n" + "=" * 70)
    print("MedGemma 1.5-4B Complete Test Suite")
    print("=" * 70)

    results = []
    t1 = await test_medgemma_connection()
    results.append(t1)

    if t1:
        results.append(await test_batch_analysis())

    results.append(await test_alert_system())

    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: {sum(results)}/{len(results)} passed")
    print("=" * 70 + "\n")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run_all_tests()))
