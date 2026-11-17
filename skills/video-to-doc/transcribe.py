# -*- coding: utf-8 -*-
"""video-to-doc: local, free transcription, no API key (Windows, macOS, Linux).

Usage (with the Python of the dedicated venv, which holds faster-whisper):
  "$VIDEO_TO_DOC_PYTHON" -I transcribe.py --input "<URL or file>" --output <dir>/transcript.txt
      [--model small] [--language en] [--no-subs] [--timeout 1800] [--chunk-chars 12000]

VIDEO_TO_DOC_PYTHON defaults to ~/.local/share/video-to-doc/venv (Scripts\\python.exe on
Windows, bin/python elsewhere).

Steps:
  1. URL: look for subtitles uploaded by the author first (yt-dlp). Fast.
  2. Otherwise: download the audio track (yt-dlp) and transcribe it with faster-whisper on CPU.
  3. Local file: transcribe directly (PyAV reads mp4, webm, m4a, mp3, wav...).
Output: UTF-8 text, one paragraph per pause, plus a .meta.json file next to it.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def venv_python():
    """Python of the dedicated venv: VIDEO_TO_DOC_PYTHON, else the default location."""
    base = Path.home() / ".local" / "share" / "video-to-doc" / "venv"
    default = base / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return os.environ.get("VIDEO_TO_DOC_PYTHON") or str(default)


def log(msg):
    print(f"[video-to-doc] {msg}", flush=True)


def ytdlp_cmd():
    """yt-dlp: module of the current Python, else of the system Python, else the binary."""
    candidates = [[sys.executable, "-m", "yt_dlp"]]
    for name in ("python", "python3", "py"):
        exe = shutil.which(name)
        if exe:
            candidates.append([exe, "-m", "yt_dlp"])
    exe = shutil.which("yt-dlp")
    if exe:
        candidates.append([exe])
    for cmd in candidates:
        try:
            r = subprocess.run(cmd + ["--version"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=60,
                               stdin=subprocess.DEVNULL)
            if r.returncode == 0:
                return cmd
        except Exception:
            continue
    sys.exit("yt-dlp not found. Install it: python -m pip install -U yt-dlp")


def run(cmd, timeout):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, env=env,
                          stdin=subprocess.DEVNULL)


def vtt_to_text(path):
    """Clean a .vtt file (tags, timestamps, repeated lines of auto captions)."""
    lines, last = [], None
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        if "-->" in line or re.fullmatch(r"\d+", line):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line and line != last:
            lines.append(line)
            last = line
    return "\n".join(lines)


def try_subtitles(cmd, url, workdir, langs, timeout):
    """Manual subtitles only (YouTube auto captions are worse than Whisper)."""
    out = str(Path(workdir) / "subs.%(ext)s")
    r = run(cmd + ["--skip-download", "--write-subs", "--sub-langs", langs,
                   "--sub-format", "vtt/best", "--convert-subs", "vtt",
                   "--no-playlist", "-o", out, url], timeout)
    files = sorted(Path(workdir).glob("subs*.vtt"))
    if r.returncode != 0 or not files:
        return None, None
    return vtt_to_text(files[0]), files[0].name


def download_audio(cmd, url, workdir, timeout):
    out = str(Path(workdir) / "audio.%(ext)s")
    r = run(cmd + ["-f", "bestaudio/best", "--no-playlist", "-o", out, url], timeout)
    files = [p for p in Path(workdir).glob("audio.*") if not p.name.endswith(".part")]
    if r.returncode != 0 or not files:
        tail = "\n".join((r.stderr or r.stdout).splitlines()[-8:])
        sys.exit(f"Audio download failed:\n{tail}")
    return files[0]


def whisper(media, model_name, language):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper missing: run this script with the venv Python "
                 f"{venv_python()} (VIDEO_TO_DOC_PYTHON)")
    log(f"Loading Whisper model '{model_name}' (downloaded on first use)...")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(media), language=language, vad_filter=True,
                                      beam_size=5)
    log(f"Detected language: {info.language} ({info.language_probability:.0%}), "
        f"duration {info.duration:.0f} s")
    paras, cur, prev_end = [], [], 0.0
    for seg in segments:
        if cur and seg.start - prev_end > 1.5:
            paras.append(" ".join(cur))
            cur = []
        cur.append(seg.text.strip())
        prev_end = seg.end
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(paras), info.language, info.duration


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="video URL or local file")
    ap.add_argument("--output", required=True, help="output text file")
    ap.add_argument("--model", default="small",
                    help="tiny, base, small (default), medium, large-v3")
    ap.add_argument("--language", default=None, help="language code (en, fr...); auto otherwise")
    ap.add_argument("--sub-langs", default="en.*", help="subtitle languages to look for")
    ap.add_argument("--no-subs", action="store_true", help="ignore subtitles")
    ap.add_argument("--timeout", type=int, default=1800, help="max time per yt-dlp call (s)")
    ap.add_argument("--chunk-chars", type=int, default=0,
                    help="also split the text into chunk-N.txt of this size (long videos)")
    a = ap.parse_args()

    t0 = time.time()
    out = Path(a.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {"input": a.input, "model": a.model}

    src = Path(a.input).expanduser()
    with tempfile.TemporaryDirectory(prefix="vtd-", ignore_cleanup_errors=True) as tmp:
        if src.is_file():
            text, lang, dur = whisper(src, a.model, a.language)
            meta.update(method="whisper", language=lang, duration_s=round(dur))
        else:
            cmd = ytdlp_cmd()
            text = None
            if not a.no_subs:
                log("Looking for subtitles...")
                text, name = try_subtitles(cmd, a.input, tmp, a.sub_langs, a.timeout)
                if text:
                    meta.update(method="subtitles", file=name)
                    log(f"Subtitles found: {name}")
            if not text:
                log("No subtitles: downloading audio...")
                audio = download_audio(cmd, a.input, tmp, a.timeout)
                text, lang, dur = whisper(audio, a.model, a.language)
                meta.update(method="whisper", language=lang, duration_s=round(dur))

    out.write_text(text.strip() + "\n", encoding="utf-8")
    meta["elapsed_s"] = round(time.time() - t0)
    meta["chars"] = len(text)
    out.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    log(f"Transcript written: {out} ({len(text)} characters, {meta['elapsed_s']} s)")

    if a.chunk_chars and len(text) > a.chunk_chars:
        chunks, cur, pieces = [], "", []
        for para in re.split(r"\n\s*\n|\n", text):
            if len(para) > a.chunk_chars:  # paragraph too long: split at sentence ends
                pieces += re.split(r"(?<=[.!?。])\s+", para)
            else:
                pieces.append(para)
        for para in pieces:
            if cur and len(cur) + len(para) > a.chunk_chars:
                chunks.append(cur)
                cur = ""
            cur = f"{cur}\n\n{para}" if cur else para
        if cur:
            chunks.append(cur)
        for i, c in enumerate(chunks):
            (out.parent / f"chunk-{i}.txt").write_text(c.strip() + "\n", encoding="utf-8")
        log(f"{len(chunks)} chunks written: {out.parent / 'chunk-0.txt'} ...")


if __name__ == "__main__":
    main()
