"""Image tools."""
from __future__ import annotations

import io

import streamlit as st
from PIL import Image, ImageOps

from .util import deliver, human_size, stem

try:  # AVIF support is optional
    import pillow_avif  # noqa: F401
except Exception:  # pragma: no cover
    pass

IMG_TYPES = ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "avif", "ico"]
FORMATS = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp", "AVIF": "avif", "BMP": "bmp", "ICO": "ico", "TIFF": "tiff"}


def _open(uploaded) -> Image.Image:
    img = Image.open(io.BytesIO(uploaded.getvalue()))
    img = ImageOps.exif_transpose(img)
    return img


def _encode(img: Image.Image, fmt: str, quality: int = 90) -> bytes:
    fmt = fmt.upper()
    if fmt in ("JPEG", "BMP") and img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, "white")
        rgba = img.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        img = bg
    elif fmt == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    kwargs = {}
    if fmt in ("JPEG", "WEBP", "AVIF"):
        kwargs["quality"] = quality
    if fmt == "JPEG":
        kwargs.update(optimize=True, progressive=True)
    if fmt == "PNG":
        kwargs["optimize"] = True
    if fmt == "ICO":
        side = min(256, max(img.size))
        kwargs["sizes"] = [(side, side)]
    img.save(buf, format=fmt, **kwargs)
    return buf.getvalue()


def _fit_to_kb(img: Image.Image, fmt: str, target_kb: int) -> bytes:
    """Binary-search quality, then shrink dimensions, until under target size."""
    target = target_kb * 1024
    work = img
    for _ in range(8):
        lo, hi, best = 5, 95, None
        while lo <= hi:
            mid = (lo + hi) // 2
            data = _encode(work, fmt, mid)
            if len(data) <= target:
                best, lo = data, mid + 1
            else:
                hi = mid - 1
        if best is not None:
            return best
        work = work.resize((max(1, int(work.width * 0.85)), max(1, int(work.height * 0.85))), Image.LANCZOS)
    return _encode(work, fmt, 5)


