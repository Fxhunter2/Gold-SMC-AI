import yfinance as yf
import requests
import time
import os
import pandas as pd
from datetime import datetime

# CONFIG
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = "GC=F"

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def run_scalper():
    # 1. Fetch fast 1m and 5m data
    print(f"[{time.strftime('%H:%M:%S')}] ⚡ Scalp Scanning...")
    df_5m = yf.download(SYMBOL, period="1d", interval="5m", progress=False)
    df_1m = yf.download(SYMBOL, period="1d", interval="1m", progress=False)

    for df in [df_5m, df_1m]:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

    if df_1m.empty: return

    # 2. SMC Scalp Logic
    # HTF Bias (5m) - Current Trend
    sma_5m = df_5m['Close'].rolling(window=10).mean().iloc[-1]
    curr_p = df_1m['Close'].iloc[-1]
    
    # Identify Liquidity Sweep on 1m
    recent_high = df_1m['High'].iloc[-15:-1].max()
    recent_low = df_1m['Low'].iloc[-15:-1].min()

    # 3. Signals
    # BUY: Price swept 1m low AND is above 5m trend
    if curr_p < recent_low and curr_p > sma_5m:
        sl = curr_p - 1.20 # Tight SL for Scalp
        tp = curr_p + 2.50 # Quick 1:2 RR
        send_alert(f"⚡ *SCALP BUY XAUUSD*\nEntry: {curr_p:.2f}\nSL: {sl:.2f}\nTP: {tp:.2f}")

    # SELL: Price swept 1m high AND is below 5m trend
    elif curr_p > recent_high and curr_p < sma_5m:
        sl = curr_p + 1.20
        tp = curr_p - 2.50
        send_alert(f"⚡ *SCALP SELL XAUUSD*\nEntry: {curr_p:.2f}\nSL: {sl:.2f}\nTP: {tp:.2f}")

# Start Message
send_alert("🏃 Scalper AI is Active. Watching 1m/5m structure for XAUUSD.")

while True:
    try:
        run_scalper()
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(60) # Scan every minute for fast entries
