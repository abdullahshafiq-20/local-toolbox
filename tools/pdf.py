"""PDF tools."""
from __future__ import annotations

import io
import re

import streamlit as st

from .util import deliver, require_binary, run, save_upload, stem, workdir


def parse_ranges(spec: str, total: int) -> list[int]:
    """'1-3,5,8-' -> zero-based page indexes. Raises ValueError on bad input."""
    pages: list[int] = []
    for part in re.split(r"\s*,\s*", spec.strip()):
        if not part:
            continue
        m = re.fullmatch(r"(\d*)\s*-\s*(\d*)", part)
        if m:
            a = int(m.group(1)) if m.group(1) else 1
            b = int(m.group(2)) if m.group(2) else total
        elif part.isdigit():
            a = b = int(part)
        else:
            raise ValueError(f"Bad range: {part!r}")
        if a < 1 or b > total or a > b:
            raise ValueError(f"Range {part!r} is outside 1-{total}")
        pages.extend(range(a - 1, b))
    if not pages:
        raise ValueError("No pages selected")
    return pages


def _pdf_up(key, multiple=False, label="PDF"):
    return st.file_uploader(label, type=["pdf"], accept_multiple_files=multiple, key=key)


def pdf_to_docx():
    st.subheader("PDF → DOCX")
    f = _pdf_up("p2d_up")
    if f and st.button("Convert", type="primary", key="p2d_go"):
        from pdf2docx import Converter
        with workdir() as d, st.spinner("Converting…"):
            src = save_upload(f, d)
            out = d / f"{stem(f.name)}.docx"
            cv = Converter(str(src))
            try:
                cv.convert(str(out))
            finally:
                cv.close()
            deliver([(out.name, out.read_bytes())])


def pdf_to_markdown():
    st.subheader("PDF → Markdown")
    f = _pdf_up("p2m_up")
    if f and st.button("Convert", type="primary", key="p2m_go"):
        import pymupdf4llm
        with workdir() as d, st.spinner("Converting…"):
            src = save_upload(f, d)
            md = pymupdf4llm.to_markdown(str(src))
        st.text_area("Preview", md[:5000], height=250)
        deliver([(f"{stem(f.name)}.md", md.encode())])


def pdf_to_text():
    st.subheader("PDF → Text")
    f = _pdf_up("p2t_up")
    if f and st.button("Extract", type="primary", key="p2t_go"):
        import pymupdf
        doc = pymupdf.open(stream=f.getvalue(), filetype="pdf")
        text = "\n\n".join(f"--- Page {i+1} ---\n{p.get_text()}" for i, p in enumerate(doc))
        if not text.replace("-", "").strip():
            st.warning("No text found. This may be a scanned PDF; use the OCR tool.")
        st.text_area("Preview", text[:5000], height=250)
        deliver([(f"{stem(f.name)}.txt", text.encode())])


def pdf_to_images():
    st.subheader("PDF → Images")
    f = _pdf_up("p2i_up")
    c1, c2, c3 = st.columns(3)
    dpi = c1.slider("DPI", 72, 300, 150, key="p2i_dpi")
    fmt = c2.selectbox("Format", ["png", "jpg"], key="p2i_fmt")
    pages = c3.text_input("Pages (blank = all)", key="p2i_pages", placeholder="1-3,5")
    if f and st.button("Convert", type="primary", key="p2i_go"):
        import pymupdf
        doc = pymupdf.open(stream=f.getvalue(), filetype="pdf")
        try:
            idx = parse_ranges(pages, len(doc)) if pages.strip() else range(len(doc))
        except ValueError as e:
            st.error(str(e))
            return
        results = []
        for i in idx:
            pix = doc[i].get_pixmap(dpi=dpi)
            results.append((f"{stem(f.name)}_p{i+1}.{fmt}", pix.tobytes("jpeg" if fmt == "jpg" else "png")))
        deliver(results, f"{stem(f.name)}_pages.zip")


def merge_pdfs():
    st.subheader("Merge PDFs")
    files = _pdf_up("mg_up", multiple=True, label="PDFs (merged in upload order)")
    if files and len(files) >= 2 and st.button("Merge", type="primary", key="mg_go"):
        from pypdf import PdfWriter
        w = PdfWriter()
        for f in files:
            w.append(io.BytesIO(f.getvalue()))
        buf = io.BytesIO()
        w.write(buf)
        deliver([("merged.pdf", buf.getvalue())])
    elif files and len(files) < 2:
        st.info("Upload at least two PDFs.")


