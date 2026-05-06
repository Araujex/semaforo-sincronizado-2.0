# ============================================================
# calculos.py — Modelo HCM + API + Offset EMA
# ============================================================

import math
from modules.config import (
    ACELERACAO_MS2, DESACELERACAO_MS2, LARGURA_LOMBADA,
    L1_REACAO, PERDA_POR_POSICAO, FILA_MINIMA,
    REDUCAO_ATRITO_KMH, EMA_ALPHA, EMA_DELTA_MAX,
)


def estimar_fila(vel_atual, vel_livre):
    if not vel_atual or not vel_livre or vel_livre == 0:
        return FILA_MINIMA
    ratio = vel_atual / vel_livre
    if ratio >= 0.90: return 1
    if ratio >= 0.75: return 3
    if ratio >= 0.55: return 5
    if ratio >= 0.35: return 7
    return 10


def calcular_slt(n_carros):
    slt = L1_REACAO
    for i in range(min(n_carros, len(PERDA_POR_POSICAO))):
        slt += PERDA_POR_POSICAO[i]
    return round(slt, 1)


def tempo_extra_lombada(vel_kmh, vel_lomb_kmh):
    v  = vel_kmh / 3.6
    vl = vel_lomb_kmh / 3.6
    if vl >= v:
        return 0
    t_com = (v - vl)/DESACELERACAO_MS2 + LARGURA_LOMBADA/vl + (v - vl)/ACELERACAO_MS2
    dist  = (v**2 - vl**2)/(2*DESACELERACAO_MS2) + LARGURA_LOMBADA + (v**2 - vl**2)/(2*ACELERACAO_MS2)
    t_sem = dist / v
    return round(t_com - t_sem, 2)


def tempo_atrito_lateral(vel_kmh, nivel, dist_m):
    reducao = REDUCAO_ATRITO_KMH.get(nivel, 6)
    v_nom   = vel_kmh / 3.6
    v_red   = max((vel_kmh - reducao) / 3.6, 1.0)
    return round(dist_m/v_red - dist_m/v_nom, 2)


def calcular_trecho_hcm(dist_m, vel_kmh, n_carros, s):
    """Tempo teórico HCM: modelo cinemático + lombadas + atrito + SLT × PHF"""
    from modules.config import PHF_DEFAULT
    if not dist_m or not vel_kmh or vel_kmh <= 0:
        return None, {}
    v   = vel_kmh / 3.6
    slt = calcular_slt(n_carros)

    dist_acel = (v**2) / (2 * ACELERACAO_MS2)
    if dist_acel >= dist_m:
        t_acel     = round(math.sqrt(2 * dist_m / ACELERACAO_MS2), 1)
        t_cruzeiro = 0
    else:
        t_acel     = round(v / ACELERACAO_MS2, 1)
        t_cruzeiro = round((dist_m - dist_acel) / v, 1)

    t_lomb   = round(tempo_extra_lombada(vel_kmh, s["vel_lombada_kmh"]) * s["n_lombadas"], 1)
    t_atrito = round(tempo_atrito_lateral(vel_kmh, s["nivel_atrito"], s["dist_influencia_m"]) * s["n_pontos_atrito"], 1)
    subtotal = round(slt + t_acel + t_cruzeiro + t_lomb + t_atrito, 1)
    total    = round(subtotal * PHF_DEFAULT, 1)

    return total, {
        "slt": slt, "t_acel": t_acel, "t_cruzeiro": t_cruzeiro,
        "t_lomb": t_lomb, "t_atrito": t_atrito,
        "subtotal": subtotal, "total": total,
    }


def calcular_trecho_api(dist_m, vel_kmh, s):
    """Tempo API: t_viagem + lombadas + atrito. Sem SLT, sem PHF."""
    if not dist_m or not vel_kmh or vel_kmh <= 0:
        return None, {}
    t_viagem = round(dist_m / (vel_kmh / 3.6), 1)
    t_lomb   = round(tempo_extra_lombada(vel_kmh, s["vel_lombada_kmh"]) * s["n_lombadas"], 1)
    t_atrito = round(tempo_atrito_lateral(vel_kmh, s["nivel_atrito"], s["dist_influencia_m"]) * s["n_pontos_atrito"], 1)
    total    = round(t_viagem + t_lomb + t_atrito, 1)
    return total, {"t_viagem": t_viagem, "t_lomb": t_lomb, "t_atrito": t_atrito, "total": total}


def calcular_offset_final(t_base, t_api):
    """
    EMA com cap: base = campo normal, API só influencia quando supera a base.
    offset = base + min(alpha × (api − base), delta_max)
    """
    if not t_base:
        return t_api, "api (sem base de campo)"
    if not t_api or t_api <= t_base:
        return t_base, "base (trânsito normal)"
    delta      = t_api - t_base
    influencia = round(min(EMA_ALPHA * delta, EMA_DELTA_MAX), 1)
    offset     = round(t_base + influencia, 1)
    return offset, f"base +{influencia}s (trânsito detectado)"
