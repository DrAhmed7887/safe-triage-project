#!/usr/bin/env python3
"""
Deploy Gemma 4 27B-IT from Vertex AI Model Garden.

Usage:
    python deploy_gemma4_vertex.py
    python deploy_gemma4_vertex.py --model google/gemma-4-27b-it
    python deploy_gemma4_vertex.py --single-gpu  # int8 quantization on 1x L4

What this does:
    1. Uploads Gemma 4 27B-IT model using a vLLM serving container
    2. Creates a Vertex AI endpoint
    3. Deploys the model with scale-to-zero (min_replica=0) to minimize costs
    4. Prints the endpoint ID — set this as GEMMA4_ENDPOINT_ID env var

Cost (scale-to-zero, billed only when active):
    Default (2x L4):  ~$2.98/hr active  → ~$60 for 20 hrs of benchmarking/demo
    Single GPU (1x L4): ~$1.19/hr active → ~$24 for 20 hrs (int8, slower)

Prerequisites:
    - gcloud auth application-default login
    - GPU quota: NVIDIA_L4_GPUS in us-central1 (at least 2 for default, 1 for --single-gpu)
    - pip install google-cloud-aiplatform>=1.60.0
    - Hugging Face token with access to google/gemma-4-27b-it (gated model)
      Set HF_TOKEN env var or pass --hf-token
"""

from __future__ import annotations

import argparse
import os
import sys

from google.cloud import aiplatform


# ---- Deployment configurations ----

DUAL_GPU_CONFIG = {
    "machine_type": "g2-standard-24",
    "accelerator_type": "NVIDIA_L4",
    "accelerator_count": 2,
    "vllm_args": [
        "--model=google/gemma-4-27b-it",
        "--tensor-parallel-size=2",
        "--max-model-len=8192",
        "--dtype=float16",
    ],
    "description": "2x L4 GPU (48GB VRAM) — full fp16, fastest inference",
}

SINGLE_GPU_CONFIG = {
    "machine_type": "g2-standard-4",
    "accelerator_type": "NVIDIA_L4",
    "accelerator_count": 1,
    "vllm_args": [
        "--model=google/gemma-4-27b-it",
        "--tensor-parallel-size=1",
        "--max-model-len=4096",
        "--dtype=float16",
        "--quantization=bitsandbytes",
        "--load-format=bitsandbytes",
    ],
    "description": "1x L4 GPU (24GB VRAM) — int8 quantized, budget option",
}


def deploy_gemma4(
    project_id: str = "safe-triage-ai",
    region: str = "us-central1",
    model_id: str = "google/gemma-4-27b-it",
    hf_token: str = "",
    single_gpu: bool = False,
    min_replicas: int = 0,
    max_replicas: int = 1,
) -> str:
    """Deploy Gemma 4 27B-IT and return the endpoint resource name."""

    config = SINGLE_GPU_CONFIG if single_gpu else DUAL_GPU_CONFIG

    print(f"[1/3] Initializing Vertex AI (project={project_id}, region={region})")
    print(f"       Config: {config['description']}")
    aiplatform.init(project=project_id, location=region)

    # Override model ID in vllm args if custom model specified
    vllm_args = list(config["vllm_args"])
    if model_id != "google/gemma-4-27b-it":
        vllm_args = [
            f"--model={model_id}" if arg.startswith("--model=") else arg
            for arg in vllm_args
        ]

    # ---- Upload model ----
    print(f"[2/3] Uploading {model_id} model (this registers it in Vertex AI)...")

    serving_container_image = (
        "us-docker.pkg.dev/vertex-ai/vertex-vision-model-garden-dockers/"
        "pytorch-vllm-serve:20240220_0936_RC01"
    )

    # Gemma models are gated on HuggingFace — pass token to container
    container_env = {}
    if hf_token:
        container_env["HUGGING_FACE_HUB_TOKEN"] = hf_token
    elif os.getenv("HF_TOKEN"):
        container_env["HUGGING_FACE_HUB_TOKEN"] = os.environ["HF_TOKEN"]

    model = aiplatform.Model.upload(
        display_name="gemma-4-27b-it",
        serving_container_image_uri=serving_container_image,
        serving_container_args=vllm_args,
        serving_container_ports=[7080],
        serving_container_predict_route="/generate",
        serving_container_health_route="/ping",
        serving_container_environment_variables=container_env or None,
    )
    print(f"    Model uploaded: {model.resource_name}")

    # ---- Create endpoint + deploy ----
    print("[3/3] Creating endpoint and deploying (this takes 15-30 min)...")
    print(f"       Machine: {config['machine_type']} + {config['accelerator_count']}x {config['accelerator_type']}")

    endpoint = aiplatform.Endpoint.create(
        display_name="gemma-4-27b-it-endpoint",
        project=project_id,
        location=region,
    )

    model.deploy(
        endpoint=endpoint,
        machine_type=config["machine_type"],
        accelerator_type=config["accelerator_type"],
        accelerator_count=config["accelerator_count"],
        min_replica_count=min_replicas,
        max_replica_count=max_replicas,
        deploy_request_timeout=2400,  # 40 min — model is ~54GB
    )

    endpoint_id = endpoint.name
    print()
    print("=" * 60)
    print("  GEMMA 4 DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"  Endpoint ID:       {endpoint_id}")
    print(f"  Endpoint resource: {endpoint.resource_name}")
    print(f"  Config:            {config['description']}")
    print(f"  Scale-to-zero:     {'Yes' if min_replicas == 0 else 'No'}")
    print()
    print("  Next steps:")
    print(f"    1. Set env var:  export GEMMA4_ENDPOINT_ID={endpoint_id}")
    print("    2. Test:         python -c \"from gemma4_client import Gemma4Client; c = Gemma4Client(); print(c.generate('Hello'))\"")
    print("    3. Cloud Run:    gcloud run services update safe-triage \\")
    print(f'         --set-env-vars="GEMMA4_ENDPOINT_ID={endpoint_id}"')
    print()
    print("  To undeploy (stop billing):")
    print("    python undeploy_gemma4.py")
    print("=" * 60)

    return endpoint_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Gemma 4 27B-IT on Vertex AI")
    parser.add_argument("--project", default="safe-triage-ai", help="GCP project ID")
    parser.add_argument("--region", default="us-central1", help="GCP region")
    parser.add_argument(
        "--model",
        default="google/gemma-4-27b-it",
        help="HuggingFace model ID (default: google/gemma-4-27b-it)",
    )
    parser.add_argument(
        "--hf-token",
        default="",
        help="HuggingFace token (or set HF_TOKEN env var)",
    )
    parser.add_argument(
        "--single-gpu",
        action="store_true",
        help="Use 1x L4 with int8 quantization (cheaper but slower)",
    )
    parser.add_argument(
        "--always-on",
        action="store_true",
        help="Keep endpoint always running (no scale-to-zero)",
    )
    args = parser.parse_args()

    min_replicas = 1 if args.always_on else 0

    try:
        deploy_gemma4(
            project_id=args.project,
            region=args.region,
            model_id=args.model,
            hf_token=args.hf_token,
            single_gpu=args.single_gpu,
            min_replicas=min_replicas,
        )
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        print("\nCommon fixes:", file=sys.stderr)
        print("  - GPU quota: request NVIDIA_L4_GPUS in Cloud Console (need 2 for default)", file=sys.stderr)
        print("  - Auth: run 'gcloud auth application-default login'", file=sys.stderr)
        print("  - HF token: export HF_TOKEN=hf_... (needed for gated Gemma models)", file=sys.stderr)
        print("  - SDK: pip install 'google-cloud-aiplatform>=1.60.0'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
