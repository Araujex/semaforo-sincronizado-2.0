"""
Teste de offset — 4 tempos lado a lado por trecho
  1. Teórico HCM  → velocidade limite da via + lombadas + atrito + SLT × PHF
  2. API          → t_viagem + lombadas + atrito (sem SLT, sem PHF)
  3. Campo        → pré-preenchido por via
  4. Offset final → campo + EMA(alpha=0.5, delta_max=15s) quando API > campo

Credenciais lidas do arquivo .env (nunca coloque senhas no código!)
"""

import requests
import math
import csv
import os
from datetime import datetime
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# =========================
# CARREGAR .env
# =========================
# Lê todas as variáveis do arquivo .env e disponibiliza via os.getenv()
load_dotenv()

HERE_API_KEY   = os.getenv("HERE_API_KEY")
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")

# =========================
# VIAS
# =========================

VIAS = {
    "1": {
        "nome": "Av. Pio XII — Descendo sentido Rafard",
        "vel_livre_kmh": 50,
        "tempos_campo": [30, 60],
        "semaforos": [
            {"nome": "Semáforo Capifer", "lat": -22.996986, "lon": -47.513359,
             "n_lombadas": 2, "vel_lombada_kmh": 25, "n_pontos_atrito": 1, "nivel_atrito": "M", "dist_influencia_m": 100},
            {"nome": "Semáforo Sky Fit", "lat": -22.999687, "lon": -47.516329,
             "n_lombadas": 2, "vel_lombada_kmh": 25, "n_pontos_atrito": 1, "nivel_atrito": "M", "dist_influencia_m": 100},
            {"nome": "Semáforo Smash Agro", "lat": -23.003839, "lon": -47.520074,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0, "nivel_atrito": "L", "dist_influencia_m": 100},
        ],
    },
    "2": {
        "nome": "Av. Pio XII — Subindo sentido Body Gym",
        "vel_livre_kmh": 50,
        "tempos_campo": [30, 24, 40, 65],
        "semaforos": [
            {"nome": "Semáforo 1", "lat": -23.004029, "lon": -47.520051,
             "n_lombadas": 2, "vel_lombada_kmh": 25, "n_pontos_atrito": 1, "nivel_atrito": "M", "dist_influencia_m": 100},
            {"nome": "Semáforo 2", "lat": -23.001623, "lon": -47.517960,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 1, "nivel_atrito": "L", "dist_influencia_m": 100},
            {"nome": "Semáforo 3", "lat": -23.000217, "lon": -47.516666,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0, "nivel_atrito": "L", "dist_influencia_m": 100},
            {"nome": "Semáforo 4", "lat": -22.997462, "lon": -47.513925,
             "n_lombadas": 2, "vel_lombada_kmh": 25, "n_pontos_atrito": 5, "nivel_atrito": "M", "dist_influencia_m": 200},
            {"nome": "Semáforo 5", "lat": -22.994663, "lon": -47.509464,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0, "nivel_atrito": "L", "dist_influencia_m": 100},
        ],
    },
    "3": {
        "nome": "Rua Padre Fabiano — Descendo",
        "vel_livre_kmh": 40,
        "tempos_campo": [32, 9, 9, 9],
        "semaforos": [
            {"nome": "Semáforo 1", "lat": -22.995611, "lon": -47.505155,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0, "nivel_atrito": "L", "dist_influencia_m": 100},
            {"nome": "Semáforo 2", "lat": -22.998457, "lon": -47.505164,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0, "nivel_atrito": "L", "dist_influencia_m": 100},
            {"nome": "Semáforo 3", "lat": -22.999346, "lon": -47.505163,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0, "nivel_atrito": "L", "dist_influencia_m": 100},
            {"nome": "Semáforo 4", "lat": -23.000262, "lon": -47.505204,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0, "nivel_atrito": "L", "dist_influencia_m": 100},
            {"nome": "Semáforo 5", "lat": -23.001175, "lon": -47.505195,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0, "nivel_atrito": "L", "dist_influencia_m": 100},
        ],
    },
}