def split_extract():
    st.subheader("Split / extract pages")
    f = _pdf_up("sp_up")
    if not f:
        return
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(io.BytesIO(f.getvalue()))
    total = len(reader.pages)
    st.caption(f"{total} pages")
    mode = st.radio("Mode", ["Extract pages", "Split every page", "Split into chunks of N pages"], key="sp_mode")
    spec = n = None
    if mode == "Extract pages":
        spec = st.text_input("Pages", "1-3", key="sp_spec", help="e.g. 1-3,5,8-")
    elif mode.endswith("N pages"):
        n = st.number_input("Pages per chunk", 1, max(1, total), min(5, total), key="sp_n")
    if not st.button("Go", type="primary", key="sp_go"):
        return

    def make(idxs):
        w = PdfWriter()
        for i in idxs:
            w.add_page(reader.pages[i])
        b = io.BytesIO()
        w.write(b)
        return b.getvalue()

    try:
        if mode == "Extract pages":
            results = [(f"{stem(f.name)}_extract.pdf", make(parse_ranges(spec, total)))]
        elif mode == "Split every page":
            results = [(f"{stem(f.name)}_p{i+1}.pdf", make([i])) for i in range(total)]
        else:
            n = int(n)
            results = [
                (f"{stem(f.name)}_part{k+1}.pdf", make(range(s, min(s + n, total))))
                for k, s in enumerate(range(0, total, n))
            ]
    except ValueError as e:
        st.error(str(e))
        return
    deliver(results, f"{stem(f.name)}_split.zip")


def compress_pdf():
    st.subheader("Compress PDF")
    f = _pdf_up("cp_up")
    level = st.select_slider("Strength", ["Light", "Medium", "Strong"], "Medium", key="cp_lvl")
    st.caption("Uses Ghostscript if installed (best results), otherwise a lossless pypdf pass.")
    if not f or not st.button("Compress", type="primary", key="cp_go"):
        return
    before = len(f.getvalue())
    out_bytes = None
    from .util import have
    if have("gs"):
        setting = {"Light": "/printer", "Medium": "/ebook", "Strong": "/screen"}[level]
        with workdir() as d, st.spinner("Compressing with Ghostscript…"):
            src = save_upload(f, d)
            out = d / "out.pdf"
            try:
                run(["gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.5", f"-dPDFSETTINGS={setting}",
                     "-dNOPAUSE", "-dQUIET", "-dBATCH", f"-sOutputFile={out}", str(src)])
                out_bytes = out.read_bytes()
            except RuntimeError as e:
                st.warning(f"Ghostscript failed, falling back to pypdf.\n{e}")
    if out_bytes is None:
        from pypdf import PdfReader, PdfWriter
        r = PdfReader(io.BytesIO(f.getvalue()))
        w = PdfWriter(clone_from=r)
        for p in w.pages:
            p.compress_content_streams()
        w.compress_identical_objects()  # defaults dedupe + drop unreferenced objects in every pypdf version
        b = io.BytesIO()
        w.write(b)
        out_bytes = b.getvalue()
    after = len(out_bytes)
    if after >= before:
        st.info("Result wasn't smaller than the original; keeping the original.")
        out_bytes = f.getvalue()
        after = before
    st.write(f"{before/1024:.0f} KB → {after/1024:.0f} KB ({100*(1-after/before):.0f}% smaller)")
    deliver([(f"{stem(f.name)}_compressed.pdf", out_bytes)])


def rotate_pages():
    st.subheader("Rotate PDF pages")
    f = _pdf_up("rt_up")
    c1, c2 = st.columns(2)
    angle = c1.selectbox("Rotate clockwise", [90, 180, 270], key="rt_ang")
    spec = c2.text_input("Pages (blank = all)", key="rt_spec", placeholder="1-3,5")
    if f and st.button("Rotate", type="primary", key="rt_go"):
        from pypdf import PdfReader, PdfWriter
        r = PdfReader(io.BytesIO(f.getvalue()))
        try:
            idx = set(parse_ranges(spec, len(r.pages))) if spec.strip() else set(range(len(r.pages)))
        except ValueError as e:
            st.error(str(e))
            return
        w = PdfWriter()
        for i, p in enumerate(r.pages):
            if i in idx:
                p.rotate(angle)
            w.add_page(p)
        b = io.BytesIO()
        w.write(b)
        deliver([(f"{stem(f.name)}_rotated.pdf", b.getvalue())])


