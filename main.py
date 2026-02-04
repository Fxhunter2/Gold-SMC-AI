import yfinance as yf
import requests
import time
import os
import pandas as pd

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Ticker mapping (Forex, Gold, Crypto)
MARKETS = {
    "XAUUSD": "GC=F", "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
    "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD"
}

# Long Scalp: 1H Narrative for Trend + 5m/1m for Sniper Entry
STRATEGY_CONFIG = {
    "htf": "1h",      # Trend Narrative
    "ltf": "5m",      # Execution Zone
    "point_target": 1200, # Your specific 1200 point goal
}

active_trades = {}

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def get_market_data(symbol, tf, period="10d"):
    df = yf.download(symbol, period=period, interval=tf, progress=False)
    if not df.empty and isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def run_long_scalp_analysis(name, symbol):
    # 1. NARRATIVE: Check 1H Trend
    df_htf = get_market_data(symbol, STRATEGY_CONFIG['htf'], "20d")
    if df_htf.empty: return
    
    # 2. LIQUIDITY: Identify "The Trap" (HTF Highs/Lows)
    bsl = df_htf['High'].iloc[-40:].max() # Buy-Side Liquidity
    ssl = df_htf['Low'].iloc[-40:].min()  # Sell-Side Liquidity
    
    # 3. EXECUTION: 5m Confirmation
    df_ltf = get_market_data(symbol, STRATEGY_CONFIG['ltf'], "3d")
    if df_ltf.empty: return
    curr_p = df_ltf['Close'].iloc[-1]

    # --- MONITOR TRADES ---
    if name in active_trades:
        trade = active_trades[name]
        # Point Calculation: Gold ($1 = 100 points), Forex (0.0001 = 1 point)
        point_diff = abs(curr_p - trade['entry']) * (10000 if "USD=X" in symbol else 100)
        
        if (trade['side'] == "BUY" and curr_p >= trade['tp']) or (trade['side'] == "SELL" and curr_p <= trade['tp']):
            send_alert(f"✅ *{point_diff:.0f} POINT TAKE PROFIT HIT: {name}*\n\nGold SMC AI is designed to make a profit from the Forex and Crypto market.")
            del active_trades[name]
        elif (trade['side'] == "BUY" and curr_p <= trade['sl']) or (trade['side'] == "SELL" and curr_p >= trade['sl']):
            send_alert(f"❌ *STOP LOSS HIT: {name}*\n\nLosing is part of the trading process—stay disciplined.")
            del active_trades[name]
        return

    # --- SMC ENTRY LOGIC (1200 POINT SETUP) ---
    # Long Scalp Buy: Sweep HTF Low + 5m CHoCH
    if df_ltf['Low'].iloc[-1] < ssl:
        ltf_high = df_ltf['High'].iloc[-15:-1].max()
        if curr_p > ltf_high:
            entry = curr_p
            # 1200 point target calculation
            tp = entry + (12.00 if name == "XAUUSD" else 0.1200 if "USD" in name else entry * 0.05)
            sl = df_ltf['Low'].iloc[-1]
            
            active_trades[name] = {'side': 'BUY', 'entry': entry, 'tp': tp, 'sl': sl}
            send_alert(f"💎 *LONG SCALP BUY: {name}*\n📍 Entry: {entry:.2f}\n🎯 TP (1200 pts): {tp:.2f}\n🛡️ SL: {sl:.2f}\n\n🔥 *Logic:* SSL Sweep + 5m CHoCH. Target set for trend expansion.")

    # Long Scalp Sell: Sweep HTF High + 5m CHoCH
    elif df_ltf['High'].iloc[-1] > bsl:
        ltf_low = df_ltf['Low'].iloc[-15:-1].min()
        if curr_p < ltf_low:
            entry = curr_p
            tp = entry - (12.00 if name == "XAUUSD" else 0.1200 if "USD" in name else entry * 0.05)
            sl = df_ltf['High'].iloc[-1]
            
            active_trades[name] = {'side': 'SELL', 'entry': entry, 'tp': tp, 'sl': sl}
            send_alert(f"💎 *LONG SCALP SELL: {name}*\n📍 Entry: {entry:.2f}\n🎯 TP (1200 pts): {tp:.2f}\n🛡️ SL: {sl:.2f}\n\n🔥 *Logic:* BSL Sweep + 5m CHoCH. Target set for trend expansion.")

# --- ENGINE LOOP ---
while True:
    for name, symbol in MARKETS.items():
        try:
            run_long_scalp_analysis(name, symbol)
            time.sleep(2)
        except Exception as e:
            print(f"Error: {e}")
    time.sleep(300) # Re-scan every 5 mins
