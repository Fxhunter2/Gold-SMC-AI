import yfinance as yf
import requests
import time
import os
import pandas as pd

# CONFIG
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = "GC=F"

# --- STEP 1: DEFINE THE ALERT TOOL FIRST ---
def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    try:
        requests.get(url)
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- STEP 2: THE TRADING LOGIC ---
def run_ai():
    print(f"[{time.strftime('%H:%M:%S')}] 🔍 Scanning Gold Market...")
    df = yf.download(SYMBOL, period="2d", interval="1h", progress=False)
    
    # Fix for the 'MultiIndex' issue in yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        print("😴 No market data available.")
        return

    # Fix for 'Ambiguous Series' error - we use .iloc[-1] to get ONE value
    current_price = df['Close'].iloc[-1]
    prev_low = df['Low'].iloc[-2]

    # SMC Sweep Detection
    if current_price < prev_low:
        send_alert(f"🚀 *Gold Sweep Alert*\nPrice {current_price:.2f} swept 1H Low!")

# --- STEP 3: START THE BOT ---
# This line proves the connection is working immediately
send_alert("🤖 AI is now LIVE and scanning Gold for the Monday session!")

while True:
    try:
        run_ai()
    except Exception as e:
        print(f"Running Error: {e}")
    time.sleep(300) # Scan every 5 minutes
