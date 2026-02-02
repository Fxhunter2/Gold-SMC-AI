import yfinance as yf
import requests
import time
import os
import pandas as pd
from datetime import datetime, timezone

# CONFIG
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = "GC=F" # Gold

# --- UTILS ---
def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def get_data(interval, period):
    df = yf.download(SYMBOL, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


# --- 1. INTERACTIVE CHAT ---
def handle_messages():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset=-1"
        data = requests.get(url).json()
        if data['result']:
            msg = data['result'][0]['message']['text'].lower()
            u_id = data['result'][0]['update_id']
            if "hello" in msg or "hi" in msg:
                send_alert("👋 Hello! I am scanning XAUUSD using HTF (4H) and LTF (5m) SMC logic.")
            requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={u_id + 1}")
    except: pass

# --- 2. SMC LOGIC (HTF/LTF) ---
def run_smc_scan():
    # A. Check Market Status
    day = datetime.utcnow().weekday()
    if day >= 5: # Saturday/Sunday
        print("Market Closed.")
        return "CLOSED"

    # B. Check News
    is_news, event_name = check_news()
    if is_news:
        print(f"Skipping due to News: {event_name}")
        return "NEWS"

    # C. HTF (4H) TREND & LIQUIDITY
    df_4h = get_data("1h", "10d") # yfinance 4h is buggy, we use 1h to build 4h
    htf_high = df_4h['High'].iloc[-48:-1].max() 
    htf_low = df_4h['Low'].iloc[-48:-1].min()
    
    # D. LTF (5m) CHoCH & ENTRY
    df_5m = get_data("5m", "1d")
    curr_price = df_5m['Close'].iloc[-1]
    
    # BULLISH SETUP: HTF Sweep + LTF CHoCH
    if df_5m['Low'].min() < htf_low:
        # CHoCH: Price breaks above last 5m Swing High
        if curr_price > df_5m['High'].iloc[-10:-1].max():
            sl = df_5m['Low'].iloc[-5:].min() - 1.0
            tp = curr_price + (abs(curr_price - sl) * 3) # 1:3 RR
            send_alert(f"🟢 *XAUUSD BUY LIMIT*\nEntry: {curr_price:.2f}\nSL: {sl:.2f}\nTP: {tp:.2f}\nType: HTF Sweep + LTF CHoCH")

    # BEARISH SETUP: HTF Sweep + LTF CHoCH
    elif df_5m['High'].max() > htf_high:
        if curr_price < df_5m['Low'].iloc[-10:-1].min():
            sl = df_5m['High'].iloc[-5:].max() + 1.0
            tp = curr_price - (abs(sl - curr_price) * 3)
            send_alert(f"🔴 *XAUUSD SELL LIMIT*\nEntry: {curr_price:.2f}\nSL: {sl:.2f}\nTP: {tp:.2f}\nType: HTF Sweep + LTF CHoCH")
            
    return "ACTIVE"

# --- MAIN LOOP ---
send_alert("🤖 *SMC AI Initialized*\nHTF: 4H/1H | LTF: 5m\nStatus: Scanning Gold...")

last_market_msg = False
while True:
    handle_messages()
    status = run_smc_scan()
    
    if status == "CLOSED" and not last_market_msg:
        send_alert("😴 *Market is Closed.* Waiting for Monday signals...")
        last_market_msg = True
    elif status == "ACTIVE":
        last_market_msg = False
        
    time.sleep(30)
