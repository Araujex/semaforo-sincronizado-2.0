# ============================================================
# api.py — HERE + TomTom
# ============================================================

import requests
import math
from modules.config import HERE_API_KEY, TOMTOM_API_KEY, CONFIDENCE_MINIMA


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p = math.pi / 180
    a = (math.sin((lat2-lat1)*p/2)**2 +
         math.cos(lat1*p) * math.cos(lat2*p) * math.sin((lon2-lon1)*p/2)**2)
    return round(2 * R * math.asin(math.sqrt(a)), 1)


def obter_distancia(lat1, lon1, lat2, lon2):
    """HERE com fallback Haversine se rota suspeita (>1.5× linha reta)."""
    linha_reta = haversine(lat1, lon1, lat2, lon2)
    url = "https://router.hereapi.com/v8/routes"
    params = {"transportMode": "car", "origin": f"{lat1},{lon1}",
              "destination": f"{lat2},{lon2}", "return": "summary", "apiKey": HERE_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=5)
        if r.status_code != 200:
            return linha_reta
        routes = r.json().get("routes", [])
        if not routes:
            return linha_reta
        dist = routes[0]["sections"][0]["summary"]["length"]
        return linha_reta if dist > 1.5 * linha_reta else dist
    except Exception:
        return linha_reta


def calcular_heading(lat1, lon1, lat2, lon2):
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    return (math.degrees(math.atan2(dlon, dlat)) + 360) % 360


def consultar_tomtom(lat, lon, heading=None):
    """Retorna (currentSpeed, freeFlowSpeed, confidence) ou None."""
    url = (f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
           f"?key={TOMTOM_API_KEY}&point={lat},{lon}&unit=KMPH")
    if heading is not None:
        url += f"&heading={heading:.1f}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json().get("flowSegmentData", {})
        conf = data.get("confidence", 0)
        if conf < CONFIDENCE_MINIMA:
            return None
        return {
            "currentSpeed":  data.get("currentSpeed"),
            "freeFlowSpeed": data.get("freeFlowSpeed"),
            "confidence":    conf,
        }
    except Exception:
        return None
