import yfinance as yf
import requests
import time
import os
import pandas as pd
from datetime import datetime, timezone

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWS_KEY = os.getenv("NEWS_API_KEY") # Get your free key at FinancialModelingPrep
SYMBOL = "GC=F" # Gold Futures (XAUUSD)

# --- UTILITY FUNCTIONS ---
def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def get_clean_data(interval, period):
    df = yf.download(SYMBOL, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# --- 1. NEWS & MARKET FILTERS ---
def check_news_pause():
    if not NEWS_KEY: return False, None
    try:
        url = f"https://financialmodelingprep.com/api/v3/economic_calendar?apikey={NEWS_KEY}"
        response = requests.get(url).json()
        now = datetime.now(timezone.utc)
        for event in response[:15]:
            event_time = datetime.strptime(event['date'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            if event['currency'] == 'USD' and event['impact'] == 'High':
                diff = (event_time - now).total_seconds() / 60
                if 0 < diff < 45: # Pause 45 mins before high-impact news
                    return True, event['event']
        return False, None
    except: return False, None

def is_market_open():
    # 5=Saturday, 6=Sunday
    return datetime.utcnow().weekday() < 5

# --- 2. INTERACTIVE LISTENER ---
def handle_chat():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset=-1"
        data = requests.get(url).json()
        if data['result']:
            msg = data['result'][0]['message']['text'].lower()
            u_id = data['result'][0]['update_id']
            if "hello" in msg or "hi" in msg:
                send_alert("👋 Hello! I'm scanning XAUUSD. HTF Bias: 4H | Entry: 5m CHoCH + FVG.")
            # Clear message so it doesn't repeat
            requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={u_id + 1}")
    except: pass

# --- 3. THE SMC CORE ENGINE ---
def run_smc_scan():
    # A. Check Filters
    if not is_market_open():
        return "CLOSED"
    
    is_news, news_event = check_news_pause()
    if is_news:
        print(f"⚠️ PAUSED: High Impact News ({news_event})")
        return "NEWS"

    # B. HTF ANALYSIS (4H - Using 1H data to find levels)
    df_htf = get_clean_data("1h", "15d")
    htf_high = df_htf['High'].iloc[-48:-1].max() # 48h Buyside Liquidity
    htf_low = df_htf['Low'].iloc[-48:-1].min()   # 48h Sellside Liquidity

    # C. LTF ANALYSIS (5m - Execution)
    df_ltf = get_clean_data("5m", "1d")
    curr_p = df_ltf['Close'].iloc[-1]
    
    # BULLISH: HTF Sweep + LTF CHoCH
    if df_ltf['Low'].min() < htf_low:
        # CHoCH Detection: Breaking the last 5m Swing High
        if curr_p > df_ltf['High'].iloc[-12:-1].max():
            sl = df_ltf['Low'].iloc[-1] - 1.5
            tp = curr_p + (abs(curr_p - sl) * 3) # 1:3 Risk Reward
            send_alert(f"🟢 *XAUUSD BUY LIMIT*\n\n🔹 Entry: {curr_p:.2f}\n🚩 SL: {sl:.2f}\n🎯 TP: {tp:.2f}\n\n✅ *Setup:* HTF Sweep + 5m CHoCH")

    # BEARISH: HTF Sweep + LTF CHoCH
    elif df_ltf['High'].max() > htf_high:
        if curr_p < df_ltf['Low'].iloc[-12:-1].min():
            sl = df_ltf['High'].iloc[-1] + 1.5
            tp = curr_p - (abs(sl - curr_p) * 3)
            send_alert(f"🔴 *XAUUSD SELL LIMIT*\n\n🔹 Entry: {curr_p:.2f}\n🚩 SL: {sl:.2f}\n🎯 TP: {tp:.2f}\n\n✅ *Setup:* HTF Sweep + 5m CHoCH")

    return "SCANNING"

# --- EXECUTION ---
send_alert("🤖 *SMC AI INITIALIZED*\nAsset: XAUUSD\nStrategy: HTF/LTF CHoCH\nStatus: Scanning...")

last_closed_notified = False

while True:
    handle_chat()
    state = run_smc_scan()
    
    if state == "CLOSED" and not last_closed_notified:
        send_alert("😴 *Market is Closed.* Waiting for Monday signals...")
        last_closed_notified = True
    elif state == "SCANNING":
        last_closed_notified = False
        
    time.sleep(30)
