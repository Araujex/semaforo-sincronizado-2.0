# ============================================================
# vias.py — Definição das vias e semáforos
# ============================================================

VIAS = {
    "pio_xii_descendo": {
        "nome":          "Av. Pio XII — Descendo sentido Rafard",
        "icone":         "⬇️",
        "vel_livre_kmh": 50,
        "tempos_campo":  [30, 60],
        "semaforos": [
            {"nome": "Semáforo Capifer", "lat": -22.996986, "lon": -47.513359,
             "n_lombadas": 2, "vel_lombada_kmh": 25, "n_pontos_atrito": 1,
             "nivel_atrito": "M", "dist_influencia_m": 100},
            {"nome": "Semáforo Sky Fit", "lat": -22.999687, "lon": -47.516329,
             "n_lombadas": 2, "vel_lombada_kmh": 25, "n_pontos_atrito": 1,
             "nivel_atrito": "M", "dist_influencia_m": 100},
            {"nome": "Semáforo Smash Agro", "lat": -23.003839, "lon": -47.520074,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0,
             "nivel_atrito": "L", "dist_influencia_m": 100},
        ],
    },
    "pio_xii_subindo": {
        "nome":          "Av. Pio XII — Subindo sentido Body Gym",
        "icone":         "⬆️",
        "vel_livre_kmh": 50,
        "tempos_campo":  [30, 24, 40, 70],
        "semaforos": [
            {"nome": "Semáforo 1", "lat": -23.004029, "lon": -47.520051,
             "n_lombadas": 2, "vel_lombada_kmh": 25, "n_pontos_atrito": 1,
             "nivel_atrito": "M", "dist_influencia_m": 100},
            {"nome": "Semáforo 2", "lat": -23.001623, "lon": -47.517960,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 1,
             "nivel_atrito": "L", "dist_influencia_m": 100},
            {"nome": "Semáforo 3", "lat": -23.000217, "lon": -47.516666,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0,
             "nivel_atrito": "L", "dist_influencia_m": 100},
            {"nome": "Semáforo 4", "lat": -22.997462, "lon": -47.513925,
             "n_lombadas": 2, "vel_lombada_kmh": 25, "n_pontos_atrito": 5,
             "nivel_atrito": "M", "dist_influencia_m": 200},
            {"nome": "Semáforo 5", "lat": -22.994663, "lon": -47.509464,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0,
             "nivel_atrito": "L", "dist_influencia_m": 100},
        ],
    },
    "padre_fabiano_descendo": {
        "nome":          "Rua Padre Fabiano — Descendo",
        "icone":         "⬇️",
        "vel_livre_kmh": 40,
        "tempos_campo":  [32, 9, 9, 9],
        "semaforos": [
            {"nome": "Semáforo 1", "lat": -22.995611, "lon": -47.505155,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0,
             "nivel_atrito": "L", "dist_influencia_m": 100},
            {"nome": "Semáforo 2", "lat": -22.998457, "lon": -47.505164,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0,
             "nivel_atrito": "L", "dist_influencia_m": 100},
            {"nome": "Semáforo 3", "lat": -22.999346, "lon": -47.505163,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0,
             "nivel_atrito": "L", "dist_influencia_m": 100},
            {"nome": "Semáforo 4", "lat": -23.000262, "lon": -47.505204,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0,
             "nivel_atrito": "L", "dist_influencia_m": 100},
            {"nome": "Semáforo 5", "lat": -23.001175, "lon": -47.505195,
             "n_lombadas": 0, "vel_lombada_kmh": 30, "n_pontos_atrito": 0,
             "nivel_atrito": "L", "dist_influencia_m": 100},
        ],
    },
}

USUARIOS = ["Araújo", "Rato", "Igor", "Porpa"]
