# ============================================================
# pages/2_Campo.py — Modo campo (celular)
# ============================================================

import streamlit as st
import time
import uuid

from modules.vias import VIAS, USUARIOS
from modules.api import obter_distancia, consultar_tomtom, calcular_heading
from modules.calculos import (
    calcular_trecho_hcm, calcular_trecho_api,
    calcular_offset_final, estimar_fila,
)
from modules.storage import salvar_sessao
from modules.config import FILA_MINIMA

st.set_page_config(
    page_title="Modo Campo — Semáforo",
    page_icon="🏁",
    layout="centered",
)

st.markdown("""
<style>
    .block-container { padding: 1rem 1rem 2rem; max-width: 480px; margin: 0 auto; }
    .sem-card {
        background: #1e1e1e; border: 2px solid #2d2d2d;
        border-radius: 14px; padding: 20px; text-align: center; margin-bottom: 12px;
    }
    .sem-card.ativo   { border-color: #2563eb; background: #0f1f3d; }
    .sem-card.pausado { border-color: #d97706; background: #1c1410; }
    .sem-card.feito   { border-color: #34d399; background: #052e16; }
    .sem-card.aguarda { border-color: #374151; opacity: .5; }
    .sem-nome { font-size: 13px; color: #888; margin-bottom: 4px; }
    .sem-num  { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
    .tempo-box {
        background: #111; border-radius: 10px;
        padding: 12px 16px; margin: 8px 0; text-align: center;
    }
    .tempo-box.pausado-box { background: #1c1410; border: 2px solid #d97706; }
    .tempo-label { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing:.05em; }
    .tempo-value { font-size: 32px; font-weight: 700; }
    .tempo-unit  { font-size: 14px; color: #888; }
    .quatro-tempos {
        display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 12px 0;
    }
    .t-card {
        background: #111; border-radius: 10px; padding: 10px 12px; text-align: center;
    }
    .t-card.destaque {
        background: #0f2d1a; border: 2px solid #34d399; grid-column: 1 / -1;
    }
    .t-label { font-size: 10px; color: #666; text-transform: uppercase;
               letter-spacing:.05em; margin-bottom: 4px; }
    .t-value { font-size: 24px; font-weight: 700; }
    .t-sub   { font-size: 10px; color: #555; margin-top: 2px; }
    .resumo-card {
        background: #1e1e1e; border: 1px solid #2d2d2d;
        border-radius: 12px; padding: 14px 16px; margin-bottom: 10px;
    }
    .resumo-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: #e5e7eb; }
    .resumo-row { display: flex; justify-content: space-between; font-size: 13px;
                  padding: 4px 0; border-bottom: 1px solid #252525; }
    .resumo-row:last-child { border-bottom: none; }
    .rk { color: #888; }
    .rv { font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# ESTADO
# ============================================================

def reset_estado():
    st.session_state.campo_fase        = "selecao"
    st.session_state.campo_semaforo    = 0
    st.session_state.campo_t_inicio    = None
    st.session_state.campo_t_global    = None
    st.session_state.campo_t_pausado   = None
    st.session_state.campo_pausado     = False
    st.session_state.campo_trechos     = []
    st.session_state.campo_previstos   = []
    st.session_state.campo_sessao_id   = str(uuid.uuid4())

for k in ["campo_fase","campo_semaforo","campo_t_inicio","campo_t_global",
          "campo_t_pausado","campo_pausado","campo_trechos",
          "campo_previstos","campo_sessao_id"]:
    if k not in st.session_state:
        reset_estado()
        break

# ============================================================
# FASE 1 — SELEÇÃO
# ============================================================

if st.session_state.campo_fase == "selecao":
    st.markdown("# 🏁 Modo Campo")
    st.markdown("Cronometragem real entre semáforos para calibrar o modelo.")
    st.divider()

    usuario = st.selectbox("👤 Quem está testando?", USUARIOS)
    via_key = st.selectbox(
        "🛣️ Qual via?",
        options=list(VIAS.keys()),
        format_func=lambda k: f"{VIAS[k]['icone']} {VIAS[k]['nome']}"
    )
    via = VIAS[via_key]
    st.info(f"**{via['nome']}**\n\n{len(via['semaforos'])} semáforos → {len(via['semaforos'])-1} trechos")

    if st.button("▶ Preparar sessão", use_container_width=True, type="primary"):
        reset_estado()
        st.session_state.campo_usuario   = usuario
        st.session_state.campo_via_key   = via_key
        st.session_state.campo_via_nome  = via["nome"]
        st.session_state.campo_semaforos = via["semaforos"]
        st.session_state.campo_fase      = "preparando"
        st.rerun()

# ============================================================
# FASE 2 — PREPARANDO
# ============================================================

elif st.session_state.campo_fase == "preparando":
    st.markdown("# ⏳ Buscando dados das APIs...")
    semaforos = st.session_state.campo_semaforos
    via_key   = st.session_state.campo_via_key
    vel_via   = VIAS[via_key].get("vel_livre_kmh", 50)
    previstos = []
    progress  = st.progress(0)

    for i in range(len(semaforos) - 1):
        s1 = semaforos[i]
        s2 = semaforos[i + 1]
        progress.progress(int((i / (len(semaforos)-1)) * 100))

        cfg = {
            "n_lombadas":        s1.get("n_lombadas", 0),
            "vel_lombada_kmh":   s1.get("vel_lombada_kmh", 30),
            "n_pontos_atrito":   s1.get("n_pontos_atrito", 0),
            "nivel_atrito":      s1.get("nivel_atrito", "L"),
            "dist_influencia_m": s1.get("dist_influencia_m", 100),
        }

        dist    = obter_distancia(s1["lat"], s1["lon"], s2["lat"], s2["lon"])
        heading = calcular_heading(s1["lat"], s1["lon"], s2["lat"], s2["lon"])
        mid_lat = (s1["lat"] + s2["lat"]) / 2
        mid_lon = (s1["lon"] + s2["lon"]) / 2
        dados   = consultar_tomtom(mid_lat, mid_lon, heading)

        # Tempo teórico HCM
        t_hcm, _ = calcular_trecho_hcm(dist, vel_via, FILA_MINIMA, cfg)

        # Tempo API
        t_api = None
        v_api = None
        if dados:
            v_api = min(dados["currentSpeed"], vel_via)
            t_api, _ = calcular_trecho_api(dist, v_api, cfg)

        # Base de campo pré-preenchida
        tempos_base = VIAS[via_key].get("tempos_campo", [])
        t_base      = tempos_base[i] if i < len(tempos_base) else None

        # Offset final
        t_offset, origem = calcular_offset_final(t_base, t_api)

        previstos.append({
            "trecho":        f"{s1['nome']} → {s2['nome']}",
            "t_hcm":         t_hcm,
            "t_api":         t_api,
            "t_base":        t_base,
            "t_offset":      t_offset,
            "origem_offset": origem,
            "currentSpeed":  v_api,
            "freeFlowSpeed": min(dados["freeFlowSpeed"], vel_via) if dados else None,
            "confidence":    dados["confidence"] if dados else None,
            "distancia_m":   round(dist),
            "cfg":           cfg,
        })

    progress.progress(100)
    st.session_state.campo_previstos = previstos
    st.session_state.campo_fase      = "correndo"
    st.rerun()

# ============================================================
# FASE 3 — CORRENDO
# ============================================================

elif st.session_state.campo_fase == "correndo":
    semaforos = st.session_state.campo_semaforos
    previstos = st.session_state.campo_previstos
    idx       = st.session_state.campo_semaforo
    n_sem     = len(semaforos)
    pausado   = st.session_state.campo_pausado

    st.markdown(f"### 🚦 {st.session_state.campo_via_nome}")
    st.caption(f"👤 {st.session_state.campo_usuario}")
    st.divider()

    # Trechos concluídos
    for t in st.session_state.campo_trechos:
        t_off    = t.get("t_offset")
        diff     = round(t["tempo_real"] - t_off, 1) if t_off else None
        cor_diff = "#34d399" if diff is not None and abs(diff) <= 5 else (
                   "#fbbf24" if diff is not None and abs(diff) <= 15 else "#f87171")
        st.markdown(f"""
        <div class="sem-card feito">
          <div class="sem-nome">{t['trecho']}</div>
          <div style="display:flex;justify-content:space-around;margin-top:8px">
            <div><div class="tempo-label">Meta</div>
                 <div class="tempo-value" style="font-size:20px;color:#34d399">{f"{t_off:.0f}s" if t_off else "—"}</div></div>
            <div><div class="tempo-label">Real</div>
                 <div class="tempo-value" style="font-size:20px;color:#60a5fa">{t['tempo_real']:.1f}s</div></div>
            <div><div class="tempo-label">Δ</div>
                 <div class="tempo-value" style="font-size:20px;color:{cor_diff}">{f"{diff:+.1f}s" if diff is not None else "—"}</div></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Semáforo atual
    if idx < n_sem:
        sem_atual   = semaforos[idx]
        is_primeiro = (idx == 0)
        is_ultimo   = (idx == n_sem - 1)

        if is_ultimo:
            st.markdown(f"""
            <div class="sem-card ativo">
              <div class="sem-nome">🏁 CHEGADA FINAL</div>
              <div class="sem-num">{sem_atual['nome']}</div>
            </div>""", unsafe_allow_html=True)
            if st.session_state.campo_t_inicio:
                t_acum = st.session_state.campo_t_pausado or 0
                t_real = t_acum + (time.time() - st.session_state.campo_t_inicio)
                prev   = previstos[idx - 1]
                st.session_state.campo_trechos.append({
                    "trecho": prev["trecho"], "t_hcm": prev["t_hcm"],
                    "t_api": prev["t_api"], "t_base": prev["t_base"],
                    "t_offset": prev["t_offset"], "tempo_real": round(t_real, 1),
                    "currentSpeed": prev["currentSpeed"],
                    "freeFlowSpeed": prev["freeFlowSpeed"],
                    "confidence": prev["confidence"],
                    "distancia_m": prev["distancia_m"],
                })
                st.session_state.campo_t_inicio  = None
                st.session_state.campo_t_pausado = None
                st.session_state.campo_pausado   = False
                st.session_state.campo_fase      = "fim"
                st.rerun()
        else:
            card_class = "pausado" if pausado else "ativo"
            label_card = "⏸ SEMÁFORO FECHADO" if pausado else ("🚀 PARTIDA" if is_primeiro else "📍 Semáforo atual")
            st.markdown(f"""
            <div class="sem-card {card_class}">
              <div class="sem-nome">{label_card}</div>
              <div class="sem-num">{sem_atual['nome']}</div>
            </div>""", unsafe_allow_html=True)

            prev     = previstos[idx]
            t_hcm    = prev.get("t_hcm")
            t_api    = prev.get("t_api")
            t_base   = prev.get("t_base")
            t_offset = prev.get("t_offset")
            vel_str  = f"{prev['currentSpeed']} km/h" if prev.get("currentSpeed") else "sem dados"

            st.markdown(f"""
            <div class="quatro-tempos">
              <div class="t-card">
                <div class="t-label">Teórico calculado</div>
                <div class="t-value" style="color:#94a3b8">{f"{t_hcm:.0f}s" if t_hcm else "—"}</div>
                <div class="t-sub">HCM + PHF</div>
              </div>
              <div class="t-card">
                <div class="t-label">Dados API</div>
                <div class="t-value" style="color:#60a5fa">{f"{t_api:.0f}s" if t_api else "—"}</div>
                <div class="t-sub">{vel_str}</div>
              </div>
              <div class="t-card">
                <div class="t-label">Base sem trânsito</div>
                <div class="t-value" style="color:#fbbf24">{f"{t_base:.0f}s" if t_base else "—"}</div>
                <div class="t-sub">campo normal</div>
              </div>
              <div class="t-card destaque">
                <div class="t-label">⏱ Meta do trecho</div>
                <div class="t-value" style="font-size:32px;color:#34d399">{f"{t_offset:.0f}s" if t_offset else "—"}</div>
                <div class="t-sub">{prev.get("origem_offset","")}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.campo_t_inicio:
                t_acum   = st.session_state.campo_t_pausado or 0
                elapsed  = t_acum + (0 if pausado else (time.time() - st.session_state.campo_t_inicio))
                meta     = t_offset or 9999
                cor_crono = "#d97706" if pausado else ("#34d399" if elapsed <= meta else "#f87171")
                label_crono = "⏸ Pausado — semáforo fechado" if pausado else "⏱ Tempo rodando"

                st.markdown(f"""
                <div class="tempo-box {'pausado-box' if pausado else ''}">
                  <div class="tempo-label">{label_crono}</div>
                  <div class="tempo-value" style="color:{cor_crono}">{elapsed:.1f}<span class="tempo-unit">s</span></div>
                </div>""", unsafe_allow_html=True)

                proximo_nome = semaforos[idx + 1]['nome']
                is_penultimo = (idx == n_sem - 2)
                col_next, col_pause = st.columns([2, 1])

                with col_next:
                    btn_label = "🏁 Cheguei — FINALIZAR!" if is_penultimo else f"📍 Cheguei no {proximo_nome}!"
                    if st.button(btn_label, use_container_width=True, type="primary"):
                        t_real = (st.session_state.campo_t_pausado or 0) + (
                            time.time() - st.session_state.campo_t_inicio)
                        st.session_state.campo_trechos.append({
                            "trecho": prev["trecho"], "t_hcm": prev["t_hcm"],
                            "t_api": prev["t_api"], "t_base": prev["t_base"],
                            "t_offset": prev["t_offset"], "tempo_real": round(t_real, 1),
                            "currentSpeed": prev["currentSpeed"],
                            "freeFlowSpeed": prev["freeFlowSpeed"],
                            "confidence": prev["confidence"],
                            "distancia_m": prev["distancia_m"],
                        })
                        if is_penultimo:
                            st.session_state.campo_t_inicio  = None
                            st.session_state.campo_t_pausado = None
                            st.session_state.campo_pausado   = False
                            st.session_state.campo_fase      = "fim"
                        else:
                            st.session_state.campo_semaforo += 1
                            st.session_state.campo_t_inicio  = time.time()
                            st.session_state.campo_t_pausado = None
                            st.session_state.campo_pausado   = False
                        st.rerun()

                with col_pause:
                    if pausado:
                        if st.button("▶ Semáforo abriu — INICIAR!", use_container_width=True, type="primary"):
                            st.session_state.campo_t_inicio  = time.time()
                            st.session_state.campo_t_pausado = None
                        st.session_state.campo_pausado   = False
                        st.rerun()
                    else:
                        
                        if st.button("⏸ Pausar", use_container_width=True):
                            t_real = (st.session_state.campo_t_pausado or 0) + (
                                time.time() - st.session_state.campo_t_inicio)
                            st.session_state.campo_trechos.append({
                                "trecho": prev["trecho"], "t_hcm": prev["t_hcm"],
                                "t_api": prev["t_api"], "t_base": prev["t_base"],
                                "t_offset": prev["t_offset"], "tempo_real": round(t_real, 1),
                                "currentSpeed": prev["currentSpeed"],
                                "freeFlowSpeed": prev["freeFlowSpeed"],
                                "confidence": prev["confidence"],
                                "distancia_m": prev["distancia_m"],
                            })
                            st.session_state.campo_semaforo += 1
                            st.session_state.campo_t_inicio  = None
                            st.session_state.campo_t_pausado = None
                            st.session_state.campo_pausado   = True
                            st.rerun()

                if not pausado:
                    time.sleep(1)
                    st.rerun()

            else:
                btn_label = "🚀 Semáforo abriu — INICIAR!" if is_primeiro else "📍 Cheguei — INICIAR trecho!"
                if st.button(btn_label, use_container_width=True, type="primary"):
                    if st.session_state.campo_t_global is None:
                        st.session_state.campo_t_global = time.time()
                    st.session_state.campo_t_inicio  = time.time()
                    st.session_state.campo_t_pausado = None
                    st.session_state.campo_pausado   = False
                    st.rerun()

    for j in range(idx + 1, n_sem):
        if j > idx + 1:
            st.markdown(f"""
            <div class="sem-card aguarda">
              <div class="sem-nome">Aguardando</div>
              <div class="sem-num" style="font-size:16px">{semaforos[j]['nome']}</div>
            </div>""", unsafe_allow_html=True)

    st.divider()
    if st.button("↩ Cancelar sessão", use_container_width=True):
        reset_estado()
        st.rerun()

# ============================================================
# FASE 4 — FIM
# ============================================================

elif st.session_state.campo_fase == "fim":
    trechos = st.session_state.campo_trechos

    st.markdown("# 🏁 Sessão concluída!")
    st.markdown(f"**{st.session_state.campo_via_nome}**")
    st.caption(f"👤 {st.session_state.campo_usuario}")
    st.divider()

    for t in trechos:
        t_off = t.get("t_offset")
        diff  = round(t["tempo_real"] - t_off, 1) if t_off else None
        icone = "✅" if diff is not None and abs(diff) <= 5 else (
                "⚠️" if diff is not None and abs(diff) <= 15 else "❌")
        cor   = "#34d399" if diff is not None and abs(diff) <= 5 else (
                "#fbbf24" if diff is not None and abs(diff) <= 15 else "#f87171")

        st.markdown(f"""
        <div class="resumo-card">
          <div class="resumo-title">{icone} {t['trecho']}</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:10px">
            <div class="t-card">
              <div class="t-label">Teórico calculado</div>
              <div class="t-value" style="font-size:18px;color:#94a3b8">{f"{t['t_hcm']:.0f}s" if t.get("t_hcm") else "—"}</div>
            </div>
            <div class="t-card">
              <div class="t-label">Dados API</div>
              <div class="t-value" style="font-size:18px;color:#60a5fa">{f"{t['t_api']:.0f}s" if t.get("t_api") else "—"}</div>
            </div>
            <div class="t-card">
              <div class="t-label">Base sem trânsito</div>
              <div class="t-value" style="font-size:18px;color:#fbbf24">{f"{t['t_base']:.0f}s" if t.get("t_base") else "—"}</div>
            </div>
            <div class="t-card" style="background:#0f2d1a;border:2px solid #34d399">
              <div class="t-label">Meta do trecho</div>
              <div class="t-value" style="font-size:18px;color:#34d399">{f"{t_off:.0f}s" if t_off else "—"}</div>
            </div>
          </div>
          <div class="resumo-row"><span class="rk">Tempo real</span>
               <span class="rv" style="color:#60a5fa">{t['tempo_real']:.1f}s</span></div>
          <div class="resumo-row"><span class="rk">Diferença (real − meta)</span>
               <span class="rv" style="color:{cor}">{f"{diff:+.1f}s" if diff is not None else "—"}</span></div>
          <div class="resumo-row"><span class="rk">Distância</span>
               <span class="rv">{t.get('distancia_m','—')}m</span></div>
          <div class="resumo-row"><span class="rk">Velocidade API</span>
               <span class="rv">{t.get('currentSpeed','—')} km/h</span></div>
          <div class="resumo-row"><span class="rk">Confidence</span>
               <span class="rv">{t.get('confidence','—')}</span></div>
        </div>
        """, unsafe_allow_html=True)

    offs_validos = [t for t in trechos if t.get("t_offset")]
    if offs_validos:
        erro = sum(abs(t["tempo_real"] - t["t_offset"]) for t in offs_validos) / len(offs_validos)
        cor  = "#34d399" if erro <= 5 else ("#fbbf24" if erro <= 15 else "#f87171")
        st.markdown(f"""
        <div class="tempo-box">
          <div class="tempo-label">Erro médio vs meta</div>
          <div class="tempo-value" style="color:{cor}">{erro:.1f}<span class="tempo-unit">s</span></div>
        </div>""", unsafe_allow_html=True)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Salvar sessão", use_container_width=True, type="primary"):
            salvar_sessao({
                "usuario":  st.session_state.campo_usuario,
                "via_nome": st.session_state.campo_via_nome,
                "trechos":  trechos,
            })
            st.success("✅ Salvo no CSV!")
    with col2:
        if st.button("🔄 Nova sessão", use_container_width=True):
            reset_estado()
            st.rerun()
