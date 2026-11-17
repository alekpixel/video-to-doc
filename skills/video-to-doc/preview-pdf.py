# -*- coding: utf-8 -*-
"""video-to-doc: PNG preview of each PDF page, for visual checks.

Some agents cannot display a PDF directly (on Windows there is often no poppler):
render the pages to PNG with PyMuPDF (dedicated venv), then look at the PNG files.

Usage: "$VIDEO_TO_DOC_PYTHON" -I preview-pdf.py <file.pdf> [--dpi 70]
Output: <file>-p1.png, <file>-p2.png... next to the PDF, plus a summary per page.
"""
import argparse
import os
import sys
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import pymupdf
except ImportError:
    _base = Path.home() / ".local" / "share" / "video-to-doc" / "venv"
    _default = _base / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    sys.exit("PyMuPDF missing: run this script with "
             f"{os.environ.get('VIDEO_TO_DOC_PYTHON') or _default} (VIDEO_TO_DOC_PYTHON)")

ap = argparse.ArgumentParser()
ap.add_argument("pdf")
ap.add_argument("--dpi", type=int, default=70)
a = ap.parse_args()

pdf = Path(a.pdf).resolve()
doc = pymupdf.open(pdf)
print(f"{pdf.name}: {doc.page_count} pages")
for i, page in enumerate(doc, start=1):
    png = pdf.with_name(f"{pdf.stem}-p{i}.png")
    page.get_pixmap(dpi=a.dpi).save(png)
    chars = len(page.get_text().strip())
    flag = "  <- nearly empty page" if chars < 80 else ""
    print(f"  page {i}: {chars} characters -> {png}{flag}")
