import yfinance as yf
import requests
import time
import os
import pandas as pd
from datetime import datetime, timezone

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWS_KEY = os.getenv("NEWS_API_KEY") 
SYMBOL = "GC=F" # XAUUSD Gold Futures

# --- STEP 1: DEFINE ALL TOOLS (Prevents NameError) ---
def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    try:
        requests.get(url)
    except Exception as e:
        print(f"Telegram Error: {e}")

def check_news():
    """Checks for High Impact USD news in the next 30 mins"""
    if not NEWS_KEY: return False, "No Key"
    try:
        url = f"https://financialmodelingprep.com/api/v3/economic_calendar?apikey={NEWS_KEY}"
        events = requests.get(url).json()
        now = datetime.now(timezone.utc)
        for event in events[:10]:
            # Convert event date to timezone-aware UTC
            event_time = datetime.strptime(event['date'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            if event['currency'] == 'USD' and event['impact'] == 'High':
                diff = (event_time - now).total_seconds() / 60
                if 0 < diff < 30: 
                    return True, event['event']
        return False, None
    except: return False, None

def handle_messages():
    """Responds to 'Hello' or 'Hi' in Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset=-1"
        data = requests.get(url).json()
        if data['result']:
            msg_text = data['result'][0]['message']['text'].lower()
            u_id = data['result'][0]['update_id']
            if any(greet in msg_text for greet in ["hello", "hi", "hey"]):
                send_alert("👋 Hello! I'm scanning XAUUSD. HTF: 4H | LTF: 5m CHoCH + FVG.")
            # Clear message to prevent loop
            requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={u_id + 1}")
    except: pass

# --- STEP 2: SMC LOGIC (HTF/LTF) ---
def run_smc_ai():
    # A. Market Status & News Check
    if datetime.utcnow().weekday() >= 5: return "CLOSED"
    
    is_news, event = check_news()
    if is_news: 
        print(f"⚠️ News Pause: {event}")
        return "NEWS"

    # B. Fetch Data (HTF=1H for 4H levels, LTF=5m)
    df_htf = yf.download(SYMBOL, period="15d", interval="1h", progress=False)
    df_ltf = yf.download(SYMBOL, period="2d", interval="5m", progress=False)
    
    for df in [df_htf, df_ltf]:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

    # C. SMC Levels (48h Lookback)
    htf_high = df_htf['High'].iloc[-48:-1].max() # Buyside Liquidity
    htf_low = df_htf['Low'].iloc[-48:-1].min()   # Sellside Liquidity
    curr_p = df_ltf['Close'].iloc[-1]

    # D. Execution: Sweep + CHoCH
    # BULLISH
    if df_ltf['Low'].min() < htf_low and curr_p > df_ltf['High'].iloc[-12:-1].max():
        sl = df_ltf['Low'].iloc[-1] - 1.5
        tp = curr_p + (abs(curr_p - sl) * 3)
        send_alert(f"🟢 *BUY LIMIT XAUUSD*\nEntry: {curr_p:.2f}\nSL: {sl:.2f}\nTP: {tp:.2f}\nModel: HTF Sweep + 5m CHoCH")
        
    # BEARISH
    elif df_ltf['High'].max() > htf_high and curr_p < df_ltf['Low'].iloc[-12:-1].min():
        sl = df_ltf['High'].iloc[-1] + 1.5
        tp = curr_p - (abs(sl - curr_p) * 3)
        send_alert(f"🔴 *SELL LIMIT XAUUSD*\nEntry: {curr_p:.2f}\nSL: {sl:.2f}\nTP: {tp:.2f}\nModel: HTF Sweep + 5m CHoCH")

    return "ACTIVE"

# --- STEP 3: MAIN EXECUTION ---
send_alert("🤖 *SMC AI Initialized*\nListening for commands and scanning Gold...")

notified_closed = False
while True:
    try:
        handle_messages()
        status = run_smc_ai()
        if status == "CLOSED" and not notified_closed:
            send_alert("😴 *Market is Closed.* Waiting for Monday signals...")
            notified_closed = True
        elif status == "ACTIVE": notified_closed = False
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(30)