# =========================
# PARÂMETROS HCM
# =========================

ACELERACAO_MS2    = 3.0
DESACELERACAO_MS2 = 2.5
LARGURA_LOMBADA   = 3.7
CONFIDENCE_MINIMA = 0.5
PHF               = 1.10

L1_REACAO         = 2.0
PERDA_POR_POSICAO = [1.8, 1.2, 0.8, 0.4]
FILA_MINIMA       = 1

REDUCAO_ATRITO_KMH = {"L": 4, "M": 6, "H": 9, "VH": 13}

# =========================
# PARÂMETROS OFFSET FINAL
# =========================

EMA_ALPHA     = 0.5
EMA_DELTA_MAX = 15.0


# =========================
# FUNÇÕES HCM
# =========================

def estimar_fila(vel_atual, vel_livre):
    if not vel_atual or not vel_livre or vel_livre == 0:
        return FILA_MINIMA
    ratio = vel_atual / vel_livre
    if ratio >= 0.90: return 1
    if ratio >= 0.75: return 3
    if ratio >= 0.55: return 5
    if ratio >= 0.35: return 7
    return 10


def calcular_slt(n):
    slt = L1_REACAO
    for i in range(min(n, len(PERDA_POR_POSICAO))):
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
    total    = round(subtotal * PHF, 1)

    return total, {
        "slt": slt, "t_acel": t_acel, "t_cruzeiro": t_cruzeiro,
        "t_lomb": t_lomb, "t_atrito": t_atrito,
        "subtotal": subtotal, "total": total,
    }


def calcular_trecho_api(dist_m, vel_kmh, s):
    if not dist_m or not vel_kmh or vel_kmh <= 0:
        return None, {}
    t_viagem = round(dist_m / (vel_kmh / 3.6), 1)
    t_lomb   = round(tempo_extra_lombada(vel_kmh, s["vel_lombada_kmh"]) * s["n_lombadas"], 1)
    t_atrito = round(tempo_atrito_lateral(vel_kmh, s["nivel_atrito"], s["dist_influencia_m"]) * s["n_pontos_atrito"], 1)
    total    = round(t_viagem + t_lomb + t_atrito, 1)

    return total, {
        "t_viagem": t_viagem, "t_lomb": t_lomb, "t_atrito": t_atrito, "total": total,
    }


def calcular_offset_final(t_campo, t_api):
    if not t_campo or not t_api:
        return t_campo, "campo (API indisponível)"
    if t_api <= t_campo:
        return t_campo, f"campo (API {t_api}s ≤ base {t_campo}s — sem influência)"
    delta      = t_api - t_campo
    influencia = round(min(EMA_ALPHA * delta, EMA_DELTA_MAX), 1)
    offset     = round(t_campo + influencia, 1)
    return offset, f"campo + {influencia}s API  (delta={delta}s, alpha={EMA_ALPHA}, cap={EMA_DELTA_MAX}s)"


# =========================
# APIs
# =========================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p = math.pi / 180
    a = (math.sin((lat2-lat1)*p/2)**2 +
         math.cos(lat1*p) * math.cos(lat2*p) * math.sin((lon2-lon1)*p/2)**2)
    return round(2 * R * math.asin(math.sqrt(a)), 1)


def obter_distancia_here(lat1, lon1, lat2, lon2):
    linha_reta = haversine(lat1, lon1, lat2, lon2)
    url = "https://router.hereapi.com/v8/routes"
    params = {"transportMode": "car", "origin": f"{lat1},{lon1}",
              "destination": f"{lat2},{lon2}", "return": "summary", "apiKey": HERE_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=5)
        if r.status_code != 200:
            return linha_reta, f"HERE HTTP {r.status_code} — usando Haversine ({linha_reta:.0f}m)"
        routes = r.json().get("routes", [])
        if not routes:
            return linha_reta, f"HERE sem rota — usando Haversine ({linha_reta:.0f}m)"
        dist_here = routes[0]["sections"][0]["summary"]["length"]
        if dist_here > 1.5 * linha_reta:
            return linha_reta, f"HERE suspeito ({dist_here:.0f}m > 1.5× {linha_reta:.0f}m) — usando Haversine"
        return dist_here, None
    except Exception as e:
        return linha_reta, f"{e} — usando Haversine ({linha_reta:.0f}m)"


