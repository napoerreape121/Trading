import yfinance as yf
import pandas as pd
import ta
import streamlit as st

# Lista completa de CEDEARs (extraída del PDF)
tickers = [
    "AAL","AALC","AALD","AAP","AAPC","AAPD","AAPL","AAPLC","AAPLD","ABBV","ABBVC","ABBVD",
    "ABEV","ABEV3","ABEVC","ABEVD","ABNB","ABNBC","ABNBD","ABT","ABTC","ABTD","ACN","ACNC","ACND",
    "ACWI","ACWIC","ACWID","ADBE","ADBEC","ADBED","ADGO","ADGOC","ADGOD","ADI","ADID","ADP","ADS",
    "ADSC","ADSD","AEG","AEM","AEMC","AEMD","AI","AIC","AID","AIG","AIGC","AIGD","AKO.B","ALAB",
    "ALAC","ALAD","AMAT","AMATC","AMATD","AMD","AMDC","AMDD","AMGN","AMGNC","AMGND","AMX","AMXC",
    "AMXD","AMZN","AMZNC","AMZND","ANF","ANFC","ANFD","ARCO","ARCOC","ARCOD","ARKK","ARKKC","ARKKD",
    "ARM","ARMD","ASML","ASMLC","ASMLD","ASR","ASTS","ASTSC","ASTSD","AVGO","AVGOC","AVGOD","AVY",
    "AVYC","AVYD","AXIA","AXIAC","AXIAD","AXP","AXPC","AXPD","AZN","AZNC","AZND","B","B.C","B.D",
    "BA","BA.C","BA.CC","BA.CD","BABA","BABAC","BABAD","BAC","BAD","BAK","BAKC","BAKD","BAS","BAYN",
    "BB","BBA3C","BBA3D","BBAS3","BBD","BBDC3","BBDCC","BBDCD","BBDD","BBV","BBVD","BCS","BHP","BHPD",
    "BIDU","BIDUC","BIDUD","BIIB","BIIBC","BIIBD","BIOX","BIOXC","BIOXD","BITF","BITFC","BITFD","BK",
    "BKC","BKD","BKNG","BKNGC","BKNGD","BKR","BKRC","BKRD","BMNR","BMNRC","BMNRD","BMY","BNG","BNGC",
    "BNGD","BP","BPA11","BPA1C","BPA1D","BPC","BPD","BRKB","BRKBC","BRKBD","BSBR","BX","BXC","BXD",
    "C","C.D","CAAP","CAAPC","CAAPD","CAH","CAHC","CAHD","CAR","CAR.C","CAR.D","CAT","CATC","CATD",
    "CC","CCL","CCLC","CCLD","CDE","CEG","CEGC","CEGD","CIBR","CIBRC","CIBRD","CL","CLC","CLD","CLS",
    "CLSC","CLSD","COIN","COINC","COIND","COPX","COPXC","COPXD","COST","COSTC","COSTD","CRM","CRMC",
    "CRMD","CRWV","CRWVC","CRWVD","CSCO","CSCOC","CSCOD","CSNA3","CSNAC","CSNAD","CVS","CVSC","CVSD",
    "CVX","CVXC","CVXD","CX","DAL","DALC","DALD","DD","DE","DEC","DECK","DECKC","DECKD","DED","DEO",
    "DEOC","DEOD","DHR","DHRC","DHRD","DIA","DIAC","DIAD","DISN","DISNC","DISND","DJN3C","DJN3D",
    "DJNJ3","DOCU","DOCUC","DOCUD","DOW","DOWC","DOWD","E","EA","EAC","EAD","EBAY","EBAYC","EBAYD",
    "EC","ECL","ECLC","ECLD","EEM","EEMC","EEMD","EFA","EFAC","EFAD","EFX","EFXC","EFXD","ELP","ELPC",
    "ELPCC","ELPCD","ELPD","EMBJ","EMBJC","EMBJD","EOAN","EOANC","EQNR","EQNRC","EQNRD","ERIC","ESGU",
    "ESGUC","ESGUD","ETHA","ETHAC","ETHAD","ETSY","ETSYC","ETSYD","EWJ","EWJC","EWJD","EWY"
]

def scanner(ticker):
    data = yf.download(ticker, period="6mo", interval="1d").dropna()
    if data.empty or "Close" not in data.columns or len(data) < 2:
        return None
    
    try:
        data["EMA9"] = ta.trend.EMAIndicator(data["Close"], window=9).ema_indicator()
        data["EMA50"] = ta.trend.EMAIndicator(data["Close"], window=50).ema_indicator()
    except Exception:
        return None
    
    last, prev = data.iloc[-1], data.iloc[-2]
    tendencia_bajista = last["EMA9"] < last["EMA50"]
    tendencia_alcista = last["EMA9"] > last["EMA50"]
    vela_verde = last["Close"] > last["Open"]
    toca_ema9 = abs(last["Close"] - last["EMA9"]) / last["EMA9"] < 0.005
    toca_ema50 = abs(last["Close"] - last["EMA50"]) / last["EMA50"] < 0.005

    if tendencia_bajista and vela_verde and toca_ema9:
        return f"{ticker}: Señal en tendencia bajista tocando EMA9"
    elif tendencia_alcista and vela_verde and (toca_ema9 or toca_ema50):
        return f"{ticker}: Señal en tendencia alcista tocando EMA9/EMA50"
    return None

# Interfaz Streamlit
st.title("Scanner de CEDEARs con EMA")

resultados = []
for t in tickers:
    señal = scanner(t)
    if señal:
        resultados.append(señal)

if resultados:
    st.subheader("Señales detectadas:")
    for r in resultados:
        st.write(r)
else:
    st.write("No se detectaron señales en este momento.")

