#!/usr/bin/env bash
# Installs system packages (Debian/Ubuntu) and Python deps into ./.venv
set -euo pipefail
cd "$(dirname "$0")"

SKIP_APT=0
[[ "${1:-}" == "--no-apt" ]] && SKIP_APT=1

if [[ $SKIP_APT -eq 0 ]]; then
  if command -v apt-get >/dev/null 2>&1; then
    SUDO=""
    [[ $EUID -ne 0 ]] && SUDO="sudo"
    echo "==> Installing system packages (needs sudo)…"
    $SUDO apt-get update
    $SUDO apt-get install -y \
      python3 python3-venv python3-pip \
      ffmpeg tesseract-ocr ghostscript pandoc \
      libreoffice-writer \
      unpaper qpdf
  else
    echo "!! apt-get not found. Install these manually: ffmpeg tesseract-ocr ghostscript pandoc libreoffice qpdf"
  fi
fi

echo "==> Creating virtualenv in .venv"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

echo
echo "==> Dependency check"
for bin in ffmpeg tesseract gs pandoc libreoffice; do
  if command -v "$bin" >/dev/null 2>&1; then echo "  ok       $bin"; else echo "  MISSING  $bin (related tools will be disabled)"; fi
done
echo
echo "Done. Start the app with:  ./run.sh"
