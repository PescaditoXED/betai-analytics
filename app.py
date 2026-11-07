import streamlit as st
import math
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="BetAI Analytics Engine",
    page_icon="📊",
    layout="wide"
)

st.title("BetAI Analytics Engine")
st.markdown("### Motor Cuantitativo, The Odds API, API-Basketball y Detección de Valor")

tab_futbol, tab_tenis, tab_basquet, tab_beisbol, tab_tracker = st.tabs([
    "Fútbol", 
    "Tenis", 
    "Básquetbol", 
    "Béisbol",
    "Bet Tracker"
])

# --- INICIALIZACIÓN DE ESTADO ---
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = "d83e44aa89294c81b7943d6cb44bf72f"
if 'odds_api_key' not in st.session_state:
    st.session_state['odds_api_key'] = "6b04c0369c0191c0edc746f7ec0ad322"
if 'basketball_api_key' not in st.session_state:
    st.session_state['basketball_api_key'] = "2875bb03a44245194d8a38f59d9d849b"
if 'modo_fuente' not in st.session_state:
    st.session_state['modo_fuente'] = "Automático (API de Partidos)"
if 'liga_sel' not in st.session_state:
    st.session_state['liga_sel'] = "La Liga (España)"
if 'historial_apuestas' not in st.session_state:
    st.session_state['historial_apuestas'] = []

