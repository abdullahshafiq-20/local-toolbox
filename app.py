"""Toolbox: a local, all-in-one file utility app built with Streamlit.

Run with:  streamlit run app.py   (or ./run.sh)
"""
import importlib
import traceback

import streamlit as st

st.set_page_config(page_title="Toolbox", page_icon="🧰", layout="wide")

CATEGORIES = {
    "🖼️ Images": "tools.images",
    "📄 PDF": "tools.pdf",
    "📝 Documents": "tools.documents",
    "📊 Data": "tools.data",
    "🎬 Media": "tools.media",
    "🧩 Misc": "tools.misc",
}


@st.cache_resource(show_spinner=False)
def load(module_name: str):
    return importlib.import_module(module_name)


def main():
    st.sidebar.title("🧰 Toolbox")
    st.sidebar.caption("Everything runs locally. Files never leave your machine.")
    category = st.sidebar.radio("Category", list(CATEGORIES), key="category")
    try:
        mod = load(CATEGORIES[category])
    except Exception as e:  # missing dependency etc.
        st.error(f"Could not load `{CATEGORIES[category]}`: {e}")
        st.info("Run `./setup.sh` (or `pip install -r requirements.txt`) to install dependencies.")
        st.code(traceback.format_exc())
        return

    tools = mod.TOOLS
    tool_name = st.sidebar.selectbox("Tool", list(tools), key=f"tool_{CATEGORIES[category]}")
    st.sidebar.divider()
    st.sidebar.caption(f"{sum(len(load(m).TOOLS) for m in CATEGORIES.values() if _safe(m))} tools available")

    try:
        tools[tool_name]()
    except Exception as e:
        st.error(f"Something went wrong: {e}")
        with st.expander("Details"):
            st.code(traceback.format_exc())


def _safe(module_name: str) -> bool:
    try:
        load(module_name)
        return True
    except Exception:
        return False


main()
