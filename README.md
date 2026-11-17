# video-to-doc

A Claude Code skill that turns a video link into a ready-to-read PDF: a step-by-step tutorial, a clean script, or an article. Everything runs on your own machine, for free, with no API key.

[English](#english) · [Français](#français)

---

## English

### What it does

1. **Gets the script.** It looks for subtitles uploaded by the author first. If there are none, it downloads the audio with yt-dlp and transcribes it locally with faster-whisper on the CPU.
2. **Asks which document you want.** Tutorial (numbered steps, key points, cheat sheet, quiz), script (faithful and readable), or article (an editorial rewrite).
3. **Renders a styled A4 PDF** with headless Chrome or Edge, then previews each page as PNG so the agent can check the layout.

### Install on Windows, step by step

Tested on Windows 11 x64 with Python 3.14.8.

1. **Python.** Install Python 3.14 from python.org and tick "Add python.exe to PATH". Check in PowerShell:
   ```powershell
   python --version
   ```
2. **yt-dlp** (downloads videos and subtitles), in the system Python:
   ```powershell
   python -m pip install -U yt-dlp
   ```
3. **Chrome or Edge.** Edge ships with Windows, so there is usually nothing to do. For another browser path, set the `VTD_BROWSER` environment variable.
4. **The skill.** Either install the plugin:
   ```powershell
   claude plugin marketplace add alekpixel/video-to-doc
   claude plugin install video-to-doc@video-to-doc
   ```
   or copy `skills/video-to-doc` into `%USERPROFILE%\.claude\skills\video-to-doc`.
5. **The dedicated Python environment.** It holds faster-whisper and PyMuPDF. A venv cannot be moved once created, so it lives in a fixed place, outside the skill folder:
   ```powershell
   python -m venv "$env:USERPROFILE\.local\share\video-to-doc\venv"
   & "$env:USERPROFILE\.local\share\video-to-doc\venv\Scripts\python.exe" -m pip install --only-binary=:all: --timeout 60 -r "<skill folder>\requirements.txt"
   ```
   To put the venv elsewhere, set the `VIDEO_TO_DOC_PYTHON` environment variable to its `python.exe`.
6. **First run.** Send Claude Code a video link. The first transcription downloads the Whisper `small` model (about 480 MB) into `%USERPROFILE%\.cache\huggingface`.

On macOS or Linux, the same steps work with `bin/python` instead of `Scripts\python.exe`. The pins were only tested on Windows.

### Pinned versions, and why

| Package | Version | Why |
|---|---|---|
| faster-whisper | 1.2.1 | Tested version. |
| ctranslate2 | 4.9.0 | Whisper inference engine, matching faster-whisper 1.2.1. |
| onnxruntime | 1.32.0 | Voice activity detection (VAD filter). |
| numpy | 2.4.4 | numpy 2.5.5 was blocked by Windows Smart App Control: its DLLs were too new to have a reputation. |
| av | 16.1.0 | PyAV 19 breaks faster-whisper 1.2.1. |
| pymupdf | 2.1 | PNG previews of the PDF pages. |

The other lines of `requirements.txt` are the indirect dependencies, as resolved in the tested environment. `--only-binary=:all:` installs wheels only, so nothing is compiled on your machine.

If Windows says "An Application Control policy has blocked this file", a wheel is too recent: go back to the pinned version.

### Usage

Paste a video link in Claude Code, or say "turn this video into a tutorial". The skill asks for the document type, then writes the PDF to `~/video-to-doc/pdf/`.

Scripts can also run by hand:

```powershell
$py = "$env:USERPROFILE\.local\share\video-to-doc\venv\Scripts\python.exe"
& $py -I skills\video-to-doc\transcribe.py --input "<URL or file>" --output out\transcript.txt
python -I skills\video-to-doc\render-pdf.py out\content.html out\doc.pdf "Title" --lang en
& $py -I skills\video-to-doc\preview-pdf.py out\doc.pdf
```

### Respect the videos you use

Only transcribe videos you have the right to use, and keep the source and licence in the PDF cover (the template has a `meta` line for that).

### Credits

This package was inspired by the free `video-to-doc` skill of the Ottho Academy marketplace, which targets macOS. It contains none of its files: the scripts, the stylesheet and the instructions were written again for this package.

---

## Français

### Ce qu'il fait

1. **Récupère le script.** Il cherche d'abord les sous-titres déposés par l'auteur. S'il n'y en a pas, il télécharge l'audio avec yt-dlp et le transcrit sur ta machine avec faster-whisper, sur le processeur.
2. **Te demande quel document tu veux.** Tuto (étapes numérotées, points clés, aide-mémoire, quiz), script (fidèle et lisible) ou article (réécriture éditoriale).
3. **Rend un PDF A4 mis en page** avec Chrome ou Edge sans fenêtre, puis fait un aperçu PNG de chaque page pour que l'agent vérifie la mise en page.

### Installation sous Windows, pas à pas

Testé sous Windows 11 x64 avec Python 3.14.8.

1. **Python.** Installe Python 3.14 depuis python.org et coche « Add python.exe to PATH ». Vérifie dans PowerShell :
   ```powershell
   python --version
   ```
2. **yt-dlp** (télécharge vidéos et sous-titres), dans le Python du système :
   ```powershell
   python -m pip install -U yt-dlp
   ```
3. **Chrome ou Edge.** Edge est livré avec Windows : en général, rien à faire. Pour un autre chemin de navigateur, renseigne la variable d'environnement `VTD_BROWSER`.
4. **Le skill.** Installe le plugin :
   ```powershell
   claude plugin marketplace add alekpixel/video-to-doc
   claude plugin install video-to-doc@video-to-doc
   ```
   ou copie `skills/video-to-doc` dans `%USERPROFILE%\.claude\skills\video-to-doc`.
5. **L'environnement Python dédié.** Il contient faster-whisper et PyMuPDF. Un venv ne se déplace pas une fois créé : il vit donc à un endroit fixe, hors du dossier du skill.
   ```powershell
   python -m venv "$env:USERPROFILE\.local\share\video-to-doc\venv"
   & "$env:USERPROFILE\.local\share\video-to-doc\venv\Scripts\python.exe" -m pip install --only-binary=:all: --timeout 60 -r "<dossier du skill>\requirements.txt"
   ```
   Pour le mettre ailleurs, fais pointer la variable `VIDEO_TO_DOC_PYTHON` sur son `python.exe`.
6. **Premier lancement.** Envoie un lien vidéo à Claude Code. La première transcription télécharge le modèle Whisper `small` (environ 480 Mo) dans `%USERPROFILE%\.cache\huggingface`.

Sous macOS ou Linux, les mêmes étapes marchent avec `bin/python` au lieu de `Scripts\python.exe`. Les versions épinglées n'ont été testées que sous Windows.

### Versions épinglées, et pourquoi

| Paquet | Version | Pourquoi |
|---|---|---|
| faster-whisper | 1.2.1 | Version testée. |
| ctranslate2 | 4.9.0 | Moteur de Whisper, accordé à faster-whisper 1.2.1. |
| onnxruntime | 1.32.0 | Détection de la voix (filtre VAD). |
| numpy | 2.4.4 | numpy 2.5.5 était bloqué par le contrôle intelligent des applications de Windows : ses DLL, trop récentes, n'avaient pas encore de réputation. |
| av | 16.1.0 | PyAV 19 casse faster-whisper 1.2.1. |
| pymupdf | 2.1 | Aperçus PNG des pages du PDF. |

Les autres lignes de `requirements.txt` sont les dépendances indirectes, telles que résolues dans l'environnement testé. `--only-binary=:all:` n'installe que des roues : rien n'est compilé sur ta machine.

Si Windows affiche « Une stratégie de contrôle d'application a bloqué ce fichier », une roue est trop récente : reviens à la version épinglée.

### Utilisation

Colle un lien vidéo dans Claude Code, ou dis « transforme cette vidéo en tuto ». Le skill demande le type de document, puis écrit le PDF dans `~/video-to-doc/pdf/`.

### Respecte les vidéos que tu utilises

Ne transcris que des vidéos que tu as le droit d'utiliser, et garde la source et la licence sur la couverture du PDF (le gabarit a une ligne `meta` pour ça).

### Crédits

Ce paquet s'inspire du skill gratuit `video-to-doc` de la marketplace Ottho Academy, pensé pour macOS. Il n'en reprend aucun fichier : les scripts, la feuille de style et les instructions ont été réécrits pour ce paquet.

---

MIT License, see [LICENSE](LICENSE).
