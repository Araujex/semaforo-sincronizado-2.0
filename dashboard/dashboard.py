# ============================================================
# dashboard.py — Página de entrada
# ============================================================

import streamlit as st

st.set_page_config(
    page_title="Semáforo Sincronizado",
    page_icon="🚦",
    layout="centered",
)

st.markdown("## 🚦 Semáforo Sincronizado — Capivari-SP")
st.divider()
st.page_link("pages/2_Campo.py", label="🏁 Modo Campo", icon="🏁")
