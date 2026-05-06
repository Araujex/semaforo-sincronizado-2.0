# ============================================================
# storage.py — Salva dados no CSV compartilhado com o script de teste
# ============================================================

import csv
import os
from datetime import datetime
from modules.config import CSV_PATH

CABECALHO = [
    "timestamp", "fonte", "usuario", "via",
    "trecho", "distancia_m", "v_api_kmh",
    "t_hcm", "t_api", "t_base", "t_offset", "t_real"
]


def _garantir_cabecalho():
    path = os.path.abspath(CSV_PATH)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f, delimiter=";").writerow(CABECALHO)


def salvar_sessao(sessao: dict):
    """
    Salva todos os trechos de uma sessão de campo no CSV.
    sessao = {usuario, via_nome, trechos: [{trecho, t_hcm, t_api, t_base,
              t_offset, tempo_real, currentSpeed, distancia_m}]}
    """
    _garantir_cabecalho()
    path      = os.path.abspath(CSV_PATH)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        for t in sessao.get("trechos", []):
            writer.writerow([
                timestamp,
                "campo",
                sessao.get("usuario", ""),
                sessao.get("via_nome", ""),
                t.get("trecho", ""),
                round(t["distancia_m"], 1)  if t.get("distancia_m") else "",
                round(t["currentSpeed"], 1) if t.get("currentSpeed") else "",
                round(t["t_hcm"],   1)      if t.get("t_hcm")       else "",
                round(t["t_api"],   1)      if t.get("t_api")        else "",
                round(t["t_base"],  1)      if t.get("t_base")       else "",
                round(t["t_offset"],1)      if t.get("t_offset")     else "",
                round(t["tempo_real"],1)    if t.get("tempo_real")   else "",
            ])
