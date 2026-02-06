#!/usr/bin/env python3
"""Generate a single PDF containing API docs, deployment guide, user guide, benchmarks, and slides outline."""
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs" / "thesis_defense"
OUT = DOCS_DIR / "Generated_Docs.pdf"

SOURCES = [
    DOCS_DIR / "API_Documentation.md",
    DOCS_DIR / "Deployment_Guide.md",
    DOCS_DIR / "User_Guide.md",
    DOCS_DIR / "Performance_Benchmark.md",
    DOCS_DIR / "Presentation_Slides.md",
]


def md_to_lines(text: str, width: int = 90):
    lines = []
    for raw in text.splitlines():
        if raw.startswith("#"):
            title = raw.lstrip("#").strip()
            lines.append(title.upper())
            lines.append("")
            continue
        if raw.startswith("```"):
            continue
        if not raw.strip():
            lines.append("")
            continue
        wrapped = textwrap.wrap(raw, width=width)
        lines.extend(wrapped if wrapped else [""])
    return lines


def write_pdf(path: Path, lines, lines_per_page=45):
    objects = []

    # build content streams per page
    pages = [lines[i:i + lines_per_page] for i in range(0, len(lines), lines_per_page)]
    contents = []
    for page_lines in pages:
        content_lines = ["BT", "/F1 11 Tf", "14 TL", "72 720 Td"]
        for i, line in enumerate(page_lines):
            if i > 0:
                content_lines.append("T*")
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            content_lines.append(f"({safe}) Tj")
        content_lines.append("ET")
        contents.append("\n".join(content_lines).encode("utf-8"))

    # PDF objects
    # 1: catalog
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    # 2: pages placeholder
    # We'll fill kids after

    # 3..n: page + content objects
    page_objs = []
    content_objs = []
    for content in contents:
        content_objs.append(f"<< /Length {len(content)} >>\nstream\n".encode("utf-8") + content + b"\nendstream")

    # Build pages
    kids = []
    obj_index = 3
    for i in range(len(contents)):
        page_obj = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents {obj_index + 1} 0 R >>".encode("utf-8")
        page_objs.append(page_obj)
        kids.append(f"{obj_index} 0 R")
        obj_index += 2

    pages_obj = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode("utf-8")
    objects.append(pages_obj)

    # Add page + content objects
    for i, page_obj in enumerate(page_objs):
        objects.append(page_obj)
        objects.append(content_objs[i])

    # Font
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    # Write PDF
    offsets = []
    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n")
    for i, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{i} 0 obj\n".encode("utf-8"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects)+1}\n".encode("utf-8"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets:
        pdf.extend(f"{off:010d} 00000 n \n".encode("utf-8"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("utf-8")
    )

    path.write_bytes(pdf)


def main():
    all_lines = []
    for source in SOURCES:
        if source.exists():
            text = source.read_text()
            all_lines.extend(md_to_lines(text))
            all_lines.append("")
            all_lines.append("-" * 60)
            all_lines.append("")
    write_pdf(OUT, all_lines)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
