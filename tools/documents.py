"""Document conversion tools (DOCX / Markdown / HTML / TXT / PDF)."""
from __future__ import annotations

import streamlit as st

from .util import deliver, have, require_binary, run, save_upload, stem, workdir


def _pandoc(src, out, extra: list[str] | None = None):
    run(["pandoc", str(src), "-o", str(out), *(extra or [])])


def docx_to_pdf():
    st.subheader("DOCX → PDF")
    files = st.file_uploader("Word files", type=["docx", "doc", "odt", "rtf"], accept_multiple_files=True, key="d2p_up")
    if not files or not st.button("Convert", type="primary", key="d2p_go"):
        return
    exe = "libreoffice" if have("libreoffice") else "soffice"
    if not (have("libreoffice") or have("soffice")):
        st.error("LibreOffice is not installed. Run `./setup.sh` or `sudo apt install libreoffice-writer`.")
        return
    results = []
    with workdir() as d, st.spinner("Converting with LibreOffice…"):
        for f in files:
            src = save_upload(f, d)
            try:
                run([exe, "--headless", "--convert-to", "pdf", "--outdir", str(d), str(src)])
            except RuntimeError as e:
                st.error(f"{f.name}: {e}")
                continue
            out = d / f"{src.stem}.pdf"
            if out.exists():
                results.append((out.name, out.read_bytes()))
    deliver(results, "pdfs.zip")


def docx_to_md():
    st.subheader("DOCX → Markdown")
    files = st.file_uploader("Word files", type=["docx"], accept_multiple_files=True, key="d2m_up")
    if not files or not st.button("Convert", type="primary", key="d2m_go"):
        return
    results = []
    if have("pandoc"):
        with workdir() as d:
            for f in files:
                src = save_upload(f, d)
                out = d / f"{src.stem}.md"
                _pandoc(src, out, ["-t", "gfm", "--wrap=none"])
                results.append((out.name, out.read_bytes()))
    else:
        import mammoth
        from markdownify import markdownify
        import io
        st.info("pandoc not found; using the mammoth fallback (images are dropped).")
        for f in files:
            html = mammoth.convert_to_html(io.BytesIO(f.getvalue())).value
            results.append((f"{stem(f.name)}.md", markdownify(html, heading_style="ATX").encode()))
    if results:
        st.text_area("Preview", results[0][1].decode(errors="replace")[:4000], height=220)
    deliver(results, "markdown.zip")


def md_to_docx():
    st.subheader("Markdown → DOCX")
    files = st.file_uploader("Markdown files", type=["md", "markdown", "txt"], accept_multiple_files=True, key="m2d_up")
    pasted = st.text_area("…or paste Markdown", height=120, key="m2d_paste")
    if not st.button("Convert", type="primary", key="m2d_go"):
        return
    if not require_binary("pandoc"):
        return
    items = [(stem(f.name), f.getvalue()) for f in files or []]
    if pasted.strip():
        items.append(("pasted", pasted.encode()))
    if not items:
        st.info("Upload a file or paste some Markdown first.")
        return
    results = []
    with workdir() as d:
        for name, data in items:
            src = d / f"{name}.md"
            src.write_bytes(data)
            out = d / f"{name}.docx"
            _pandoc(src, out)
            results.append((out.name, out.read_bytes()))
    deliver(results, "docx.zip")


def _md_to_html_body(md_text: str) -> str:
    import markdown
    return markdown.markdown(md_text, extensions=["extra", "tables", "fenced_code", "toc", "sane_lists"])


CSS = """
body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:780px;margin:2em auto;padding:0 1em;line-height:1.6;color:#222}
pre{background:#f5f5f5;padding:1em;overflow:auto;border-radius:6px}code{background:#f5f5f5;padding:.1em .3em;border-radius:4px}
pre code{background:none;padding:0}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.4em .8em}
blockquote{border-left:4px solid #ddd;margin-left:0;padding-left:1em;color:#555}img{max-width:100%}
"""