def calcular_heading(lat1, lon1, lat2, lon2):
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    return (math.degrees(math.atan2(dlon, dlat)) + 360) % 360


def consultar_tomtom(lat, lon, heading=None):
    url = (f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
           f"?key={TOMTOM_API_KEY}&point={lat},{lon}&unit=KMPH")
    if heading is not None:
        url += f"&heading={heading:.1f}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None, f"TomTom HTTP {r.status_code}"
        data = r.json().get("flowSegmentData", {})
        return {"currentSpeed": data.get("currentSpeed"),
                "freeFlowSpeed": data.get("freeFlowSpeed"),
                "confidence": data.get("confidence")}, None
    except Exception as e:
        return None, str(e)


# =========================
# MYSQL — CONEXÃO E GRAVAÇÃO
# =========================

def conectar_mysql():
    """Conecta ao banco usando as credenciais do .env"""
    return mysql.connector.connect(
        host             = os.getenv("MYSQL_HOST"),
        port             = int(os.getenv("MYSQL_PORT")),
        database         = os.getenv("MYSQL_DATABASE"),
        user             = os.getenv("MYSQL_USER"),
        password         = os.getenv("MYSQL_PASSWORD"),
        connection_timeout  = 30,
        autocommit          = False,
        ssl_verify_cert     = False,
        ssl_verify_identity = False,
    )


