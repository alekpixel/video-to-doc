# -*- coding: utf-8 -*-
"""video-to-doc: render a PDF from an HTML fragment (the <body> content only).

Adds the <head> and assets/base.css, then prints with Chrome or Edge in headless mode.
Standard library only: works with any Python 3.

Usage: python render-pdf.py <fragment.html> <output.pdf> ["Tab title"] [--lang en] [--timeout 120]
"""
import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def find_browser():
    env = os.environ.get("VTD_BROWSER")
    cands = [env] if env else []
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")
    cands += [
        rf"{pf}\Google\Chrome\Application\chrome.exe",
        rf"{pf86}\Google\Chrome\Application\chrome.exe",
        rf"{local}\Google\Chrome\Application\chrome.exe",
        rf"{pf86}\Microsoft\Edge\Application\msedge.exe",
        rf"{pf}\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    for name in ("chrome", "msedge", "google-chrome", "chromium", "chromium-browser"):
        w = shutil.which(name)
        if w:
            cands.append(w)
    for c in cands:
        if c and Path(c).is_file():
            return c
    sys.exit("Chrome or Edge not found. Set its path in the VTD_BROWSER variable.")


def count_pages(pdf):
    data = Path(pdf).read_bytes()
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", data))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fragment")
    ap.add_argument("output")
    ap.add_argument("title", nargs="?", default="Document")
    ap.add_argument("--lang", default="en", help="document language (html lang attribute)")
    ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args()

    here = Path(__file__).resolve().parent
    css = (here / "assets" / "base.css").read_text(encoding="utf-8")
    frag = Path(a.fragment).read_text(encoding="utf-8")
    out = Path(a.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    doc = (f'<!doctype html><html lang="{html.escape(a.lang)}"><head><meta charset="utf-8">'
           f"<title>{html.escape(a.title)}</title><style>\n{css}\n</style></head><body>\n"
           f"{frag}\n</body></html>\n")

    browser = find_browser()
    with tempfile.TemporaryDirectory(prefix="vtd-", ignore_cleanup_errors=True) as tmp:
        page = Path(tmp) / "doc.html"
        page.write_text(doc, encoding="utf-8")
        profile = Path(tmp) / "profile"  # throwaway profile: does not touch an open browser
        cmd = [browser, "--headless", "--disable-gpu", "--no-first-run",
               "--no-default-browser-check", "--disable-extensions",
               f"--user-data-dir={profile}", "--no-pdf-header-footer",
               f"--print-to-pdf={out}", page.as_uri()]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                stdin=subprocess.DEVNULL)
        try:
            proc.wait(timeout=a.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
            sys.exit(f"Timed out ({a.timeout} s): browser stopped.")

    if not out.is_file() or out.stat().st_size == 0:
        sys.exit("PDF generation failed.")
    print(f"PDF written: {out} ({count_pages(out)} pages, {out.stat().st_size // 1024} KB, "
          f"browser: {Path(browser).name})")


if __name__ == "__main__":
    main()
