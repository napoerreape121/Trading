import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime
import ta  

# Rutas absolutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_DB = os.path.join(BASE_DIR, "portafolio.csv")
ARCHIVO_HISTORIAL = os.path.join(BASE_DIR, "historial_cerradas.csv")

COSTO_OPERATIVO_TOTAL = (0.0050 + 0.0005) * 1.21
COLUMNAS_PORTAFOLIO = ["Ticker", "Cantidad", "PrecioCompra", "StopLoss", "TakeProfit", "FechaEntrada"]
MIN_VELAS = 200

# Configuración del panel de control
st.set_page_config(page_title="Asistente Cuantitativo Pro", page_icon="🤖", layout="wide")

st.title("🤖 Asistente de Trading de CEDEARs con Gestión Activa de Portafolio")
st.write(
    "Sistema Cuantitativo Estricto: El bot filtra oportunidades usando confluencias de Tendencia (EMA 200), "
    "Momentum (MACD + RSI), Estructura (Soporte/Resistencia 10d) y Gatillos de Volumen."
)

TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", os.environ.get("TELEGRAM_TOKEN", "8624285419:AAHS-aTMjxM9H33dqtqC4JCQzwyqqL_Q71Y"))
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", "6872048498"))


def enviar_alerta_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def precio_compra_neto(precio_bruto):
    return precio_bruto * (1 + COSTO_OPERATIVO_TOTAL)


def precio_venta_neto(precio_bruto):
    return precio_bruto * (1 - COSTO_OPERATIVO_TOTAL)


def extraer_ohlc(datos, ticker):
    if datos is None or datos.empty:
        raise ValueError(f"Sin datos de mercado para {ticker}")

    columnas = datos.columns
    if isinstance(columnas, pd.MultiIndex):
        niveles = columnas.get_level_values(-1)
        if ticker in niveles:
            sub = datos.xs(ticker, axis=1, level=-1)
        elif ticker in columnas.get_level_values(0):
            sub = datos.xs(ticker, axis=1, level=0)
        else:
            sub = pd.DataFrame({
                "Open": datos["Open"][ticker],
                "High": datos["High"][ticker],
                "Low": datos["Low"][ticker],
                "Close": datos["Close"][ticker],
                "Volume": datos["Volume"][ticker],
            })
    else:
        sub = datos[["Open", "High", "Low", "Close", "Volume"]].copy()

    sub = sub.dropna()
    if len(sub) < MIN_VELAS:
        raise ValueError(f"Datos insuficientes para {ticker}")
    return sub


@st.cache_data(ttl=900)  
def descargar_mercado(tickers, period="2y"): 
    if isinstance(tickers, str):
        tickers = [tickers]
    datos = yf.download(
        tickers,
        period=period,
        interval="1d",
        progress=False,
        group_by="column",
        auto_adjust=True,
        threads=True,
    )
    if datos is None or datos.empty:
        raise ValueError("yfinance no devolvió datos")
    return datos


def guardar_portafolio(df):
    df.to_csv(ARCHIVO_DB, index=False)


def cargar_portafolio():
    if not os.path.exists(ARCHIVO_DB):
        pd.DataFrame(columns=COLUMNAS_PORTAFOLIO).to_csv(ARCHIVO_DB, index=False)
    df = pd.read_csv(ARCHIVO_DB)
    if df.empty:
        return df
    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    return df


def registrar_cierre(row, motivo, precio_cierre):
    registro = pd.DataFrame([{
        "Ticker": row["Ticker"],
        "Cantidad": int(row["Cantidad"]),
        "PrecioCompra": float(row["PrecioCompra"]),
        "StopLoss": float(row["StopLoss"]),
        "TakeProfit": float(row["TakeProfit"]),
        "FechaEntrada": row["FechaEntrada"],
        "FechaCierre": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "MotivoCierre": motivo,
        "PrecioCierre": float(precio_cierre),
    }])
    if os.path.exists(ARCHIVO_HISTORIAL):
        pd.concat([pd.read_csv(ARCHIVO_HISTORIAL), registro], ignore_index=True).to_csv(
            ARCHIVO_HISTORIAL, index=False
        )
    else:
        registro.to_csv(ARCHIVO_HISTORIAL, index=False)


