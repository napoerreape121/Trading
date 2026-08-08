import pandas as pd
import numpy as np
import yfinance as yf
import ta
from datetime import datetime

# --- PARÁMETROS DE SIMULACIÓN ---
CAPITAL_INICIAL = 1_000_000.0  # $1.000.000 ARS
COSTO_OPERATIVO_TOTAL = (0.0050 + 0.0005) * 1.21  # Fricción real (comisiones + IVA)
MIN_VELAS = 200

tickers_prueba = [
    "AAPL.BA", "AMZN.BA", "GOOGL.BA", "MSFT.BA", "NVDA.BA", 
    "TSLA.BA", "MELI.BA", "KO.BA", "JPM.BA", "WMT.BA"
]

def precio_compra_neto(precio_bruto):
    return precio_bruto * (1 + COSTO_OPERATIVO_TOTAL)

def precio_venta_neto(precio_bruto):
    return precio_bruto * (1 - COSTO_OPERATIVO_TOTAL)

print("📥 Descargando datos históricos para Backtesting (2 años)...")
datos = yf.download(tickers_prueba, period="2y", interval="1d", progress=False, group_by="column", auto_adjust=True)

capital_actual = CAPITAL_INICIAL
efectivo = CAPITAL_INICIAL
portafolio_activo = []  # Posiciones abiertas
historial_operaciones = []  # Trades cerrados

fechas = datos.index

print(f"🔄 Iniciando simulación temporal desde {fechas[MIN_VELAS].strftime('%Y-%m-%d')} hasta {fechas[-1].strftime('%Y-%m-%d')}...\n")

