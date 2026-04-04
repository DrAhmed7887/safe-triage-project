#!/usr/bin/env python3
"""
Deploy MedGemma 4B-IT from Vertex AI Model Garden.

Usage:
    python deploy_medgemma_vertex.py

What this does:
    1. Uploads MedGemma 4B-IT model using a vLLM serving container
    2. Creates a Vertex AI endpoint
    3. Deploys the model with scale-to-zero (min_replica=0) to minimize costs
    4. Prints the endpoint ID — set this as MEDGEMMA_ENDPOINT_ID env var

Cost:  ~$1.19/hr when running (g2-standard-4 + L4 GPU).
       With scale-to-zero, you only pay during active QA runs (~$6-10 for 2 days).

Prerequisites:
    - gcloud auth application-default login
    - GPU quota: at least 1x NVIDIA_L4_GPUS in us-central1
    - pip install google-cloud-aiplatform>=1.60.0
"""

from __future__ import annotations

import argparse
import sys

from google.cloud import aiplatform


def deploy_medgemma(
    project_id: str = "safe-triage-ai",
    region: str = "us-central1",
    machine_type: str = "g2-standard-4",
    accelerator_type: str = "NVIDIA_L4",
    min_replicas: int = 0,
    max_replicas: int = 1,
) -> str:
    """Deploy MedGemma 4B-IT and return the endpoint resource name."""

    print(f"[1/3] Initializing Vertex AI (project={project_id}, region={region})")
    aiplatform.init(project=project_id, location=region)

    # ---- Upload model ----
    # The vLLM serving container runs MedGemma on GPU.
    # It downloads the model weights from Hugging Face on first startup (~8 GB).
    print("[2/3] Uploading MedGemma 4B-IT model (this registers it in Vertex AI)...")

    serving_container_image = (
        "us-docker.pkg.dev/vertex-ai/vertex-vision-model-garden-dockers/"
        "pytorch-vllm-serve:20240220_0936_RC01"
    )

    model = aiplatform.Model.upload(
        display_name="medgemma-4b-it",
        serving_container_image_uri=serving_container_image,
        serving_container_args=[
            "--model=google/medgemma-4b-it",
            "--tensor-parallel-size=1",
            "--max-model-len=8192",
            "--dtype=float16",
        ],
        serving_container_ports=[7080],
        serving_container_predict_route="/generate",
        serving_container_health_route="/ping",
    )
    print(f"    Model uploaded: {model.resource_name}")

    # ---- Create endpoint + deploy ----
    print("[3/3] Creating endpoint and deploying (this takes 15-30 min)...")

    endpoint = aiplatform.Endpoint.create(
        display_name="medgemma-4b-it-endpoint",
        project=project_id,
        location=region,
    )

    model.deploy(
        endpoint=endpoint,
        machine_type=machine_type,
        accelerator_type=accelerator_type,
        accelerator_count=1,
        min_replica_count=min_replicas,
        max_replica_count=max_replicas,
        deploy_request_timeout=1800,  # 30 min for model download
    )

    endpoint_id = endpoint.name  # numeric ID
    print()
    print("=" * 60)
    print("  DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"  Endpoint ID:       {endpoint_id}")
    print(f"  Endpoint resource: {endpoint.resource_name}")
    print(f"  Machine:           {machine_type} + 1x {accelerator_type}")
    print(f"  Scale-to-zero:     {'Yes' if min_replicas == 0 else 'No'}")
    print()
    print("  Next steps:")
    print(f"    1. Set env var:  export MEDGEMMA_ENDPOINT_ID={endpoint_id}")
    print("    2. Test:         python test_medgemma.py")
    print("    3. Cloud Run:    gcloud run services update safe-triage \\")
    print(f'         --set-env-vars="MEDGEMMA_ENDPOINT_ID={endpoint_id}"')
    print()
    print("  To undeploy (stop billing):")
    print("    python undeploy_medgemma.py")
    print("=" * 60)

    return endpoint_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy MedGemma 4B-IT on Vertex AI")
    parser.add_argument("--project", default="safe-triage-ai", help="GCP project ID")
    parser.add_argument("--region", default="us-central1", help="GCP region")
    parser.add_argument(
        "--machine-type",
        default="g2-standard-4",
        help="Machine type (default: g2-standard-4 with L4 GPU)",
    )
    parser.add_argument(
        "--always-on",
        action="store_true",
        help="Keep endpoint always running (no scale-to-zero). Costs ~$57/2days.",
    )
    args = parser.parse_args()

    min_replicas = 1 if args.always_on else 0

    try:
        deploy_medgemma(
            project_id=args.project,
            region=args.region,
            machine_type=args.machine_type,
            min_replicas=min_replicas,
        )
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        print("\nCommon fixes:", file=sys.stderr)
        print("  - GPU quota: request NVIDIA_L4_GPUS in Cloud Console", file=sys.stderr)
        print("  - Auth: run 'gcloud auth application-default login'", file=sys.stderr)
        print("  - SDK: pip install 'google-cloud-aiplatform>=1.60.0'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
