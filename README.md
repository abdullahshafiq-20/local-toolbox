# Toolbox

A local, all-in-one file utility app (Streamlit). Resize images, convert PDFs to DOCX/Markdown, compress video, and more. Everything runs on your machine; files are never uploaded anywhere.

## Quick start (Debian / Ubuntu)

```bash
unzip toolbox.zip && cd toolbox
chmod +x setup.sh run.sh
./setup.sh        # installs system packages + Python venv (asks for sudo once)
./run.sh          # opens at http://localhost:8501
```

Use a different port: `./run.sh 9000`.
Skip the `apt` step (e.g. on a non-Debian distro or no sudo): `./setup.sh --no-apt`, then install the system packages below yourself.

### Running on a remote server (e.g. your VPS)

`run.sh` binds to `127.0.0.1` for safety. Reach it through an SSH tunnel instead of exposing it:

```bash
ssh -L 8501:localhost:8501 user@your-server
# then open http://localhost:8501 locally
```

## Tools

| Category | Tools |
|---|---|
| **Images** | Resize / compress (width, scale %, quality or target KB) · Convert format (PNG, JPG, WebP, AVIF, BMP, ICO, TIFF) · Crop / rotate / flip · Remove background · Images → PDF · Strip EXIF |
| **PDF** | PDF → DOCX · PDF → Markdown · PDF → Text · PDF → Images · Merge · Split / extract pages · Compress · Rotate · Add/remove password · Watermark · OCR |
| **Documents** | DOCX → PDF · DOCX → Markdown · Markdown → DOCX · Markdown → PDF · Markdown → HTML · HTML → PDF · TXT → PDF |
| **Data** | CSV ⇄ XLSX · JSON ⇄ CSV · JSON formatter/validator · YAML ⇄ JSON |
| **Media** | Video compress · Video → GIF · Extract audio · Audio convert |
| **Misc** | QR code · Base64 · Hash generator · Text diff · Zip / unzip · Word & char counter |

## System packages

`setup.sh` installs these via apt. Each is only needed by specific tools; the rest of the app works without them.

| Package | Needed for |
|---|---|
| `ffmpeg` | all Media tools |
| `tesseract-ocr` | PDF OCR (add `tesseract-ocr-urd` etc. for other languages) |
| `ghostscript` | stronger PDF compression (falls back to pypdf without it) |
| `pandoc` | Markdown → DOCX (required), DOCX → Markdown (better output) |
| `libreoffice-writer` | DOCX → PDF |

## Project layout

```
toolbox/
├── app.py              # Streamlit entry point (sidebar navigation)
├── requirements.txt
├── setup.sh / run.sh
├── .streamlit/config.toml
└── tools/
    ├── util.py         # shared helpers (temp dirs, ffmpeg runner, download buttons)
    ├── images.py
    ├── pdf.py
    ├── documents.py
    ├── data.py
    ├── media.py
    └── misc.py
```

### Adding a tool

1. Write a function in the relevant `tools/*.py` module that draws its UI with `st.*`.
2. Register it in that module's `TOOLS` dict: `"My tool": my_function`.
3. Restart or refresh. It shows up in the sidebar automatically.

## Notes and limits

- **First use of Remove background** downloads a ~170 MB model to `~/.u2net/`.
- **Upload limit** is 1 GB per file (`.streamlit/config.toml`). Large videos are held in RAM by Streamlit, so keep an eye on memory.
- **HTML → PDF / Markdown → PDF** use a built-in renderer (PyMuPDF). It handles text, tables, code and images well, but not JavaScript or complex CSS. For pixel-perfect output, convert via DOCX → PDF instead.
- **PDF → DOCX** works best on text-based PDFs; scanned PDFs need OCR first.
- **OCR** uses `ocrmypdf`, which needs Ghostscript and Tesseract. `--skip-text` leaves pages that already have text untouched.

## Troubleshooting

- *"X is not installed" banner in a tool*: install the system package from the table above.
- *`pip install` fails on `rembg` / `onnxruntime` / `ocrmypdf`*: these are the heaviest packages. If you don't need background removal or searchable-PDF OCR, delete those lines from `requirements.txt`; the rest keeps working and those tools just show an error when opened.
- *Port already in use*: `./run.sh 8600`.
