---
name: video-to-doc
description: >-
  Turns a video link into a ready-to-read PDF document. Three steps: 1) get the script
  (author subtitles, or local Whisper transcription), 2) ask which TYPE of document to make
  (tutorial, clean script, or article), 3) write natural prose and render a styled PDF with
  headless Chrome or Edge. USE WHEN the user sends a video URL (YouTube, Vimeo, archive.org,
  any site yt-dlp supports) or a local video or audio file and wants a document, a PDF, a
  tutorial, a clean transcript or an article from it. Also triggers on "turn this video into
  a pdf/tutorial/article", "make a doc from this link", or a video link pasted alone.
---

# video-to-doc

Pipeline: **video link, then script, then a typed PDF written in a human voice.** Reply in the user's language.

Everything runs locally, for free, with no API key.

## Tools

| Role | Tool | Where |
|---|---|---|
| Skill Python | dedicated venv | variable `VIDEO_TO_DOC_PYTHON`; if unset, `~/.local/share/video-to-doc/venv` (`Scripts\python.exe` on Windows, `bin/python` elsewhere). Written `VENV` below. |
| Transcription | faster-whisper (CPU, int8), models cached in `~/.cache/huggingface` | venv |
| Page previews | PyMuPDF | venv |
| Download | yt-dlp | system Python (`python -m yt_dlp`) or the `yt-dlp` binary |
| PDF | Chrome, or Edge as a fallback, headless | found automatically, or set `VTD_BROWSER` |

Versions are pinned in `requirements.txt` next to this file. Do not upgrade them without testing (see the README for why).

Launch rules: give every command a timeout; never pipe code into `python -`; run scripts with `-I`.

## The 3 steps (in order, with checkpoints)

Work folder: `~/video-to-doc/sources/<slug>/` (create it if missing). `SKILL` below is the folder of this file.

### 1. Get the script

```bash
"$VENV" -I "$SKILL/transcribe.py" --input "<URL_OR_FILE>" --output "$HOME/video-to-doc/sources/<slug>/transcript.txt"
```

- Allow up to 10 minutes. For a video longer than 20 minutes, run it in the background and read the file when done.
- The script first looks for subtitles uploaded by the author (fast); otherwise it downloads the audio and transcribes it with Whisper. Output is punctuated UTF-8 text, one paragraph per pause.
- Options: `--model small` by default (good trade-off on CPU, about 25 s for 90 s of video once cached); `medium` or `large-v3` for more accuracy, slower. `--language xx` forces the language. `--sub-langs "fr.*,en.*"` picks subtitle languages. `--no-subs` skips subtitles. `--chunk-chars 12000` also writes `chunk-0.txt`, `chunk-1.txt`... for long videos.
- `transcript.meta.json` records the method (subtitles or whisper), the language and the duration.

Read the transcript before going on. If it is empty, the video probably has no speech (music only): tell the user.

### 2. Ask for the document TYPE (required)

Ask the user (do not guess). Three choices:

| Type | What it produces |
|---|---|
| **Tutorial** | Step-by-step learning guide: numbered sections, "key point" boxes, a cheat sheet table, do and don't, a self-check quiz with answers. Reorganises the content for learning. |
| **Script** | Clean, faithful transcript: punctuation fixed, paragraphs, light section titles. The substance is not rewritten, only made readable. |
| **Article** | Editorial rewrite: strong title, standfirst, themed sections, conclusion. Fluid prose, a clear angle. |

Also ask for the **output language** if it differs from the video's.

### 3. Write, then render the PDF

1. Write the prose in a natural voice: concrete, no generic AI phrasing, no filler. If a humanizer or writing-style skill is installed, apply it.
2. Write the **HTML content** (a `<body>` fragment only, no `<html>` or `<head>`) in the work folder, in UTF-8, using the classes of `assets/base.css` (see "Templates").
3. Render the PDF (any Python 3, standard library only):

```bash
python -I "$SKILL/render-pdf.py" "$HOME/video-to-doc/sources/<slug>/content.html" "$HOME/video-to-doc/pdf/<slug>.pdf" "Tab title" --lang en
```

   The script finds Chrome, then Edge (or the path in `VTD_BROWSER`), prints with a throwaway profile, stops after 120 s (`--timeout`) and prints the page count.
4. **Check visually**: render PNG previews, then look at them.

```bash
"$VENV" -I "$SKILL/preview-pdf.py" "$HOME/video-to-doc/pdf/<slug>.pdf"
```

   Fix any overflow or nearly empty page (the script flags them), then delete the PNG files.
5. Give the user the full path of the PDF.

## HTML templates (base.css classes)

Always open with a cover:
```html
<div class="cover">
  <div class="kicker">Notes · <type></div>
  <h1>Title</h1>
  <p class="sub">Subtitle or one-sentence promise.</p>
  <div class="meta">Source: <URL> · <type> · made with video-to-doc</div>
</div>
```

- **Tutorial**: one `<section><h2><span class="n">1.</span>Title</h2>…</section>` per step. Boxes `<div class="box k-tip">` or `k-key`. Cheat sheet = `<table>` with `<kbd>`. Do and don't = `<div class="grid2"><div class="dont">…</div><div class="do">…</div></div>`. Quiz = `<div class="quiz"><ol>…</ol><div class="answers">…</div></div>`.
- **Script**: one `<h2>` per main part, one `<p>` per paragraph. Striking quotes in `<blockquote>`. Plain.
- **Article**: standfirst in `<p class="lead">`, themed `<h2>`, `<blockquote>` for strong lines, a conclusion.

## Known pitfalls

- **yt-dlp `HTTP Error 403` or "No supported JavaScript runtime"** (YouTube): update yt-dlp (`python -m pip install -U yt-dlp`, every month or two). If YouTube asks for a JS runtime and Node is installed, add `--js-runtimes node`. If the 403 persists, browser cookies can help, only with the user's consent.
- **HTTP Error 429** from some hosts (Wikimedia Commons, for example): use another source or an already downloaded file.
- **Windows "An Application Control policy has blocked this file"** (a DLL refused by Smart App Control): a wheel that is too recent has no reputation yet. Go back to the version pinned in `requirements.txt`.
- **Do not force** `page-break-after: always` on blocks and do not hand-build footers: that creates blank pages. Let the flow paginate; `section { break-inside: avoid }` (already in base.css) is enough.
- Check the page count after rendering; a nearly empty page means a block is too tall, shorten it.
- Accented characters: write real UTF-8 in the HTML, not entities.

## Notes

- Nothing here costs money: subtitles, Whisper and the browser all run locally.
- The first run with a new Whisper model downloads it (about 480 MB for `small`).
