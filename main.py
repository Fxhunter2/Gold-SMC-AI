import yfinance as yf
import requests
import time
import os
import pandas as pd

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MARKETS = {
    "XAUUSD": "GC=F",
    "EURUSD": "EURUSD=X",
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",
    "XRPUSD": "XRP-USD"
}

# Specific Multi-Timeframe Pairs
STRATEGY_LAYERS = [
    {"name": "Swing", "htf": "4h", "ltf": "15m", "period_h": "60d", "period_l": "5d"},
    {"name": "DayTrade", "htf": "1h", "ltf": "5m", "period_h": "20d", "period_l": "2d"},
    {"name": "Scalp", "htf": "15m", "ltf": "1m", "period_h": "5d", "period_l": "1d"}
]

active_trades = {}

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def get_pips(symbol, entry, current):
    diff = abs(current - entry)
    # Forex (EURUSD etc) uses 4th decimal for pips
    if "USD=X" in symbol:
        return diff * 10000
    # Gold and Crypto: $1.00 move = 100 pips
    return diff * 100

def run_smc_engine(name, symbol, layer):
    # Fetch Data
    df_htf = yf.download(symbol, period=layer['period_h'], interval=layer['htf'], progress=False)
    df_ltf = yf.download(symbol, period=layer['period_l'], interval=layer['ltf'], progress=False)
    
    if df_htf.empty or df_ltf.empty: return
    if isinstance(df_htf.columns, pd.MultiIndex): df_htf.columns = df_htf.columns.get_level_values(0)
    if isinstance(df_ltf.columns, pd.MultiIndex): df_ltf.columns = df_ltf.columns.get_level_values(0)

    # HTF Liquidity Pools (Swing Highs/Lows)
    htf_high = df_htf['High'].iloc[-50:].max()
    htf_low = df_htf['Low'].iloc[-50:].min()
    
    curr_p = df_ltf['Close'].iloc[-1]
    trade_key = f"{name}_{layer['name']}"

    # 1. MONITOR ACTIVE TRADES
    if trade_key in active_trades:
        trade = active_trades[trade_key]
        pips = get_pips(symbol, trade['entry'], curr_p)

        # TP HIT
        if (trade['side'] == "BUY" and curr_p >= trade['tp']) or (trade['side'] == "SELL" and curr_p <= trade['tp']):
            send_alert(f"✅ *{pips:.0f} PIP TAKE PROFIT HIT: {name}*\n\n"
                       f"💰 *Exit:* {curr_p:.2f}\n"
                       f"📝 *Note:* Gold SMC AI is designed to make a profit from the Forex and Crypto market.")
            del active_trades[trade_key]
        
        # SL HIT
        elif (trade['side'] == "BUY" and curr_p <= trade['sl']) or (trade['side'] == "SELL" and curr_p >= trade['sl']):
            send_alert(f"❌ *{pips:.0f} PIP STOP LOSS HIT: {name}*\n\n"
                       f"📉 *Exit:* {curr_p:.2f}\n"
                       f"📝 *Note:* Losing is part of the trading process—stay disciplined.")
            del active_trades[trade_key]
        return

    # 2. SMC SIGNAL GENERATION (Both Buy & Sell)
    # --- BUY LIMIT (HTF Low Sweep + LTF CHoCH) ---
    if df_ltf['Low'].iloc[-1] < htf_low:
        if curr_p > df_ltf['High'].iloc[-10:-1].max(): # CHoCH confirmed
            entry, sl = curr_p, df_ltf['Low'].iloc[-1]
            tp = entry + (abs(entry - sl) * 3)
            active_trades[trade_key] = {'side': 'BUY', 'entry': entry, 'tp': tp, 'sl': sl}
            send_alert(f"🚀 *NEW SIGNAL: BUY {name} ({layer['name']})*\n📍 Entry: {entry:.2f}\n🎯 TP: {tp:.2f}\n🛡️ SL: {sl:.2f}")

    # --- SELL LIMIT (HTF High Sweep + LTF CHoCH) ---
    elif df_ltf['High'].iloc[-1] > htf_high:
        if curr_p < df_ltf['Low'].iloc[-10:-1].min(): # CHoCH confirmed
            entry, sl = curr_p, df_ltf['High'].iloc[-1]
            tp = entry - (abs(sl - entry) * 3)
            active_trades[trade_key] = {'side': 'SELL', 'entry': entry, 'tp': tp, 'sl': sl}
            send_alert(f"🚀 *NEW SIGNAL: SELL {name} ({layer['name']})*\n📍 Entry: {entry:.2f}\n🎯 TP: {tp:.2f}\n🛡️ SL: {sl:.2f}")

# --- START BOT ---
send_alert("🌍 *AI SMC Multi-Timeframe Bot Online*\nMonitoring Swing, Day, and Scalp Layers.")

while True:
    for name, symbol in MARKETS.items():
        for layer in STRATEGY_LAYERS:
            try:
                run_smc_engine(name, symbol, layer)
                time.sleep(1)
            except Exception as e:
                print(f"Error on {name}: {e}")
    time.sleep(60)
