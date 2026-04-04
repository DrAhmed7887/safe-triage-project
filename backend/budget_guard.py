#!/usr/bin/env python3
"""
Budget Guard — hard stop when GenAI App Builder credit is exhausted.

Checks Vertex AI endpoint spend and auto-undeploys all model endpoints
when the budget threshold is reached. Run hourly via Cloud Scheduler
or cron to enforce the $1,000 hard cap.

Usage:
    python budget_guard.py                    # check + undeploy if over
    python budget_guard.py --dry-run          # check only, don't undeploy
    python budget_guard.py --budget 800       # custom budget cap
    python budget_guard.py --status           # show current endpoint costs

How it works:
    1. Lists all Vertex AI endpoints in the project
    2. For each deployed model, calculates cost = uptime * hourly rate
    3. If total spend >= budget threshold → undeploys ALL endpoints
    4. Logs every action to budget_guard.log for audit trail

Cost rates (us-central1):
    g2-standard-4  + 1x L4:  ~$1.19/hr  (MedGemma 4B)
    g2-standard-24 + 2x L4:  ~$2.98/hr  (Gemma 4 27B)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import aiplatform

# ---- Configuration ----

DEFAULT_BUDGET = float(os.getenv("VERTEX_BUDGET_USD", "950"))  # $50 buffer from $1000
PROJECT_ID = os.getenv("PROJECT_ID", "safe-triage-ai")
REGION = os.getenv("VERTEX_REGION", "us-central1")

# Hourly cost by machine type (us-central1 pricing)
MACHINE_COST_PER_HOUR = {
    "g2-standard-4": 1.19,    # 1x L4 (MedGemma)
    "g2-standard-8": 1.58,
    "g2-standard-12": 1.98,
    "g2-standard-24": 2.98,   # 2x L4 (Gemma 4 default)
    "g2-standard-48": 5.96,   # 4x L4
    "a2-highgpu-1g": 3.67,    # 1x A100 40GB
    "n1-standard-8": 0.38,    # CPU only (no GPU)
}
DEFAULT_HOURLY_RATE = 3.00  # fallback if machine type unknown

SPEND_LOG = Path(__file__).parent / "budget_spend.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BudgetGuard] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent / "budget_guard.log"),
    ],
)
log = logging.getLogger(__name__)


def _load_spend_log() -> dict:
    if SPEND_LOG.exists():
        try:
            return json.loads(SPEND_LOG.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"total_spend_usd": 0.0, "entries": [], "last_check": None}


def _save_spend_log(data: dict) -> None:
    SPEND_LOG.write_text(json.dumps(data, indent=2, default=str))


def list_active_endpoints() -> list[dict]:
    """List all Vertex AI endpoints with deployed models."""
    aiplatform.init(project=PROJECT_ID, location=REGION)
    endpoints = aiplatform.Endpoint.list(project=PROJECT_ID, location=REGION)

    active = []
    for ep in endpoints:
        deployed = ep.gca_resource.deployed_models
        if not deployed:
            continue

        for dm in deployed:
            machine_type = dm.dedicated_resources.machine_spec.machine_type if dm.dedicated_resources else "unknown"
            min_replicas = dm.dedicated_resources.min_replica_count if dm.dedicated_resources else 0
            max_replicas = dm.dedicated_resources.max_replica_count if dm.dedicated_resources else 0
            create_time = ep.create_time

            hourly_rate = MACHINE_COST_PER_HOUR.get(machine_type, DEFAULT_HOURLY_RATE)
            # Scale-to-zero endpoints (min_replicas=0) only cost during active inference
            # Estimate conservatively: if min_replicas=0, assume 10% active time
            uptime_factor = 1.0 if min_replicas > 0 else 0.1

            if create_time:
                hours_alive = (datetime.now(timezone.utc) - create_time).total_seconds() / 3600
            else:
                hours_alive = 0

            estimated_cost = hours_alive * hourly_rate * uptime_factor

            active.append({
                "endpoint_name": ep.display_name,
                "endpoint_id": ep.name,
                "model_name": dm.display_name or dm.model,
                "machine_type": machine_type,
                "min_replicas": min_replicas,
                "max_replicas": max_replicas,
                "hourly_rate": hourly_rate,
                "hours_alive": round(hours_alive, 1),
                "uptime_factor": uptime_factor,
                "estimated_cost_usd": round(estimated_cost, 2),
                "scale_to_zero": min_replicas == 0,
            })

    return active


def check_and_enforce(budget: float, dry_run: bool = False) -> dict:
    """Check spend against budget. Undeploy if over threshold."""

    log.info("Checking Vertex AI endpoints (budget=$%.0f, project=%s)", budget, PROJECT_ID)

    spend_log = _load_spend_log()
    endpoints = list_active_endpoints()

    current_estimated = sum(ep["estimated_cost_usd"] for ep in endpoints)
    cumulative = spend_log["total_spend_usd"] + current_estimated

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "budget_usd": budget,
        "current_session_usd": round(current_estimated, 2),
        "cumulative_usd": round(cumulative, 2),
        "remaining_usd": round(budget - cumulative, 2),
        "budget_pct": round((cumulative / budget) * 100, 1) if budget > 0 else 0,
        "active_endpoints": len(endpoints),
        "endpoints": endpoints,
        "action": "none",
    }

    # ---- Alerts ----
    if result["budget_pct"] >= 100:
        log.critical(
            "BUDGET EXCEEDED: $%.2f / $%.0f (%.1f%%)",
            cumulative, budget, result["budget_pct"],
        )
        result["action"] = "undeploy_all"
    elif result["budget_pct"] >= 90:
        log.warning(
            "BUDGET WARNING (90%%): $%.2f / $%.0f",
            cumulative, budget,
        )
        result["action"] = "warning_90"
    elif result["budget_pct"] >= 75:
        log.info(
            "Budget at 75%%: $%.2f / $%.0f",
            cumulative, budget,
        )
        result["action"] = "info_75"
    else:
        log.info(
            "Budget OK: $%.2f / $%.0f (%.1f%%)",
            cumulative, budget, result["budget_pct"],
        )

    # ---- Hard stop ----
    if result["action"] == "undeploy_all":
        if dry_run:
            log.info("DRY RUN — would undeploy %d endpoints", len(endpoints))
        else:
            _undeploy_all_endpoints()
            spend_log["total_spend_usd"] = cumulative
            spend_log["entries"].append({
                "timestamp": result["timestamp"],
                "action": "hard_stop",
                "spend_usd": cumulative,
            })
            _save_spend_log(spend_log)

    # Update last check
    spend_log["last_check"] = result["timestamp"]
    _save_spend_log(spend_log)

    return result


def _undeploy_all_endpoints() -> None:
    """Nuclear option: undeploy ALL Vertex AI model endpoints in the project."""
    log.critical("HARD STOP — Undeploying all Vertex AI endpoints")

    aiplatform.init(project=PROJECT_ID, location=REGION)
    endpoints = aiplatform.Endpoint.list(project=PROJECT_ID, location=REGION)

    for ep in endpoints:
        if not ep.gca_resource.deployed_models:
            continue
        try:
            log.info("Undeploying: %s (%s)", ep.display_name, ep.name)
            ep.undeploy_all()
            log.info("  Undeployed successfully")
        except Exception as exc:
            log.error("  Failed to undeploy %s: %s", ep.display_name, exc)

    log.critical("HARD STOP COMPLETE — all endpoints undeployed, billing stopped")


def show_status(budget: float) -> None:
    """Print current endpoint status and cost estimates."""
    endpoints = list_active_endpoints()
    spend_log = _load_spend_log()
    cumulative_base = spend_log["total_spend_usd"]
    current = sum(ep["estimated_cost_usd"] for ep in endpoints)
    total = cumulative_base + current

    print()
    print("=" * 65)
    print(f"  BUDGET GUARD STATUS — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}")
    print("=" * 65)
    print(f"  Budget:     ${budget:,.0f}")
    print(f"  Spent:      ${total:,.2f}  ({(total/budget)*100:.1f}%)")
    print(f"  Remaining:  ${budget - total:,.2f}")
    print(f"  Endpoints:  {len(endpoints)} active")
    print("-" * 65)

    if not endpoints:
        print("  No active endpoints. Cost = $0/hr.")
    else:
        for ep in endpoints:
            s2z = " (scale-to-zero)" if ep["scale_to_zero"] else " (ALWAYS-ON)"
            print(f"  {ep['endpoint_name']}")
            print(f"    Machine: {ep['machine_type']}{s2z}")
            print(f"    Rate:    ${ep['hourly_rate']:.2f}/hr")
            print(f"    Alive:   {ep['hours_alive']:.1f} hrs")
            print(f"    Est:     ${ep['estimated_cost_usd']:.2f}")
            print()

    print("=" * 65)


def main() -> None:
    parser = argparse.ArgumentParser(description="Budget guard for Vertex AI endpoints")
    parser.add_argument(
        "--budget", type=float, default=DEFAULT_BUDGET,
        help=f"Budget cap in USD (default: ${DEFAULT_BUDGET:.0f})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Check only, don't undeploy")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--project", default=None, help="GCP project ID")
    parser.add_argument("--region", default=None, help="GCP region")
    args = parser.parse_args()

    global PROJECT_ID, REGION  # noqa: PLW0603
    if args.project:
        PROJECT_ID = args.project
    if args.region:
        REGION = args.region

    if args.status:
        show_status(args.budget)
        return

    result = check_and_enforce(args.budget, dry_run=args.dry_run)

    if result["action"] == "undeploy_all" and not args.dry_run:
        print(f"\n*** HARD STOP: Budget exceeded (${result['cumulative_usd']:.2f} / ${args.budget:.0f})")
        print("*** All Vertex AI endpoints have been undeployed.")
        sys.exit(2)
    elif result["action"] == "undeploy_all" and args.dry_run:
        print(f"\n*** DRY RUN: Would undeploy (${result['cumulative_usd']:.2f} / ${args.budget:.0f})")
        sys.exit(2)

    print(f"Budget OK: ${result['cumulative_usd']:.2f} / ${args.budget:.0f} ({result['budget_pct']:.1f}%)")


if __name__ == "__main__":
    main()
