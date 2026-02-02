import yfinance as yf
import requests
import time
import os
import pandas as pd
from datetime import datetime, timezone

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = "GC=F"

# Memory to track the trade
active_position = None 

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def check_trade_status(current_price):
    global active_position
    if not active_position:
        return

    entry = active_position['entry']
    tp = active_position['tp']
    sl = active_position['sl']
    side = active_position['side']

    # Calculate Pips (1.00 USD = 100 Pips)
    pip_diff = abs(current_price - entry) * 100

    # 1. CHECK TAKE PROFIT
    if (side == "BUY" and current_price >= tp) or (side == "SELL" and current_price <= tp):
        send_alert(f"✅ *TAKE PROFIT HIT!*\n💰 Result: +{pip_diff:.0f} Pips\nTarget of {tp:.2f} reached. Great job stay disciplined!")
        active_position = None # Reset for next trade

    # 2. CHECK STOP LOSS
    elif (side == "BUY" and current_price <= sl) or (side == "SELL" and current_price >= sl):
        send_alert(f"❌ *STOP LOSS HIT*\n📉 Result: -{pip_diff:.0f} Pips\nPrice hit {sl:.2f}. This is just a part of trading—stay focused for the next setup.")
        active_position = None # Reset for next trade

def run_day_trader():
    global active_position
    print(f"[{time.strftime('%H:%M:%S')}] 📅 Day Trade Scanning...")
    
    # Fetch Data
    df_1h = yf.download(SYMBOL, period="20d", interval="1h", progress=False)
    df_15m = yf.download(SYMBOL, period="5d", interval="15m", progress=False)

    for df in [df_1h, df_15m]:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

    if df_1h.empty or df_15m.empty: return

    curr_p = df_15m['Close'].iloc[-1]

    # --- MONITOR ACTIVE TRADE ---
    if active_position:
        check_trade_status(curr_p)
        return # Don't look for new trades if one is already open

    # --- LOOK FOR NEW SIGNALS ---
    htf_high = df_1h['High'].iloc[-24:-1].max() 
    htf_low = df_1h['Low'].iloc[-24:-1].min()

    # BULLISH: Sweep PDL then 15m CHoCH
    if df_15m['Low'].iloc[-1] < htf_low:
        if curr_p > df_15m['High'].iloc[-5:-1].max():
            sl_val = curr_p - 2.5
            tp_val = curr_p + 7.5 # Target 750 pips (1:3 RR)
            active_position = {'side': 'BUY', 'entry': curr_p, 'tp': tp_val, 'sl': sl_val}
            send_alert(f"💎 *XAUUSD BUY SIGNAL*\n\nEntry: {curr_p:.2f}\nSL: {sl_val:.2f}\nTP: {tp_val:.2f}\n\n*Status:* Trade is now being tracked...")

    # BEARISH: Sweep PDH then 15m CHoCH
    elif df_15m['High'].iloc[-1] > htf_high:
        if curr_p < df_15m['Low'].iloc[-5:-1].min():
            sl_val = curr_p + 2.5
            tp_val = curr_p - 7.5
            active_position = {'side': 'SELL', 'entry': curr_p, 'tp': tp_val, 'sl': sl_val}
            send_alert(f"💎 *XAUUSD SELL SIGNAL*\n\nEntry: {curr_p:.2f}\nSL: {sl_val:.2f}\nTP: {tp_val:.2f}\n\n*Status:* Trade is now being tracked...")

# Startup Notification
send_alert("📅 *Gold Day Trader + Tracker Active*\nTracking Pips, TP, and SL hits in real-time.")

while True:
    try:
        run_day_trader()
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(60) # Scan every 1 minute for better TP/SL tracking
