"""
Teste de offset — 4 tempos lado a lado por trecho
  1. Teórico HCM  → velocidade limite da via + lombadas + atrito + SLT × PHF
  2. API          → t_viagem + lombadas + atrito (sem SLT, sem PHF)
  3. Campo        → pré-preenchido por via
  4. Offset final → campo + EMA(alpha=0.5, delta_max=15s) quando API > campo

Credenciais lidas do arquivo .env (nunca coloque senhas no código!)
"""

import sys
import os
import requests
import math
import csv
from datetime import datetime
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# ── Path para importar os módulos do dashboard ────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "dashboard"))

from modules.vias import VIAS
from modules.calculos import (
    calcular_trecho_hcm, calcular_trecho_api,
    calcular_offset_final, estimar_fila,
)
from modules.config import (
    CONFIDENCE_MINIMA, EMA_ALPHA, EMA_DELTA_MAX,
    FILA_MINIMA, PHF_DEFAULT as PHF,
)

# =========================
# CREDENCIAIS (.env)
# =========================

load_dotenv()
HERE_API_KEY   = os.getenv("HERE_API_KEY")
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")


# =========================
# FUNÇÕES DE API
# (versão verbose para terminal — retornam (resultado, mensagem_erro))
# =========================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p = math.pi / 180
    a = (math.sin((lat2-lat1)*p/2)**2 +
         math.cos(lat1*p) * math.cos(lat2*p) * math.sin((lon2-lon1)*p/2)**2)
    return round(2 * R * math.asin(math.sqrt(a)), 1)


def obter_distancia_here(lat1, lon1, lat2, lon2):
    linha_reta = haversine(lat1, lon1, lat2, lon2)
    url    = "https://router.hereapi.com/v8/routes"
    params = {"transportMode": "car", "origin": f"{lat1},{lon1}",
              "destination": f"{lat2},{lon2}", "return": "summary",
              "apiKey": HERE_API_KEY}
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
        return {"currentSpeed":  data.get("currentSpeed"),
                "freeFlowSpeed": data.get("freeFlowSpeed"),
                "confidence":    data.get("confidence")}, None
    except Exception as e:
        return None, str(e)


# =========================
# MYSQL — CONEXÃO E GRAVAÇÃO
# =========================

def conectar_mysql():
    return mysql.connector.connect(
        host                = os.getenv("MYSQL_HOST"),
        port                = int(os.getenv("MYSQL_PORT")),
        database            = os.getenv("MYSQL_DATABASE"),
        user                = os.getenv("MYSQL_USER"),
        password            = os.getenv("MYSQL_PASSWORD"),
        connection_timeout  = 30,
        autocommit          = False,
        ssl_verify_cert     = False,
        ssl_verify_identity = False,
    )


def salvar_mysql(resultados, via):
    """Salva os resultados no MySQL. Se falhar, avisa mas não para o script."""
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
                datetime.now(), "teste", "",
                via["nome"], r["trecho"],
                round(r["dist"],     1),
                round(r["v_api"],    1),
                round(r["t_hcm"],    1) if r["t_hcm"]    else None,
                round(r["t_api"],    1) if r["t_api"]    else None,
                round(r["t_campo"],  1) if r["t_campo"]  else None,
                round(r["t_offset"], 1) if r["t_offset"] else None,
                None,  # t_real preenchido depois em campo
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
vias_list = list(VIAS.items())
for i, (k, v) in enumerate(vias_list, 1):
    print(f"  {i}. {v['nome']}  ({v['vel_livre_kmh']} km/h)")

escolha = input(f"\nEscolha a via (1–{len(vias_list)}): ").strip()
if not escolha.isdigit() or not (1 <= int(escolha) <= len(vias_list)):
    print("Opção inválida.")
    exit()

via_key, via = vias_list[int(escolha) - 1]
semaforos    = via["semaforos"]
vel_via_kmh  = via["vel_livre_kmh"]
tempos_campo = via.get("tempos_campo", [])

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

    heading  = calcular_heading(s1["lat"], s1["lon"], s2["lat"], s2["lon"])
    mid_lat  = (s1["lat"] + s2["lat"]) / 2
    mid_lon  = (s1["lon"] + s2["lon"]) / 2
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
    print(f"│  │  SLT={det_hcm['slt']}s  Acel={det_hcm['t_acel']}s  "
          f"Cruzeiro={det_hcm['t_cruzeiro']}s  "
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
        phf_obs = round(t_campo / det_hcm["subtotal"], 3)
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
    hcm_str    = f"{r['t_hcm']}s"    if r["t_hcm"]    else "  —"
    api_str    = f"{r['t_api']}s"    if r["t_api"]    else "  —"
    campo_str  = f"{r['t_campo']}s"  if r["t_campo"]  else "  —"
    offset_str = f"{r['t_offset']}s" if r["t_offset"] else "  —"
    print(f"  {r['trecho']:<30} {hcm_str:>7} {api_str:>7} {campo_str:>7} {offset_str:>8}")

print(f"\n  Via: {via['nome']}  |  limite {vel_via_kmh} km/h  "
      f"|  PHF={PHF}  |  alpha={EMA_ALPHA}  |  delta_max={EMA_DELTA_MAX}s")
print("=" * 65)

# =========================
# SALVAR CSV (backup local)
# =========================

CSV_FILE     = "dados_offset.csv"
timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M")
cabecalho    = ["timestamp", "fonte", "usuario", "via", "trecho",
                "distancia_m", "v_api_kmh", "t_hcm", "t_api", "t_base", "t_offset", "t_real"]
arquivo_novo = not os.path.exists(CSV_FILE)

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
            timestamp, "teste", "", via["nome"], r["trecho"],
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
