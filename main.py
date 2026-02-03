import yfinance as yf
import requests
import time
import os
import pandas as pd

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MARKETS = {
    "XAUUSD": "GC=F", "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
    "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD", "XRPUSD": "XRP-USD"
}

# Your Specific Timeframe Pairs
TF_LAYERS = [
    {"name": "Swing", "htf": "4h", "ltf": "15m", "period_h": "60d", "period_l": "5d"},
    {"name": "DayTrade", "htf": "1h", "ltf": "5m", "period_h": "20d", "period_l": "2d"},
    {"name": "Scalp", "htf": "15m", "ltf": "1m", "period_h": "5d", "period_l": "1d"}
]

active_trades = {}

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def get_data(symbol, tf, period):
    df = yf.download(symbol, period=period, interval=tf, progress=False)
    if not df.empty and isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def run_multi_layer_smc(name, symbol, layer):
    # 1. HTF Analysis: Identify Liquidity Pools (Swing Highs/Lows)
    df_htf = get_data(symbol, layer['htf'], layer['period_h'])
    if df_htf.empty: return
    htf_high = df_htf['High'].iloc[-50:].max()
    htf_low = df_htf['Low'].iloc[-50:].min()

    # 2. LTF Analysis: Confirmation & Entry
    df_ltf = get_data(symbol, layer['ltf'], layer['period_l'])
    if df_ltf.empty: return
    curr_p = df_ltf['Close'].iloc[-1]

    # Trade ID includes the layer name to track multiple styles per asset
    trade_id = f"{name}_{layer['name']}"

    # MONITOR ACTIVE TRADES
    if trade_id in active_trades:
        trade = active_trades[trade_id]
        diff = abs(curr_p - trade['entry'])
        pips = diff * 10000 if "USD=X" in symbol else diff * 100
        
        if (trade['side'] == "BUY" and curr_p >= trade['tp']) or (trade['side'] == "SELL" and curr_p <= trade['tp']):
            send_alert(f"✅ *TP HIT ({layer['name']}): {name}*\n💰 Result: +{pips:.0f} Pips\nTarget reached!")
            del active_trades[trade_id]
        elif (trade['side'] == "BUY" and curr_p <= trade['sl']) or (trade['side'] == "SELL" and curr_p >= trade['sl']):
            send_alert(f"❌ *SL HIT ({layer['name']}): {name}*\n📉 Result: -{pips:.0f} Pips\nPart of the process—stay disciplined.")
            del active_trades[trade_id]
        return

    # 3. SMC ENTRY LOGIC
    # BULLISH: HTF Sweep + LTF CHoCH
    if df_ltf['Low'].iloc[-1] < htf_low:
        if curr_p > df_ltf['High'].iloc[-10:-1].max(): # CHoCH confirmed
            entry, sl = curr_p, df_ltf['Low'].iloc[-1]
            tp = entry + (abs(entry - sl) * 3)
            active_trades[trade_id] = {'side': 'BUY', 'entry': entry, 'tp': tp, 'sl': sl}
            send_alert(f"🚀 *SMC BUY ({layer['name']}): {name}*\nStack: {layer['htf']}+{layer['ltf']}\nEntry: {entry:.2f}\nSL: {sl:.2f}\nTP: {tp:.2f}")

    # BEARISH: HTF Sweep + LTF CHoCH
    elif df_ltf['High'].iloc[-1] > htf_high:
        if curr_p < df_ltf['Low'].iloc[-10:-1].min(): # CHoCH confirmed
            entry, sl = curr_p, df_ltf['High'].iloc[-1]
            tp = entry - (abs(sl - entry) * 3)
            active_trades[trade_id] = {'side': 'SELL', 'entry': entry, 'tp': tp, 'sl': sl}
            send_alert(f"🚀 *SMC SELL ({layer['name']}): {name}*\nStack: {layer['htf']}+{layer['ltf']}\nEntry: {entry:.2f}\nSL: {sl:.2f}\nTP: {tp:.2f}")

# --- EXECUTION LOOP ---
send_alert("🌍 *AI SMC Multi-Timeframe Bot Online*\nMonitoring Swing, Day, and Scalp Layers.")

while True:
    for name, symbol in MARKETS.items():
        for layer in TF_LAYERS:
            try:
                run_multi_layer_smc(name, symbol, layer)
                time.sleep(1) # Prevent rate limiting
            except Exception as e:
                print(f"Error on {name} {layer['name']}: {e}")
    time.sleep(60) # Scan every minute
