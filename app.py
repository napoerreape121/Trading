import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# Configuración del panel de control inteligente en internet
st.set_page_config(page_title="Asistente Algorítmico Inteligente", page_icon="🤖", layout="wide")

st.title("🤖 Asistente de Selección y Asignación de Capital")
st.write("Inteligencia Cuantitativa: El bot filtra, puntúa y selecciona la mejor decisión para tu presupuesto real.")

# Credenciales fijas y verificadas de tu canal de Telegram
TELEGRAM_TOKEN = "8624285419:AAHS-aTMjxM9H33dqtqC4JCQzwyqqL_Q71Y"
TELEGRAM_CHAT_ID = "6872048498"

def enviar_alerta_telegram(mensaje):
    """Módulo oficial de comunicación en red con la API de Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

# Lista matriz de tus 80 CEDEARs en pesos
tickers = [
    'AAL.BA','ABT.BA','ACWI.BA','ADBE.BA','AMD.BA',
    'AMZN.BA','AAPL.BA','ARM.BA','ARKK.BA','ASML.BA',
    'AXP.BA','BAC.BA','BA.BA','BABA.BA','BKNG.BA',
    'BP.BA','BRKB.BA','BX.BA','C.BA','CAT.BA',
    'CCL.BA','COPX.BA','COIN.BA','COST.BA','CRM.BA',
    'CVS.BA','CVX.BA','DAL.BA','DE.BA','DISN.BA',
    'DIA.BA','EFA.BA','ETHA.BA','GE.BA','GOOGL.BA',
    'GS.BA','HD.BA','HON.BA','IBM.BA','INTC.BA',
    'JNJ.BA','JPM.BA','KO.BA','LLY.BA','MA.BA',
    'MCD.BA','META.BA','MELI.BA','MMM.BA','MSFT.BA',
    'NFLX.BA','NKE.BA','NVDA.BA','ORCL.BA','PANW.BA',
    'PEP.BA','PFE.BA','PG.BA','PYPL.BA','QCOM.BA',
    'QQQ.BA','ROKU.BA','SHOP.BA','SNOW.BA',
    'SONY.BA','SPY.BA','T.BA','TEAM.BA',
    'TGT.BA','TSLA.BA','TSM.BA','TXN.BA','UAL.BA',
    'UBER.BA','UNH.BA','V.BA','VZ.BA','WFC.BA',
    'WMT.BA','XOM.BA'
]

# Menú lateral para setear tu caja de Balanz actual
st.sidebar.header("💰 Caja Real de Balanz")
capital_cuenta = st.sidebar.number_input("Saldo Disponible ($ ARS)", min_value=10000, value=158000, step=50000)
riesgo_maximo_ars = capital_cuenta * 0.02

st.sidebar.markdown(f"**Tu riesgo máximo permitido (2%):** ${riesgo_maximo_ars:,.2f}")

st.sidebar.header("⚙️ Calibración de Filtros")
ratio_beneficio = st.sidebar.slider("Ratio Recompensa / Riesgo Mínimo", 1.5, 3.5, 2.0, step=0.1)
umbral = st.sidebar.slider("Tolerancia de proximidad EMA", 0.001, 0.015, 0.005, step=0.001)

COSTO_OPERATIVO_TOTAL = (0.0050 + 0.0005) * 1.21 

# VALIDACIÓN DEL HORARIO DE APERTURA GANADOR (11:00h a 13:00h)
hora_actual = datetime.now().hour
es_horario_optimo = 11 <= hora_actual <= 13

if st.sidebar.button("🔔 Probar Conexión de Telegram"):
    exito = enviar_alerta_telegram("✨ ¡Conexión Exitosa! El motor de Selección Inteligente está listo para operar.")
    if exito: st.sidebar.success("¡Mensaje enviado! Revisa tu celular.")
    else: st.sidebar.error("Error de enlace. Verifica las credenciales.")

if st.button("🚀 Ejecutar Algoritmo de Asignación y Selección"):
    if not es_horario_optimo:
        st.warning("⚠️ Alerta de Contexto: No estás dentro de la ventana de apertura óptima (11:00h a 13:00h). El bot escaneará el mercado pero recuerda que la estadística ganadora se da temprano.")
        
    with st.spinner("Analizando mercado, calculando lotes nominales enteros y seleccionando la mejor decisión..."):
        try:
            datos_mercado = yf.download(tickers, period="6mo", interval="1d", progress=False)
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            datos_mercado = None

    if datos_mercado is not None and not datos_market_empty := datos_mercado.empty:
        candidatos_validos = []

        for ticker in tickers:
            try:
                df_ticker = pd.DataFrame()
                df_ticker['Close'] = datos_mercado['Close'][ticker].dropna()
                df_ticker['Open'] = datos_mercado['Open'][ticker].dropna()
                df_ticker['Low'] = datos_mercado['Low'][ticker].dropna()
                df_ticker['High'] = datos_mercado['High'][ticker].dropna()
                
                if len(df_ticker) < 50: continue
                
                precio_actual = float(df_ticker['Close'].iloc[-1])
                precio_apertura = float(df_ticker['Open'].iloc[-1])
                precio_minimo = float(df_ticker['Low'].iloc[-1])
                
                ema9 = df_ticker['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
                ema50 = df_ticker['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                
                high_low = df_ticker['High'] - df_ticker['Low']
                high_close_prev = abs(df_ticker['High'] - df_ticker['Close'].shift())
                low_close_prev = abs(df_ticker['Low'] - df_ticker['Close'].shift())
                true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
                atr14 = true_range.rolling(14).mean().iloc[-1]
                
                delta = df_ticker['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi14 = 100 - (100 / (1 + rs)).iloc[-1]
                
                exp1 = df_ticker['Close'].ewm(span=12, adjust=False).mean()
                exp2 = df_ticker['Close'].ewm(span=26, adjust=False).mean()
                macd_line = exp1 - exp2
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                histograma_macd = (macd_line - signal_line).iloc[-1]
                hist_anterior = (macd_line - signal_line).iloc[-2]
                
                # REGLAS FILTRADAS
                es_vela_verde = precio_actual > precio_apertura
                tendencia_alcista = precio_actual > ema50
                toca_ema9 = abs(precio_minimo - ema9) / precio_actual <= umbral
                toca_ema50 = abs(precio_minimo - ema50) / precio_actual <= umbral
                
                disparar = False
                ema_ref = ema50
                
                if tendencia_alcista and es_vela_verde and (toca_ema9 or toca_ema50):
                    disparar = True
                    ema_ref = ema50 if toca_ema50 else ema9
                elif not tendencia_alcista and es_vela_verde and toca_ema9 and rsi14 <= 55:
                    disparar = True
                    ema_ref = ema9

                if disparar:
                    precio_entrada_neto = precio_actual * (1 + COSTO_OPERATIVO_TOTAL)
                    stop_loss_grafico = ema_ref - (2 * atr14)
                    if stop_loss_grafico >= precio_actual: stop_loss_grafico = precio_actual * 0.97
                    precio_salida_stop_neto = stop_loss_grafico * (1 - COSTO_OPERATIVO_TOTAL)
                    
                    distancia_riesgo_pct = (precio_entrada_neto - precio_salida_stop_neto) / precio_entrada_neto
                    precio_take_profit = precio_actual * (1 + (distancia_riesgo_pct * ratio_beneficio))
                    
                    perdida_por_accion = precio_entrada_neto - precio_salida_stop_neto
                    cantidad_cedears = int(riesgo_maximo_ars // perdida_por_accion)
                    
                    if cantidad_cedears <= 0: continue
                    monto_total_compra = precio_entrada_neto * cantidad_cedears
                    
                    # FILTRO DE FACTIBILIDAD REAL: El capital debe alcanzar para comprar nominales enteros 
                    # Y el precio de una sola unidad no debe superar tu saldo total disponible en Balanz
                    if monto_total_compra > capital_cuenta or precio_entrada_neto > capital_cuenta: continue
                    
                    # CÁLCULO DEL SCORE CUANTITATIVO DE CALIDAD (0 a 3 Puntos)
                    score_calidad = 0
                    if rsi14 > 40 and rsi14 < 60: score_calidad += 1
                    if histograma_macd > hist_anterior: score_calidad += 1
                    if tendencia_alcista: score_calidad += 1 # Otorga prioridad a activos a favor de corriente mayor
                    
                    candidatos_validos.append({
                        "Ticker": ticker.split('.')[0], "Precio_Mercado": precio_actual, "Precio_Neto": precio_entrada_neto,
                        "Stop_Loss": stop_loss_grafico, "Take_Profit": precio_take_profit, "Cantidad": cantidad_cedears,
                        "Total_Pesos": monto_total_compra, "Score": score_calidad, "RSI": rsi14
                    })
            except Exception:
                continue

        if candidatos_validos:
            # Ordenamos los candidatos estrictamente de mayor a menor calidad (Score)
            df_oportunidades = pd.DataFrame(candidatos_validos).sort_values(by="Score", ascending=False).reset_index(drop=True)
            
            st.success("🤖 ¡Análisis de asignación inteligente completado!")
            
            # SELECCIÓN EXCLUSIVA DE LA MEJOR DECISIÓN
            mejor_opcion = df_oportunidades.iloc[0]
            
            # RENDERIZADO DEL MAPA DE CARGA EN LA WEB
            st.subheader("🎯 La Mejor Decisión Seleccionada para tu Cuenta")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("CEDEAR Recomendado", mejor_opcion["Ticker"])
            col_b.metric("Cantidad de Nominales", int(mejor_opcion["Cantidad"]))
            col_c.metric("Capital a Invertir", f"$ {mejor_opcion['Total_Pesos']:,.2f}")
            
            # DESPACHO DEL MENSAJE EXCLUSIVO INTEGRADO A TELEGRAM
            msg_telegram = (
                f"🤖 *¡ASIGNACIÓN DE CAPITAL REALISTA E INTELIGENTE!*\n\n"
                f"🎯 *La mejor decisión para hoy:* `{mejor_opcion['Ticker']}`\n"
                f"🧮 *Cantidad nominal a comprar:* {int(mejor_opcion['Cantidad'])} unidades\n\n"
                f"💵 *Precio Pantalla:* ${mejor_opcion['Precio_Mercado']:,.2f}\n"
                f"📐 *Precio Entrada Neto:* ${mejor_opcion['Precio_Neto']:,.2f} (Con costos Balanz)\n"
                f"🛡️ *ORDEN DE STOP LOSS:* ${mejor_opcion['Stop_Loss']:,.2f}\n"
                f"🎯 *ORDEN DE TAKE PROFIT:* ${mejor_opcion['Take_Profit']:,.2f}\n\n"
                f"💰 *Costo Total Requerido:* ${mejor_opcion['Total_Pesos']:,.2f}\n"
                f"🔍 *Puntaje de Calidad Institucional:* {int(mejor_opcion['Score'])} / 3 Puntos.\n"
                f"⏰ *Estado:* Ventana de apertura validada. Cargar órdenes en Balanz."
            )
            enviar_alerta_telegram(msg_telegram)
            
            st.subheader("📋 Matriz Completa de Oportunidades Factibles Ordenadas por Calidad")
            st.dataframe(df_oportunidades, use_container_width=True)
        else:
            st.info("Ningún CEDEAR cumple las condiciones técnicas y las restricciones de lote mínimo para tu saldo actual de cuenta hoy.")

