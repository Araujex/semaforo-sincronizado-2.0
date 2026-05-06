# ============================================================
# dashboard.py — Ponto de entrada e navegação
# ============================================================

import streamlit as st

st.set_page_config(
    page_title="Semáforo Sincronizado",
    page_icon="🚦",
    layout="centered",
)

pg = st.navigation([
    st.Page("pages/rua.py",            title="Rua",            icon="🏁"),
    st.Page("pages/administrador.py",  title="Administrador",  icon="⚙️"),
])
pg.run()
