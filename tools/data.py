"""Data format tools."""
from __future__ import annotations

import io
import json

import streamlit as st

from .util import deliver, stem


def csv_xlsx():
    st.subheader("CSV ⇄ XLSX")
    import pandas as pd
    f = st.file_uploader("CSV or XLSX", type=["csv", "tsv", "xlsx", "xls"], key="cx_up")
    if not f:
        return
    ext = f.name.rsplit(".", 1)[-1].lower()
    try:
        if ext in ("xlsx", "xls"):
            sheets = pd.read_excel(io.BytesIO(f.getvalue()), sheet_name=None)
            st.caption(f"{len(sheets)} sheet(s): {', '.join(sheets)}")
            sheet = st.selectbox("Sheet to export", list(sheets), key="cx_sheet")
            df = sheets[sheet]
            out = df.to_csv(index=False).encode()
            st.dataframe(df.head(50))
            if st.button("Convert to CSV", type="primary", key="cx_go"):
                deliver([(f"{stem(f.name)}_{sheet}.csv", out)])
        else:
            sep = "\t" if ext == "tsv" else None
            df = pd.read_csv(io.BytesIO(f.getvalue()), sep=sep, engine="python")
            st.dataframe(df.head(50))
            if st.button("Convert to XLSX", type="primary", key="cx_go2"):
                buf = io.BytesIO()
                df.to_excel(buf, index=False)
                deliver([(f"{stem(f.name)}.xlsx", buf.getvalue())])
    except Exception as e:
        st.error(f"Could not read file: {e}")


def json_csv():
    st.subheader("JSON ⇄ CSV")
    import pandas as pd
    f = st.file_uploader("JSON or CSV", type=["json", "csv"], key="jc_up")
    if not f:
        return
    ext = f.name.rsplit(".", 1)[-1].lower()
    try:
        if ext == "json":
            data = json.loads(f.getvalue().decode("utf-8"))
            df = pd.json_normalize(data if isinstance(data, list) else [data])
            st.dataframe(df.head(50))
            if st.button("Convert to CSV", type="primary", key="jc_go"):
                deliver([(f"{stem(f.name)}.csv", df.to_csv(index=False).encode())])
        else:
            df = pd.read_csv(io.BytesIO(f.getvalue()))
            st.dataframe(df.head(50))
            if st.button("Convert to JSON", type="primary", key="jc_go2"):
                deliver([(f"{stem(f.name)}.json", df.to_json(orient="records", indent=2, force_ascii=False).encode())])
    except Exception as e:
        st.error(f"Could not convert: {e}")


def json_format():
    st.subheader("JSON formatter / validator")
    f = st.file_uploader("JSON file (optional)", type=["json"], key="jf_up")
    text = f.getvalue().decode("utf-8", "replace") if f else st.text_area("Paste JSON", height=200, key="jf_text")
    c1, c2, c3 = st.columns(3)
    indent = c1.selectbox("Indent", [2, 4, 0], key="jf_ind", format_func=lambda v: "minified" if v == 0 else f"{v} spaces")
    sort = c2.checkbox("Sort keys", key="jf_sort")
    ascii_ = c3.checkbox("Escape non-ASCII", key="jf_ascii")
    if not text.strip():
        return
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e.msg} (line {e.lineno}, column {e.colno})")
        return
    st.success("Valid JSON")
    out = json.dumps(obj, indent=indent or None, sort_keys=sort, ensure_ascii=ascii_,
                     separators=(",", ":") if indent == 0 else None)
    st.code(out[:8000], language="json")
    deliver([(f"{stem(f.name) if f else 'formatted'}.json", out.encode())])


def yaml_json():
    st.subheader("YAML ⇄ JSON")
    import yaml
    direction = st.radio("Direction", ["YAML → JSON", "JSON → YAML"], horizontal=True, key="yj_dir")
    f = st.file_uploader("File (optional)", type=["yaml", "yml", "json"], key="yj_up")
    text = f.getvalue().decode("utf-8", "replace") if f else st.text_area("Or paste text", height=200, key="yj_text")
    if not text.strip() or not st.button("Convert", type="primary", key="yj_go"):
        return
    try:
        if direction == "YAML → JSON":
            out, ext, lang = json.dumps(yaml.safe_load(text), indent=2, ensure_ascii=False, default=str), "json", "json"
        else:
            out, ext, lang = yaml.safe_dump(json.loads(text), sort_keys=False, allow_unicode=True), "yaml", "yaml"
    except Exception as e:
        st.error(f"Could not convert: {e}")
        return
    st.code(out[:8000], language=lang)
    deliver([(f"{stem(f.name) if f else 'converted'}.{ext}", out.encode())])


TOOLS = {
    "CSV ⇄ XLSX": csv_xlsx,
    "JSON ⇄ CSV": json_csv,
    "JSON formatter / validator": json_format,
    "YAML ⇄ JSON": yaml_json,
}
