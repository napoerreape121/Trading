import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import time
import threading
from datetime import datetime, timedelta

# Configuración del panel de control inteligente en internet
st.set_page_config(page_title="Asistente Cuantitativo Pro", page_icon="🤖", layout="wide")
st.title("🤖 Asistente de Trading de CEDEARs con Gestión de Portafolio")
st.write("Carga tus operaciones reales de Balanz. El bot vigilará tus Stop Loss y Take Profit de forma automatizada.")

# Credenciales fijas y verificadas de tu canal de Telegram
TELEGRAM_TOKEN = "8624285419:AAHS-aTMjxM9H33dqtqC4JCQzwyqqL_Q71Y"
TELEGRAM_CHAT_ID = "6872048498"
HORA_AUTOMATICA = "00:46"  # <-- Configura acá la hora exacta en formato 24hs para recibir el informe

def enviar_alerta_telegram(mensaje):
    """Módulo oficial de comunicación en red con la API de Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def obtener_ventana_balance_estimada(ticker):
    """Calcula la próxima ventana estimada de presentación de balances en Wall Street"""
    ahora = datetime.now()
    mes_actual = ahora.month
    año_actual = ahora.year
    
    if mes_actual in [12, 1, 2]:
        estimado = datetime(año_actual if mes_actual != 12 else año_actual + 1, 1, 25)
    elif mes_actual in [3, 4, 5]:
        estimado = datetime(año_actual, 4, 25)
    elif mes_actual in [6, 7, 8]:
        estimado = datetime(año_actual, 7, 25)
    else:
        estimado = datetime(año_actual, 10, 25)
        
    if estimado < ahora:
        estimado += timedelta(days=90)
        
    dias_restantes = (estimado - ahora).days
    alerta_balance = "⚠️ ¡ALERTA: BALANCE CERCA!" if dias_restantes <= 14 else "🟢 Zona Segura"
    return f"{estimado.strftime('%d/%m/%Y')} ({alerta_balance} - Faltan ~{dias_restantes} días)"

# BASE DE DATOS LOCAL PERMANENTE
ARCHIVO_DB = "portafolio.csv"
if not os.path.exists(ARCHIVO_DB):
    df_inicial = pd.DataFrame(columns=["Ticker", "Cantidad", "PrecioCompra", "StopLoss", "TakeProfit", "FechaEntrada"])
    df_inicial.to_csv(ARCHIVO_DB, index=False)

df_portafolio = pd.read_csv(ARCHIVO_DB)

# MÓDULO lateral: Carga de Operaciones Reales con Guardado Permanente
st.sidebar.header("📥 Registrar Compra Real en Balanz")
with st.sidebar.form(key="formulario_balanz", clear_on_submit=True):
    ticker_real = st.text_input("Ticker del CEDEAR (Ej: AAPL)").upper().strip()
    if ticker_real and not ticker_real.endswith(".BA"):
        ticker_real = f"{ticker_real}.BA"
    
    cant_real = st.number_input("Cantidad de nominales comprados", min_value=1, value=1, step=1)
    precio_real = st.number_input("Precio de compra por unidad ($)", min_value=1.0, value=1000.0, step=100.0)
    sl_real = st.number_input("Stop Loss fijado ($)", min_value=0.0, value=900.0, step=100.0)
    tp_real = st.number_input("Take Profit fijado ($)", min_value=0.0, value=1200.0, step=100.0)
    
    boton_guardar = st.form_submit_button(label="💾 Guardar de Forma Permanente")
    
    if boton_guardar and ticker_real:
        nueva_posicion = pd.DataFrame([{
            "Ticker": ticker_real, "Cantidad": int(cant_real), "PrecioCompra": float(precio_real),
            "StopLoss": float(sl_real), "TakeProfit": float(tp_real), "FechaEntrada": datetime.now().strftime('%Y-%m-%d')
        }])
        df_actualizado = pd.concat([df_portafolio, nueva_posicion], ignore_index=True)
        df_actualizado.to_csv(ARCHIVO_DB, index=False)
        st.sidebar.success(f"¡{ticker_real} grabado en el disco duro con éxito!")
        st.rerun()

# PANEL PRINCIPAL: Visualización de tus acciones bajo vigilancia permanente
st.subheader("📋 Tus Posiciones Abiertas Actualmente Activas")
if not df_portafolio.empty:
    st.dataframe(df_portafolio, use_container_width=True)
    
    st.write("---")
    st.markdown("### 🛠️ Gestión de Cartera Abierta")
    col_borrar, col_vaciar = st.columns(2)
    
    with col_borrar:
        opciones_borrar = [f"{row['Ticker']} - Compra: ${row['PrecioCompra']:,.2f} [Cant: {int(row['Cantidad'])}]" for idx, row in df_portafolio.iterrows()]
        seleccion_activo = st.selectbox("Seleccioná la posición exacta que querés eliminar:", opciones_borrar)
        
        if st.button("🗑️ Eliminar Activo Seleccionado"):
            indice_a_borrar = opciones_borrar.index(seleccion_activo)
            ticker_eliminado = df_portafolio.iloc[indice_a_borrar]["Ticker"]
            df_portafolio = df_portafolio.drop(df_portafolio.index[indice_a_borrar]).reset_index(drop=True)
            df_portafolio.to_csv(ARCHIVO_DB, index=False)
            st.success(f"¡La posición de {ticker_eliminado} fue eliminada del disco duro!")
            st.rerun()
            
    with col_vaciar:
        st.write("<br>", unsafe_allow_html=True)
        if st.button("🚨 Vaciar todo el Portafolio Completo"):
            df_limpio = pd.DataFrame(columns=["Ticker", "Cantidad", "PrecioCompra", "StopLoss", "TakeProfit", "FechaEntrada"])
            df_limpio.to_csv(ARCHIVO_DB, index=False)
            st.success("¡Base de datos limpiada correctamente!")
            st.rerun()
    st.write("---")
else:
    st.info("No tienes operaciones cargadas. El portafolio de vigilancia permanente está vacío.")

# Listado de tus 80 CEDEARs para escaneo de compras
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

# --- NÚCLEO CENTRAL DE PROCESAMIENTO REUTILIZABLE ---
def ejecutar_analisis_cuantitativo():
    """Ejecuta toda la lógica interna de trading y envía alertas a Telegram"""
    df_actual_portafolio = pd.read_csv(ARCHIVO_DB)
    precios_vivos_cartera = {}
    
    if not df_actual_portafolio.empty:
        tickers_cartera = df_actual_portafolio["Ticker"].unique().tolist()
        try:
            datos_cartera = yf.download(tickers_cartera, period="5d", interval="1d", progress=False)
            for idx, row in df_actual_portafolio.iterrows():
                tick = row["Ticker"]
                close_vivo = float(datos_cartera['Close'][tick].dropna().iloc[-1])
                low_vivo = float(datos_cartera['Low'][tick].dropna().iloc[-1])
                high_vivo = float(datos_cartera['High'][tick].dropna().iloc[-1])
                precios_vivos_cartera[tick] = close_vivo
                
                if low_vivo <= float(row["StopLoss"]):
                    msg_sl = f"🚨 *¡ALERTA CRÍTICA DE SALIDA!* 🚨\n\n📉 El CEDEAR `{tick}` tocó tu *Stop Loss* de ${row['StopLoss']:,.2f}.\n🛒 *Acción:* VENDER de inmediato tus {int(row['Cantidad'])} unidades en Balanz para cortar pérdidas."
                    enviar_alerta_telegram(msg_sl)
                elif high_vivo >= float(row["TakeProfit"]):
                    msg_tp = f"🎯 *¡ALERTA DE OBJETIVO CUMPLIDO!* 🎯\n\n📈 El CEDEAR `{tick}` tocó tu *Take Profit* de ${row['TakeProfit']:,.2f}.\n🛒 *Acción:* VENDER tus {int(row['Cantidad'])} unidades en Balanz y cobrar ganancias netas."
                    enviar_alerta_telegram(msg_tp)
        except Exception:
            pass

    detalles_bloqueo_capital = {}
    try:
        datos_mercado = yf.download(tickers_escaner, period="6mo", interval="1d", progress=False)
    except Exception:
        datos_mercado = None
        
    if datos_mercado is not None and not datos_mercado.empty:
        candidatos_validos = []
        for ticker in tickers_escaner:
            try:
                df_t = pd.DataFrame()
                df_t['Close'] = datos_mercado['Close'][ticker].dropna()
                df_t['Open'] = datos_mercado['Open'][ticker].dropna()
                df_t['Low'] = datos_mercado['Low'][ticker].dropna()
                df_t['High'] = datos_mercado['High'][ticker].dropna()
                
                precio_act = float(df_t['Close'].iloc[-1])
                precio_ape = float(df_t['Open'].iloc[-1])
                precio_min = float(df_t['Low'].iloc[-1])
                
                ema9 = df_t['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
                ema50 = df_t['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                
                high_low = df_t['High'] - df_t['Low']
                high_close_prev = abs(df_t['High'] - df_t['Close'].shift())
                low_close_prev = abs(df_t['Low'] - df_t['Close'].shift())
                true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
                atr14 = true_range.rolling(14).mean().iloc[-1]
                
                delta = df_t['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rsi14 = 100 - (100 / (1 + (gain / loss))).iloc[-1]
                
                exp1 = df_t['Close'].ewm(span=12, adjust=False).mean()
                exp2 = df_t['Close'].ewm(span=26, adjust=False).mean()
                histograma_macd = (exp1 - exp2 - (exp1 - exp2).ewm(span=9, adjust=False).mean()).iloc[-1]
                hist_anterior = (exp1 - exp2 - (exp1 - exp2).ewm(span=9, adjust=False).mean()).iloc[-2]
                
                es_vela_verde = precio_act > precio_ape
                tendencia_alcista = precio_act > ema50
                toca_ema9 = abs(precio_min - ema9) / precio_act <= umbral
                toca_ema50 = abs(precio_min - ema50) / precio_act <= umbral
                
                disparar = False
                ema_ref = ema50
                if tendencia_alcista and es_vela_verde and (toca_ema9 or toca_ema50):
                    disparar = True
                    ema_ref = ema50 if toca_ema50 else ema9
                elif not tendencia_alcista and es_vela_verde and toca_ema9 and rsi14 <= 55:
                    disparar = True
                    ema_ref = ema9
                    
                if disparar:
                    precio_ent_neto = precio_act * (1 + COSTO_OPERATIVO_TOTAL)
                    sl_g = ema_ref - (2 * atr14)
                    if sl_g >= precio_act * 0.97: 
                        sl_g = precio_act * 0.97
                    precio_sal_sl_neto = sl_g * (1 - COSTO_OPERATIVO_TOTAL)
                    
                    dist_riesgo = (precio_ent_neto - precio_sal_sl_neto) / precio_ent_neto
                    precio_tp = precio_act * (1 + (dist_riesgo * ratio_beneficio))
                    
                    perdida_accion = precio_ent_neto - precio_sal_sl_neto
                    cant_cedears = int(riesgo_maximo_ars // perdida_accion)
                    
                    if cant_cedears <= 0: 
                        continue
                    monto_compra = precio_ent_neto * cant_cedears
                    ticker_limpio = ticker.replace('.BA', '')
                    
                    if monto_compra > capital_disponible or precio_ent_neto > capital_disponible: 
                        detalles_bloqueo_capital[ticker_limpio] = {
                            "MontoRequerido": monto_compra, "CantidadSugerida": cant_cedears,
                            "Precio": precio_act, "Neto": precio_ent_neto, "SL": sl_g, "TP": precio_tp,
                            "Score": 3 if tendencia_alcista and (40 < rsi14 < 60) and (histograma_macd > hist_anterior) else 2
                        }
                        continue
                    
                    score = 0
                    if 40 < rsi14 < 60: score += 1
                    if histograma_macd > hist_anterior: score += 1
                    if tendencia_alcista: score += 1
                    
                    candidatos_validos.append({
                        "Ticker": ticker_limpio, "Precio": precio_act, "Neto": precio_ent_neto,
                        "StopLoss": sl_g, "TakeProfit": precio_tp, "Cantidad": cant_cedears,
                        "Total": monto_compra, "Score": score, "PerdidaUnidad": perdida_accion
                    })
            except Exception:
                continue
        
        texto_inventario_completo = ""
        if not df_actual_portafolio.empty:
            texto_inventario_completo = "\n\n📦 *Detalle Crítico de tus Posiciones Abiertas:*"
            for idx, row in df_actual_portafolio.iterrows():
                t_completo = row["Ticker"] if row["Ticker"].endswith(".BA") else f"{row['Ticker']}.BA"
                t_corto = row["Ticker"].replace('.BA', '')
                
                if t_completo in precios_vivos_cartera:
                    pr_actual = precios_vivos_cartera[t_completo]
                else:
                    try:
                        pr_actual = float(yf.download(t_completo, period="1d", progress=False)['Close'].iloc[-1])
                    except Exception:
                        pr_actual = float(row["PrecioCompra"])
                
                rendimiento_porc = ((pr_actual - float(row["PrecioCompra"])) / float(row["PrecioCompra"])) * 100
                emoji_rendimiento = "🟢" if rendimiento_porc >= 0 else "🔴"
                info_balance = obtener_ventana_balance_estimada(t_corto)
                
                texto_inventario_completo += (
                    f"\n\n▪️ *CEDEAR:* `{t_corto}`"
                    f"\n  • Cantidad en Cartera: {int(row['Cantidad'])} unidades"
                    f"\n  • Precio Compra Balanz: ${row['PrecioCompra']:,.2f}"
                    f"\n  • Cotización en Vivo: ${pr_actual:,.2f}"
                    f"\n  • Rendimiento Actual: {emoji_rendimiento} {rendimiento_porc:+.2f}%"
                    f"\n  • Próximo Balance Estimado: {info_balance}"
                )
        else:
            texto_inventario_completo = "\n\n📌 *Posiciones Abiertas:* Ninguna posición activa."
                
        hora_actual = datetime.now().time()
        if hora_actual < datetime.strptime("15:30", "%H:%M").time():
            advertencia_horaria = "\n\n⏳ *⚠️ ADVERTENCIA DE RUEDA TEMPRANA:*\nEstás ejecutando el análisis antes de las 15:30. Vela en formación."
        else:
            advertencia_horaria = "\n\n📊 *CONSOLIDACIÓN:* Análisis ejecutado en hora óptima. Vela diaria madura."

        if candidatos_validos:
            df_ops = pd.DataFrame(candidatos_validos).sort_values(by="Score", ascending=False).reset_index(drop=True)
            mejor_opcion = df_ops.iloc[0]
            
            saldo_restante = capital_disponible - mejor_opcion["Total"]
            riesgo_consumido = int(mejor_opcion["Cantidad"]) * mejor_opcion["PerdidaUnidad"]
            riesgo_remanente_permitido = riesgo_maximo_ars - riesgo_consumido
            
            if riesgo_remanente_permitido >= mejor_opcion["PerdidaUnidad"]:
                papeles_extras_posibles = int(riesgo_remanente_permitido // mejor_opcion["PerdidaUnidad"])
                max_por_dinero = int(saldo_restante // mejor_opcion["Neto"])
                if papeles_extras_posibles > max_por_dinero:
                    papeles_extras_posibles = max_por_dinero
                
                if papeles_extras_posibles > 0:
                    texto_estado_billetera = f"✅ *¡SÍ PODES COMPRAR MÁS ADELANTE!* Te quedaría un saldo de ${saldo_restante:,.2f}."
                else:
                    texto_estado_billetera = f"🛑 *¡NO PODES COMPRAR MÁS PAPELES DE ESTA SEÑAL!* Rompería la regla del 2%."
            else:
                texto_estado_billetera = f"🛑 *¡NO PODES COMPRAR MÁS PAPELES DE ESTA SEÑAL!* Se agotó el riesgo del trade."

            balance_candidato = obtener_ventana_balance_estimada(mejor_opcion["Ticker"])
            es_recompra = not df_actual_portafolio.empty and (mejor_opcion["Ticker"] in df_actual_portafolio["Ticker"].str.replace('.BA', '', regex=False).values)
            tipo_operacion = "🔄 *RECOMPRA / REFUERZO DE CARTERA*" if es_recompra else "🎯 *NUEVO CEDEAR SELECCIONADO*"

            msg_tg = (
                f"🤖 *¡Hola David! Este es tu informe cuantitativo oficial.*\n\n"
                f"🟢 *ESTADO GENERAL:* ¡SI PODES COMPRAR!\n\n"
                f"{tipo_operacion}: `{mejor_opcion['Ticker']}`\n"
                f"🛒 *Acción en Balanz:* COMPRAR exactamente `{int(mejor_opcion['Cantidad'])}` unidades.\n\n"
                f"💵 Precio Mercado: ${mejor_opcion['Precio']:,.2f}\n"
                f"🛡️ ORDEN DE STOP LOSS: ${mejor_opcion['StopLoss']:,.2f}\n"
                f"🎯 ORDEN DE TAKE PROFIT: ${mejor_opcion['TakeProfit']:,.2f}\n\n"
                f"💰 Costo Total Operación: ${mejor_opcion['Total']:,.2f}\n"
                f"📅 Próximo Balance del Candidato: {balance_candidato}"
                f"{advertencia_horaria}\n\n{texto_estado_billetera}"
                f"{texto_inventario_completo}"
            )
            enviar_alerta_telegram(msg_tg)
            return df_ops
        else:
            if detalles_bloqueo_capital:
                primer_tk = list(detalles_bloqueo_capital.keys())[0]
                info_bloqueo = detalles_bloqueo_capital[primer_tk]
                falta_dinero = info_bloqueo["MontoRequerido"] - capital_disponible
                balance_bloqueado = obtener_ventana_balance_estimada(primer_tk)
                
                msg_bloqueo = (
                    f"🤖 *¡Hola David! Este es tu informe cuantitativo oficial.*\n\n"
                    f"🔴 *ESTADO GENERAL:* ¡NO PODES COMPRAR!\n\n"
                    f"⚠️ *Motivo:* Tu capital disponible actual (${capital_disponible:,.2f}) es insuficiente.\n\n"
                    f"🔍 *Activo Congelado:* `{primer_tk}`\n"
                    f"❌ Faltante de Caja: Necesitás transferir exactamente `${falta_dinero:,.2f}` a Balanz.\n"
                    f"📅 Próximo Balance del Candidato: {balance_bloqueado}"
                    f"{advertencia_horaria}{texto_inventario_completo}"
                )
                enviar_alerta_telegram(msg_bloqueo)
    return None

# --- BOTÓN MANUAL TRADICIONAL EN PANTALLA ---
if st.button("🚀 Ejecutar Escáner General y Despachar Gestión"):
    df_resultado = ejecutar_analisis_cuantitativo()
    if df_resultado is not None:
        st.success("¡Informe despachado con éxito de forma manual a tu Telegram!")
        st.dataframe(df_resultado.drop(columns=["PerdidaUnidad"]), use_container_width=True)
    else:
        st.info("Ningún CEDEAR reúne condiciones o falta saldo. Revisá Telegram.")

# --- NUEVO MOTOR DE ENTRADA EN SEGUNDO PLANO (AUTOMATIZACIÓN HORARIA) ---
def daemon_reloj_bot():
    """Bucle infinito en segundo plano que vigila el reloj para enviar el informe"""
    ultima_fecha_ejecutada = ""
    while True:
        ahora = datetime.now()
        hora_str = ahora.strftime("%H:%M")
        fecha_str = ahora.strftime("%Y-%m-%d")
        
        # Si coincide la hora programada y hoy todavía no se envió el reporte diario
        if hora_str == HORA_AUTOMATICA and fecha_str != ultima_fecha_ejecutada:
            # Los días Sábados y Domingos se saltean porque el mercado BYMA está cerrado
            if ahora.weekday() < 5: 
                ejecutar_analisis_cuantitativo()
            ultima_fecha_ejecutada = fecha_str
            
        time.sleep(30) # Revisa el reloj del sistema cada 30 segundos de forma eficiente

# Registrar e iniciar el hilo paralelo únicamente la primera vez que se monta la app
if "daemon_activo" not in st.session_state:
    st.session_state["daemon_activo"] = True
    t = threading.Thread(target=daemon_reloj_bot, daemon=True)
    t.start()

st.sidebar.write(f"⏰ **Estatus del Robot:** Automatizado para enviar reporte de forma autónoma todos los días hábiles a las `{HORA_AUTOMATICA}hs` de Argentina.")
