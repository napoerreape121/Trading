import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime

# =====================================================================
# ⚙️ CONFIGURACIÓN DE LA INTERFAZ WEB
# =====================================================================
st.set_page_config(
    page_title="Asistente Cuantitativo Pro", 
    page_icon="🤖", 
    layout="wide"
)

st.title("🤖 Asistente de Trading de CEDEARs con Gestión Activa de Portafolio")
st.write("Monitoreo Dinámico: Lógica matemática estricta para mitigar falsas señales y proteger el Triángulo de Hierro (Riesgo máximo 2%).")

# Credenciales de Telegram
TELEGRAM_TOKEN = "8624285419:AAHS-aTMjxM9H33dqtqC4JCQzwyqqL_Q71Y"
TELEGRAM_CHAT_ID = "6872048498"

def enviar_alerta_telegram(mensaje):
    """Módulo oficial de comunicación en red con la API de Telegram"""
    url = f"telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

# =====================================================================
# 💾 BASE DE DATOS LOCAL PERMANENTE (portafolio.csv)
# =====================================================================
ARCHIVO_DB = "portafolio.csv"
if not os.path.exists(ARCHIVO_DB):
    df_inicial = pd.DataFrame(columns=["Ticker", "Cantidad", "PrecioCompra", "StopLoss", "TakeProfit", "FechaEntrada"])
    df_inicial.to_csv(ARCHIVO_DB, index=False)

df_portafolio = pd.read_csv(ARCHIVO_DB)

# MÓDULO lateral: Configuración de Entornos y Carga de Posiciones
st.sidebar.header("🔑 Configuración del Cerebro IA")
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Conseguila en openai.com")

st.sidebar.markdown("---")
st.sidebar.header("📥 Registrar Compra Real en Balanz")
with st.sidebar.form(key="formulario_balanz", clear_on_submit=True):
    ticker_real = st.text_input("Ticker del CEDEAR (Ej: AAPL)").upper().strip()
    if ticker_real and not ticker_real.endswith(".BA"):
        ticker_real = f"{ticker_real}.BA"
    
    cant_real = st.number_input("Cantidad de nominales", min_value=1, value=1, step=1)
    precio_real = st.number_input("Precio de compra ($)", min_value=1.0, value=1000.0, step=100.0)
    sl_real = st.number_input("Stop Loss inicial ($)", min_value=0.0, value=900.0, step=100.0)
    tp_real = st.number_input("Take Profit inicial ($)", min_value=0.0, value=1200.0, step=100.0)
    
    boton_guardar = st.form_submit_button(label="💾 Guardar Posición Abierta")
    
    if boton_guardar and ticker_real:
        nueva_posicion = pd.DataFrame([{
            "Ticker": ticker_real, "Cantidad": int(cant_real), "PrecioCompra": float(precio_real),
            "StopLoss": float(sl_real), "TakeProfit": float(tp_real), 
            "FechaEntrada": datetime.now().strftime('%Y-%m-%d')
        }])
        df_portafolio = pd.concat([df_portafolio, nueva_posicion], ignore_index=True)
        df_portafolio.to_csv(ARCHIVO_DB, index=False)
        st.sidebar.success(f"¡{ticker_real} guardado con éxito!")
        st.rerun()

# PANEL PRINCIPAL: Visualización de Cartera Activa
st.subheader("📋 Tus Posiciones Abiertas Actualmente Activas")
if not df_portafolio.empty:
    st.dataframe(df_portafolio, use_container_width=True)
    if st.button("🗑️ Vaciar todo el Portafolio (Borrar Base de Datos)"):
        df_limpio = pd.DataFrame(columns=["Ticker", "Cantidad", "PrecioCompra", "StopLoss", "TakeProfit", "FechaEntrada"])
        df_limpio.to_csv(ARCHIVO_DB, index=False)
        st.success("¡Base de datos limpiada!")
        st.rerun()
else:
    st.info("No tienes operaciones cargadas en el archivo permanente.")

