import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import ta

# =====================================================================
# 🛠️ CONFIGURACIÓN DE LA PÁGINA
# =====================================================================
st.set_page_config(
    page_title="Simulador Cuantitativo: Trend Following CEDEARs", 
    page_icon="📈", 
    layout="wide"
)

st.title("📈 Simulador Cuantitativo: Tendencia de Largo Plazo (CEDEARs)")
st.markdown("Estrategia optimizada para operar CEDEARs en pesos con baja rotación, minimizando comisiones y capturando grandes tendencias.")

# =====================================================================
# 📋 UNIVERSO DE ACTIVOS (CEDEARs)
# =====================================================================
tickers = [
    'AAPL.BA','AMZN.BA','GOOGL.BA','META.BA','MSFT.BA',
    'NVDA.BA','TSLA.BA','AMD.BA','MELI.BA','KO.BA',
    'JNJ.BA','WMT.BA','PG.BA','XOM.BA','JPM.BA',
    'V.BA','MA.BA','DISN.BA','NFLX.BA','INTC.BA'
]

# =====================================================================
# 🎛️ PANEL LATERAL (PARÁMETROS)
# =====================================================================
st.sidebar.header("💰 Parámetros Financieros")
capital_inicial = st.sidebar.number_input("Capital Inicial ($ ARS)", min_value=100000, value=1000000, step=50000)

st.sidebar.header("📅 Período de la Simulación")
opcion_tiempo = st.sidebar.radio("Horizonte temporal a testear:", ("1 Año", "2 Años", "3 Años"), index=0)

if opcion_tiempo == "1 Año":
    periodo_download = "18mo"
    ruedas_recorte = 250
elif opcion_tiempo == "2 Años":
    periodo_download = "30mo"
    ruedas_recorte = 500
else:
    periodo_download = "42mo"
    ruedas_recorte = 750

# Costo realista local operador argentino (ALyC + Aranceles + IVA) aprox 1.2% total por vuelta
COSTO_OPERATIVO = 0.012 

if "diccionario_precios_historicos" not in st.session_state:
    st.session_state.diccionario_precios_historicos = {}

