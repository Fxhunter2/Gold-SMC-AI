import yfinance as yf
import requests
import time
import os
import pandas as pd

# 1. SETUP (The Identity)
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = "GC=F"

# 2. DEFINITION (The Sauce Recipe)
def send_alert(msg):
    # This must be defined BEFORE the bot tries to use it
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

# 3. THE AI BRAIN
def run_ai():
    print(f"[{time.strftime('%H:%M:%S')}] 🔍 Scanning Gold...")
    df = yf.download(SYMBOL, period="5d", interval="1h", progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        return

    current_price = df['Close'].iloc[-1]
    prev_low = df['Low'].iloc[-2]

    if current_price < prev_low:
        send_alert(f"🚀 *Gold Sweep:* Price {current_price:.2f} is below 1H Low!")

# 4. START THE BOT
# We call send_alert here to test if it works immediately
send_alert("🤖 AI Initialized. Market scanning is active!")

while True:
    try:
        run_ai()
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(300)
