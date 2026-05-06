# ============================================================
# storage.py — Salva dados da sessão de campo no MySQL (Railway)
# ============================================================

from datetime import datetime, timezone, timedelta

BRASILIA = timezone(timedelta(hours=-3))
import mysql.connector
from mysql.connector import Error
from modules.config import get_secret


def _conectar():
    return mysql.connector.connect(
        host               = get_secret("MYSQL_HOST"),
        port               = int(get_secret("MYSQL_PORT")),
        database           = get_secret("MYSQL_DATABASE"),
        user               = get_secret("MYSQL_USER"),
        password           = get_secret("MYSQL_PASSWORD"),
        connection_timeout  = 30,
        autocommit          = False,
        ssl_verify_cert     = False,
        ssl_verify_identity = False,
    )


def salvar_sessao(sessao: dict):
    """
    Salva todos os trechos de uma sessão de campo no MySQL.
    sessao = {usuario, via_nome, trechos: [{trecho, t_hcm, t_api, t_base,
              t_offset, tempo_real, currentSpeed, distancia_m}]}
    """
    conn = None
    try:
        conn   = _conectar()
        cursor = conn.cursor()

        sql = """
            INSERT INTO offset_data
            (timestamp, fonte, usuario, via, trecho,
             distancia_m, v_api_kmh, t_hcm, t_api,
             t_base, t_offset, t_real)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        timestamp = datetime.now(BRASILIA)

        for t in sessao.get("trechos", []):
            cursor.execute(sql, (
                timestamp,
                "campo",
                sessao.get("usuario", ""),
                sessao.get("via_nome", ""),
                t.get("trecho", ""),
                round(t["distancia_m"],  1) if t.get("distancia_m")  else None,
                round(t["currentSpeed"], 1) if t.get("currentSpeed") else None,
                round(t["t_hcm"],        1) if t.get("t_hcm")        else None,
                round(t["t_api"],        1) if t.get("t_api")         else None,
                round(t["t_base"],       1) if t.get("t_base")        else None,
                round(t["t_offset"],     1) if t.get("t_offset")      else None,
                round(t["tempo_real"],   1) if t.get("tempo_real")    else None,
            ))

        conn.commit()
        return True, f"{cursor.rowcount} trechos salvos no banco de dados."

    except Error as e:
        return False, f"Erro ao salvar: {e}"

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
