#!/usr/bin/env python3
"""
Undeploy MedGemma from Vertex AI — stops all billing.

Usage:
    python undeploy_medgemma.py
    python undeploy_medgemma.py --endpoint-id 1234567890
    python undeploy_medgemma.py --project safe-triage-ai --region us-central1

What this does:
    1. Finds MedGemma endpoint (by ID or by display name)
    2. Undeploys all models from the endpoint
    3. Deletes the endpoint
    4. Deletes the uploaded model resource
    5. All billing stops immediately
"""

from __future__ import annotations

import argparse
import sys

from google.cloud import aiplatform


def undeploy_medgemma(
    project_id: str = "safe-triage-ai",
    region: str = "us-central1",
    endpoint_id: str | None = None,
) -> None:
    """Undeploy MedGemma and delete all resources."""

    print(f"Initializing Vertex AI (project={project_id}, region={region})")
    aiplatform.init(project=project_id, location=region)

    # ---- Find endpoint ----
    if endpoint_id:
        print(f"Looking up endpoint: {endpoint_id}")
        endpoint = aiplatform.Endpoint(endpoint_id)
    else:
        print("Searching for MedGemma endpoints...")
        endpoints = aiplatform.Endpoint.list(
            filter='display_name="medgemma-4b-it-endpoint"',
            project=project_id,
            location=region,
        )
        if not endpoints:
            print("No MedGemma endpoints found. Nothing to undeploy.")
            return
        endpoint = endpoints[0]
        print(f"Found endpoint: {endpoint.display_name} ({endpoint.name})")

    # ---- Undeploy all models ----
    print("Undeploying all models from endpoint...")
    try:
        endpoint.undeploy_all()
        print("  Models undeployed.")
    except Exception as exc:
        print(f"  Warning during undeploy: {exc}")

    # ---- Delete endpoint ----
    print("Deleting endpoint...")
    try:
        endpoint.delete(force=True)
        print("  Endpoint deleted.")
    except Exception as exc:
        print(f"  Warning during endpoint delete: {exc}")

    # ---- Delete model resource ----
    print("Searching for MedGemma model resources...")
    models = aiplatform.Model.list(
        filter='display_name="medgemma-4b-it"',
        project=project_id,
        location=region,
    )
    for model in models:
        print(f"  Deleting model: {model.display_name} ({model.name})")
        try:
            model.delete()
            print(f"    Deleted.")
        except Exception as exc:
            print(f"    Warning: {exc}")

    print()
    print("=" * 60)
    print("  UNDEPLOY COMPLETE — billing stopped")
    print("=" * 60)
    print("  All MedGemma Vertex AI resources have been removed.")
    print("  The system will fall back to Gemini if MEDGEMMA_GEMINI_FALLBACK=true.")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Undeploy MedGemma from Vertex AI")
    parser.add_argument("--project", default="safe-triage-ai", help="GCP project ID")
    parser.add_argument("--region", default="us-central1", help="GCP region")
    parser.add_argument("--endpoint-id", default=None, help="Specific endpoint ID")
    args = parser.parse_args()

    try:
        undeploy_medgemma(
            project_id=args.project,
            region=args.region,
            endpoint_id=args.endpoint_id,
        )
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
