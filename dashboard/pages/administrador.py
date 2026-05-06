# ============================================================
# pages/administrador.py — Painel de administração
# ============================================================

import streamlit as st
from modules.usuarios import carregar_usuarios, adicionar_usuario, renomear_usuario, remover_usuario
from modules.config import get_secret

st.markdown("# ⚙️ Administrador")
st.markdown("Gerenciamento de usuários do sistema.")
st.divider()

# ── Autenticação ──────────────────────────────────────────────
if "adm_autenticado" not in st.session_state:
    st.session_state.adm_autenticado = False

SENHA_ADM = get_secret("ADMIN_SENHA") or "admin"

if not st.session_state.adm_autenticado:
    senha = st.text_input("🔐 Senha de administrador:", type="password")
    if senha == SENHA_ADM:
        st.session_state.adm_autenticado = True
        st.rerun()
    elif senha:
        st.error("Senha incorreta.")
    st.stop()

# ── Painel (autenticado) ──────────────────────────────────────
st.success("✅ Acesso liberado")
lista_usuarios = carregar_usuarios()

st.markdown("### 👥 Usuários ativos")
for u in lista_usuarios:
    st.markdown(f"- {u}")

st.divider()

# Adicionar
st.markdown("### ➕ Adicionar usuário")
col_an, col_ab = st.columns([3, 1])
with col_an:
    novo = st.text_input("Nome:", key="adm_add", placeholder="Nome do usuário")
with col_ab:
    st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
    if st.button("Adicionar", use_container_width=True):
        ok, msg = adicionar_usuario(novo)
        st.success(msg) if ok else st.error(msg)
        if ok:
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# Renomear
st.markdown("### ✏️ Renomear usuário")
col_ru, col_rn = st.columns(2)
with col_ru:
    ren_de = st.selectbox("Usuário:", lista_usuarios, key="adm_ren_de")
with col_rn:
    ren_para = st.text_input("Novo nome:", key="adm_ren_para")
if st.button("Renomear", use_container_width=True):
    ok, msg = renomear_usuario(ren_de, ren_para)
    st.success(msg) if ok else st.error(msg)
    if ok:
        st.rerun()

st.divider()

# Remover
st.markdown("### 🗑️ Remover usuário")
remover = st.selectbox("Usuário:", lista_usuarios, key="adm_rem")
if st.button(f"Remover '{remover}'", use_container_width=True, type="primary"):
    ok, msg = remover_usuario(remover)
    st.success(msg) if ok else st.error(msg)
    if ok:
        st.rerun()

st.divider()
if st.button("🔒 Sair", use_container_width=True):
    st.session_state.adm_autenticado = False
    st.rerun()