# Universo de Tickers
tickers_escaner = [
    'AAL.BA','ABT.BA','ACWI.BA','ADBE.BA','AMD.BA','AMZN.BA','AAPL.BA','ARM.BA','ARKK.BA','ASML.BA',
    'AXP.BA','BAC.BA','BA.BA','BABA.BA','BKNG.BA','BP.BA','BRKB.BA','BX.BA','C.BA','CAT.BA',
    'CCL.BA','COPX.BA','COIN.BA','COST.BA','CRM.BA','CVS.BA','CVX.BA','DAL.BA','DE.BA','DISN.BA',
    'DIA.BA','EFA.BA','ETHA.BA','GE.BA','GOOGL.BA','GS.BA','HD.BA','HON.BA','IBM.BA','INTC.BA',
    'JNJ.BA','JPM.BA','KO.BA','LLY.BA','MA.BA','MCD.BA','META.BA','MELI.BA','MMM.BA','MSFT.BA',
    'NFLX.BA','NKE.BA','NVDA.BA','ORCL.BA','PANW.BA','PEP.BA','PFE.BA','PG.BA','PYPL.BA','QCOM.BA',
    'QQQ.BA','ROKU.BA','SHOP.BA','SNOW.BA','SONY.BA','SPY.BA','T.BA','TEAM.BA','TGT.BA','TSLA.BA',
    'TSM.BA','TXN.BA','UAL.BA','UBER.BA','UNH.BA','V.BA','VZ.BA','WFC.BA','WMT.BA','XOM.BA'
]

st.sidebar.header("⚙️ Parámetros del Escáner de Compras")
capital_disponible = st.sidebar.number_input("Tu Capital Total Libre ($ ARS)", min_value=10000, value=158000, step=10000)
riesgo_maximo_ars = capital_disponible * 0.02
ratio_beneficio = st.sidebar.slider("Ratio Recompensa / Riesgo Mínimo", 1.5, 3.5, 2.0, step=0.1)
umbral = st.sidebar.slider("Tolerancia de proximidad EMA", 0.001, 0.015, 0.005, step=0.001)
COSTO_OPERATIVO_TOTAL = (0.0050 + 0.0005) * 1.21 

