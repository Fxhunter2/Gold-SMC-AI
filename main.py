import yfinance as yf
import requests
import time
import os

# CONFIG (Pulling from Railway Variables)
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = "GC=F"

def calculate_lot_size(balance, risk_percent, sl_pips):
    risk_amount = balance * (risk_percent / 100)
    # Gold calculation: $1 move = $100 per lot
    lot_size = risk_amount / (sl_pips * 100)
    return round(max(lot_size, 0.01), 2)

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def run_ai():
    print(f"[{time.strftime('%H:%M:%S')}] 🔍 Scanning Gold...")
    df = yf.download(SYMBOL, period="5d", interval="1h", progress=False)
    
    # 🛑 WEEKEND CHECK
    if df.empty or len(df) < 5:
        print("😴 Market Locked (Weekend). Waiting...")
        return

    htf_low = df['Low'].iloc[-2]
    current_price = df['Close'].iloc[-1]
    
    # SMC SIGNAL LOGIC
    if current_price < htf_low:
        # Calculate Lot for 1% risk on $1000 account
        lots = calculate_lot_size(1000, 1, 3.0) 
        msg = (f"🔔 *GOLD SMC ALERT*\n"
               f"Status: Liquidity Swept!\n"
               f"Price: {current_price:.2f}\n"
               f"Suggested Lot: {lots}")
        send_alert(msg)

while True:
    try:
        run_ai()
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(300) # Scan every 5 minutes
