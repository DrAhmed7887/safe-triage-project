"""
MedGemma Hourly Job
Entrypoint used by Cloud Scheduler and manual trigger endpoint.
"""

from __future__ import annotations

import asyncio
from typing import Dict

from medgemma_alerts import send_disaster_alert, send_hourly_report
from medgemma_batch_qa import MedGemmaBatchQA


async def run_hourly_job() -> Dict:
    qa_agent = MedGemmaBatchQA()
    results = await qa_agent.run_hourly_review()

    if results.get("status") == "success":
        for case in results.get("critical_cases", []):
            await send_disaster_alert(case)
        await send_hourly_report(results)
        return results

    return results


def main() -> Dict:
    return asyncio.run(run_hourly_job())


if __name__ == "__main__":
    print(main())

