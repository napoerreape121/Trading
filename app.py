import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime
from ta.trend import EMAIndicator  # Librería ta para la EMA_200

# Rutas absolutas para persistencia local de datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_DB = os.path.join(BASE_DIR, "portafolio.csv")
ARCHIVO_HISTORIAL = os.path.join(BASE_DIR, "historial_cerradas.csv")

# Costo operativo de Balanz (0.5% + 0.05% de derechos de mercado) * IVA (21%)
COSTO_OPERATIVO_TOTAL = (0.0050 + 0.0005) * 1.21

COLUMNAS_PORTAFOLIO = ["Ticker", "Cantidad", "PrecioCompra", "StopLoss", "TakeProfit", "FechaEntrada"]
MIN_VELAS = 200  # Incrementado a 200 para el correcto cálculo de la EMA_200

# Configuración de Streamlit
st.set_page_config(page_title="Asistente Cuantitativo Pro", page_icon="🤖", layout="wide")
st.title("🤖 Asistente de Trading de CEDEARs - Confluencias Estrictas")
st.write("Monitoreo y Escáner Algorítmico basado en reglas cuantitativas sin subjetividad.")

# Variables de entorno para comunicación
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8624285419:AAHS-aTMjxM9H33dqtqC4JCQzwyqqL_Q71Y")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6872048498")

def enviar_alerta_telegram(mensaje):
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
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
                "Volume": datos["Volume"][ticker]
            })
    else:
        sub = datos[["Open", "High", "Low", "Close", "Volume"]].copy()
    
    sub = sub.dropna()
    if len(sub) < MIN_VELAS:
        raise ValueError(f"Datos insuficientes para {ticker} ({len(sub)} velas requeridas: {MIN_VELAS})")
    return sub

def calcular_atr(df):
    high_low = df["High"] - df["Low"]
    high_close_prev = (df["High"] - df["Close"].shift()).abs()
    low_close_prev = (df["Low"] - df["Close"].shift()).abs()
    true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    atr = true_range.rolling(14).mean().iloc[-1]
    if pd.isna(atr) or atr <= 0:
        raise ValueError("ATR inválido")
    return float(atr)