def password():
    st.subheader("Add / remove PDF password")
    f = _pdf_up("pw_up")
    mode = st.radio("Action", ["Add password", "Remove password"], horizontal=True, key="pw_mode")
    pw = st.text_input("Password", type="password", key="pw_pw")
    if not f or not pw or not st.button("Go", type="primary", key="pw_go"):
        return
    from pypdf import PdfReader, PdfWriter
    r = PdfReader(io.BytesIO(f.getvalue()))
    if mode == "Remove password":
        if r.is_encrypted and not r.decrypt(pw):
            st.error("Wrong password.")
            return
        if not r.is_encrypted:
            st.info("This PDF isn't encrypted; returning it unchanged.")
    w = PdfWriter(clone_from=r)
    if mode == "Add password":
        w.encrypt(pw)
    b = io.BytesIO()
    w.write(b)
    suffix = "locked" if mode == "Add password" else "unlocked"
    deliver([(f"{stem(f.name)}_{suffix}.pdf", b.getvalue())])


def watermark():
    st.subheader("Add watermark")
    f = _pdf_up("wm_up")
    c1, c2, c3 = st.columns(3)
    text = c1.text_input("Text", "CONFIDENTIAL", key="wm_text")
    size = c2.slider("Font size", 20, 150, 60, key="wm_size")
    opacity = c3.slider("Opacity", 0.05, 1.0, 0.25, key="wm_op")
    if f and text and st.button("Apply", type="primary", key="wm_go"):
        import pymupdf
        doc = pymupdf.open(stream=f.getvalue(), filetype="pdf")
        for page in doc:
            r = page.rect
            center = pymupdf.Point(r.width / 2, r.height / 2)
            tw = pymupdf.get_text_length(text, fontname="helv", fontsize=size)
            start = pymupdf.Point(center.x - tw / 2, center.y + size / 3)
            page.insert_text(
                start, text, fontsize=size, fontname="helv", color=(0.5, 0.5, 0.5),
                fill_opacity=opacity, rotate=0,
                morph=(center, pymupdf.Matrix(45)),
                overlay=True,
            )
        deliver([(f"{stem(f.name)}_watermarked.pdf", doc.tobytes())])


def ocr_pdf():
    st.subheader("OCR (scanned PDF → searchable)")
    f = _pdf_up("ocr_up")
    c1, c2 = st.columns(2)
    lang = c1.text_input("Tesseract language(s)", "eng", key="ocr_lang", help="e.g. eng, urd, eng+urd. Needs the matching tesseract-ocr-<lang> package.")
    mode = c2.radio("Output", ["Searchable PDF", "Plain text"], key="ocr_mode")
    if not f or not st.button("Run OCR", type="primary", key="ocr_go"):
        return
    if not require_binary("tesseract", "tesseract-ocr"):
        return
    with workdir() as d, st.spinner("Running OCR (can take a while)…"):
        src = save_upload(f, d)
        if mode == "Searchable PDF":
            out = d / "ocr.pdf"
            try:
                run(["ocrmypdf", "--skip-text", "-l", lang, str(src), str(out)])
            except (RuntimeError, FileNotFoundError) as e:
                st.error(f"ocrmypdf failed: {e}")
                return
            deliver([(f"{stem(f.name)}_ocr.pdf", out.read_bytes())])
        else:
            import pymupdf
            import pytesseract
            from PIL import Image
            doc = pymupdf.open(str(src))
            parts = []
            bar = st.progress(0.0)
            for i, page in enumerate(doc):
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                parts.append(f"--- Page {i+1} ---\n{pytesseract.image_to_string(img, lang=lang)}")
                bar.progress((i + 1) / len(doc))
            text = "\n\n".join(parts)
            st.text_area("Preview", text[:5000], height=250)
            deliver([(f"{stem(f.name)}_ocr.txt", text.encode())])


TOOLS = {
    "PDF → DOCX": pdf_to_docx,
    "PDF → Markdown": pdf_to_markdown,
    "PDF → Text": pdf_to_text,
    "PDF → Images": pdf_to_images,
    "Merge": merge_pdfs,
    "Split / extract pages": split_extract,
    "Compress": compress_pdf,
    "Rotate pages": rotate_pages,
    "Add / remove password": password,
    "Watermark": watermark,
    "OCR": ocr_pdf,
}