# Simulamos día por día (empezando desde MIN_VELAS para tener historia para la EMA200)
for i in range(MIN_VELAS, len(fechas)):
    fecha_actual = fechas[i]
    
    # -------------------------------------------------------------
    # 1. GESTIÓN DE POSICIONES ABIERTAS (Revisar SL, TP y Trailing)
    # -------------------------------------------------------------
    posiciones_a_cerrar = []
    for pos in portafolio_activo:
        tick = pos["Ticker"]
        try:
            sub_df = datos.loc[:fecha_actual, tick].dropna()
            if len(sub_df) < 15:
                continue
            
            high_v = float(sub_df["High"].iloc[-1])
            low_v = float(sub_df["Low"].iloc[-1])
            close_v = float(sub_df["Close"].iloc[-1])
            
            ema9_v = ta.trend.ema_indicator(sub_df["Close"], window=9).iloc[-1]
            atr14_v = ta.volatility.average_true_range(sub_df["High"], sub_df["Low"], sub_df["Close"], window=14).iloc[-1]
            
            # Chequear Stop Loss
            if low_v <= pos["StopLoss"]:
                precio_salida = precio_venta_neto(pos["StopLoss"])
                monto_recuperado = precio_salida * pos["Cantidad"]
                efectivo += monto_recuperado
                historial_operaciones.append({
                    "Ticker": tick, "FechaEntrada": pos["FechaEntrada"], "FechaSalida": fecha_actual.strftime('%Y-%m-%d'),
                    "Motivo": "Stop Loss", "Cantidad": pos["Cantidad"], "PrecioEntrada": pos["PrecioCompraNeto"],
                    "PrecioSalida": precio_salida, "ResultadoARS": (precio_salida - pos["PrecioCompraNeto"]) * pos["Cantidad"]
                })
                posiciones_a_cerrar.append(pos)
                continue
                
            # Chequear Take Profit
            if high_v >= pos["TakeProfit"]:
                precio_salida = precio_venta_neto(pos["TakeProfit"])
                monto_recuperado = precio_salida * pos["Cantidad"]
                efectivo += monto_recuperado
                historial_operaciones.append({
                    "Ticker": tick, "FechaEntrada": pos["FechaEntrada"], "FechaSalida": fecha_actual.strftime('%Y-%m-%d'),
                    "Motivo": "Take Profit", "Cantidad": pos["Cantidad"], "PrecioEntrada": pos["PrecioCompraNeto"],
                    "PrecioSalida": precio_salida, "ResultadoARS": (precio_salida - pos["PrecioCompraNeto"]) * pos["Cantidad"]
                })
                posiciones_a_cerrar.append(pos)
                continue
                
            # Actualizar Trailing Stop dinámico
            nuevo_stop = round(ema9_v - (1.5 * atr14_v), 2)
            if close_v > pos["PrecioCompraNeto"] and nuevo_stop > pos["StopLoss"] and nuevo_stop < close_v:
                pos["StopLoss"] = nuevo_stop
                
        except Exception:
            continue
            
    for p in posiciones_a_cerrar:
        portafolio_activo.remove(p)

    # -------------------------------------------------------------
    # 2. ESCÁNER DE NUEVAS ENTRADAS (Con control de dinero real)
    # -------------------------------------------------------------
    tickers_en_cartera = {p["Ticker"] for p in portafolio_activo}
    
    for ticker in tickers_prueba:
        if ticker in tickers_en_cartera:
            continue
            
        try:
            df_t = datos.loc[:fecha_actual, ticker].dropna()
            if len(df_t) < MIN_VELAS:
                continue
                
            df_t["EMA_9"] = ta.trend.ema_indicator(df_t["Close"], window=9)
            df_t["EMA_200"] = ta.trend.ema_indicator(df_t["Close"], window=200)
            df_t["RSI_14"] = ta.momentum.rsi(df_t["Close"], window=14)
            df_t["MACD_Hist"] = ta.trend.MACD(df_t["Close"]).macd_diff()
            df_t["ATR_14"] = ta.volatility.average_true_range(df_t["High"], df_t["Low"], df_t["Close"], window=14)
            df_t["Volumen_SMA_9"] = df_t["Volume"].rolling(window=9).mean()
            
            last = df_t.iloc[-1]
            prev = df_t.iloc[-2]
            
            cond_tendencia = last["Close"] > last["EMA_200"]
            cond_momentum = (last["Close"] > last["EMA_9"]) and (last["MACD_Hist"] > prev["MACD_Hist"]) and (40 < last["RSI_14"] < 65)
            cond_gatillo = (last["Close"] > last["Open"]) and (last["Volume"] > last["Volumen_SMA_9"])
            
            if not (cond_tendencia and cond_momentum and cond_gatillo):
                continue
                
            capital_total_estimado = efectivo + sum([p["Cantidad"] * last["Close"] for p in portafolio_activo])
            riesgo_maximo_ars = capital_total_estimado * 0.02
            
            p_neto_entrada = precio_compra_neto(last["Close"])
            stop_loss = p_neto_entrada - (2 * last["ATR_14"])
            target = p_neto_entrada + ((p_neto_entrada - stop_loss) * 2)
            
            riesgo_por_accion = p_neto_entrada - stop_loss
            if stop_loss <= 0 or riesgo_por_accion <= 0:
                continue
                
            cantidad = int(riesgo_maximo_ars // riesgo_por_accion)
            if cantidad <= 0:
                continue
                
            costo_total = p_neto_entrada * cantidad
            
            # RESTRICCIÓN: Si no hay efectivo disponible, no compra
            if costo_total > efectivo:
                continue
                
            efectivo -= costo_total
            portafolio_activo.append({
                "Ticker": ticker,
                "Cantidad": cantidad,
                "PrecioCompraNeto": p_neto_entrada,
                "StopLoss": stop_loss,
                "TakeProfit": target,
                "FechaEntrada": fecha_actual.strftime('%Y-%m-%d')
            })
            
        except Exception:
            continue

# -------------------------------------------------------------
# 3. RESULTADOS FINALES DE LA SIMULACIÓN
# -------------------------------------------------------------
print("="*50)
print("📊 RESULTADOS FINALES DEL BACKTESTING ($1M ARS INICIAL)")
print("="*50)

df_historial = pd.DataFrame(historial_operaciones)
if not df_historial.empty:
    total_trades = len(df_historial)
    ganadores = len(df_historial[df_historial["ResultadoARS"] > 0])
    perdedores = len(df_historial[df_historial["ResultadoARS"] <= 0])
    win_rate = (ganadores / total_trades) * 100
    resultado_neto_total = df_historial["ResultadoARS"].sum()
    capital_final = efectivo + sum([p["Cantidad"] * datos.loc[fechas[-1], p["Ticker"]]["Close"] for p in portafolio_activo])
    
    print(f"Total de operaciones ejecutadas: {total_trades}")
    print(f"Operaciones ganadoras (TP): {ganadores}")
    print(f"Operaciones perdedoras (SL): {perdedores}")
    print(f"Win Rate (Efectividad): {win_rate:.2f}%")
    print(f"Resultado Neto Total: $ {resultado_neto_total:,.2f} ARS")
    print(f"Capital Final Estimado: $ {capital_final:,.2f} ARS")
    print("-" * 50)
    print("Desglose de operaciones cerradas:")
    print(df_historial[["Ticker", "FechaEntrada", "FechaSalida", "Motivo", "ResultadoARS"]])
else:
    print("No se registraron operaciones bajo las condiciones estrictas en el período seleccionado.")
