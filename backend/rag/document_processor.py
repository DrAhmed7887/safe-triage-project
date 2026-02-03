"""
PDF Document Processor for RAG System
Chunks clinical guidelines into searchable segments
"""

import os
from typing import List, Dict
from PyPDF2 import PdfReader


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Full document text
        chunk_size: Characters per chunk
        chunk_overlap: Overlap between chunks (for context continuity)

    Returns:
        List of text chunks
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            if break_point > chunk_size // 2:
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())
        start = end - chunk_overlap

    return [c for c in chunks if len(c) > 50]  # Filter tiny chunks


def process_document(
    pdf_path: str,
    source_name: str
) -> List[Dict]:
    """
    Process a PDF into chunks with metadata.

    Returns:
        List of dicts with 'text', 'source', 'chunk_id'
    """
    text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(text)

    return [
        {
            "text": chunk,
            "source": source_name,
            "chunk_id": f"{source_name}_{i}"
        }
        for i, chunk in enumerate(chunks)
    ]


def process_all_documents(documents_dir: str) -> List[Dict]:
    """Process all PDFs in the documents directory."""
    all_chunks = []

    pdf_files = {
        "Emergency_Severity_Index_Handbook.pdf": "ESI_v5",
        "news2-official.pdf": "NEWS2",
        "gahar-handbook-for-hospital-standards-2021--arabic-version-.pdf": "GAHAR"
    }

    for filename, source_name in pdf_files.items():
        pdf_path = os.path.join(documents_dir, filename)
        if os.path.exists(pdf_path):
            print(f"Processing {filename}...")
            chunks = process_document(pdf_path, source_name)
            all_chunks.extend(chunks)
            print(f"  -> {len(chunks)} chunks created")
        else:
            print(f"  !! {filename} not found")

    print(f"\nTotal chunks: {len(all_chunks)}")
    return all_chunks


if __name__ == "__main__":
    # Test processing
    docs_dir = os.path.join(os.path.dirname(__file__), "documents")
    chunks = process_all_documents(docs_dir)

    # Preview first chunk from each source
    for source in ["ESI_v5", "NEWS2", "GAHAR"]:
        sample = next((c for c in chunks if c["source"] == source), None)
        if sample:
            print(f"\n{'='*50}")
            print(f"Sample from {source}:")
            print(sample["text"][:300] + "...")
