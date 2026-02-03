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

active_trades = {}

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def get_pips(symbol, entry, current):
    diff = abs(current - entry)
    return diff * 10000 if "USD=X" in symbol else diff * 100

def run_smc_analysis(name, symbol):
    # 1. HTF (4H) - Liquidity Pools
    df_htf = yf.download(symbol, period="20d", interval="4h", progress=False)
    if df_htf.empty: return
    if isinstance(df_htf.columns, pd.MultiIndex): df_htf.columns = df_htf.columns.get_level_values(0)
    
    htf_high = df_htf['High'].iloc[-30:].max()
    htf_low = df_htf['Low'].iloc[-30:].min()

    # 2. LTF (15m) - Confirmation
    df_ltf = yf.download(symbol, period="5d", interval="15m", progress=False)
    if df_ltf.empty: return
    if isinstance(df_ltf.columns, pd.MultiIndex): df_ltf.columns = df_ltf.columns.get_level_values(0)
    
    curr_p = df_ltf['Close'].iloc[-1]

    # --- MONITOR TRADES ---
    if name in active_trades:
        trade = active_trades[name]
        pips = get_pips(symbol, trade['entry'], curr_p)
        # TP HIT
        if (trade['side'] == "BUY" and curr_p >= trade['tp']) or (trade['side'] == "SELL" and curr_p <= trade['tp']):
            send_alert(f"✅ *{pips:.0f} PIP TAKE PROFIT HIT: {name}*\n\nNote: Gold SMC AI is designed to make a profit from the Forex and Crypto market.")
            del active_trades[name]
        # SL HIT
        elif (trade['side'] == "BUY" and curr_p <= trade['sl']) or (trade['side'] == "SELL" and curr_p >= trade['sl']):
            send_alert(f"❌ *{pips:.0f} PIP STOP LOSS HIT: {name}*\n\nNote: Losing is part of the trading process—stay disciplined.")
            del active_trades[name]
        return

    # --- 3. SIGNAL GENERATION ---
    
    # 🟢 BUY LIMIT LOGIC
    if df_ltf['Low'].iloc[-1] < htf_low: # Sweep HTF Low
        if curr_p > df_ltf['High'].iloc[-5:-1].max(): # CHoCH (Structure Break)
            entry = curr_p
            sl = df_ltf['Low'].iloc[-1]
            tp = entry + (abs(entry - sl) * 3)
            active_trades[name] = {'side': 'BUY', 'entry': entry, 'tp': tp, 'sl': sl}
            send_alert(f"🚀 *NEW SIGNAL: BUY {name} @ {entry:.2f}*\nTP: {tp:.2f}\nSL: {sl:.2f}\nType: BUY LIMIT (SMC)")

    # 🔴 SELL LIMIT LOGIC (Added)
    elif df_ltf['High'].iloc[-1] > htf_high: # Sweep HTF High
        if curr_p < df_ltf['Low'].iloc[-5:-1].min(): # CHoCH (Structure Break)
            entry = curr_p
            sl = df_ltf['High'].iloc[-1]
            tp = entry - (abs(sl - entry) * 3)
            active_trades[name] = {'side': 'SELL', 'entry': entry, 'tp': tp, 'sl': sl}
            send_alert(f"🚀 *NEW SIGNAL: SELL {name} @ {entry:.2f}*\nTP: {tp:.2f}\nSL: {sl:.2f}\nType: SELL LIMIT (SMC)")

# --- LOOP ---
while True:
    for name, symbol in MARKETS.items():
        try: run_smc_analysis(name, symbol)
        except Exception as e: print(f"Error {name}: {e}")
        time.sleep(2)
    time.sleep(300)
