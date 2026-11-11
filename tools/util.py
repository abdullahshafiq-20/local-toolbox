"""Shared helpers: temp dirs, running external commands, download buttons, zipping."""
from __future__ import annotations

import io
import mimetypes
import shutil
import subprocess
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path

import streamlit as st


@contextmanager
def workdir():
    """Temporary directory that is cleaned up afterwards."""
    d = Path(tempfile.mkdtemp(prefix="toolbox_"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def save_upload(uploaded, directory: Path) -> Path:
    """Write a Streamlit UploadedFile to disk and return its path."""
    path = directory / Path(uploaded.name).name
    path.write_bytes(uploaded.getvalue())
    return path


def have(binary: str) -> bool:
    return shutil.which(binary) is not None


def require_binary(binary: str, apt_pkg: str | None = None) -> bool:
    """Show an error and return False if a system binary is missing."""
    if have(binary):
        return True
    st.error(
        f"`{binary}` is not installed. Install it with: "
        f"`sudo apt install {apt_pkg or binary}` (or run `./setup.sh`)."
    )
    return False


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 900) -> subprocess.CompletedProcess:
    """Run a command, raising RuntimeError with stderr on failure."""
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-1500:]
        raise RuntimeError(f"{cmd[0]} failed (exit {proc.returncode}):\n{tail}")
    return proc


def human_size(n: int | float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def mime_for(name: str) -> str:
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


def download(data: bytes | Path, name: str, label: str | None = None, key: str | None = None):
    """Download button for bytes or a file path."""
    if isinstance(data, Path):
        data = data.read_bytes()
    st.download_button(
        label or f"⬇ Download {name}",
        data=data,
        file_name=name,
        mime=mime_for(name),
        key=key or f"dl_{name}_{len(data)}",
    )


def zip_bytes(files: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files:
            z.writestr(name, data)
    return buf.getvalue()


def deliver(results: list[tuple[str, bytes]], zip_name: str = "results.zip"):
    """Offer one file directly, or several as individual buttons plus a zip."""
    if not results:
        return
    if len(results) == 1:
        download(results[0][1], results[0][0])
        return
    download(zip_bytes(results), zip_name, label=f"⬇ Download all ({len(results)} files, zip)")
    with st.expander("Individual files"):
        for i, (name, data) in enumerate(results):
            download(data, name, key=f"dl_{i}_{name}")


def stem(name: str) -> str:
    return Path(name).stem