# ==========================================
# MÓDULO DE FÚTBOL (ÍNTEGRO)
# ==========================================
with tab_futbol:
    st.header("Módulo de Fútbol: Poisson, Contexto Completo, Cuotas US y Kelly")
    st.write("Sincronización automática de partidos y cuotas reales de mercado en Estados Unidos.")
    
    with st.expander("Configuración de Credenciales API", expanded=False):
        st.session_state['api_key'] = st.text_input(
            "API Key de football-data.org (Partidos)", 
            value=st.session_state['api_key']
        )
        st.session_state['odds_api_key'] = st.text_input(
            "API Key de The Odds API (Cuotas Reales)", 
            value=st.session_state['odds_api_key']
        )
        
        st.session_state['modo_fuente'] = st.radio(
            "Modo de entrada de datos:", 
            ["Automático (API de Partidos)", "Manual"],
            index=0 if st.session_state['modo_fuente'] == "Automático (API de Partidos)" else 1,
            key="modo_f_radio"
        )
        
        competencias = {
            "La Liga (España)": ("PD", "soccer_spain_la_liga"),
            "Premier League (Inglaterra)": ("PL", "soccer_epl"),
            "Serie A (Italia)": ("SA", "soccer_italy_serie_a"),
            "Bundesliga (Alemania)": ("BL1", "soccer_germany_bundesliga"),
            "Ligue 1 (Francia)": ("FL1", "soccer_france_ligue_one"),
            "UEFA Champions League": ("CL", "soccer_uefa_champs_league"),
            "UEFA Europa League": ("EL", "soccer_uefa_europa_league"),
            "Copa Libertadores": ("CLI", "soccer_copa_libertadores"),
            "Liga Profesional (Argentina)": ("APF", "soccer_argentina_primera_division"),
            "Brasileirão Série A (Brasil)": ("BSA", "soccer_brazil_campeonato"),
            "Eredivisie (Países Bajos)": ("DED", "soccer_netherlands_eredivisie"),
            "Primeira Liga (Portugal)": ("PPL", "soccer_portugal_primeira_liga")
        }
        
        lista_ligas = list(competencias.keys())
        idx_actual = lista_ligas.index(st.session_state['liga_sel']) if st.session_state['liga_sel'] in lista_ligas else 0
        
        st.session_state['liga_sel'] = st.selectbox(
            "Selecciona la competición:", 
            lista_ligas,
            index=idx_actual,
            key="sel_liga_f"
        )
        
        codigo_liga, odds_sport_key = competencias[st.session_state['liga_sel']]

    api_key_activa = st.session_state['api_key']
    odds_key_activa = st.session_state['odds_api_key']

    cuotas_por_partido = {}
    if odds_key_activa:
        try:
            url_odds = f"https://api.the-odds-api.com/v4/sports/{odds_sport_key}/odds/?apiKey={odds_key_activa}®ions=us&markets=h2h&oddsFormat=decimal"
            resp_odds = requests.get(url_odds, timeout=5)
            if resp_odds.status_code == 200:
                data_odds = resp_odds.json()
                for evento in data_odds:
                    h_team = evento.get("home_team", "").lower()
                    a_team = evento.get("away_team", "").lower()
                    bookmakers = evento.get("bookmakers", [])
                    if bookmakers:
                        bookmaker_dict = {}
                        for bm in bookmakers:
                            bm_title = bm.get("title")
                            markets = bm.get("markets", [])
                            for m in markets:
                                if m.get("key") == "h2h":
                                    outcomes = m.get("outcomes", [])
                                    o_dict = {}
                                    for out in outcomes:
                                        o_dict[out.get("name").lower()] = out.get("price")
                                    bookmaker_dict[bm_title] = o_dict
                        cuotas_por_partido[(h_team, a_team)] = bookmaker_dict
        except Exception as e:
            pass

    st.markdown("---")
    st.subheader("Análisis Individual de Partido (Poisson, Contexto y Mitades)")

    local = "Sevilla"
    visitante = "Alaves"
    xg_local_base = 1.75
    xg_visitante_base = 1.20
    form_local_str, form_vis_str = "N/D", "N/D"

    if st.session_state['modo_fuente'] == "Automático (API de Partidos)" and api_key_activa:
        try:
            headers = {"X-Auth-Token": api_key_activa}
            url_partidos = f"https://api.football-data.org/v4/competitions/{codigo_liga}/matches?status=SCHEDULED"
            response_p = requests.get(url_partidos, headers=headers, timeout=5)
            
            team_forms = {}
            try:
                url_standings = f"https://api.football-data.org/v4/competitions/{codigo_liga}/standings"
                response_s = requests.get(url_standings, headers=headers, timeout=5)
                if response_s.status_code == 200:
                    data_s = response_s.json()
                    for table_type in data_s.get("standings", []):
                        for row in table_type.get("table", []):
                            t_name = row.get('team', {}).get('name')
                            t_form = row.get('form')
                            if t_name:
                                team_forms[t_name] = t_form if t_form else "N/D"
            except:
                pass

            if response_p.status_code == 200:
                data_p = response_p.json()
                matches = data_p.get("matches", [])
                
                if matches:
                    dict_partidos = {f"{m['homeTeam']['name']} vs {m['awayTeam']['name']} ({m['utcDate'][:10]})": m for m in matches}
                    lista_nombres = list(dict_partidos.keys())
                    
                    partido_elegido = st.selectbox(f"Partidos próximos en {st.session_state['liga_sel']}:", lista_nombres, key="p_sel_f")
                    
                    match_obj = dict_partidos[partido_elegido]
                    local = match_obj['homeTeam']['name']
                    visitante = match_obj['awayTeam']['name']
                    
                    form_local_str = team_forms.get(local, "N/D")
                    form_vis_str = team_forms.get(visitante, "N/D")
                    
                    st.success(f"Partido sincronizado: **{local}** vs **{visitante}**")
                else:
                    st.warning("No hay partidos programados próximamente para esta competición.")
            else:
                st.error("Error al conectar con la API de partidos.")
        except Exception as e:
            st.error(f"Error de conexión: {e}")
    else:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            local = st.text_input("Equipo Local", "Sevilla", key="loc_m_f")
        with col_m2:
            visitante = st.text_input("Equipo Visitante", "Alaves", key="vis_m_f")

    st.markdown("---")
    st.subheader("Factores Contextuales y Estado de Forma")

    with st.expander("Ver Estado de Forma y Ajustes Opcionales", expanded=True):
        fc1, fc2 = st.columns(2)
        
        with fc1:
            st.markdown(f"**{local} (Local)**")
            xg_l_input = st.number_input("xG Base Local", min_value=0.1, max_value=5.0, value=xg_local_base, step=0.05, key="xg_l")
            
            if form_local_str and form_local_str != "N/D":
                st.text(f"Forma API (Últimos 5): {form_local_str}")
                f_limpio_l = form_local_str.replace(",", "").upper()
                wins_l = f_limpio_l.count('W')
                ajuste_forma_l = 0.15 if wins_l >= 4 else (0.0 if wins_l >= 2 else -0.15)
            else:
                forma_man_l = st.selectbox("Seleccionar forma manual (Local):", ["Excelente (4-5 Victorias)", "Estable (2-3 Victorias)", "Irregular / Malo"], index=1, key="fm_l")
                ajuste_forma_l = 0.15 if "Excelente" in forma_man_l else (0.0 if "Estable" in forma_man_l else -0.15)

            bajas_local = st.selectbox("Bajas Clave (Local)", ["Sin bajas importantes", "Baja sensible en defensa", "Baja sensible en ataque (Goleador)"], index=0, key="b_loc")
            
        with fc2:
            st.markdown(f"**{visitante} (Visitante)**")
            xg_v_input = st.number_input("xG Base Visitante", min_value=0.1, max_value=5.0, value=xg_visitante_base, step=0.05, key="xg_v")
            
            if form_vis_str and form_vis_str != "N/D":
                st.text(f"Forma API (Últimos 5): {form_vis_str}")
                f_limpio_v = form_vis_str.replace(",", "").upper()
                wins_v = f_limpio_v.count('W')
                ajuste_forma_v = 0.15 if wins_v >= 4 else (0.0 if wins_v >= 2 else -0.15)
            else:
                forma_man_v = st.selectbox("Seleccionar forma manual (Visitante):", ["Excelente (4-5 Victorias)", "Estable (2-3 Victorias)", "Irregular / Malo"], index=1, key="fm_v")
                ajuste_forma_v = 0.15 if "Excelente" in forma_man_v else (0.0 if "Estable" in forma_man_v else -0.15)

            bajas_vis = st.selectbox("Bajas Clave (Visitante)", ["Sin bajas importantes", "Baja sensible en defensa", "Baja sensible en ataque (Goleador)"], index=0, key="b_vis")

        st.markdown("---")
        cc_a, cc_b, cc_c = st.columns(3)
        with cc_a:
            clima = st.selectbox("Condiciones Climáticas", ["Normal / Óptimo", "Lluvia intensa / Canto Pesado", "Temperatura Extrema / Altitud"], index=0, key="clima_f")
        with cc_b:
            factor_h2h = st.selectbox("Historial H2H reciente", ["Neutral", f"Dominio histórico de {local}", f"Dominio histórico de {visitante}", "Tendencia a empates / partidos cerrados"], index=0, key="h2h_f")
        with cc_c:
            importancia_duelo = st.selectbox("Contexto / Motivación", ["Liga regular estándar", "Clásico / Rivalidad directa", "Necesidad absoluta de puntos (Descenso/Título)"], index=0, key="ctx_f")

    ajuste_l = ajuste_forma_l
    ajuste_v = ajuste_forma_v

    if "ataque" in bajas_local: ajuste_l -= 0.20
    if "defensa" in bajas_local: ajuste_v += 0.10
    if "ataque" in bajas_vis: ajuste_v -= 0.20
    if "defensa" in bajas_vis: ajuste_l += 0.10

    if "Lluvia" in clima:
        ajuste_l -= 0.10
        ajuste_v -= 0.10

    if local in factor_h2h: ajuste_l += 0.10
    elif visitante in factor_h2h: ajuste_v += 0.10

    xg_local_final = max(0.1, xg_l_input + ajuste_l)
    xg_visitante_final = max(0.1, xg_v_input + ajuste_v)

    st.info(f"xG Ajustados (Forma + Contexto) -> **{local}: {xg_local_final:.2f}** | **{visitante}: {xg_visitante_final:.2f}**")
        
    st.markdown("---")
    
    if st.button("Ejecutar Modelo Matemático Avanzado (Fútbol)", key="btn_exec_f"):
        def poisson_prob(lmbda, k):
            return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)

        matriz_prob = {}
        for g_loc in range(8):
            for g_vis in range(8):
                matriz_prob[(g_loc, g_vis)] = poisson_prob(xg_local_final, g_loc) * poisson_prob(xg_visitante_final, g_vis)

        p_loc, p_emp, p_vis = 0.0, 0.0, 0.0
        for (g_loc, g_vis), p in matriz_prob.items():
            if g_loc > g_vis: p_loc += p
            elif g_loc == g_vis: p_emp += p
            else: p_vis += p

        st.session_state['matriz'] = matriz_prob
        st.session_state['p_loc'] = p_loc
        st.session_state['p_emp'] = p_emp
        st.session_state['p_vis'] = p_vis
        st.session_state['xg_l_fin'] = xg_local_final
        st.session_state['xg_v_fin'] = xg_visitante_final
        st.session_state['calculado'] = True

    if st.session_state.get('calculado', False):
        matriz = st.session_state['matriz']
        p_loc = st.session_state['p_loc']
        p_emp = st.session_state['p_emp']
        p_vis = st.session_state['p_vis']
        xg_l_f = st.session_state['xg_l_fin']
        xg_v_f = st.session_state['xg_v_fin']

        match_bookmakers = {}
        for (k_home, k_away), bm_dict in cuotas_por_partido.items():
            if local.lower() in k_home or k_home in local.lower() or \
               visitante.lower() in k_away or k_away in visitante.lower():
                match_bookmakers = bm_dict
                break

        cuota_real_local, cuota_real_empate, cuota_real_visita = None, None, None
        casa_elegida_nombre = "Ninguna (Solo Cuota Justa)"

        if match_bookmakers:
            lista_casas = list(match_bookmakers.keys())
            casa_elegida_nombre = st.selectbox("🌐 Selecciona la Casa de Apuestas US (DraftKings, FanDuel, etc.):", lista_casas, key="c_us_f")
            odds_casa = match_bookmakers[casa_elegida_nombre]
            
            for t_name, price in odds_casa.items():
                if local.lower() in t_name or t_name in local.lower():
                    cuota_real_local = price
                elif visitante.lower() in t_name or t_name in visitante.lower():
                    cuota_real_visita = price
                elif t_name in ["draw", "empate"]:
                    cuota_real_empate = price

        st.subheader("Probabilidades y Cuotas de Mercado US (1X2)")
        m1, m2, m3 = st.columns(3)
        c_l_disp = f"Cuota Casa US: {cuota_real_local}" if cuota_real_local else f"Cuota Justa: {1/p_loc:.2f}"
        c_e_disp = f"Cuota Casa US: {cuota_real_empate}" if cuota_real_empate else f"Cuota Justa: {1/p_emp:.2f}"
        c_v_disp = f"Cuota Casa US: {cuota_real_visita}" if cuota_real_visita else f"Cuota Justa: {1/p_vis:.2f}"

        m1.metric(f"Victoria {local} (1)", f"{p_loc*100:.1f}%", c_l_disp)
        m2.metric("Empate (X)", f"{p_emp*100:.1f}%", c_e_disp)
        m3.metric(f"Victoria {visitante} (2)", f"{p_vis*100:.1f}%", c_v_disp)

        st.markdown("---")
        st.subheader("Análisis por Mitades (1T vs 2T) - Líneas 0.5 a 2.5")
        xg_l_1t, xg_v_1t = xg_l_f * 0.40, xg_v_f * 0.40
        xg_l_2t, xg_v_2t = xg_l_f * 0.60, xg_v_f * 0.60
        lam_total_1t = xg_l_1t + xg_v_1t
        lam_total_2t = xg_l_2t + xg_v_2t

        def poisson_p_simple(lmbda, k):
            return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)

        lineas_mitades = [0.5, 1.5, 2.5]
        hm1, hm2 = st.columns(2)
        with hm1:
            st.markdown(f"**Primer Tiempo (1T)** | xG Est. 1T: {xg_l_1t:.2f} - {xg_v_1t:.2f}")
            for lin in lineas_mitades:
                p_under = sum(poisson_p_simple(lam_total_1t, k) for k in range(int(lin) + 1))
                p_over = 1.0 - p_under
                st.text(f"Más/Menos {lin} (1T) -> OVER: {p_over*100:.1f}% | UNDER: {p_under*100:.1f}%")
        with hm2:
            st.markdown(f"**Segundo Tiempo (2T)** | xG Est. 2T: {xg_l_2t:.2f} - {xg_v_2t:.2f}")
            for lin in lineas_mitades:
                p_under = sum(poisson_p_simple(lam_total_2t, k) for k in range(int(lin) + 1))
                p_over = 1.0 - p_under
                st.text(f"Más/Menos {lin} (2T) -> OVER: {p_over*100:.1f}% | UNDER: {p_under*100:.1f}%")

        st.markdown("---")
        st.subheader("Listado de Hándicaps (hasta ±3.5)")
        lineas_handicap = [-3.5, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0, +0.5, +1.0, +1.5, +2.0, +2.5, +3.0, +3.5]
        col_h_local, col_h_vis = st.columns(2)

        with col_h_local:
            st.markdown(f"**{local} (Local)**")
            for h in lineas_handicap:
                prob_ganada, prob_push = 0.0, 0.0
                for (g_loc, g_vis), p in matriz.items():
                    ajuste = g_loc + h
                    if ajuste > g_vis: prob_ganada += p
                    elif ajuste == g_vis: prob_push += p
                prob_efectiva = prob_ganada / (1.0 - prob_push) if (1.0 - prob_push) > 0 else prob_ganada
                cuota_justa = 1.0 / prob_efectiva if prob_efectiva > 0 else 0.0
                signo = "+" if h > 0 else ""
                push_txt = f" (Push: {prob_push*100:.1f}%)" if prob_push > 0 else ""
                st.text(f"HC {signo}{h}: {prob_ganada*100:.1f}%{push_txt} | Justa: {cuota_justa:.2f}")

        with col_h_vis:
            st.markdown(f"**{visitante} (Visitante)**")
            for h in lineas_handicap:
                prob_ganada, prob_push = 0.0, 0.0
                for (g_loc, g_vis), p in matriz.items():
                    ajuste = g_vis + h
                    if ajuste > g_loc: prob_ganada += p
                    elif ajuste == g_loc: prob_push += p
                prob_efectiva = prob_ganada / (1.0 - prob_push) if (1.0 - prob_push) > 0 else prob_ganada
                cuota_justa = 1.0 / prob_efectiva if prob_efectiva > 0 else 0.0
                signo = "+" if h > 0 else ""
                push_txt = f" (Push: {prob_push*100:.1f}%)" if prob_push > 0 else ""
                st.text(f"HC {signo}{h}: {prob_ganada*100:.1f}%{push_txt} | Justa: {cuota_justa:.2f}")

        st.markdown("---")
        st.subheader("Tiros de Esquina (Corners)")
        cc1, cc2 = st.columns(2)
        with cc1: corners_l = st.number_input(f"Promedio Córners ({local})", min_value=0.5, max_value=15.0, value=5.5, step=0.1, key="cor_l")
        with cc2: corners_v = st.number_input(f"Promedio Córners ({visitante})", min_value=0.5, max_value=15.0, value=4.2, step=0.1, key="cor_v")

        total_lambda_corners = corners_l + corners_v
        st.text(f"Total Córners Esperados: {total_lambda_corners:.2f}")
        for lin in [7.5, 8.5, 9.5, 10.5, 11.5]:
            prob_under = sum((math.exp(-total_lambda_corners) * (total_lambda_corners ** k)) / math.factorial(k) for k in range(int(lin) + 1))
            prob_over = 1.0 - prob_under
            col_l, col_o, col_u = st.columns(3)
            col_l.text(f"Línea {lin}")
            col_o.text(f"OVER: {prob_over*100:.1f}% | Justa: {1/prob_over:.2f}")
            col_u.text(f"UNDER: {prob_under*100:.1f}% | Justa: {1/prob_under:.2f}")

        st.markdown("---")
        st.subheader("Mercado BTTS (Ambos Equipos Anotan) y Goles Totales")
        prob_btts_yes = sum(p for (g_loc, g_vis), p in matriz.items() if g_loc > 0 and g_vis > 0)
        prob_btts_no = 1.0 - prob_btts_yes
        b1, b2 = st.columns(2)
        b1.text(f"BTTS SÍ: {prob_btts_yes*100:.1f}% | Justa: {1/prob_btts_yes:.2f}")
        b2.text(f"BTTS NO: {prob_btts_no*100:.1f}% | Justa: {1/prob_btts_no:.2f}")

        st.markdown("**Líneas de Goles Totales (Over / Under)**")
        prob_over_25 = 1.0 - sum(p for (g_loc, g_vis), p in matriz.items() if (g_loc + g_vis) <= 2.5)
        for lin in [0.5, 1.5, 2.5, 3.5, 4.5]:
            prob_under_g = sum(p for (g_loc, g_vis), p in matriz.items() if (g_loc + g_vis) <= lin)
            prob_over_g = 1.0 - prob_under_g
            g1, g2, g3 = st.columns(3)
            g1.text(f"Más/Menos {lin} Goles")
            g2.text(f"OVER: {prob_over_g*100:.1f}% | Justa: {1/prob_over_g:.2f}")
            g3.text(f"UNDER: {prob_under_g*100:.1f}% | Justa: {1/prob_under_g:.2f}")

        st.markdown("---")
        col_top, col_builder = st.columns(2)
        with col_top:
            st.subheader("Top 3 Oportunidades Beneficio/Riesgo")
            candidatos_mercados = [
                {"Mercado": f"Victoria {local}", "Probabilidad": p_loc, "Cuota Justa": 1/p_loc if p_loc > 0 else 0},
                {"Mercado": f"Victoria {visitante}", "Probabilidad": p_vis, "Cuota Justa": 1/p_vis if p_vis > 0 else 0},
                {"Mercado": "Empate (X)", "Probabilidad": p_emp, "Cuota Justa": 1/p_emp if p_emp > 0 else 0},
                {"Mercado": "Over 2.5 Goles", "Probabilidad": prob_over_25, "Cuota Justa": 1/prob_over_25 if prob_over_25 > 0 else 0},
                {"Mercado": "BTTS (Ambos Anotan SÍ)", "Probabilidad": prob_btts_yes, "Cuota Justa": 1/prob_btts_yes if prob_btts_yes > 0 else 0},
            ]
            for i, item in enumerate(sorted(candidatos_mercados, key=lambda x: x["Probabilidad"], reverse=True)[:3], 1):
                st.markdown(f"**{i}. {item['Mercado']}** (Prob: {item['Probabilidad']*100:.1f}% | Mínima: {item['Cuota Justa']:.2f})")

        with col_builder:
            st.subheader("Recomendaciones de Combinadas (Bet Builder)")
            eq_fav = local if p_loc > p_vis else visitante
            st.markdown(f"🔹 **Combinada 1:** Gana {eq_fav} + Over 1.5 Goles")
            st.markdown(f"🔹 **Combinada 2:** Ambos Anotan + Over 2.5 Goles")

        st.markdown("---")
        st.subheader("Calculadora de Valor Esperado (EV) y Criterio de Kelly")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            mercado_sel = st.selectbox(
                "Mercado a analizar:",
                [f"Victoria Local ({local})", "Empate (X)", f"Victoria Visitante ({visitante})"],
                key="merc_f_sel"
            )
        with c2:
            default_val = float(cuota_real_local) if (mercado_sel.startswith("Victoria Local") and cuota_real_local) else (
                          float(cuota_real_empate) if ("Empate" in mercado_sel and cuota_real_empate) else (
                          float(cuota_real_visita) if (mercado_sel.startswith("Victoria Visitante") and cuota_real_visita) else 2.10))
            
            cuota_ingresada = st.number_input("Cuota de la casa de apuestas:", min_value=1.01, value=default_val, step=0.01, key="cuota_f_in")
        with c3:
            bankroll_total = st.number_input("Capital Total ($ Bankroll):", min_value=10.0, value=1000.0, step=50.0, key="bk_f_in")

        prob_apuesta = p_loc if mercado_sel.startswith("Victoria Local") else (p_emp if "Empate" in mercado_sel else p_vis)
        ev_pct = ((prob_apuesta * cuota_ingresada) - 1) * 100

        b = cuota_ingresada - 1 
        kelly_fraction = (b * prob_apuesta - (1.0 - prob_apuesta)) / b if b > 0 else 0.0
        kelly_medio = max(0.0, kelly_fraction * 0.5)

        r1, r2, r3 = st.columns(3)
        r1.metric("Probabilidad Modelo", f"{prob_apuesta*100:.1f}%")
        r2.metric("Probabilidad Implícita Casa", f"{(1/cuota_ingresada)*100:.1f}%")
        r3.metric("Valor Esperado (EV)", f"{ev_pct:+.2f}%")

        if ev_pct >= 5.0:
            st.success(f"Apuesta con valor detectada. EV: +{ev_pct:.2f}% (Supera el filtro del 5%).")
            if st.button("Registrar Apuesta en Bet Tracker", key="btn_trk_f"):
                st.session_state['historial_apuestas'].append({
                    "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Partido": f"{local} vs {visitante}",
                    "Mercado": mercado_sel,
                    "Cuota": cuota_ingresada,
                    "Stake ($)": round(bankroll_total * kelly_medio, 2),
                    "EV (%)": round(ev_pct, 2),
                    "Estado": "Pendiente"
                })
                st.success("¡Apuesta registrada con éxito!")
        else:
            st.error(f"Sin valor suficiente. EV: {ev_pct:.2f}%.")