def normalizar_ticker(ticker):
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return ""
    if not ticker.endswith(".BA"):
        ticker = f"{ticker}.BA"
    return ticker


def validar_operacion(precio, sl, tp):
    if sl <= 0 or tp <= 0 or precio <= 0:
        return "Los precios deben ser mayores a cero."
    if not (sl < precio < tp):
        return "Debe cumplirse: Stop Loss < Precio de compra < Take Profit."
    return None

# ==========================================
# INICIO DE APLICACIÓN
# ==========================================

df_portafolio = cargar_portafolio()

st.sidebar.header("📥 Registrar Compra Real en Balanz")
with st.sidebar.form(key="formulario_balanz", clear_on_submit=True):
    ticker_input = st.text_input("Ticker del CEDEAR (Ej: AAPL)")
    cant_real = st.number_input("Cantidad de nominales comprados", min_value=1, value=1, step=1)
    precio_real = st.number_input("Precio de compra neto ($)", min_value=0.01, value=1000.0, step=100.0)
    sl_real = st.number_input("Stop Loss inicial ($)", min_value=0.01, value=900.0, step=100.0)
    tp_real = st.number_input("Take Profit inicial ($)", min_value=0.01, value=1200.0, step=100.0)

    boton_guardar = st.form_submit_button(label="💾 Guardar y Monitorear Posición")

    if boton_guardar:
        ticker_real = normalizar_ticker(ticker_input)
        if not ticker_real:
            st.sidebar.error("Ingresá un ticker válido.")
        else:
            error_validacion = validar_operacion(precio_real, sl_real, tp_real)
            if error_validacion:
                st.sidebar.error(error_validacion)
            elif ticker_real in df_portafolio["Ticker"].values:
                st.sidebar.error(f"{ticker_real} ya está en el portafolio. Cerrala antes de reingresarla.")
            else:
                nueva_posicion = pd.DataFrame([{
                    "Ticker": ticker_real,
                    "Cantidad": int(cant_real),
                    "PrecioCompra": float(precio_real),
                    "StopLoss": float(sl_real),
                    "TakeProfit": float(tp_real),
                    "FechaEntrada": datetime.now().strftime("%Y-%m-%d"),
                }])
                df_actualizado = pd.concat([df_portafolio, nueva_posicion], ignore_index=True)
                guardar_portafolio(df_actualizado)
                st.sidebar.success(f"¡{ticker_real} grabado con éxito!")
                st.rerun()

st.subheader("📋 Tus Posiciones Abiertas Actualmente Activas")
if not df_portafolio.empty:
    st.dataframe(df_portafolio, use_container_width=True)

    if st.button("🗑️ Vaciar todo el Portafolio"):
        pd.DataFrame(columns=COLUMNAS_PORTAFOLIO).to_csv(ARCHIVO_DB, index=False)
        st.success("¡Base de datos limpiada correctamente!")
        st.rerun()
else:
    st.info("No tienes operaciones cargadas. El portafolio de vigilancia permanente está vacío.")

if os.path.exists(ARCHIVO_HISTORIAL):
    df_historial = pd.read_csv(ARCHIVO_HISTORIAL)
    if not df_historial.empty:
        with st.expander("📜 Historial de posiciones cerradas"):
            st.dataframe(df_historial, use_container_width=True)