# =====================================================================
# 🚀 MOTOR DE BACKTESTING TREND FOLLOWING
# =====================================================================
if st.button(f"🚀 Ejecutar Simulación de Tendencia ({opcion_tiempo})"):
    with st.spinner(f"Descargando datos y procesando tendencias de CEDEARs..."):
        try:
            full_tickers = tickers + ['SPY.BA']
            datos_globales = yf.download(full_tickers, period=periodo_download, interval="1d", progress=False)
        except Exception as e:
            st.error(f"Error al descargar datos: {e}")
            datos_globales = None

    if datos_globales is not None and not datos_globales.empty:
        st.session_state.diccionario_precios_historicos = {}
        
        try:
            spy_df = pd.DataFrame()
            spy_df['Close'] = datos_globales['Close']['SPY.BA'].dropna()
            spy_df['SMA_200'] = spy_df['Close'].rolling(window=200).mean()
            spy_df = spy_df.dropna()
            spy_df.index = pd.to_datetime(spy_df.index).normalize()
        except Exception:
            spy_df = pd.DataFrame()

        lista_fechas_totales = []
        
        for ticker in tickers:
            try:
                df = pd.DataFrame()
                df['Close'] = datos_globales['Close'][ticker].dropna()
                df['Open'] = datos_globales['Open'][ticker].dropna()
                df['Low'] = datos_globales['Low'][ticker].dropna()
                df['High'] = datos_globales['High'][ticker].dropna()
                df['Volume'] = datos_globales['Volume'][ticker].dropna()
                
                if len(df) < 200:
                    continue
                
                df['SMA_200'] = df['Close'].rolling(window=200).mean()
                df['SMA_50'] = df['Close'].rolling(window=50).mean()
                df['ATR_14'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
                
                df = df.dropna()
                df.index = pd.to_datetime(df.index).normalize()
                
                st.session_state.diccionario_precios_historicos[ticker] = df.copy()
                df_recortado = df.tail(ruedas_recorte)
                lista_fechas_totales.extend(df_recortado.index.tolist())
            except Exception:
                continue

        fechas_unicas = sorted(list(set(lista_fechas_totales)))
        
        if fechas_unicas and st.session_state.diccionario_precios_historicos:
            posiciones_activas = {}
            historial_trades = []
            efectivo = capital_inicial
            total_fechas = len(fechas_unicas)
            
            for f in range(total_fechas - 1):
                fecha_hoy = fechas_unicas[f]
                fecha_manana = fechas_unicas[f+1]
                
                # Filtro macro: ¿El mercado general (SPY en pesos) está alcista?
                mercado_alcista = True
                if not spy_df.empty and fecha_hoy in spy_df.index:
                    if spy_df.loc[fecha_hoy, 'Close'] < spy_df.loc[fecha_hoy, 'SMA_200']:
                        mercado_alcista = False
                
                capital_liberado_hoy = 0
                tickers_a_cerrar = []
                
                # ==========================================
                # 1. EVALUAR SALIDAS (Trend Following por pérdida de SMA 50 o Mercado Bajista)
                # ==========================================
                for t_activo, pos in list(posiciones_activas.items()):
                    df_activo = st.session_state.diccionario_precios_historicos[t_activo]
                    
                    if fecha_hoy in df_activo.index:
                        row_h = df_activo.loc[fecha_hoy]
                        p_close = float(row_h["Close"])
                        sma_50 = float(row_h["SMA_50"])
                        
                        # Sale si rompe la media de 50 hacia abajo o el mercado general se pone bajista
                        if (p_close < sma_50) or (not mercado_alcista):
                            if fecha_manana in df_activo.index:
                                p_open_m = float(df_activo.loc[fecha_manana, "Open"])
                                precio_salida_neto = p_open_m * (1 - COSTO_OPERATIVO)
                                
                                monto_recuperado = precio_salida_neto * pos["Cantidad"]
                                monto_invertido = pos["PrecioCompraNeto"] * pos["Cantidad"]
                                ganancia_pesos = monto_recuperado - monto_invertido
                                
                                capital_liberado_hoy += monto_recuperado
                                rend = ((precio_salida_neto - pos["PrecioCompraNeto"]) / pos["PrecioCompraNeto"]) * 100
                                
                                historial_trades.append({
                                    "Fecha Compra": pos["FechaEntrada"],
                                    "Fecha Venta": fecha_manana,
                                    "CEDEAR": t_activo,
                                    "Resultado": "📈 SALIDA TENDENCIA",
                                    "Rendimiento (%)": round(rend, 2),
                                    "Cantidad Nominales": pos["Cantidad"],
                                    "Ganancia Neta Trade ($)": ganancia_pesos,
                                    "Precio Compra ($)": pos["PrecioCompraNeto"],
                                    "Precio Salida ($)": precio_salida_neto,
                                    "SL Inicial": pos["PrecioCompraNeto"] * 0.85, # Stop técnico amplio
                                    "TP Inicial": pos["PrecioCompraNeto"] * 1.50
                                })
                                tickers_a_cerrar.append(t_activo)
                
                for t in tickers_a_cerrar:
                    posiciones_activas.pop(t)
                
                efectivo += capital_liberado_hoy
                tickers_en_cartera = set(posiciones_activas.keys())
                
                # ==========================================
                # 2. EVALUAR ENTRADAS (Solo si el mercado está alcista)
                # ==========================================
                if mercado_alcista:
                    for tick, df_activo in st.session_state.diccionario_precios_historicos.items():
                        if tick in tickers_en_cartera:
                            continue
                        
                        if len(posiciones_activas) >= 4: # Máximo 4 CEDEARs en cartera
                            break
                        
                        if fecha_hoy in df_activo.index:
                            row_hoy = df_activo.loc[fecha_hoy]
                            p_close = float(row_hoy["Close"])
                            sma_200 = float(row_hoy["SMA_200"])
                            sma_50 = float(row_hoy["SMA_50"])
                            
                            # Condición de compra: Precio arriba de SMA 200 y SMA 50 (Fuerza alcista clara)
                            if (p_close > sma_200) and (p_close > sma_50):
                                if fecha_manana in df_activo.index:
                                    p_open_m = float(df_activo.loc[fecha_manana, "Open"])
                                    p_neto_compra = p_open_m * (1 + COSTO_OPERATIVO)
                                    
                                    capital_total_actual = efectivo + sum(p["PrecioCompraNeto"] * p["Cantidad"] for p in posiciones_activas.values())
                                    monto_por_cedear = capital_total_actual / 4 # Dividir en 4 partes iguales
                                    
                                    cantidad = int(monto_por_cedear // p_neto_compra)
                                    if cantidad <= 0 or (p_neto_compra * cantidad) > efectivo:
                                        continue
                                    
                                    costo_total = p_neto_compra * cantidad
                                    efectivo -= costo_total
                                    
                                    posiciones_activas[tick] = {
                                        "PrecioCompraNeto": p_neto_compra,
                                        "Cantidad": cantidad,
                                        "FechaEntrada": fecha_manana
                                    }
            
            capital_final = efectivo + sum(p["PrecioCompraNeto"] * p["Cantidad"] for p in posiciones_activas.values())
            
            if historial_trades:
                st.session_state.df_trades_global = pd.DataFrame(historial_trades).sort_values(by=["Fecha Venta", "CEDEAR"]).reset_index(drop=True)
                st.session_state.capital_final_total_global = capital_final
            else:
                st.session_state.df_trades_global = None

# =====================================================================
# 📊 VISUALIZACIÓN DE RESULTADOS
# =====================================================================
if "df_trades_global" in st.session_state and st.session_state.df_trades_global is not None:
    df_trades = st.session_state.df_trades_global.copy()
    
    balances = [capital_inicial]
    acc = capital_inicial
    for _, row in df_trades.iterrows():
        acc += row["Ganancia Neta Trade ($)"]
        balances.append(acc)
    
    total_t = len(df_trades)
    ganados = len(df_trades[df_trades['Rendimiento (%)'] > 0])
    winrate = (ganados / total_t) * 100 if total_t > 0 else 0
    ganancia_neta_ars = st.session_state.capital_final_total_global - capital_inicial
    rendimiento_pct = (ganancia_neta_ars / capital_inicial) * 100
    
    df_bal = pd.DataFrame({
        "Fecha": [df_trades.iloc[0]["Fecha Compra"]] + list(df_trades["Fecha Venta"]),
        "Balance": balances
    }).drop_duplicates(subset=["Fecha"]).set_index("Fecha")
    
    df_bal['Max_Balance'] = df_bal['Balance'].cummax()
    df_bal['Drawdown'] = (df_bal['Balance'] - df_bal['Max_Balance']) / df_bal['Max_Balance']
    max_dd = df_bal['Drawdown'].min() * 100
    
    st.success("✅ ¡Simulación de Tendencia ejecutada con éxito!")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Operaciones Totales", total_t)
    col2.metric("Efectividad (Win Rate)", f"{winrate:.1f}%")
    col3.metric("Ganancia Neta ($)", f"$ {ganancia_neta_ars:,.2f}")
    col4.metric("Rendimiento Total", f"{rendimiento_pct:+.2f}%")
    col5.metric("Máxima Caída (Max DD)", f"{max_dd:.2f}%", delta_color="inverse")
    
    st.line_chart(df_bal["Balance"], use_container_width=True)
    
    st.subheader("📋 Historial de Operaciones de Tendencia")
    df_view = df_trades.copy()
    df_view["Fecha Compra"] = df_view["Fecha Compra"].dt.strftime('%Y-%m-%d')
    df_view["Fecha Venta"] = df_view["Fecha Venta"].dt.strftime('%Y-%m-%d')
    df_view["Ganancia Neta Trade ($)"] = df_view["Ganancia Neta Trade ($)"].apply(lambda x: f"$ {x:+,.2f}")
    st.dataframe(df_view[["Fecha Compra", "Fecha Venta", "CEDEAR", "Resultado", "Rendimiento (%)", "Ganancia Neta Trade ($)"]], use_container_width=True)
elif "df_trades_global" in st.session_state:
    st.info("No se registraron operaciones bajo las condiciones de tendencia actuales.")
