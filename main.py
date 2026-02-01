import yfinance as yf
import requests
import time
import os
import pandas as pd

# CONFIG
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = "GC=F" # Gold Futures

def send_signal(side, entry, sl, tp, rr="1:3"):
    msg = (f"🔔 *NEW SMC GOLD SIGNAL*\n"
           f"Type: {side} LIMIT\n\n"
           f"🔹 *Entry:* {entry:.2f}\n"
           f"🚩 *Stop Loss:* {sl:.2f}\n"
           f"🎯 *Take Profit:* {tp:.2f}\n\n"
           f"⚖️ RR: {rr} | Session: Active")
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def get_data(interval, period="5d"):
    df = yf.download(SYMBOL, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def detect_fvg(df):
    """Detects the most recent unmitigated Fair Value Gap"""
    if len(df) < 3: return None
    # Bullish FVG: Gap between Candle 1 High and Candle 3 Low
    if df['Low'].iloc[-1] > df['High'].iloc[-3]:
        return {"type": "BULL", "top": df['Low'].iloc[-1], "bottom": df['High'].iloc[-3]}
    # Bearish FVG: Gap between Candle 1 Low and Candle 3 High
    if df['High'].iloc[-1] < df['Low'].iloc[-3]:
        return {"type": "BEAR", "top": df['Low'].iloc[-3], "bottom": df['High'].iloc[-1]}
    return None

def run_smc_ai():
    print(f"[{time.strftime('%H:%M:%S')}] 🔍 Analyzing Market Structure...")
    
    # 1. HTF Analysis (1H) - Trend & Liquidity
    df_htf = get_data("1h", "10d")
    if df_htf.empty: return
    
    htf_low = df_htf['Low'].iloc[-10:-1].min() # Sellside Liquidity
    htf_high = df_htf['High'].iloc[-10:-1].max() # Buyside Liquidity
    
    # 2. LTF Analysis (5m) - Confirmation (CHoCH & FVG)
    df_ltf = get_data("5m", "2d")
    if df_ltf.empty: return
    
    curr_price = df_ltf['Close'].iloc[-1]
    ltf_prev_high = df_ltf['High'].iloc[-2]
    ltf_prev_low = df_ltf['Low'].iloc[-2]
    fvg = detect_fvg(df_ltf)

    # --- BULLISH SETUP (HTF Sweep + LTF CHoCH + FVG) ---
    # Price swept HTF Low, now price breaks 5m High (CHoCH)
    if df_ltf['Low'].min() < htf_low and curr_price > ltf_prev_high:
        if fvg and fvg['type'] == "BULL":
            entry = fvg['top']
            sl = df_ltf['Low'].tail(5).min() - 0.5
            tp = entry + (abs(entry - sl) * 3)
            send_signal("BUY", entry, sl, tp)

    # --- BEARISH SETUP (HTF Sweep + LTF CHoCH + FVG) ---
    elif df_ltf['High'].max() > htf_high and curr_price < ltf_prev_low:
        if fvg and fvg['type'] == "BEAR":
            entry = fvg['bottom']
            sl = df_ltf['High'].tail(5).max() + 0.5
            tp = entry - (abs(sl - entry) * 3)
            send_signal("SELL", entry, sl, tp)
while True:
    try:
        send_alert("🚀 System Check: AI is online and connected to Telegram!")
        run_smc_ai()
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(300)