tickers_escaner = [
    "AAL.BA", "ABT.BA", "ACWI.BA", "ADBE.BA", "AMD.BA", "AMZN.BA", "AAPL.BA", "ARM.BA", "ARKK.BA", "ASML.BA",
    "AXP.BA", "BAC.BA", "BA.BA", "BABA.BA", "BKNG.BA", "BP.BA", "BRKB.BA", "BX.BA", "C.BA", "CAT.BA",
    "CCL.BA", "COPX.BA", "COIN.BA", "COST.BA", "CRM.BA", "CVS.BA", "CVX.BA", "DAL.BA", "DE.BA", "DISN.BA",
    "DIA.BA", "EFA.BA", "ETHA.BA", "GE.BA", "GOOGL.BA", "GS.BA", "HD.BA", "HON.BA", "IBM.BA", "INTC.BA",
    "JNJ.BA", "JPM.BA", "KO.BA", "LLY.BA", "MA.BA", "MCD.BA", "META.BA", "MELI.BA", "MMM.BA", "MSFT.BA",
    "NFLX.BA", "NKE.BA", "NVDA.BA", "ORCL.BA", "PANW.BA", "PEP.BA", "PFE.BA", "PG.BA", "PYPL.BA", "QCOM.BA",
    "QQQ.BA", "ROKU.BA", "SHOP.BA", "SNOW.BA", "SONY.BA", "SPY.BA", "T.BA", "TEAM.BA", "TGT.BA", "TSLA.BA",
    "TSM.BA", "TXN.BA", "UAL.BA", "UBER.BA", "UNH.BA", "V.BA", "VZ.BA", "WFC.BA", "WMT.BA", "XOM.BA",
]

st.sidebar.header("⚙️ Parámetros del Escáner de Compras")
capital_disponible = st.sidebar.number_input("Tu Capital Total Libre ($ ARS)", min_value=10000, value=158000, step=10000)