# ==========================================
# MÓDULO DE TENIS (RESTAURADOS HÁNDICAPS Y JUEGOS)
# ==========================================
with tab_tenis:
    st.header("Módulo de Tenis: Apuestas Recomendadas, Hándicaps y Juegos (1.70 - 2.20)")
    st.write("Análisis cuantitativo de tenis con apuestas recomendadas y líneas detalladas de hándicaps y juegos.")

    st.markdown("---")
    st.subheader("1. Identidad de los Tenistas y Ranking ATP/WTA")

    tc1, tc2 = st.columns(2)
    with tc1:
        tenista_1 = st.text_input("Tenista 1 (Favorito)", "Carlos Alcaraz", key="t1_n_pro")
        rank_t1 = st.number_input(f"Ranking ATP/WTA ({tenista_1})", min_value=1, max_value=500, value=2, step=1, key="rk_t1")
    with tc2:
        tenista_2 = st.text_input("Tenista 2 (Underdog)", "Taylor Fritz", key="t2_n_pro")
        rank_t2 = st.number_input(f"Ranking ATP/WTA ({tenista_2})", min_value=1, max_value=500, value=12, step=1, key="rk_t2")

    st.markdown("---")
    st.subheader("2. Rendimiento en Superficie y Estadísticas del Año")

    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown(f"**{tenista_1}**")
        win_rate_t1 = st.slider(f"% Victorias en esta Superficie ({tenista_1})", 10.0, 95.0, 82.0, 0.5, key="wr_t1")
        fatiga_t1 = st.selectbox(f"Desgaste Físico / Descanso ({tenista_1})", ["Descansado (Óptimo)", "Partido largo ayer (-3 horas)", "Acumulación de partidos / Cansado"], index=0, key="fat_t1")

    with sc2:
        st.markdown(f"**{tenista_2}**")
        win_rate_t2 = st.slider(f"% Victorias en esta Superficie ({tenista_2})", 10.0, 95.0, 68.0, 0.5, key="wr_t2")
        fatiga_t2 = st.selectbox(f"Desgaste Físico / Descanso ({tenista_2})", ["Descansado (Óptimo)", "Partido largo ayer (-3 horas)", "Acumulación de partidos / Cansado"], index=0, key="fat_t2")

    superficie_tenis = st.selectbox(
        "Superficie del Torneo:", 
        ["Dura (Hard)", "Arcilla / Tierra Batida (Clay)", "Hierba (Grass)"],
        key="sup_pro"
    )

    st.markdown("---")
    st.subheader("3. Historial Directo (H2H)")
    h2h_tenis = st.selectbox(
        "Historial H2H reciente entre ambos:",
        ["Neutral / Sin claro dominante", f"Dominio claro de {tenista_1}", f"Dominio claro de {tenista_2}"],
        index=0, key="h2h_pro"
    )

    if st.button("Ejecutar Motor de Tenis Pro", key="btn_exec_t"):
        factor_rank_1 = max(1.0, 100.0 / math.sqrt(rank_t1))
        factor_rank_2 = max(1.0, 100.0 / math.sqrt(rank_t2))
        
        base_fuerza_1 = factor_rank_1 * (win_rate_t1 / 100.0)
        base_fuerza_2 = factor_rank_2 * (win_rate_t2 / 100.0)

        if "ayer" in fatiga_t1: base_fuerza_1 *= 0.88
        elif "Cansado" in fatiga_t1: base_fuerza_1 *= 0.82

        if "ayer" in fatiga_t2: base_fuerza_2 *= 0.88
        elif "Cansado" in fatiga_t2: base_fuerza_2 *= 0.82

        if tenista_1 in h2h_tenis: base_fuerza_1 *= 1.12
        elif tenista_2 in h2h_tenis: base_fuerza_2 *= 1.12

        total_fuerza_t = base_fuerza_1 + base_fuerza_2
        prob_t1_final = base_fuerza_1 / total_fuerza_t
        prob_t2_final = base_fuerza_2 / total_fuerza_t

        st.session_state['tenis_calc_pro'] = True
        st.session_state['p_t1_pro'] = prob_t1_final
        st.session_state['p_t2_pro'] = prob_t2_final

    if st.session_state.get('tenis_calc_pro', False):
        pt1 = st.session_state['p_t1_pro']
        pt2 = st.session_state['p_t2_pro']
        t1 = tenista_1
        t2 = tenista_2

        st.subheader("Probabilidades y Cuotas del Partido (Tenis)")
        col_res1, col_res2 = st.columns(2)
        col_res1.metric(f"Victoria {t1}", f"{pt1*100:.1f}%", f"Cuota Justa: {1/pt1:.2f}")
        col_res2.metric(f"Victoria {t2}", f"{pt2*100:.1f}%", f"Cuota Justa: {1/pt2:.2f}")

        # --- APUESTAS RECOMENDADAS EXCLUSIVAS (1.70 - 2.20) ---
        st.markdown("---")
        st.subheader("⭐ Apuestas Recomendadas en Rango Atractivo (Cuotas 1.70 a 2.20)")
        st.write("Selección directa de líneas de beneficio/riesgo óptimo según el modelo cuantitativo.")
        
        candidatos_atractivos = []
        
        if 1.70 <= (1/pt1) <= 2.20:
            candidatos_atractivos.append({"Mercado": f"Victoria Simple: {t1}", "Prob": pt1, "Cuota": 1/pt1})
        if 1.70 <= (1/pt2) <= 2.20:
            candidatos_atractivos.append({"Mercado": f"Victoria Simple: {t2}", "Prob": pt2, "Cuota": 1/pt2})
            
        for hj in [-4.5, -3.5, -2.5, -1.5, +1.5, +2.5, +3.5, +4.5]:
            prob_h = max(0.05, min(0.95, pt1 + (hj * 0.03)))
            cuota_h = 1.0 / prob_h if prob_h > 0 else 0
            if 1.70 <= cuota_h <= 2.20:
                signo_h = "+" if hj > 0 else ""
                candidatos_atractivos.append({"Mercado": f"Hándicap de Juegos {signo_h}{hj} ({t1})", "Prob": prob_h, "Cuota": cuota_h})

        if candidatos_atractivos:
            for i, item in enumerate(sorted(candidatos_atractivos, key=lambda x: x["Prob"], reverse=True), 1):
                st.success(f"**{i}. {item['Mercado']}** -> Cuota Estimada: **{item['Cuota']:.2f}** (Prob. Modelo: {item['Prob']*100:.1f}%)")
        else:
            st.info("ℹ️ Para este emparejamiento exacto las líneas directas están fuera de 1.70-2.20. Revisa los hándicaps detallados abajo.")

        # --- HÁNDICAPS DE JUEGOS Y JUEGOS TOTALES RESTAURADOS ---
        st.markdown("---")
        st.subheader("Hándicaps de Juegos (Ambos Tenistas)")
        
        h_col_t1, h_col_t2 = st.columns(2)
        lineas_h_juegos = [-4.5, -3.5, -2.5, -1.5, +1.5, +2.5, +3.5, +4.5]
        
        with h_col_t1:
            st.markdown(f"**Hándicap de Juegos: {t1}**")
            for hj in lineas_h_juegos:
                prob_hj = max(0.05, min(0.95, pt1 + (hj * 0.03)))
                cuota_hj = 1.0 / prob_hj if prob_hj > 0 else 0.0
                signo_h = "+" if hj > 0 else ""
                atractivo_tag = " 🔥 [Rango 1.70-2.20]" if 1.70 <= cuota_hj <= 2.20 else ""
                st.text(f"HC {signo_h}{hj}: Prob. {prob_hj*100:.1f}% | Justa: {cuota_hj:.2f}{atractivo_tag}")

        with h_col_t2:
            st.markdown(f"**Hándicap de Juegos: {t2}**")
            for hj in lineas_h_juegos:
                prob_hj_2 = max(0.05, min(0.95, pt2 + (hj * 0.03)))
                cuota_hj_2 = 1.0 / prob_hj_2 if prob_hj_2 > 0 else 0.0
                signo_h = "+" if hj > 0 else ""
                atractivo_tag = " 🔥 [Rango 1.70-2.20]" if 1.70 <= cuota_hj_2 <= 2.20 else ""
                st.text(f"HC {signo_h}{hj}: Prob. {prob_hj_2*100:.1f}% | Justa: {cuota_hj_2:.2f}{atractivo_tag}")

        st.markdown("---")
        st.subheader("Líneas de Juegos Totales (Over / Under)")
        diferencia_prob = abs(pt1 - pt2)
        games_base_est = 23.5 - (diferencia_prob * 4.0)
        st.info(f"Promedio de Juegos Estimados para el Partido: **{games_base_est:.1f} Games**")
        
        for linea_g in [20.5, 21.5, 22.5, 23.5, 24.5]:
            diff_g = linea_g - games_base_est
            prob_over = max(0.05, min(0.95, 0.50 - (diff_g * 0.09)))
            prob_under = 1.0 - prob_over
            c_over = 1.0 / prob_over if prob_over > 0 else 0
            c_under = 1.0 / prob_under if prob_under > 0 else 0
            tag_o = " 🔥 [1.70-2.20]" if 1.70 <= c_over <= 2.20 else ""
            tag_u = " 🔥 [1.70-2.20]" if 1.70 <= c_under <= 2.20 else ""
            
            og1, og2, og3 = st.columns(3)
            og1.text(f"Línea {linea_g} Juegos")
            og2.text(f"OVER: {prob_over*100:.1f}% | Justa: {c_over:.2f}{tag_o}")
            og3.text(f"UNDER: {prob_under*100:.1f}% | Justa: {c_under:.2f}{tag_u}")

        # --- CALCULADORA DE VALOR Y KELLY (TENIS) ---
        st.markdown("---")
        st.subheader("Calculadora de Valor Esperado (EV) y Criterio de Kelly (Tenis)")
        
        tc_1, tc_2, tc_3 = st.columns(3)
        with tc_1:
            mercado_sel_t = st.selectbox(
                "Mercado de Tenis a analizar:",
                [f"Victoria {t1}", f"Victoria {t2}"],
                key="merc_t_sel"
            )
        with tc_2:
            default_val_t = float(1/pt1) if mercado_sel_t.startswith(f"Victoria {t1}") else float(1/pt2)
            cuota_ingresada_t = st.number_input("Cuota de la casa (Tenis):", min_value=1.01, value=round(default_val_t, 2), step=0.01, key="cit")
        with tc_3:
            bankroll_total_t = st.number_input("Capital Total ($ Bankroll - Tenis):", min_value=10.0, value=1000.0, step=50.0, key="btt")

        prob_apuesta_t = pt1 if mercado_sel_t.startswith(f"Victoria {t1}") else pt2
        ev_pct_t = ((prob_apuesta_t * cuota_ingresada_t) - 1) * 100

        b_t = cuota_ingresada_t - 1 
        kelly_frac_t = (b_t * prob_apuesta_t - (1.0 - prob_apuesta_t)) / b_t if b_t > 0 else 0.0
        kelly_medio_t = max(0.0, kelly_frac_t * 0.5)

        tr1, tr2, tr3 = st.columns(3)
        tr1.metric("Probabilidad Modelo (Tenis)", f"{prob_apuesta_t*100:.1f}%")
        tr2.metric("Probabilidad Implícita Casa", f"{(1/cuota_ingresada_t)*100:.1f}%")
        tr3.metric("Valor Esperado (EV - Tenis)", f"{ev_pct_t:+.2f}%")

        if ev_pct_t >= 5.0:
            st.success(f"Apuesta de tenis con valor detectada. EV: +{ev_pct_t:.2f}% (Supera el filtro del 5%).")
            if st.button("Registrar Apuesta de Tenis en Bet Tracker", key="btn_trk_t"):
                st.session_state['historial_apuestas'].append({
                    "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Partido": f"{t1} vs {t2}",
                    "Mercado": mercado_sel_t,
                    "Cuota": cuota_ingresada_t,
                    "Stake ($)": round(bankroll_total_t * kelly_medio_t, 2),
                    "EV (%)": round(ev_pct_t, 2),
                    "Estado": "Pendiente"
                })
                st.success("¡Apuesta de tenis registrada con éxito!")
        else:
            st.error(f"Sin valor suficiente en tenis. EV: {ev_pct_t:.2f}%.")