# =====================================================================
# 🚀 MOTOR CUANTITATIVO: MONITOREO Y ESCÁNER ESTRICTO
# =====================================================================
if st.button("🚀 Ejecutar Escáner General y Despachar Gestión"):
    
    # PARTE 1: AUDITORÍA DE POSICIONES EXISTENTES (TRAILING Y SALIDAS)
    if not df_portafolio.empty:
        st.subheader("🕵️ Análisis Cuantitativo de tus Posiciones Abiertas")
        tickers_cartera = df_portafolio["Ticker"].unique().tolist()
        try:
            datos_cartera = yf.download(tickers_cartera, period="6mo", interval="1d", progress=False)
            
            for idx, row in df_portafolio.iterrows():
                tick = row["Ticker"]
                df_t_cart = pd.DataFrame()
                df_t_cart['Close'] = datos_cartera['Close'][tick].dropna()
                df_t_cart['Open'] = datos_cartera['Open'][tick].dropna()
                df_t_cart['Low'] = datos_cartera['Low'][tick].dropna()
                df_t_cart['High'] = datos_cartera['High'][tick].dropna()
                
                precio_vivo = float(df_t_cart['Close'].iloc[-1])
                low_vivo = float(df_t_cart['Low'].iloc[-1])
                high_vivo = float(df_t_cart['High'].iloc[-1])
                
                ema9_v = df_t_cart['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
                
                high_low = df_t_cart['High'] - df_t_cart['Low']
                high_close_prev = abs(df_t_cart['High'] - df_t_cart['Close'].shift())
                low_close_prev = abs(df_t_cart['Low'] - df_t_cart['Close'].shift())
                true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
                atr14_v = true_range.rolling(14).mean().iloc[-1]
                
                ticker_limpio = tick.split('.')[0]
                
                # Regla de Salidas Inmediatas por matriz de precios
                if low_vivo <= float(row["StopLoss"]):
                    msg_sl = f"🚨 *¡ALERTA CRÍTICA DE SALIDA!* 🚨\n\n📉 El CEDEAR `{ticker_limpio}` perforó tu *Stop Loss* de ${row['StopLoss']:,.2f}.\n🛒 *Acción:* VENDER de inmediato tus {int(row['Cantidad'])} unidades en Balanz."
                    enviar_alerta_telegram(msg_sl)
                    st.error(f"¡Alerta enviada por Stop Loss Perforado en {ticker_limpio}!")
                    continue
                elif high_vivo >= float(row["TakeProfit"]):
                    msg_tp = f"🎯 *¡ALERTA DE OBJETIVO CUMPLIDO!* 🎯\n\n📈 El CEDEAR `{ticker_limpio}` tocó tu *Take Profit* de ${row['TakeProfit']:,.2f}.\n🛒 *Acción:* VENDER tus {int(row['Cantidad'])} unidades y asegurar ganancias."
                    enviar_alerta_telegram(msg_tp)
                    st.success(f"¡Alerta enviada por Objetivo Cumplido en {ticker_limpio}!")
                    continue
                
                # Trailing Stop Dinámico Basado en ATR x 1.5
                nuevo_stop_sugerido = ema9_v - (1.5 * atr14_v)
                if precio_vivo > float(row["PrecioCompra"]) and nuevo_stop_sugerido > float(row["StopLoss"]):
                    st.info(f"🔄 **Sugerencia para {ticker_limpio}:** Sube tu Stop Loss en Balanz a **${nuevo_stop_sugerido:,.2f}** para blindar beneficios.")
                    msg_trailing = f"🔄 *¡AJUSTE DE SEGURIDAD (Trailing Stop)!*\n\n📈 El CEDEAR `{ticker_limpio}` avanza a favor.\n🛠️ *Acción:* Sube tu Stop Loss a `${nuevo_stop_sugerido:,.2f}`."
                    enviar_alerta_telegram(msg_trailing)
                elif precio_vivo < ema9_v and precio_vivo > float(row["StopLoss"]):
                    st.warning(f"⚠️ **Advertencia para {ticker_limpio}:** Cierre técnico por debajo de la EMA 9. Estructura débil.")
        except Exception as e:
            st.warning(f"No se pudo auditar dinámicamente tu portafolio: {e}")

    # PARTE 2: BUSCAR NUEVAS COMPRAS (CEREBRO CORREGIDO DE RAÍZ CON MEJORAS DE PRECISIÓN)
    with st.spinner("Buscando oportunidades reales bajo tus reglas estrictas..."):
        try:
            datos_mercado = yf.download(tickers_escaner, period="6mo", interval="1d", progress=False)
        except Exception:
            datos_mercado = None
            
        if datos_mercado is not None and not datos_mercado.empty:
            candidatos_validos = []
            for ticker in tickers_escaner:
                try:
                    if not df_portafolio.empty and ticker in df_portafolio["Ticker"].values: 
                        continue
                    
                    df_t = pd.DataFrame()
                    df_t['Close'] = datos_mercado['Close'][ticker].dropna()
                    df_t['Open'] = datos_mercado['Open'][ticker].dropna()
                    df_t['Low'] = datos_mercado['Low'][ticker].dropna()
                    df_t['High'] = datos_mercado['High'][ticker].dropna()
                    df_t['Volume'] = datos_mercado['Volume'][ticker].dropna()
                    
                    c0, o0, l0, h0, v0 = float(df_t['Close'].iloc[-1]), float(df_t['Open'].iloc[-1]), float(df_t['Low'].iloc[-1]), float(df_t['High'].iloc[-1]), float(df_t['Volume'].iloc[-1])
                    c1, o1, l1, h1 = float(df_t['Close'].iloc[-2]), float(df_t['Open'].iloc[-2]), float(df_t['Low'].iloc[-2]), float(df_t['High'].iloc[-2])
                    c2, o2, l2, h2 = float(df_t['Close'].iloc[-3]), float(df_t['Open'].iloc[-3]), float(df_t['Low'].iloc[-3]), float(df_t['High'].iloc[-3])
                    
                    # FILTRO DE VOLUMEN ABSOLUTO Y RELATIVO (Evita trampas de liquidez)
                    volumen_nominal_ars = v0 * c0
                    volumen_promedio_10d = df_t['Volume'].rolling(10).mean().iloc[-1]
                    
                    tiene_liquidez_minima = volumen_nominal_ars > 8000000  # Mínimo $8 millones operados en el día
                    volumen_institucional = v0 > (volumen_promedio_10d * 1.15) # 15% arriba del volumen promedio
                    
                    # Medias Móviles y ATR
                    ema9 = df_t['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
                    ema50 = df_t['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                    
                    high_low = df_t['High'] - df_t['Low']
                    high_close_prev = abs(df_t['High'] - df_t['Close'].shift())
                    low_close_prev = abs(df_t['Low'] - df_t['Close'].shift())
                    true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
                    atr14 = true_range.rolling(14).mean().iloc[-1]
                    
                    # RSI estricto
                    delta = df_t['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rsi14 = 100 - (100 / (1 + (gain / loss))).iloc[-1]
                    
                    # MACD y proximidad de cruce
                    exp1 = df_t['Close'].ewm(span=12, adjust=False).mean()
                    exp2 = df_t['Close'].ewm(span=26, adjust=False).mean()
                    linea_macd = exp1 - exp2
                    linea_senal = linea_macd.ewm(span=9, adjust=False).mean()
                    
                    macd_hoy, senal_hoy = linea_macd.iloc[-1], linea_senal.iloc[-1]
                    macd_ayer, senal_ayer = linea_macd.iloc[-2], linea_senal.iloc[-2]
                    
                    # REGLAS REQUERIDAS POR EL USUARIO
                    es_vela_verde = c0 > o0
                    rsi_no_sobrecomprado = rsi14 < 65
                    
                    distancia_macd = abs(macd_hoy - senal_hoy) / c0
                    macd_proximo_cruce = (macd_ayer < senal_ayer and macd_hoy >= senal_hoy) or (macd_hoy < senal_hoy and distancia_macd < 0.005)

                    disparar = False
                    
                    if c0 > ema50:  # TENDENCIA ALCISTA
                        vela_sobre_ema9 = (c0 > ema9) and (o0 > ema9)
                        vela_en_ema50 = abs(l0 - ema50) / c0 <= umbral
                        if es_vela_verde and rsi_no_sobrecomprado and (vela_sobre_ema9 or vela_en_ema50):
                            disparar = True
                    else:  # TENDENCIA BAJISTA
                        vela_sobre_ema50 = c0 > ema50
                        if es_vela_verde and rsi_no_sobrecomprado and vela_sobre_ema50:
                            disparar = True

                    # VALIDACIÓN DE SUBYACENTE EN WALL STREET (Filtro Anti-Arbitrajes artificiales del CCL)
                    subyacente_sano = False
                    if disparar:
                        ticker_ny = ticker.split('.')[0]
                        try:
                            df_ny = yf.download(ticker_ny, period="5d", interval="1d", progress=False)
                            subyacente_sano = float(df_ny['Close'].iloc[-1]) >= float(df_ny['Open'].iloc[-1]) * 0.995
                        except Exception:
                            subyacente_sano = False

                    # FILTRADO DE ENTRADA DEFINITIVO
                    if disparar and tiene_liquidez_minima and volumen_institucional and subyacente_sano:
                        
                        # Patrones de Velas Japonesas
                        score_patron = 0
                        cuerpo_abs = abs(c0 - o0)
                        rango_tot = h0 - l0 if (h0 - l0) > 0 else 0.01
                        es_martillo = ((min(o0, c0) - l0) > (2 * cuerpo_abs)) and ((h0 - max(o0, c0)) < (0.2 * rango_tot))
                        es_envolvente = (c1 < o1) and (c0 > o0) and (c0 > o1) and (o0 < c1)
                        es_estrella = (c2 < o2) and (abs(c1 - o1) < (0.3 * abs(c2 - o2))) and (c0 > o0) and (c0 > (o2 + c2)/2)
                        if es_martillo or es_envolvente or es_estrella:
                            score_patron = 1

                        # MATEMÁTICA DEL TRIÁNGULO DE HIERRO (Stop Loss basado en ATR x 2 exacto)
                        precio_ent_neto = c0 * (1 + COSTO_OPERATIVO_TOTAL)
                        sl_g = c0 - (2 * atr14)
                        precio_sal_sl_neto = sl_g * (1 - COSTO_OPERATIVO_TOTAL)
                        
                        dist_riesgo = (precio_ent_neto - precio_sal_sl_neto) / precio_ent_neto
                        precio_tp = c0 * (1 + (dist_riesgo * ratio_beneficio))
                        
                        perdida_por_accion = precio_ent_neto - precio_sal_sl_neto
                        if perdida_por_accion <= 0: 
                            continue
                            
                        cant_cedears = int(riesgo_maximo_ars // perdida_por_accion)
                        if cant_cedears <= 0: 
                            continue
                        monto_compra = precio_ent_neto * cant_cedears
                        
                        if monto_compra > capital_disponible: 
                            continue
                        
                        score_total = 0
                        if score_patron > 0: score_total += 1
                        if macd_proximo_cruce: score_total += 1
                        if 45 < rsi14 < 55: score_total += 1
                        
                        candidatos_validos.append({
                            "Ticker": ticker, "Precio": c0, "Neto": precio_ent_neto,
                            "StopLoss": sl_g, "TakeProfit": precio_tp, 
                            "Cantidad": cant_cedears, "Total": monto_compra, "Score": score_total
                        })
                except Exception:
                    continue
                    
            if candidatos_validos:
                df_ops = pd.DataFrame(candidatos_validos).sort_values(by="Score", ascending=False).reset_index(drop=True)
                mejor_opcion = df_ops.iloc[0]
                
                st.success("🤖 ¡Análisis de Oportunidades Completado!")
                st.subheader("🎯 La Mejor Decisión Sugerida por el Cerebro Cuantitativo")
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("CEDEAR", mejor_opcion["Ticker"])
                col_b.metric("Cantidad de Nominales", int(mejor_opcion["Cantidad"]))
                col_c.metric("Capital Invertido Neto", f"$ {mejor_opcion['Total']:,.2f}")
                
                ticker_notif = mejor_opcion["Ticker"].split('.')[0]
                msg_tg = (
                    f"🤖 *¡SEÑAL INSTITUCIONAL DETECTADA!*\n\n"
                    f"🎯 *CEDEAR Seleccionado:* `{ticker_notif}`\n"
                    f"🤖 *Cantidad nominal a comprar:* {int(mejor_opcion['Cantidad'])} unidades\n\n"
                    f"💵 *Precio Pantalla:* ${mejor_opcion['Precio']:,.2f}\n"
                    f"📐 *Precio Entrada Neto:* ${mejor_opcion['Neto']:,.2f}\n"
                    f"🛡️ *ORDEN DE STOP LOSS (ATR x 2):* ${mejor_opcion['StopLoss']:,.2f}\n"
                    f"🎯 *ORDEN DE TAKE PROFIT:* ${mejor_opcion['TakeProfit']:,.2f}\n\n"
                    f"💰 *Costo Total:* ${mejor_opcion['Total']:,.2f}\n"
                    f"🔍 *Score Técnico:* {int(mejor_opcion['Score'])} / 3 Puntos."
                )
                enviar_alerta_telegram(msg_tg)
                st.dataframe(df_ops, use_container_width=True)
            else:
                st.info("Ningún CEDEAR reúne los filtros estrictos y el volumen institucional en la rueda de hoy.")

# =====================================================================
# 💬 NUEVO MÓDULO: PANEL DE PREGUNTAS CON IA AVANZADA (OPENAI)
# =====================================================================
st.markdown("---")
col_chat_title, col_chat_clear = st.columns([4, 1])

with col_chat_title:
    st.subheader("💬 Consulta a tu Cerebro Cuantitativo con IA")
    st.write("Hazle preguntas financieras o estratégicas sobre tus posiciones reales.")

if "historial_chat" not in st.session_state:
    st.session_state.historial_chat = []

with col_chat_clear:
    if st.button("膜 Limpiar Chat", use_container_width=True):
        st.session_state.historial_chat = []
        st.rerun()

for mensaje in st.session_state.historial_chat:
    with st.chat_message(mensaje["rol"]):
        st.write(mensaje["contenido"])

if pregunta_usuario := st.chat_input("Ej: ¿Qué acciones tengo en cartera y cuál es mi riesgo patrimonial hoy?"):
    
    with st.chat_message("user"):
        st.write(pregunta_usuario)
    st.session_state.historial_chat.append({"rol": "user", "contenido": pregunta_usuario})
    
    if not openai_api_key:
        respuesta_bot = "⚠️ Por favor, ingresá tu **OpenAI API Key** en la barra lateral izquierda para poder habilitar el razonamiento analítico de la IA."
        with st.chat_message("assistant"):
            st.write(respuesta_bot)
        st.session_state.historial_chat.append({"rol": "assistant", "contenido": respuesta_bot})
    else:
        with st.spinner("El cerebro cuántico analizando datos..."):
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_api_key)
                contexto_portafolio = df_portafolio.to_string(index=False) if not df_portafolio.empty else "Vacío. Sin posiciones abiertas registradas."
                
                system_prompt = (
                    f"Sos el Asistente Cuantitativo Pro, un experto en finanzas y trading de CEDEARs en Argentina.\n"
                    f"Tenés acceso en tiempo real a los siguientes datos analizados:\n\n"
                    f"--- PORTAFOLIO EN HISTORIAL REAL ---\n{contexto_portafolio}\n\n"
                    f"--- REGLAS DEL SISTEMA ACTUAL ---\n"
                    f"- Capital libre disponible: ${capital_disponible:,.2f} ARS\n"
                    f"- Riesgo máximo por operación (2% del patrimonio): ${riesgo_maximo_ars:,.2f} ARS\n"
                    f"- Ratio Recompensa/Riesgo mínimo: {ratio_beneficio}x\n"
                    f"- Parámetros de Stop Loss: Basado estrictamente en 2 ATR de volatilidad de mercado.\n"
                    f"- Filtros añadidos: Volumen nominal > $8M, volumen institucional +15%, validación de subyacente en Wall Street y vela verde obligatoria.\n\n"
                    f"Instrucciones: Respondé siempre en español con modismos de Argentina, de manera profesional, técnica y muy concisa. "
                    f"No inventes datos. Si te piden opiniones de mercado, enmarcalas bajo la estricta gestión de riesgos del 2% del usuario."
                )
                
                mensajes_api = [{"role": "system", "content": system_prompt}]
                for m in st.session_state.historial_chat:
                    api_role = "user" if m["rol"] == "user" else "assistant"
                    mensajes_api.append({"role": api_role, "content": m["contenido"]})
                
                computo_ia = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=mensajes_api,
                    temperature=0.3
                )
                respuesta_bot = computo_ia.choices.message.content
                
            except Exception as e:
                respuesta_bot = f"❌ Error de comunicación con OpenAI: {str(e)}"
        
        with st.chat_message("assistant"):
            st.write(respuesta_bot)
        st.session_state.historial_chat.append({"rol": "assistant", "contenido": respuesta_bot})
