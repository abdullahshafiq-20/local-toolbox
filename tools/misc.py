"""Misc utilities."""
from __future__ import annotations

import base64
import difflib
import hashlib
import io
import re
import zipfile

import streamlit as st

from .util import deliver, download, human_size, stem


def qr_code():
    st.subheader("QR code generator")
    import qrcode
    text = st.text_area("Text or URL", key="qr_text")
    c1, c2, c3 = st.columns(3)
    box = c1.slider("Size", 4, 20, 10, key="qr_box")
    ec = c2.selectbox("Error correction", ["L", "M", "Q", "H"], index=1, key="qr_ec")
    fg = c3.color_picker("Colour", "#000000", key="qr_fg")
    if not text.strip():
        return
    levels = {"L": qrcode.constants.ERROR_CORRECT_L, "M": qrcode.constants.ERROR_CORRECT_M,
              "Q": qrcode.constants.ERROR_CORRECT_Q, "H": qrcode.constants.ERROR_CORRECT_H}
    qr = qrcode.QRCode(error_correction=levels[ec], box_size=box, border=4)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fg, back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    st.image(buf.getvalue(), width=300)
    download(buf.getvalue(), "qrcode.png")


def base64_tool():
    st.subheader("Base64 encode / decode")
    mode = st.radio("Mode", ["Text", "File"], horizontal=True, key="b64_mode")
    action = st.radio("Action", ["Encode", "Decode"], horizontal=True, key="b64_act")
    if mode == "Text":
        text = st.text_area("Input", key="b64_text")
        if not text:
            return
        try:
            if action == "Encode":
                out = base64.b64encode(text.encode()).decode()
            else:
                out = base64.b64decode(re.sub(r"\s+", "", text), validate=True).decode("utf-8", "replace")
        except Exception as e:
            st.error(f"Could not decode: {e}")
            return
        st.text_area("Output", out, height=150)
    else:
        f = st.file_uploader("File", key="b64_up")
        if not f:
            return
        try:
            if action == "Encode":
                download(base64.b64encode(f.getvalue()), f"{f.name}.b64")
            else:
                data = base64.b64decode(re.sub(r"\s+", "", f.getvalue().decode()), validate=True)
                download(data, stem(f.name) if f.name.endswith(".b64") else f"{f.name}.decoded")
        except Exception as e:
            st.error(f"Could not decode: {e}")


def hash_tool():
    st.subheader("Hash generator")
    algos = ["md5", "sha1", "sha256", "sha512"]
    mode = st.radio("Input", ["Text", "File"], horizontal=True, key="hs_mode")
    if mode == "Text":
        text = st.text_area("Text", key="hs_text")
        data = text.encode() if text else None
    else:
        f = st.file_uploader("File", key="hs_up")
        data = f.getvalue() if f else None
    if data is None:
        return
    for a in algos:
        st.code(f"{a.upper():7} {hashlib.new(a, data).hexdigest()}", language=None)
    expected = st.text_input("Compare with a known hash (optional)", key="hs_cmp").strip().lower()
    if expected:
        match = [a for a in algos if hashlib.new(a, data).hexdigest() == expected]
        st.success(f"Match ({match[0].upper()})") if match else st.error("No match")


def text_diff():
    st.subheader("Text diff")
    c1, c2 = st.columns(2)
    a = c1.text_area("Original", height=220, key="df_a")
    b = c2.text_area("Changed", height=220, key="df_b")
    if not (a or b):
        return
    al, bl = a.splitlines(), b.splitlines()
    if al == bl:
        st.success("Texts are identical.")
        return
    html = difflib.HtmlDiff(wrapcolumn=70).make_table(al, bl, "Original", "Changed", context=True, numlines=3)
    st.components.v1.html(
        "<style>table.diff{font-family:monospace;font-size:13px;width:100%}"
        ".diff_add{background:#c8f7c5}.diff_chg{background:#fff3b0}.diff_sub{background:#f9c0c0}"
        ".diff_header{background:#eee;color:#555}td{padding:1px 4px}</style>" + html,
        height=500, scrolling=True,
    )
    unified = "\n".join(difflib.unified_diff(al, bl, "original", "changed", lineterm=""))
    download(unified.encode(), "changes.diff")


def zip_tool():
    st.subheader("Zip / unzip")
    mode = st.radio("Action", ["Create zip", "Extract zip"], horizontal=True, key="zp_mode")
    if mode == "Create zip":
        files = st.file_uploader("Files", accept_multiple_files=True, key="zp_up")
        name = st.text_input("Archive name", "archive", key="zp_name")
        if files and st.button("Create", type="primary", key="zp_go"):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for f in files:
                    z.writestr(f.name, f.getvalue())
            download(buf.getvalue(), f"{name or 'archive'}.zip")
    else:
        f = st.file_uploader("Zip file", type=["zip"], key="zp_in")
        if not f:
            return
        try:
            z = zipfile.ZipFile(io.BytesIO(f.getvalue()))
        except zipfile.BadZipFile:
            st.error("That doesn't look like a valid zip file.")
            return
        infos = [i for i in z.infolist() if not i.is_dir()]
        st.write(f"{len(infos)} file(s), {human_size(sum(i.file_size for i in infos))} uncompressed")
        for k, i in enumerate(infos[:200]):
            safe = i.filename.lstrip("/")
            if ".." in safe.split("/"):
                st.warning(f"Skipped unsafe path: {i.filename}")
                continue
            download(z.read(i), safe.split("/")[-1], label=f"⬇ {safe} ({human_size(i.file_size)})", key=f"zp_{k}")


def counter():
    st.subheader("Word & character counter")
    f = st.file_uploader("Text file (optional)", type=["txt", "md"], key="wc_up")
    text = f.getvalue().decode("utf-8", "replace") if f else st.text_area("Text", height=250, key="wc_text")
    words = re.findall(r"\S+", text)
    c = st.columns(5)
    c[0].metric("Words", len(words))
    c[1].metric("Characters", len(text))
    c[2].metric("No spaces", len(re.sub(r"\s", "", text)))
    c[3].metric("Lines", len(text.splitlines()))
    c[4].metric("Read time (min)", f"{max(len(words) / 220, 0):.1f}")


TOOLS = {
    "QR code": qr_code,
    "Base64": base64_tool,
    "Hash generator": hash_tool,
    "Text diff": text_diff,
    "Zip / unzip": zip_tool,
    "Word & char counter": counter,
}