def resize_compress():
    st.subheader("Image resize / compress")
    files = st.file_uploader("Images", type=IMG_TYPES, accept_multiple_files=True, key="rc_up")
    c1, c2 = st.columns(2)
    mode = c1.radio("Resize by", ["Keep original size", "Max width/height (px)", "Scale %"], key="rc_mode")
    out_fmt = c2.selectbox("Output format", ["Same as input"] + list(FORMATS), key="rc_fmt")
    max_px = scale = None
    if mode == "Max width/height (px)":
        max_px = st.number_input("Max side (px)", 16, 20000, 1280, key="rc_px")
    elif mode == "Scale %":
        scale = st.slider("Scale %", 5, 100, 50, key="rc_scale")
    cq1, cq2 = st.columns(2)
    strategy = cq1.radio("Compression", ["Quality slider", "Target file size"], key="rc_strat")
    if strategy == "Quality slider":
        quality = cq2.slider("Quality", 5, 100, 80, key="rc_q")
        target_kb = None
    else:
        target_kb = cq2.number_input("Target size (KB)", 5, 20000, 200, key="rc_kb")
        quality = 80
    if not files or not st.button("Process", type="primary", key="rc_go"):
        return
    results = []
    for f in files:
        img = _open(f)
        before = len(f.getvalue())
        if max_px:
            img.thumbnail((max_px, max_px), Image.LANCZOS)
        elif scale:
            img = img.resize((max(1, img.width * scale // 100), max(1, img.height * scale // 100)), Image.LANCZOS)
        if out_fmt == "Same as input":
            fmt = (img.format or Image.open(io.BytesIO(f.getvalue())).format or "PNG").upper()
            fmt = "JPEG" if fmt == "MPO" else fmt
            if fmt not in FORMATS:
                fmt = "PNG"
        else:
            fmt = out_fmt
        data = _fit_to_kb(img, fmt, int(target_kb)) if target_kb else _encode(img, fmt, quality)
        name = f"{stem(f.name)}.{FORMATS[fmt]}"
        results.append((name, data))
        st.write(f"**{f.name}** → {name}: {human_size(before)} → {human_size(len(data))} ({img.width}×{img.height})")
    deliver(results, "images.zip")


def convert_format():
    st.subheader("Convert image format")
    files = st.file_uploader("Images", type=IMG_TYPES, accept_multiple_files=True, key="cf_up")
    fmt = st.selectbox("Convert to", list(FORMATS), key="cf_fmt")
    quality = st.slider("Quality (JPEG/WEBP/AVIF)", 5, 100, 90, key="cf_q")
    if files and st.button("Convert", type="primary", key="cf_go"):
        results = [(f"{stem(f.name)}.{FORMATS[fmt]}", _encode(_open(f), fmt, quality)) for f in files]
        deliver(results, "converted.zip")


def crop_rotate_flip():
    st.subheader("Crop / rotate / flip")
    f = st.file_uploader("Image", type=IMG_TYPES, key="crf_up")
    if not f:
        return
    img = _open(f)
    st.caption(f"Original: {img.width}×{img.height}")
    c1, c2, c3 = st.columns(3)
    rot = c1.selectbox("Rotate (clockwise)", [0, 90, 180, 270], key="crf_rot")
    flip_h = c2.checkbox("Flip horizontal", key="crf_fh")
    flip_v = c3.checkbox("Flip vertical", key="crf_fv")
    st.write("Crop (percent of each side to trim)")
    k1, k2, k3, k4 = st.columns(4)
    left = k1.slider("Left %", 0, 90, 0, key="crf_l")
    right = k2.slider("Right %", 0, 90, 0, key="crf_r")
    top = k3.slider("Top %", 0, 90, 0, key="crf_t")
    bottom = k4.slider("Bottom %", 0, 90, 0, key="crf_b")
    if left + right >= 100 or top + bottom >= 100:
        st.error("Crop margins leave nothing of the image.")
        return
    if rot:
        img = img.rotate(-rot, expand=True)
    if flip_h:
        img = ImageOps.mirror(img)
    if flip_v:
        img = ImageOps.flip(img)
    w, h = img.size
    img = img.crop((w * left // 100, h * top // 100, w - w * right // 100, h - h * bottom // 100))
    st.image(img, caption=f"Result: {img.width}×{img.height}")
    fmt = (f.name.rsplit(".", 1)[-1] or "png").lower()
    out = "JPEG" if fmt in ("jpg", "jpeg") else (fmt.upper() if fmt.upper() in FORMATS else "PNG")
    deliver([(f"{stem(f.name)}_edited.{FORMATS[out]}", _encode(img, out))])


def remove_background():
    st.subheader("Remove background")
    st.caption("Uses `rembg` (downloads a ~170 MB model on first use).")
    files = st.file_uploader("Images", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="rb_up")
    if not files or not st.button("Remove background", type="primary", key="rb_go"):
        return
    try:
        from rembg import remove
    except Exception as e:
        st.error(f"rembg is not installed or failed to import: {e}")
        return
    results = []
    bar = st.progress(0.0)
    for i, f in enumerate(files):
        with st.spinner(f"Processing {f.name}…"):
            out = remove(f.getvalue())
        results.append((f"{stem(f.name)}_nobg.png", out))
        st.image(out, caption=f.name, width=250)
        bar.progress((i + 1) / len(files))
    deliver(results, "no_background.zip")


def images_to_pdf():
    st.subheader("Images to PDF")
    files = st.file_uploader("Images (order = upload order)", type=IMG_TYPES, accept_multiple_files=True, key="i2p_up")
    page = st.selectbox("Page size", ["Fit to image", "A4", "Letter"], key="i2p_page")
    if not files or not st.button("Create PDF", type="primary", key="i2p_go"):
        return
    sizes = {"A4": (595, 842), "Letter": (612, 792)}
    imgs = []
    for f in files:
        im = _open(f).convert("RGB")
        if page != "Fit to image":
            pw, ph = sizes[page]
            if im.width > im.height:
                pw, ph = ph, pw
            canvas = Image.new("RGB", (pw * 2, ph * 2), "white")
            im.thumbnail((pw * 2 - 80, ph * 2 - 80), Image.LANCZOS)
            canvas.paste(im, ((canvas.width - im.width) // 2, (canvas.height - im.height) // 2))
            im = canvas
        imgs.append(im)
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:], resolution=150)
    deliver([("images.pdf", buf.getvalue())])


def strip_exif():
    st.subheader("Strip EXIF / metadata")
    files = st.file_uploader("Images", type=["jpg", "jpeg", "png", "webp", "tiff"], accept_multiple_files=True, key="ex_up")
    if not files:
        return
    for f in files:
        raw = Image.open(io.BytesIO(f.getvalue()))
        exif = raw.getexif()
        with st.expander(f"{f.name}: {len(exif)} EXIF tag(s)"):
            if exif:
                from PIL.ExifTags import TAGS
                st.json({TAGS.get(k, str(k)): str(v)[:100] for k, v in exif.items()})
            else:
                st.write("No EXIF data found.")
    if st.button("Strip metadata", type="primary", key="ex_go"):
        results = []
        for f in files:
            raw = Image.open(io.BytesIO(f.getvalue()))
            fmt = (raw.format or "PNG").upper()
            if fmt == "MPO":
                fmt = "JPEG"
            if fmt not in FORMATS:
                fmt = "PNG"
            # Apply the orientation tag first so the picture stays upright, then
            # re-encode without passing exif/icc/info, which drops all metadata.
            img = ImageOps.exif_transpose(raw)
            results.append((f"{stem(f.name)}_clean.{FORMATS[fmt]}", _encode(img, fmt, 95)))
        deliver(results, "clean_images.zip")


TOOLS = {
    "Resize / compress": resize_compress,
    "Convert format": convert_format,
    "Crop / rotate / flip": crop_rotate_flip,
    "Remove background": remove_background,
    "Images to PDF": images_to_pdf,
    "Strip EXIF metadata": strip_exif,
}
