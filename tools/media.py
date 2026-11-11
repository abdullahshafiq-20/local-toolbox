"""Audio / video tools (ffmpeg)."""
from __future__ import annotations

import streamlit as st

from .util import deliver, human_size, require_binary, run, save_upload, stem, workdir

VIDEO_TYPES = ["mp4", "mkv", "mov", "avi", "webm", "flv", "m4v"]
AUDIO_TYPES = ["mp3", "wav", "ogg", "flac", "m4a", "aac", "opus"]


def video_compress():
    st.subheader("Video compress")
    f = st.file_uploader("Video", type=VIDEO_TYPES, key="vc_up")
    c1, c2, c3 = st.columns(3)
    crf = c1.slider("Quality (CRF, lower = better)", 18, 35, 28, key="vc_crf")
    height = c2.selectbox("Max height", ["Original", "1080", "720", "480", "360"], index=2, key="vc_h")
    audio = c3.selectbox("Audio bitrate", ["64k", "96k", "128k", "192k"], index=2, key="vc_a")
    if not f or not st.button("Compress", type="primary", key="vc_go"):
        return
    if not require_binary("ffmpeg"):
        return
    with workdir() as d, st.spinner("Encoding (this can take a while)…"):
        src = save_upload(f, d)
        out = d / f"{src.stem}_compressed.mp4"
        cmd = ["ffmpeg", "-y", "-i", str(src), "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf)]
        if height != "Original":
            cmd += ["-vf", f"scale=-2:'min({height},ih)'"]
        cmd += ["-c:a", "aac", "-b:a", audio, "-movflags", "+faststart", str(out)]
        try:
            run(cmd)
        except RuntimeError as e:
            st.error(str(e))
            return
        st.write(f"{human_size(len(f.getvalue()))} → {human_size(out.stat().st_size)}")
        deliver([(out.name, out.read_bytes())])


def video_to_gif():
    st.subheader("Video → GIF")
    f = st.file_uploader("Video", type=VIDEO_TYPES, key="vg_up")
    c1, c2, c3, c4 = st.columns(4)
    start = c1.number_input("Start (s)", 0.0, 36000.0, 0.0, key="vg_s")
    dur = c2.number_input("Duration (s)", 0.5, 120.0, 5.0, key="vg_d")
    fps = c3.slider("FPS", 5, 30, 12, key="vg_fps")
    width = c4.selectbox("Width", [320, 480, 640, 800], index=1, key="vg_w")
    if not f or not st.button("Make GIF", type="primary", key="vg_go"):
        return
    if not require_binary("ffmpeg"):
        return
    with workdir() as d, st.spinner("Rendering GIF…"):
        src = save_upload(f, d)
        out = d / f"{src.stem}.gif"
        vf = f"fps={fps},scale={width}:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse"
        try:
            run(["ffmpeg", "-y", "-ss", str(start), "-t", str(dur), "-i", str(src), "-vf", vf, str(out)])
        except RuntimeError as e:
            st.error(str(e))
            return
        data = out.read_bytes()
        st.image(data)
        deliver([(out.name, data)])


def extract_audio():
    st.subheader("Extract audio from video")
    f = st.file_uploader("Video", type=VIDEO_TYPES, key="ea_up")
    c1, c2 = st.columns(2)
    fmt = c1.selectbox("Format", ["mp3", "wav", "ogg", "flac", "m4a"], key="ea_fmt")
    br = c2.selectbox("Bitrate (lossy formats)", ["128k", "192k", "256k", "320k"], index=1, key="ea_br")
    if not f or not st.button("Extract", type="primary", key="ea_go"):
        return
    if not require_binary("ffmpeg"):
        return
    with workdir() as d, st.spinner("Extracting…"):
        src = save_upload(f, d)
        out = d / f"{src.stem}.{fmt}"
        cmd = ["ffmpeg", "-y", "-i", str(src), "-vn"]
        if fmt in ("mp3", "ogg", "m4a"):
            cmd += ["-b:a", br]
        try:
            run(cmd + [str(out)])
        except RuntimeError as e:
            st.error(str(e))
            return
        deliver([(out.name, out.read_bytes())])


def audio_convert():
    st.subheader("Audio format convert")
    files = st.file_uploader("Audio files", type=AUDIO_TYPES, accept_multiple_files=True, key="ac_up")
    c1, c2 = st.columns(2)
    fmt = c1.selectbox("Convert to", ["mp3", "wav", "ogg", "flac", "m4a", "opus"], key="ac_fmt")
    br = c2.selectbox("Bitrate (lossy formats)", ["96k", "128k", "192k", "256k", "320k"], index=2, key="ac_br")
    if not files or not st.button("Convert", type="primary", key="ac_go"):
        return
    if not require_binary("ffmpeg"):
        return
    results = []
    with workdir() as d, st.spinner("Converting…"):
        for f in files:
            src = save_upload(f, d)
            out = d / f"{src.stem}.{fmt}"
            if out == src:
                out = d / f"{src.stem}_converted.{fmt}"
            cmd = ["ffmpeg", "-y", "-i", str(src), "-vn"]
            if fmt in ("mp3", "ogg", "m4a", "opus"):
                cmd += ["-b:a", br]
            try:
                run(cmd + [str(out)])
            except RuntimeError as e:
                st.error(f"{f.name}: {e}")
                continue
            results.append((out.name, out.read_bytes()))
    deliver(results, "audio.zip")


TOOLS = {
    "Video compress": video_compress,
    "Video → GIF": video_to_gif,
    "Extract audio": extract_audio,
    "Audio convert": audio_convert,
}
