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

# Timeframe Pairs: HTF (Narrative) + LTF (Execution)
TF_PAIRS = [
    {"name": "Swing", "htf": "4h", "ltf": "15m", "lookback": 50},
    {"name": "DayTrade", "htf": "1h", "ltf": "5m", "lookback": 40},
    {"name": "Scalp", "htf": "15m", "ltf": "1m", "lookback": 30}
]

active_trades = {}

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def get_data(symbol, tf, period="10d"):
    df = yf.download(symbol, period=period, interval=tf, progress=False)
    if not df.empty and isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def run_smc_logic(name, symbol, tf_config):
    # 1. NARRATIVE (HTF Structure & Bias)
    df_htf = get_data(symbol, tf_config['htf'], "30d")
    if df_htf.empty: return
    
    # Identify HTF Liquidity (BSL/SSL)
    htf_high = df_htf['High'].iloc[-tf_config['lookback']:].max()
    htf_low = df_htf['Low'].iloc[-tf_config['lookback']:].min()
    
    # 2. EXECUTION (LTF Sweep + CHoCH)
    df_ltf = get_data(symbol, tf_config['ltf'], "3d")
    if df_ltf.empty: return
    curr_p = df_ltf['Close'].iloc[-1]
    
    trade_id = f"{name}_{tf_config['name']}"

    # --- MONITOR TP/SL ---
    if trade_id in active_trades:
        trade = active_trades[trade_id]
        pips = abs(curr_p - trade['entry']) * (10000 if "USD=X" in symbol else 100)
        
        if (trade['side'] == "BUY" and curr_p >= trade['tp']) or (trade['side'] == "SELL" and curr_p <= trade['tp']):
            send_alert(f"✅ *{pips:.0f} PIP TAKE PROFIT HIT: {name}*\n\nGold SMC AI is designed to make a profit from the Forex and Crypto market.")
            del active_trades[trade_id]
        elif (trade['side'] == "BUY" and curr_p <= trade['sl']) or (trade['side'] == "SELL" and curr_p >= trade['sl']):
            send_alert(f"❌ *STOP LOSS HIT: {name}*\n\nLosing is part of the trading process—stay disciplined.")
            del active_trades[trade_id]
        return

    # --- ENTRY REFINEMENT ---
    # BULLISH: Price sweeps HTF Low (SSL) then breaks internal LTF High (CHoCH)
    if df_ltf['Low'].iloc[-1] < htf_low:
        ltf_internal_high = df_ltf['High'].iloc[-10:-1].max()
        if curr_p > ltf_internal_high:
            sl = df_ltf['Low'].iloc[-1]
            tp = curr_p + (abs(curr_p - sl) * 3)
            active_trades[trade_id] = {'side': 'BUY', 'entry': curr_p, 'tp': tp, 'sl': sl}
            send_alert(f"💎 *BUY LIMIT: {name} ({tf_config['name']})*\n\n"
                       f"📍 Entry: {curr_p:.2f}\n🛡️ SL: {sl:.2f}\n🎯 TP: {tp:.2f}\n\n"
                       f"🔥 *SMC Logic:* SSL Sweep + {tf_config['ltf']} CHoCH")

    # BEARISH: Price sweeps HTF High (BSL) then breaks internal LTF Low (CHoCH)
    elif df_ltf['High'].iloc[-1] > htf_high:
        ltf_internal_low = df_ltf['Low'].iloc[-10:-1].min()
        if curr_p < ltf_internal_low:
            sl = df_ltf['High'].iloc[-1]
            tp = curr_p - (abs(sl - curr_p) * 3)
            active_trades[trade_id] = {'side': 'SELL', 'entry': curr_p, 'tp': tp, 'sl': sl}
            send_alert(f"💎 *SELL LIMIT: {name} ({tf_config['name']})*\n\n"
                       f"📍 Entry: {curr_p:.2f}\n🛡️ SL: {sl:.2f}\n🎯 TP: {tp:.2f}\n\n"
                       f"🔥 *SMC Logic:* BSL Sweep + {tf_config['ltf']} CHoCH")

# --- MAIN ENGINE ---
send_alert("🧠 *SMC Strategy AI Online*\nAnalyzing Market Structure, Liquidity, and CHoCH confirmation.")

while True:
    for name, symbol in MARKETS.items():
        for tf_pair in TF_PAIRS:
            try:
                run_smc_logic(name, symbol, tf_pair)
                time.sleep(1)
            except Exception as e:
                print(f"Error: {e}")
    time.sleep(60)