# ==========================================
# MÓDULO DE BÁSQUETBOL (CON PUNTOS POR EQUIPO AÑADIDOS)
# ==========================================
with tab_basquet:
    st.header("Módulo de Básquetbol Pro: API-Basketball, Puntos por Equipo, Forma y H2H")
    st.write("Análisis cuantitativo de básquetbol con sincronización API, puntos individuales por equipo y filtro de cuotas 1.70 a 2.20.")

    with st.expander("Configuración API de Básquetbol", expanded=False):
        st.session_state['basketball_api_key'] = st.text_input(
            "API Key de API-Basketball (API-Sports)", 
            value=st.session_state['basketball_api_key'],
            key="b_key_input"
        )
        modo_b_fuente = st.radio(
            "Modo de entrada de datos (Básquetbol):",
            ["Automático (API-Basketball)", "Manual"],
            index=0,
            key="modo_b_radio"
        )

    b_api_key_activa = st.session_state['basketball_api_key']
    
    b_local = "Los Angeles Lakers"
    b_visitante = "Boston Celtics"
    ppg_local = 114.5
    ppg_vis = 112.0

    if modo_b_fuente == "Automático (API-Basketball)" and b_api_key_activa:
        try:
            url_b_games = "https://v1.basketball.api-sports.io/games"
            headers_b = {
                'x-apisports-key': b_api_key_activa
            }
            today_str = datetime.now().strftime("%Y-%m-%d")
            params_b = {"date": today_str}
            
            resp_b = requests.get(url_b_games, headers=headers_b, params=params_b, timeout=5)
            if resp_b.status_code == 200:
                data_b = resp_b.json().get("response", [])
                if data_b:
                    dict_b_partidos = {f"{g['teams']['home']['name']} vs {g['teams']['away']['name']} ({g['date'][:10]})": g for g in data_b}
                    lista_b_nombres = list(dict_b_partidos.keys())
                    
                    partido_b_elegido = st.selectbox("Selecciona partido de Básquetbol:", lista_b_nombres, key="sel_part_b")
                    match_b_obj = dict_b_partidos[partido_b_elegido]
                    
                    b_local = match_b_obj['teams']['home']['name']
                    b_visitante = match_b_obj['teams']['away']['name']
                    st.success(f"Partido de básquetbol sincronizado: **{b_local}** vs **{b_visitante}**")
                else:
                    st.info("No hay partidos programados para hoy en la API. Usando modo manual de respaldo.")
            else:
                st.warning("No se pudo conectar a la API de básquetbol con la clave proporcionada. Usando modo manual.")
        except Exception as e:
            st.warning(f"Error de conexión con API-Basketball: {e}")

    st.markdown("---")
    st.subheader("1. Promedios Ofensivos (PPG) y Nombres")

    bc1, bc2 = st.columns(2)
    with bc1:
        b_loc_input = st.text_input("Equipo Local", b_local, key="b_loc_name")
        ppg_l = st.number_input(f"PPG Promedio ({b_loc_input})", min_value=70.0, max_value=140.0, value=ppg_local, step=0.5, key="ppg_l")
    with bc2:
        b_vis_input = st.text_input("Equipo Visitante", b_visitante, key="b_vis_name")
        ppg_v = st.number_input(f"PPG Promedio ({b_vis_input})", min_value=70.0, max_value=140.0, value=ppg_vis, step=0.5, key="ppg_v")

    st.markdown("---")
    st.subheader("2. Estado de Forma, Bajas y Factores Contextuales")

    with st.expander("Ajustes de Forma y Contexto (Básquetbol)", expanded=True):
        b_fc1, b_fc2 = st.columns(2)
        with b_fc1:
            st.markdown(f"**{b_loc_input} (Local)**")
            forma_bl = st.selectbox(
                f"Estado de forma ({b_loc_input}):",
                ["Excelente (Racha ganadora)", "Estable (Normal)", "Irregular / Mal momento"],
                index=0, key="f_bl"
            )
            bajas_bl = st.selectbox(
                f"Bajas clave ({b_loc_input}):",
                ["Sin bajas importantes", "Baja sensible de estrella / titular"],
                index=0, key="b_bl"
            )
        with b_fc2:
            st.markdown(f"**{b_vis_input} (Visitante)**")
            forma_bv = st.selectbox(
                f"Estado de forma ({b_vis_input}):",
                ["Excelente (Racha ganadora)", "Estable (Normal)", "Irregular / Malo momento"],
                index=1, key="f_bv"
            )
            bajas_bv = st.selectbox(
                f"Bajas clave ({b_vis_input}):",
                ["Sin bajas importantes", "Baja sensible de estrella / titular"],
                index=0, key="b_bv"
            )

        st.markdown("---")
        h2h_basquet = st.selectbox(
            "Historial H2H reciente entre ambos:",
            ["Neutral / Sin claro dominante", f"Dominio histórico de {b_loc_input}", f"Dominio histórico de {b_vis_input}"],
            index=0, key="h2h_b"
        )

    if st.button("Ejecutar Modelo Avanzado de Básquetbol Pro", key="btn_exec_b"):
        ppg_l_adj = ppg_l
        ppg_v_adj = ppg_v

        if "Excelente" in forma_bl: ppg_l_adj += 4.0
        elif "Irregular" in forma_bl: ppg_l_adj -= 4.0
        if "estrella" in bajas_bl: ppg_l_adj -= 6.0

        if "Excelente" in forma_bv: ppg_v_adj += 4.0
        elif "Irregular" in forma_bv: ppg_v_adj -= 4.0
        if "estrella" in bajas_bv: ppg_v_adj -= 6.0

        if b_loc_input in h2h_basquet: ppg_l_adj += 2.5
        elif b_vis_input in h2h_basquet: ppg_v_adj += 2.5

        st.session_state['basquet_calc_pro'] = True
        st.session_state['b_l_name'] = b_loc_input
        st.session_state['b_v_name'] = b_vis_input
        st.session_state['ppg_l_adj'] = ppg_l_adj
        st.session_state['ppg_v_adj'] = ppg_v_adj

    if st.session_state.get('basquet_calc_pro', False):
        t_loc = st.session_state['b_l_name']
        t_vis = st.session_state['b_v_name']
        pl = st.session_state['ppg_l_adj']
        pv = st.session_state['ppg_v_adj']

        total_puntos_est = pl + pv
        dif_puntos = pl - pv
        
        prob_bl = 1.0 / (1.0 + math.exp(-0.15 * dif_puntos))
        prob_bv = 1.0 - prob_bl

        st.subheader("Probabilidades y Cuotas del Partido (Básquetbol)")
        col_rb1, col_rb2 = st.columns(2)
        col_rb1.metric(f"Victoria {t_loc} (Moneyline)", f"{prob_bl*100:.1f}%", f"Cuota Justa: {1/prob_bl:.2f}")
        col_rb2.metric(f"Victoria {t_vis} (Moneyline)", f"{prob_bv*100:.1f}%", f"Cuota Justa: {1/prob_bv:.2f}")

        # --- PUNTOS POR EQUIPO (TEAM TOTALS) ---
        st.markdown("---")
        st.subheader("Puntos por Equipo (Team Total Points)")
        t_col1, t_col2 = st.columns(2)
        t_col1.metric(f"Puntos Estimados ({t_loc})", f"{pl:.1f} Puntos")
        t_col2.metric(f"Puntos Estimados ({t_vis})", f"{pv:.1f} Puntos")

        st.markdown("---")
        st.subheader("⭐ Top Apuestas Recomendadas en Rango Atractivo (Cuotas 1.70 a 2.20)")
        st.write("Filtro especializado en mercados con alta probabilidad y cuotas competitivas en el rango deseado.")

        candidatos_b_atractivos = []
        
        if 1.70 <= (1/prob_bl) <= 2.20:
            candidatos_b_atractivos.append({"Mercado": f"Victoria Simple: {t_loc}", "Prob": prob_bl, "Cuota": 1/prob_bl})
        if 1.70 <= (1/prob_bv) <= 2.20:
            candidatos_b_atractivos.append({"Mercado": f"Victoria Simple: {t_vis}", "Prob": prob_bv, "Cuota": 1/prob_bv})

        for sp in [-7.5, -4.5, -2.5, +2.5, +4.5, +7.5]:
            prob_sp = max(0.05, min(0.95, prob_bl + (sp * 0.025)))
            cuota_sp = 1.0 / prob_sp if prob_sp > 0 else 0
            if 1.70 <= cuota_sp <= 2.20:
                signo_sp = "+" if sp > 0 else ""
                candidatos_b_atractivos.append({"Mercado": f"Hándicap de Puntos {signo_sp}{sp} ({t_loc})", "Prob": prob_sp, "Cuota": cuota_sp})

        if candidatos_b_atractivos:
            for i, item in enumerate(sorted(candidatos_b_atractivos, key=lambda x: x["Prob"], reverse=True)[:3], 1):
                st.success(f"**{i}. {item['Mercado']}** -> Cuota Estimada: **{item['Cuota']:.2f}** (Prob. Modelo: {item['Prob']*100:.1f}%)")
        else:
            st.info("ℹ️ Para este emparejamiento exacto las líneas directas están fuera de 1.70-2.20. Revisa los hándicaps detallados abajo.")

        st.markdown("---")
        st.subheader("Recomendaciones de Combinadas (Bet Builder - Básquetbol)")
        eq_fav_b = t_loc if prob_bl > prob_bv else t_vis
        st.markdown(f"🔹 **Combinada 1:** Gana {eq_fav_b} + Over 215.5 Puntos Totales")
        st.markdown(f"🔹 **Combinada 2:** Hándicap favorable a {eq_fav_b} + Over de Puntos del Equipo")

        st.markdown("---")
        st.subheader("Líneas de Puntos Totales (Game Totals - Over / Under)")
        st.info(f"Puntos Totales Ajustados Esperados: **{total_puntos_est:.1f} Puntos**")

        for linea_pts in [215.5, 221.5, 227.5, 233.5, 239.5]:
            diff_p = linea_pts - total_puntos_est
            p_over_b = max(0.05, min(0.95, 0.50 - (diff_p * 0.05)))
            p_under_b = 1.0 - p_over_b
            
            c_over_b = 1.0 / p_over_b if p_over_b > 0 else 0
            c_under_b = 1.0 / p_under_b if p_under_b > 0 else 0
            
            tag_ob = " 🔥 [1.70-2.20]" if 1.70 <= c_over_b <= 2.20 else ""
            tag_ub = " 🔥 [1.70-2.20]" if 1.70 <= c_under_b <= 2.20 else ""

            ob1, ob2, ob3 = st.columns(3)
            ob1.text(f"Línea {linea_pts} Puntos")
            ob2.text(f"OVER: {p_over_b*100:.1f}% | Justa: {c_over_b:.2f}{tag_ob}")
            ob3.text(f"UNDER: {p_under_b*100:.1f}% | Justa: {c_under_b:.2f}{tag_ub}")

        st.markdown("---")
        st.subheader("Hándicaps de Puntos (Spreads)")
        
        sp_col1, sp_col2 = st.columns(2)
        sp_lineas = [-7.5, -5.5, -3.5, -1.5, +1.5, +3.5, +5.5, +7.5]
        
        with sp_col1:
            st.markdown(f"**Hándicap: {t_loc}**")
            for sp in sp_lineas:
                prob_sp = max(0.05, min(0.95, prob_bl + (sp * 0.02)))
                cuota_sp = 1.0 / prob_sp if prob_sp > 0 else 0
                signo_sp = "+" if sp > 0 else ""
                tag_sp = " 🔥 [1.70-2.20]" if 1.70 <= cuota_sp <= 2.20 else ""
                st.text(f"Spread {signo_sp}{sp}: Prob. {prob_sp*100:.1f}% | Justa: {cuota_sp:.2f}{tag_sp}")

        with sp_col2:
            st.markdown(f"**Hándicap: {t_vis}**")
            for sp in sp_lineas:
                prob_sp_v = max(0.05, min(0.95, prob_bv + (sp * 0.02)))
                cuota_sp_v = 1.0 / prob_sp_v if prob_sp_v > 0 else 0
                signo_sp = "+" if sp > 0 else ""
                tag_sp_v = " 🔥 [1.70-2.20]" if 1.70 <= cuota_sp_v <= 2.20 else ""
                st.text(f"Spread {signo_sp}{sp}: Prob. {prob_sp_v*100:.1f}% | Justa: {cuota_sp_v:.2f}{tag_sp_v}")

        st.markdown("---")
        st.subheader("Desglose por Cuartos y Medio Tiempo (HT)")
        
        q_l_est, q_v_est = pl / 4.0, pv / 4.0
        ht_l_est, ht_v_est = pl / 2.0, pv / 2.0
        
        qb1, qb2 = st.columns(2)
        with qb1:
            st.markdown("**Primera Mitad (1H / Half Time)**")
            st.text(f"Puntos Estimados 1H: {t_loc} ({ht_l_est:.1f}) - {t_vis} ({ht_v_est:.1f})")
            st.text(f"Total 1H Esperado: {ht_l_est + ht_v_est:.1f} Puntos")
        with qb2:
            st.markdown("**Por Cuarto (Promedio Estimado Q1-Q4)**")
            st.text(f"Puntos Estimados por Cuarto: {t_loc} ({q_l_est:.1f}) | {t_vis} ({q_v_est:.1f})")
            st.text(f"Total por Cuarto Esperado: {q_l_est + q_v_est:.1f} Puntos")

        st.markdown("---")
        st.subheader("Calculadora de Valor Esperado (EV) y Criterio de Kelly (Básquetbol)")
        
        bc_1, bc_2, bc_3 = st.columns(3)
        with bc_1:
            mercado_sel_b = st.selectbox(
                "Mercado de Básquetbol a analizar:",
                [f"Victoria {t_loc}", f"Victoria {t_vis}"],
                key="merc_b_sel"
            )
        with bc_2:
            default_val_b = float(1/prob_bl) if mercado_sel_b.startswith(f"Victoria {t_loc}") else float(1/prob_bv)
            cuota_ingresada_b = st.number_input("Cuota de la casa (Básquetbol):", min_value=1.01, value=round(default_val_b, 2), step=0.01, key="cib")
        with bc_3:
            bankroll_total_b = st.number_input("Capital Total ($ Bankroll - Básquetbol):", min_value=10.0, value=1000.0, step=50.0, key="btb")

        prob_apuesta_b = prob_bl if mercado_sel_b.startswith(f"Victoria {t_loc}") else prob_bv
        ev_pct_b = ((prob_apuesta_b * cuota_ingresada_b) - 1) * 100

        b_b = cuota_ingresada_b - 1 
        kelly_frac_b = (b_b * prob_apuesta_b - (1.0 - prob_apuesta_b)) / b_b if b_b > 0 else 0.0
        kelly_medio_b = max(0.0, kelly_frac_b * 0.5)

        br1, br2, br3 = st.columns(3)
        br1.metric("Probabilidad Modelo (Básquetbol)", f"{prob_apuesta_b*100:.1f}%")
        br2.metric("Probabilidad Implícita Casa", f"{(1/cuota_ingresada_b)*100:.1f}%")
        br3.metric("Valor Esperado (EV - Básquetbol)", f"{ev_pct_b:+.2f}%")

        if ev_pct_b >= 5.0:
            st.success(f"Apuesta de básquetbol con valor detectada. EV: +{ev_pct_b:.2f}% (Supera el filtro del 5%).")
            if st.button("Registrar Apuesta de Básquetbol en Bet Tracker", key="btn_trk_b"):
                st.session_state['historial_apuestas'].append({
                    "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Partido": f"{t_loc} vs {t_vis}",
                    "Mercado": mercado_sel_b,
                    "Cuota": cuota_ingresada_b,
                    "Stake ($)": round(bankroll_total_b * kelly_medio_b, 2),
                    "EV (%)": round(ev_pct_b, 2),
                    "Estado": "Pendiente"
                })
                st.success("¡Apuesta de básquetbol registrada con éxito!")
        else:
            st.error(f"Sin valor suficiente en básquetbol. EV: {ev_pct_b:.2f}%.")


# ==========================================
# MÓDULO DE BÉISBOL (RUTINA SECUNDARIA)
# ==========================================
with tab_beisbol: 
    st.header("Módulo de Béisbol")
    st.write("Próximamente.")


# ==========================================
# BET TRACKER (ÍNTEGRO)
# ==========================================
with tab_tracker:
    st.header("Historial de Apuestas (Bet Tracker)")
    if st.session_state['historial_apuestas']:
        st.dataframe(pd.DataFrame(st.session_state['historial_apuestas']), use_container_width=True)
        if st.button("Limpiar Historial", key="clr_hist"): 
            st.session_state['historial_apuestas'] = []
            st.rerun()
    else:
        st.info("No hay apuestas registradas todavía.")