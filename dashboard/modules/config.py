# ============================================================
# config.py — Configurações globais
# Lê credenciais do st.secrets (Streamlit Cloud) ou do .env (local)
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()

def _get(chave):
    """Tenta st.secrets primeiro (cloud), depois os.getenv (local)."""
    try:
        import streamlit as st
        return st.secrets[chave]
    except Exception:
        return os.getenv(chave)

HERE_API_KEY   = _get("HERE_API_KEY")
TOMTOM_API_KEY = _get("TOMTOM_API_KEY")

MYSQL_HOST     = _get("MYSQL_HOST")
MYSQL_PORT     = _get("MYSQL_PORT")
MYSQL_DATABASE = _get("MYSQL_DATABASE")
MYSQL_USER     = _get("MYSQL_USER")
MYSQL_PASSWORD = _get("MYSQL_PASSWORD")

ACELERACAO_MS2    = 3.0
DESACELERACAO_MS2 = 2.5
LARGURA_LOMBADA   = 3.7
CONFIDENCE_MINIMA = 0.5

L1_REACAO         = 2.0
PERDA_POR_POSICAO = [1.8, 1.2, 0.8, 0.4]
FILA_MINIMA       = 1
FILA_MAXIMA       = 10

REDUCAO_ATRITO_KMH = {"L": 4, "M": 6, "H": 9, "VH": 13}

PHF_DEFAULT = 1.10

EMA_ALPHA     = 0.5
EMA_DELTA_MAX = 15.0
