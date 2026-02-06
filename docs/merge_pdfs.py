#!/usr/bin/env python3
"""Merge PDFs into a single thesis package."""
from pathlib import Path
from PyPDF2 import PdfMerger

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "SAFE_Triage_Complete_Package.pdf"

sources = [
    Path("/Users/ahmedzayed/Downloads/SAFE_Triage_Complete_Final.pdf"),
    Path("/Users/ahmedzayed/Downloads/SAFE_Triage_Safety_Plan_FINAL2.pdf"),
    ROOT / "docs" / "Test_Results_Report.pdf",
    ROOT / "docs" / "thesis_defense" / "Generated_Docs.pdf",
]

merger = PdfMerger()
for src in sources:
    if src.exists():
        merger.append(str(src))

OUT.parent.mkdir(exist_ok=True)
with OUT.open("wb") as f:
    merger.write(f)

print(f"Wrote {OUT}")
