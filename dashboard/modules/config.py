# ============================================================
# config.py — Configurações globais
# Credenciais lidas em tempo de execução via get_secret()
# ============================================================

import os

# Carrega .env apenas se existir (desenvolvimento local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_secret(chave):
    """
    Lê credencial em tempo de execução.
    Tenta st.secrets (Streamlit Cloud) primeiro, depois os.getenv (local).
    Deve ser chamada dentro de funções, nunca no nível do módulo.
    """
    try:
        import streamlit as st
        val = st.secrets.get(chave)
        if val is not None:
            return val
    except Exception:
        pass
    return os.getenv(chave)


# ── Constantes físicas (seguras no nível do módulo) ──────────────

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