if st.button("🚀 Ejecutar Escáner General y Despachar Gestión"):
    df_portafolio_activo = cargar_portafolio()
    portafolio_modificado = False

    if not df_portafolio_activo.empty:
        st.subheader("🕵️ Análisis Cuantitativo de tus Posiciones Abiertas")
        tickers_cartera = df_portafolio_activo["Ticker"].unique().tolist()
        indices_cerrar = []

        try:
            datos_cartera = descargar_mercado(tickers_cartera, period="1y")

            for idx, row in df_portafolio_activo.iterrows():
                tick = row["Ticker"]
                try:
                    df_t_cart = extraer_ohlc(datos_cartera, tick)
                except Exception as err:
                    st.warning(f"No se pudo analizar {tick}: {err}")
                    continue

                precio_vivo = float(df_t_cart["Close"].iloc[-1])
                low_vivo = float(df_t_cart["Low"].iloc[-1])
                high_vivo = float(df_t_cart["High"].iloc[-1])
                
                ema9_v = ta.trend.ema_indicator(df_t_cart["Close"], window=9).iloc[-1]
                atr14_v = ta.volatility.average_true_range(df_t_cart["High"], df_t_cart["Low"], df_t_cart["Close"], window=14).iloc[-1]

                stop_actual = float(row["StopLoss"])
                take_profit = float(row["TakeProfit"])
                precio_compra = float(row["PrecioCompra"])

                if low_vivo <= stop_actual:
                    msg_sl = (
                        f"🚨 *¡ALERTA CRÍTICA DE SALIDA!* 🚨\n\n"
                        f"📉 El CEDEAR `{tick.split('.')[0]}` perforó tu *Stop Loss* de ${stop_actual:,.2f}.\n"
                        f"🛒 *Acción:* VENDER de inmediato tus {int(row['Cantidad'])} unidades.\n"
                    )
                    enviar_alerta_telegram(msg_sl)
                    registrar_cierre(row, "Stop Loss", stop_actual)
                    indices_cerrar.append(idx)
                    portafolio_modificado = True
                    st.error(f"{tick}: Stop Loss perforado.")
                    continue

                if high_vivo >= take_profit:
                    msg_tp = (
                        f"🎯 *¡ALERTA DE OBJETIVO CUMPLIDO!* 🎯\n\n"
                        f"📈 El CEDEAR `{tick.split('.')[0]}` tocó tu *Take Profit* de ${take_profit:,.2f}.\n"
                        f"🛒 *Acción:* VENDER tus {int(row['Cantidad'])} unidades y retirar ganancias.\n"
                    )
                    enviar_alerta_telegram(msg_tp)
                    registrar_cierre(row, "Take Profit", take_profit)
                    indices_cerrar.append(idx)
                    portafolio_modificado = True
                    st.success(f"{tick}: Take Profit alcanzado.")
                    continue

                nuevo_stop = round(ema9_v - (1.5 * atr14_v), 2)
                if (precio_vivo > precio_compra and nuevo_stop > stop_actual and nuevo_stop < precio_vivo):
                    df_portafolio_activo.at[idx, "StopLoss"] = nuevo_stop
                    portafolio_modificado = True
                    msg_trailing = (
                        f"🔄 *¡TRAILING STOP ACTUALIZADO!*\n\n"
                        f"📈 `{tick.split('.')[0]}` sigue a tu favor.\n"
                        f"🛡️ *Nuevo Stop Loss:* `${nuevo_stop:,.2f}` (antes `${stop_actual:,.2f}`)\n"
                    )
                    enviar_alerta_telegram(msg_trailing)
                    st.info(f"🔄 **{tick.split('.')[0]}:** Stop Loss actualizado a **${nuevo_stop:,.2f}**")

            if indices_cerrar:
                df_portafolio_activo = df_portafolio_activo.drop(indices_cerrar).reset_index(drop=True)
            if portafolio_modificado:
                guardar_portafolio(df_portafolio_activo)

        except Exception as e:
            st.warning(f"Error al auditar tu portafolio: {e}")

    with st.spinner("Ejecutando algoritmo de confluencias estrictas (Estructura a 10 días)..."):
        try:
            datos_mercado = descargar_mercado(tickers_escaner, period="2y")
        except Exception as e:
            st.error(f"Error en la descarga de mercado: {e}")
            datos_mercado = None

    if datos_mercado is not None and not datos_mercado.empty:
        candidatos_validos = []
        tickers_en_cartera = set(df_portafolio_activo["Ticker"].tolist()) if not df_portafolio_activo.empty else set()
        riesgo_maximo_ars = capital_disponible * 0.02 

        for ticker in tickers_escaner:
            if ticker in tickers_en_cartera:
                continue
            
            try:
                df_t = extraer_ohlc(datos_mercado, ticker)

                df_t["EMA_9"] = ta.trend.ema_indicator(df_t["Close"], window=9)
                df_t["EMA_200"] = ta.trend.ema_indicator(df_t["Close"], window=200)
                df_t["RSI_14"] = ta.momentum.rsi(df_t["Close"], window=14)
                df_t["MACD_Hist"] = ta.trend.MACD(df_t["Close"]).macd_diff()
                df_t["ATR_14"] = ta.volatility.average_true_range(df_t["High"], df_t["Low"], df_t["Close"], window=14)
                df_t["Volumen_SMA_9"] = df_t["Volume"].rolling(window=9).mean()
                
                # MODIFICACIÓN APLICADA: Estructura de 10 días para sincronizar con la EMA 9
                df_t["Soporte_10"] = df_t["Low"].rolling(window=10).min()
                df_t["Resistencia_10"] = df_t["High"].rolling(window=10).max()

                df_t = df_t.dropna()
                if len(df_t) < 2:
                    continue

                last = df_t.iloc[-1]
                prev = df_t.iloc[-2]

                Precio_Cierre = last["Close"]
                Precio_Apertura = last["Open"]
                Volumen_Actual = last["Volume"]
                
                EMA_200 = last["EMA_200"]
                EMA_9 = last["EMA_9"]
                MACD_Hist_Actual = last["MACD_Hist"]
                MACD_Hist_Previo = prev["MACD_Hist"]
                RSI_Actual = last["RSI_14"]
                Volumen_SMA_9 = last["Volumen_SMA_9"]
                ATR_Actual = last["ATR_14"]

                # Extraemos niveles estructurales de 10 días
                Soporte = prev["Soporte_10"] 
                Resistencia = prev["Resistencia_10"] 

                Condicion_Tendencia = (Precio_Cierre > EMA_200)
                Condicion_Momentum = (Precio_Cierre > EMA_9) and (MACD_Hist_Actual > MACD_Hist_Previo) and (40 < RSI_Actual < 65)
                Condicion_Gatillo = (Precio_Cierre > Precio_Apertura) and (Volumen_Actual > Volumen_SMA_9)
                
                # Mantuvimos la rigurosidad: Rebote al 2% y Camino Libre de 1.5x
                Toco_Soporte = (last["Low"] <= Soporte * 1.02) and (last["Low"] >= Soporte * 0.98)
                Distancia_Resistencia = Resistencia - Precio_Cierre
                Distancia_Soporte = Precio_Cierre - Soporte
                Camino_Libre = Distancia_Resistencia >= (Distancia_Soporte * 1.5)
                
                Condicion_Estructura = Toco_Soporte and Camino_Libre

                SEÑAL_COMPRA = Condicion_Tendencia and Condicion_Momentum and Condicion_Gatillo and Condicion_Estructura

                if not SEÑAL_COMPRA:
                    continue

                Precio_Neto_Entrada = precio_compra_neto(Precio_Cierre)
                Stop_Loss = Precio_Neto_Entrada - (2 * ATR_Actual)
                Target = Precio_Neto_Entrada + ((Precio_Neto_Entrada - Stop_Loss) * 2) 
                
                Riesgo_por_Accion = Precio_Neto_Entrada - Stop_Loss

                if Stop_Loss <= 0 or Riesgo_por_Accion <= 0:
                    continue

                Cantidad = int(riesgo_maximo_ars // Riesgo_por_Accion)
                if Cantidad <= 0:
                    continue

                Costo_Total = Precio_Neto_Entrada * Cantidad
                if Costo_Total > capital_disponible:
                    continue

                candidatos_validos.append({
                    "Ticker": ticker,
                    "PrecioNetoEntrada": round(Precio_Neto_Entrada, 2),
                    "StopLoss": round(Stop_Loss, 2),
                    "Target": round(Target, 2),
                    "Cantidad": Cantidad,
                    "CostoTotal": round(Costo_Total, 2)
                })

            except Exception:
                continue

        if candidatos_validos:
            df_ops = pd.DataFrame(candidatos_validos).sort_values(by="CostoTotal", ascending=False).reset_index(drop=True)
            mejor_opcion = df_ops.iloc[0]

            st.success("🎯 ¡Sistema de Confluencias Activado! Se ha detectado una oportunidad de Alta Probabilidad estructural.")
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("CEDEAR", mejor_opcion["Ticker"])
            col_b.metric("Cantidad Sugerida", int(mejor_opcion["Cantidad"]))
            col_c.metric("Costo Estimado", f"$ {mejor_opcion['CostoTotal']:,.2f}")

            st.dataframe(df_ops, use_container_width=True)

            msg_tg = (
                f"🟩 *SEÑAL DE COMPRA CONFIRMADA (FRANCOTIRADOR)* 🟩\n\n"
                f"📌 *Ticker:* `{mejor_opcion['Ticker']}`\n"
                f"⚖️ *Cantidad de nominales:* {int(mejor_opcion['Cantidad'])} *(Riesgo 2% del capital)*\n"
                f"💲 *Precio de Entrada Neto:* `${mejor_opcion['PrecioNetoEntrada']:,.2f}`\n\n"
                f"⛔ *Stop Loss sugerido:* `${mejor_opcion['StopLoss']:,.2f}`\n"
                f"🎯 *Target de salida (Ratio 1:2):* `${mejor_opcion['Target']:,.2f}`\n\n"
                f"✅ _Confluencias: Tendencia (EMA200) + Momentum + Rebote en Soporte 10d + Camino Libre hacia Resistencia._"
            )
            enviar_alerta_telegram(msg_tg)
        else:
            st.info("Ningún CEDEAR superó el filtro de francotirador en la sesión actual. Protegiendo capital.")

    if portafolio_modificado:
        st.subheader("📋 Portafolio actualizado tras la gestión")
        st.dataframe(df_portafolio_activo, use_container_width=True)
