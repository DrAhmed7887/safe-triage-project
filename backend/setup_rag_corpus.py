"""One-time setup: Create a Vertex AI RAG corpus and upload knowledge base documents.

Usage:
    python setup_rag_corpus.py          # Create corpus + upload files
    python setup_rag_corpus.py --status # Check existing corpus status
    python setup_rag_corpus.py --delete # Delete corpus (cleanup)

After running, set the environment variable:
    export SAFE_TRIAGE_RAG_CORPUS="<corpus_name>"

The corpus name is printed on successful creation.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import vertexai

# Support both GA and preview RAG API
try:
    from vertexai import rag as rag_module
except ImportError:
    from vertexai.preview import rag as rag_module

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "safe-triage-ai")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
CORPUS_DISPLAY_NAME = "safe-triage-educational-kb"
KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parent / "knowledge_base"

KNOWLEDGE_FILES = [
    ("esi_v5_decision_algorithm.txt", "ESI v5 Complete Decision Algorithm"),
    ("news2_scoring_guide.txt", "NEWS2 Scoring Guide"),
    ("safe_triage_clinical_rules.txt", "SAFE-Triage Clinical Rules"),
]


def init_vertex():
    """Initialize Vertex AI."""
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    print(f"Vertex AI initialized: project={PROJECT_ID}, location={LOCATION}")


def find_existing_corpus():
    """Find an existing SAFE-Triage RAG corpus."""
    try:
        corpora = rag_module.list_corpora()
        for corpus in corpora:
            if CORPUS_DISPLAY_NAME in (corpus.display_name or ""):
                return corpus
    except Exception as e:
        print(f"Error listing corpora: {e}")
    return None


def create_corpus():
    """Create a new RAG corpus and upload knowledge base files."""
    existing = find_existing_corpus()
    if existing:
        print(f"\nCorpus already exists: {existing.name}")
        print(f"Display name: {existing.display_name}")
        print("\nTo recreate, run: python setup_rag_corpus.py --delete")
        print(f"\nSet environment variable:")
        print(f'  export SAFE_TRIAGE_RAG_CORPUS="{existing.name}"')
        return existing.name

    print(f"\nCreating RAG corpus: {CORPUS_DISPLAY_NAME}")
    corpus = rag_module.create_corpus(
        display_name=CORPUS_DISPLAY_NAME,
        description=(
            "SAFE-Triage educational knowledge base containing ESI v5 "
            "decision algorithm, NEWS2 scoring guide, and clinical rules. "
            "Used to ground educational chat responses."
        ),
    )
    print(f"Corpus created: {corpus.name}")

    # Upload knowledge base files
    for filename, display_name in KNOWLEDGE_FILES:
        filepath = KNOWLEDGE_BASE_DIR / filename
        if not filepath.exists():
            print(f"  SKIP: {filename} not found at {filepath}")
            continue

        print(f"  Uploading: {filename} ({filepath.stat().st_size:,} bytes)")
        try:
            rag_file = rag_module.upload_file(
                corpus_name=corpus.name,
                path=str(filepath),
                display_name=display_name,
            )
            print(f"  OK: {rag_file.name}")
        except Exception as e:
            print(f"  ERROR uploading {filename}: {e}")

    # Wait for indexing
    print("\nWaiting for document indexing (30 seconds)...")
    time.sleep(30)

    print(f"\n{'='*60}")
    print(f"RAG corpus ready!")
    print(f"Corpus name: {corpus.name}")
    print(f"\nSet this environment variable in your .env or Cloud Run config:")
    print(f'  SAFE_TRIAGE_RAG_CORPUS="{corpus.name}"')
    print(f"{'='*60}")
    return corpus.name


def check_status():
    """Check the status of the existing corpus."""
    existing = find_existing_corpus()
    if not existing:
        print("No SAFE-Triage RAG corpus found.")
        print("Run: python setup_rag_corpus.py")
        return

    print(f"Corpus: {existing.name}")
    print(f"Display name: {existing.display_name}")

    try:
        files = rag_module.list_files(corpus_name=existing.name)
        file_list = list(files)
        print(f"Files: {len(file_list)}")
        for f in file_list:
            print(f"  - {f.display_name}: {f.name}")
    except Exception as e:
        print(f"Error listing files: {e}")

    # Test retrieval
    print("\nTesting retrieval: 'Why was this patient assigned ESI 2?'")
    try:
        response = rag_module.retrieval_query(
            rag_resources=[rag_module.RagResource(rag_corpus=existing.name)],
            text="Why was this patient assigned ESI 2?",
            similarity_top_k=3,
        )
        contexts = response.contexts
        if hasattr(contexts, "contexts"):
            contexts = contexts.contexts
        for i, ctx in enumerate(contexts):
            text_preview = (ctx.text[:120] + "...") if len(ctx.text) > 120 else ctx.text
            print(f"  [{i+1}] score={getattr(ctx, 'score', 'N/A'):.3f}: {text_preview}")
        print("\nRAG retrieval is working.")
    except Exception as e:
        print(f"Retrieval test failed: {e}")

    print(f'\nEnvironment variable to set:')
    print(f'  SAFE_TRIAGE_RAG_CORPUS="{existing.name}"')


def delete_corpus():
    """Delete the existing corpus."""
    existing = find_existing_corpus()
    if not existing:
        print("No SAFE-Triage RAG corpus found.")
        return

    confirm = input(f"Delete corpus {existing.name}? [y/N] ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    try:
        rag_module.delete_corpus(name=existing.name)
        print(f"Corpus deleted: {existing.name}")
        print("Remember to unset SAFE_TRIAGE_RAG_CORPUS environment variable.")
    except Exception as e:
        print(f"Error deleting corpus: {e}")


def main():
    parser = argparse.ArgumentParser(description="SAFE-Triage RAG Corpus Setup")
    parser.add_argument("--status", action="store_true", help="Check corpus status")
    parser.add_argument("--delete", action="store_true", help="Delete existing corpus")
    args = parser.parse_args()

    init_vertex()

    if args.status:
        check_status()
    elif args.delete:
        delete_corpus()
    else:
        create_corpus()


if __name__ == "__main__":
    main()