def calcular_rsi(close, window=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    valor = rsi.iloc[-1]
    if pd.isna(valor):
        return 50.0
    return float(valor)

def descargar_mercado(tickers, period="1y"):  # Ampliado a 1 año para colectar suficientes datos para EMA_200
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
        pd.concat([pd.read_csv(ARCHIVO_HISTORIAL), registro], ignore_index=True).to_csv(ARCHIVO_HISTORIAL, index=False)
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

# Carga de base de datos e interfaz de usuario de control
df_portafolio = cargar_portafolio()

st.sidebar.header("📥 Registrar Compra Real en Balanz")
with st.sidebar.form(key="formulario_balanz", clear_on_submit=True):
    ticker_input = st.text_input("Ticker del CEDEAR (Ej: AAPL)")
    cant_real = st.number_input("Cantidad de nominales comprados", min_value=1, value=1, step=1)
    precio_real = st.number_input("Precio de compra por unidad ($)", min_value=0.01, value=1000.0, step=100.0)
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
            st.sidebar.error(f"{ticker_real} ya está en el portafolio.")
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
    st.info("El portafolio de vigilancia permanente está vacío.")

if os.path.exists(ARCHIVO_HISTORIAL):
    df_historial = pd.read_csv(ARCHIVO_HISTORIAL)
    if not df_historial.empty:
        with st.expander("📜 Historial de posiciones cerradas"):
            st.dataframe(df_historial, use_container_width=True)


# Listado de activos para escaneo
tickers_escaner = [
    "AAL.BA", "ABT.BA", "ACWI.BA", "ADBE.BA", "AMD.BA", "AMZN.BA", "AAPL.BA", "ARM.BA", "ARKK.BA", "ASML.BA",
    "AXP.BA", "BAC.BA", "BA.BA", "BABA.BA", "BKNG.BA", "BP.BA", "BRKB.BA", "BX.BA", "C.BA", "CAT.BA",
    "CCL.BA", "COPX.BA", "COIN.BA", "COST.BA", "CRM.BA", "CVS.BA", "CVX.BA", "DAL.BA", "DE.BA", "DISN.BA",
    "DIA.BA", "EFA.BA", "ETHA.BA", "GE.BA", "GOOGL.BA", "GS.BA", "HD.BA", "HON.BA", "IBM.BA", "INTC.BA",
    "JNJ.BA", "JPM.BA", "KO.BA", "LLY.BA", "MA.BA", "MCD.BA", "META.BA", "MELI.BA", "MMM.BA", "MSFT.BA",
    "NFLX.BA", "NKE.BA", "NVDA.BA", "ORCL.BA", "PANW.BA", "PEP.BA", "PFE.BA", "PG.BA", "PYPL.BA", "QCOM.BA",
    "QQQ.BA", "ROKU.BA", "SHOP.BA", "SNOW.BA", "SONY.BA", "SPY.BA", "T.BA", "TEAM.BA", "TGT.BA", "TSLA.BA",
    "TSM.BA", "TXN.BA", "UAL.BA", "UBER.BA", "UNH.BA", "V.BA", "VZ.BA", "WFC.BA", "WMT.BA", "XOM.BA"
]

st.sidebar.header("⚙️ Parámetros del Escáner de Compras")
capital_disponible = st.sidebar.number_input("Tu Capital Total Libre ($ ARS)", min_value=10000, value=158000, step=10000)
riesgo_maximo_ars = capital_disponible * 0.02

if st.button("🚀 Ejecutar Escáner General y Despachar Gestión"):
    df_portafolio_activo = cargar_portafolio()
    portafolio_modificado = False
    
    # PARTE 1: ANALIZADOR DE GESTIÓN ACTIVA (Monitoreo de Salidas)
    if not df_portafolio_activo.empty:
        st.subheader("🕵️ Análisis Cuantitativo de tus Posiciones Abiertas")
        tickers_cartera = df_portafolio_activo["Ticker"].unique().tolist()
        indices_cerrar = []
        try:
            datos_cartera = descargar_mercado(tickers_cartera)
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
                stop_actual = float(row["StopLoss"])
                take_profit = float(row["TakeProfit"])
                
                if low_vivo <= stop_actual:
                    msg_sl = (
                        f"🚨 *¡ALERTA CRÍTICA DE SALIDA!* 🚨\n\n"
                        f"📉 El CEDEAR `{tick.split('.')[0]}` perforó tu *Stop Loss* de ${stop_actual:,.2f}.\n"
                        f"🛒 *Acción:* VENDER de inmediato tus {int(row['Cantidad'])} unidades en Balanz.\n"
                    )
                    enviar_alerta_telegram(msg_sl)
                    registrar_cierre(row, "Stop Loss", stop_actual)
                    indices_cerrar.append(idx)
                    portafolio_modificado = True
                    st.error(f"{tick}: Stop Loss perforado. Posición cerrada.")
                    continue
                
                if high_vivo >= take_profit:
                    msg_tp = (
                        f"🎯 *¡ALERTA DE OBJETIVO CUMPLIDO!* 🎯\n\n"
                        f"📈 El CEDEAR `{tick.split('.')[0]}` tocó tu *Take Profit* de ${take_profit:,.2f}.\n"
                        f"🛒 *Acción:* VENDER tus {int(row['Cantidad'])} unidades en Balanz.\n"
                    )
                    enviar_alerta_telegram(msg_tp)
                    registrar_cierre(row, "Take Profit", take_profit)
                    indices_cerrar.append(idx)
                    portafolio_modificado = True
                    st.success(f"{tick}: Take Profit alcanzado. Posición cerrada.")
                    continue
            
            if indices_cerrar:
                df_portafolio_activo = df_portafolio_activo.drop(indices_cerrar).reset_index(drop=True)
                guardar_portafolio(df_portafolio_activo)
        except Exception as e:
            st.warning(f"No se pudo auditar el portafolio: {e}")


    # PARTE 2: BUSCAR NUEVAS COMPRAS INTELIGENTES (Módulo de Confluencias Estrictas)
    with st.spinner("Buscando oportunidades bajo confluencias estrictas..."):
        try:
            datos_mercado = descargar_mercado(tickers_escaner)
        except Exception as e:
            st.error(f"No se pudieron descargar datos del mercado: {e}")
            datos_mercado = None
            
        if datos_mercado is not None and not datos_mercado.empty:
            candidatos_validos = []
            tickers_en_cartera = set(df_portafolio_activo["Ticker"].tolist()) if not df_portafolio_activo.empty else set()
            
            for ticker in tickers_escaner:
                if ticker in tickers_en_cartera:
                    continue
                try:
                    df_t = extraer_ohlc(datos_mercado, ticker)
                    
                    # 1. Variables de precios, volumen y cálculo de indicadores
                    precio_cierre = float(df_t["Close"].iloc[-1])
                    precio_apertura = float(df_t["Open"].iloc[-1])
                    volumen_actual = float(df_t["Volume"].iloc[-1])
                    
                    if precio_cierre <= 0 or volumen_actual <= 0:
                        continue
                    
                    # Indicadores base
                    ema_9 = float(df_t["Close"].ewm(span=9, adjust=False).mean().iloc[-1])
                    rsi_actual = calcular_rsi(df_t["Close"])
                    atr_actual = calcular_atr(df_t)
                    
                    # EMA_200 con librería 'ta'
                    ema_200_serie = EMAIndicator(close=df_t["Close"], window=200).ema_indicator()
                    ema_200 = float(ema_200_serie.iloc[-1])
                    
                    # MACD Line e Histograma
                    exp1 = df_t["Close"].ewm(span=12, adjust=False).mean()
                    exp2 = df_t["Close"].ewm(span=26, adjust=False).mean()
                    macd_line = exp1 - exp2
                    macd_hist = macd_line - macd_line.ewm(span=9, adjust=False).mean()
                    macd_hist_actual = float(macd_hist.iloc[-1])
                    macd_hist_previo = float(macd_hist.iloc[-2])
                    
                    # Media Móvil Simple de Volumen (SMA_9)
                    volumen_sma_9 = float(df_t["Volume"].rolling(window=9).mean().iloc[-1])
                    
                    if pd.isna(ema_200) or pd.isna(volumen_sma_9):
                        continue
                        
                    # 2. Lógica de Gatillo Algorítmico Estratificado (SEÑAL_FINAL)
                    condicion_tendencia = (precio_cierre > ema_200)
                    condicion_momentum = (precio_cierre > ema_9) and (macd_hist_actual > macd_hist_previo) and (40 < rsi_actual < 65)
                    condicion_gatillo = (precio_cierre > precio_apertura) and (volumen_actual > volumen_sma_9)
                    
                    senal_compra = condicion_tendencia and condicion_momentum and condicion_gatillo
                    
                    if senal_compra:
                        # 3. Modelado Estricto de Salidas y Gestión de Riesgo Dinámico
                        precio_neto_entrada = precio_compra_neto(precio_cierre)
                        stop_loss_sugerido = precio_neto_entrada - (2 * atr_actual)
                        
                        # Evitar stops negativos o ilógicos
                        if stop_loss_sugerido <= 0 or stop_loss_sugerido >= precio_neto_entrada:
                            continue
                            
                        target_salida = precio_neto_entrada + ((precio_neto_entrada - stop_loss_sugerido) * 2)
                        
                        # Cálculo del tamaño de la posición basándonos en el riesgo del 2%
                        riesgo_por_nominal = precio_neto_entrada - stop_loss_sugerido
                        cant_cedears = int(riesgo_maximo_ars // riesgo_por_nominal)
                        
                        if cant_cedears <= 0:
                            continue
                            
                        monto_total_operacion = precio_neto_entrada * cant_cedears
                        
                        # Filtro de restricción de liquidez / capital total
                        if monto_total_operacion > capital_disponible:
                            continue
                            
                        candidatos_validos.append({
                            "Ticker": ticker,
                            "Precio Entrada Neto": round(precio_neto_entrada, 2),
                            "Stop Loss": round(stop_loss_sugerido, 2),
                            "Target (1:2)": round(target_salida, 2),
                            "Cantidad Nominales": cant_cedears,
                            "Costo Total ($ ARS)": round(monto_total_operacion, 2)
                        })
                except Exception:
                    continue
            
            # 4. Formateo y despacho de alertas de confirmación
            if candidatos_validos:
                df_ops = pd.DataFrame(candidatos_validos).sort_values(by="Costo Total ($ ARS)", ascending=False).reset_index(drop=True)
                mejor_opcion = df_ops.iloc[0]
                
                st.success("🤖 ¡Análisis de Confluencias Completado!")
                st.subheader("🎯 Señal de Compra Validada por el Sistema")
                
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("CEDEAR", mejor_opcion["Ticker"])
                col_b.metric("Cantidad a comprar", int(mejor_opcion["Cantidad Nominales"]))
                col_c.metric("Costo Estimado Neto", f"$ {mejor_opcion['Costo Total ($ ARS)']:,.2f}")
                
                msg_tg = (
                    f"🤖 *¡SEÑAL DE COMPRA CONFIRMADA POR CONFLUENCIA!*\n\n"
                    f"🎯 *Ticker:* `{mejor_opcion['Ticker']}`\n"
                    f"📐 *Precio de Entrada Neto:* ${mejor_opcion['Precio Entrada Neto']:,.2f}\n"
                    f"🛡️ *Stop Loss Sugerido:* ${mejor_opcion['Stop Loss']:,.2f}\n"
                    f"🎯 *Target de Salida (Ratio 1:2):* ${mejor_opcion['Target (1:2)']:,.2f}\n\n"
                    f"📊 *Cantidad de Nominales:* {int(mejor_opcion['Cantidad Nominales'])} unidades\n"
                    f"💰 *Capital Asignado (Riesgo 2%):* ${mejor_opcion['Costo Total ($ ARS)']:,.2f}"
                )
                enviar_alerta_telegram(msg_tg)
                st.dataframe(df_ops, use_container_width=True)
            else:
                st.info("Ningún CEDEAR reunió el 100% de las confluencias cuantitativas en la rueda actual.")