def salvar_mysql(resultados, via):
    """
    Salva os resultados no MySQL (Railway).
    Se a conexão falhar, avisa mas não para o script — o CSV ainda será salvo.
    """
    conn = None
    try:
        conn   = conectar_mysql()
        cursor = conn.cursor()

        sql = """
            INSERT INTO offset_data
            (timestamp, fonte, usuario, via, trecho,
             distancia_m, v_api_kmh, t_hcm, t_api,
             t_base, t_offset, t_real)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        for r in resultados:
            if r is None:
                continue
            cursor.execute(sql, (
                datetime.now(),
                "teste",
                "",
                via["nome"],
                r["trecho"],
                round(r["dist"],     1),
                round(r["v_api"],    1),
                round(r["t_hcm"],    1) if r["t_hcm"]    else None,
                round(r["t_api"],    1) if r["t_api"]    else None,
                round(r["t_campo"],  1) if r["t_campo"]  else None,
                round(r["t_offset"], 1) if r["t_offset"] else None,
                None  # t_real preenchido depois em campo
            ))

        conn.commit()
        print(f"  ✔ {cursor.rowcount} registros salvos no MySQL (Railway)")

    except Error as e:
        print(f"  ✗ Erro MySQL: {e}")
        print(f"  ℹ Os dados foram salvos no CSV como backup.")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


# =========================
# SELEÇÃO DE VIA
# =========================

print("\n=== TESTE DE OFFSET — 4 Tempos por Trecho ===\n")
for k, v in VIAS.items():
    print(f"  {k}. {v['nome']}  ({v['vel_livre_kmh']} km/h)")

escolha = input("\nEscolha a via (1/2/3): ").strip()
if escolha not in VIAS:
    print("Opção inválida.")
    exit()

via          = VIAS[escolha]
semaforos    = via["semaforos"]
vel_via_kmh  = via["vel_livre_kmh"]
tempos_campo = via["tempos_campo"]

print(f"\n✔ Via selecionada: {via['nome']}")
print(f"  {len(semaforos)} semáforos → {len(semaforos)-1} trechos  |  limite {vel_via_kmh} km/h")
print(f"  Tempos de campo: {tempos_campo}")
print(f"  EMA: alpha={EMA_ALPHA}  delta_max={EMA_DELTA_MAX}s\n")
print("=" * 65)

# =========================
# DISTÂNCIAS (HERE + Haversine fallback)
# =========================

distancias      = []
distancia_total = 0

print("Buscando distâncias (HERE)...")
for i in range(len(semaforos) - 1):
    s1, s2 = semaforos[i], semaforos[i+1]
    dist, aviso = obter_distancia_here(s1["lat"], s1["lon"], s2["lat"], s2["lon"])
    if aviso:
        print(f"  Trecho {i+1}: {dist:.0f} m  ⚠  {aviso}")
    else:
        print(f"  Trecho {i+1}: {dist:.0f} m")
    distancias.append(dist)
    distancia_total += dist

print(f"  Total da via: {distancia_total:.0f} m\n")

# =========================
# LOOP POR TRECHO
# =========================

print("=" * 65)
resultados = []

for i in range(len(semaforos) - 1):
    s1   = semaforos[i]
    s2   = semaforos[i+1]
    dist = distancias[i]

    print(f"\n┌─ Trecho {i+1}: {s1['nome']} → {s2['nome']}")
    print(f"│  Distância: {dist:.0f} m  |  lombadas={s1['n_lombadas']}x  |  atrito={s1['n_pontos_atrito']}x {s1['nivel_atrito']}")

    heading = calcular_heading(s1["lat"], s1["lon"], s2["lat"], s2["lon"])
    mid_lat = (s1["lat"] + s2["lat"]) / 2
    mid_lon = (s1["lon"] + s2["lon"]) / 2
    dados_tt, erro_tt = consultar_tomtom(mid_lat, mid_lon, heading)

    tt_ok = False
    if erro_tt:
        print(f"│  TomTom: ERRO — {erro_tt}")
    elif dados_tt["confidence"] < CONFIDENCE_MINIMA:
        print(f"│  TomTom: confidence {dados_tt['confidence']:.2f} — descartado")
    else:
        tt_ok     = True
        v_tt_at   = min(dados_tt["currentSpeed"],  vel_via_kmh)
        v_tt_livr = min(dados_tt["freeFlowSpeed"], vel_via_kmh)
        print(f"│  TomTom:  {v_tt_at} km/h atual  |  {v_tt_livr} km/h livre  "
              f"|  conf {dados_tt['confidence']}  |  heading {heading:.0f}°")

    if not tt_ok:
        print(f"│  ERRO: TomTom indisponível — trecho ignorado\n└")
        resultados.append(None)
        continue

    t_hcm, det_hcm = calcular_trecho_hcm(dist, vel_via_kmh, FILA_MINIMA, s1)
    t_api, det_api = calcular_trecho_api(dist, v_tt_at, s1)
    t_campo        = tempos_campo[i] if i < len(tempos_campo) else None
    t_offset, origem_offset = calcular_offset_final(t_campo, t_api)

    print(f"│")
    print(f"│  ┌──────────────────────────────────────────────────────┐")
    print(f"│  │  TEMPO 1 — Teórico HCM  ({vel_via_kmh} km/h limite)")
    print(f"│  │  SLT={det_hcm['slt']}s  Acel={det_hcm['t_acel']}s  Cruzeiro={det_hcm['t_cruzeiro']}s  "
          f"Lomb={det_hcm['t_lomb']}s  Atrito={det_hcm['t_atrito']}s")
    print(f"│  │  Subtotal={det_hcm['subtotal']}s  × PHF{PHF} = {t_hcm}s")
    print(f"│  ├──────────────────────────────────────────────────────┤")
    print(f"│  │  TEMPO 2 — API  ({v_tt_at} km/h real)")
    print(f"│  │  Viagem={det_api['t_viagem']}s  Lomb={det_api['t_lomb']}s  Atrito={det_api['t_atrito']}s")
    print(f"│  │  Total={t_api}s  (sem SLT, sem PHF)")
    print(f"│  ├──────────────────────────────────────────────────────┤")
    if t_campo:
        delta   = round(t_campo - t_hcm, 1)
        sinal   = "+" if delta >= 0 else ""
        phf_obs = round(t_campo / det_hcm['subtotal'], 3)
        print(f"│  │  TEMPO 3 — Campo  = {t_campo}s")
        print(f"│  │  PHF observado = {phf_obs}  |  Δ campo−HCM = {sinal}{delta}s")
    else:
        print(f"│  │  TEMPO 3 — Campo  = (não informado)")
    print(f"│  ├──────────────────────────────────────────────────────┤")
    print(f"│  │  OFFSET FINAL = {t_offset}s")
    print(f"│  │  {origem_offset}")
    print(f"│  └──────────────────────────────────────────────────────┘")
    print(f"└")

    resultados.append({
        "trecho":   f"{s1['nome']} → {s2['nome']}",
        "dist":     dist,
        "v_api":    v_tt_at,
        "t_hcm":    t_hcm,
        "t_api":    t_api,
        "t_campo":  t_campo,
        "t_offset": t_offset,
    })

# =========================
# RESUMO FINAL
# =========================

print("\n" + "=" * 65)
print("  RESUMO — 4 TEMPOS POR TRECHO")
print("=" * 65)
print(f"  {'Trecho':<30} {'HCM':>7} {'API':>7} {'Campo':>7} {'Offset':>8}")
print(f"  {'-'*30} {'-'*7} {'-'*7} {'-'*7} {'-'*8}")
for r in resultados:
    if r is None:
        continue
    hcm_str    = f"{r['t_hcm']}s"    if r['t_hcm']    else "  —"
    api_str    = f"{r['t_api']}s"    if r['t_api']    else "  —"
    campo_str  = f"{r['t_campo']}s"  if r['t_campo']  else "  —"
    offset_str = f"{r['t_offset']}s" if r['t_offset'] else "  —"
    print(f"  {r['trecho']:<30} {hcm_str:>7} {api_str:>7} {campo_str:>7} {offset_str:>8}")

print(f"\n  Via: {via['nome']}  |  limite {vel_via_kmh} km/h  |  PHF={PHF}  |  alpha={EMA_ALPHA}  |  delta_max={EMA_DELTA_MAX}s")
print("=" * 65)

# =========================
# SALVAR CSV (backup local)
# =========================

CSV_FILE     = "dados_offset.csv"
timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M")
cabecalho    = ["timestamp", "fonte", "usuario", "via", "trecho",
                "distancia_m", "v_api_kmh", "t_hcm", "t_api", "t_base", "t_offset", "t_real"]
arquivo_novo = not os.path.exists(CSV_FILE)

# Converte número para string com vírgula decimal (padrão BR para Excel)
def fmt(valor):
    if valor == "" or valor is None:
        return ""
    return str(valor).replace(".", ",")

with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter=";")
    if arquivo_novo:
        writer.writerow(cabecalho)
    for r in resultados:
        if r is None:
            continue
        writer.writerow([
            timestamp,
            "teste",
            "",
            via["nome"],
            r["trecho"],
            fmt(round(r["dist"],     1)),
            fmt(round(r["v_api"],    1)),
            fmt(round(r["t_hcm"],    1)) if r["t_hcm"]    else "",
            fmt(round(r["t_api"],    1)) if r["t_api"]    else "",
            fmt(round(r["t_campo"],  1)) if r["t_campo"]  else "",
            fmt(round(r["t_offset"], 1)) if r["t_offset"] else "",
            "",
        ])

print(f"\n  ✔ Backup salvo em {CSV_FILE}")

# =========================
# SALVAR MYSQL (Railway)
# =========================

print("  Conectando ao MySQL (Railway)...")
salvar_mysql(resultados, via)