def _html_doc(body: str, title: str = "Document") -> str:
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{CSS}</style></head><body>{body}</body></html>"


def _html_to_pdf_bytes(html: str) -> bytes:
    """HTML -> PDF via PyMuPDF's Story API (no external browser needed)."""
    import pymupdf
    story = pymupdf.Story(html=html, user_css=CSS)
    import io
    buf = io.BytesIO()
    writer = pymupdf.DocumentWriter(buf)
    mediabox = pymupdf.paper_rect("a4")
    where = mediabox + (50, 50, -50, -50)
    more = True
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()
    return buf.getvalue()


def md_to_pdf():
    st.subheader("Markdown → PDF")
    f = st.file_uploader("Markdown file", type=["md", "markdown", "txt"], key="m2p_up")
    pasted = st.text_area("…or paste Markdown", height=120, key="m2p_paste")
    if not st.button("Convert", type="primary", key="m2p_go"):
        return
    text = f.getvalue().decode("utf-8", "replace") if f else pasted
    if not text.strip():
        st.info("Upload a file or paste some Markdown first.")
        return
    name = stem(f.name) if f else "document"
    pdf = _html_to_pdf_bytes(_html_doc(_md_to_html_body(text), name))
    deliver([(f"{name}.pdf", pdf)])


def md_to_html():
    st.subheader("Markdown → HTML")
    f = st.file_uploader("Markdown file", type=["md", "markdown", "txt"], key="m2h_up")
    pasted = st.text_area("…or paste Markdown", height=120, key="m2h_paste")
    standalone = st.checkbox("Standalone page with styling", True, key="m2h_sa")
    if not st.button("Convert", type="primary", key="m2h_go"):
        return
    text = f.getvalue().decode("utf-8", "replace") if f else pasted
    if not text.strip():
        st.info("Upload a file or paste some Markdown first.")
        return
    name = stem(f.name) if f else "document"
    body = _md_to_html_body(text)
    html = _html_doc(body, name) if standalone else body
    st.code(html[:3000], language="html")
    deliver([(f"{name}.html", html.encode())])


def html_to_pdf():
    st.subheader("HTML → PDF")
    f = st.file_uploader("HTML file", type=["html", "htm"], key="h2p_up")
    pasted = st.text_area("…or paste HTML", height=120, key="h2p_paste")
    st.caption("Uses a built-in renderer: good for text, tables, and simple styling; not for JavaScript-heavy pages.")
    if not st.button("Convert", type="primary", key="h2p_go"):
        return
    html = f.getvalue().decode("utf-8", "replace") if f else pasted
    if not html.strip():
        st.info("Upload a file or paste some HTML first.")
        return
    name = stem(f.name) if f else "document"
    deliver([(f"{name}.pdf", _html_to_pdf_bytes(html))])


def txt_to_pdf():
    st.subheader("TXT → PDF")
    files = st.file_uploader("Text files", type=["txt", "log", "csv"], accept_multiple_files=True, key="t2p_up")
    size = st.slider("Font size", 7, 16, 10, key="t2p_size")
    if not files or not st.button("Convert", type="primary", key="t2p_go"):
        return
    import html as h
    results = []
    for f in files:
        text = f.getvalue().decode("utf-8", "replace")
        body = f"<pre style='font-family:monospace;font-size:{size}pt;white-space:pre-wrap'>{h.escape(text)}</pre>"
        results.append((f"{stem(f.name)}.pdf", _html_to_pdf_bytes(_html_doc(body))))
    deliver(results, "pdfs.zip")


TOOLS = {
    "DOCX → PDF": docx_to_pdf,
    "DOCX → Markdown": docx_to_md,
    "Markdown → DOCX": md_to_docx,
    "Markdown → PDF": md_to_pdf,
    "Markdown → HTML": md_to_html,
    "HTML → PDF": html_to_pdf,
    "TXT → PDF": txt_to_pdf,
}
