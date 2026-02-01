import yfinance as yf
import requests
import time
import os
import pandas as pd

# CONFIG
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = "GC=F"

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def run_ai():
    print(f"[{time.strftime('%H:%M:%S')}] 🔍 Scanning Gold Market...")
    # Fetch 5 days of 1-hour data
    df = yf.download(SYMBOL, period="5d", interval="1h", progress=False)
    
    # 1. FIX: Flatten MultiIndex columns (Common yfinance crash cause)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0) #

    # 2. FIX: Check if empty to avoid truth value errors
    if df.empty: #
        print("😴 Market Locked (Weekend).")
        return

    # 3. SMC LOGIC: Use .iloc[-1] to get the SINGLE latest value
    # This prevents the "Truth value of a Series is ambiguous" crash
    current_price = df['Close'].iloc[-1]
    prev_low = df['Low'].iloc[-2]

    if current_price < prev_low:
        msg = f"🚀 *Gold Liquidity Sweep*\nPrice {current_price:.2f} swept 1H Low!"
        send_alert(msg)

# Force a connection test on startup
send_alert("🤖 AI Initialized. Watching Gold for the market open.")

while True:
    try:
        run_ai()
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(300) # Scan every 5 mins
