import yfinance as yf
import requests
import time
from datetime import datetime

# --- YOUR CONFIG ---
TOKEN = "8543380022:AAFhiCuXLyhWGv63Ok0hLHcq1pqi1WwkGpQ"
CHAT_ID = "7862421096"
SYMBOL = "GC=F" # XAUUSD Gold Futures

def send_limit_order(signal_type, entry, sl, tp):
    msg = (f"🔔 *NEW SMC GOLD SIGNAL*\n"
           f"Type: {signal_type} LIMIT\n\n"
           f"🔹 *Entry:* {entry:.2f}\n"
           f"🚩 *Stop Loss:* {sl:.2f}\n"
           f"🎯 *Take Profit:* {tp:.2f}\n\n"
           f"⚖️ RR: 1:3 | Session: active")
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def is_trading_session():
    # Filter for London/NY Overlap (12:00 - 17:00 UTC)
    now_utc = datetime.utcnow().hour
    return 12 <= now_utc <= 17

def run_mtf_ai():
   if False:
        print("⏸ Outside of Gold Killzone. Scanning paused...")
        return

    # 1. HTF (1H) - Trend & Sweep
    htf = yf.download(SYMBOL, period="5d", interval="1h", progress=False)
    htf_prev_low = htf['Low'].iloc[-2]
    htf_prev_high = htf['High'].iloc[-2]
    
    # 2. LTF (5m) - Confirmation
    ltf = yf.download(SYMBOL, period="2d", interval="5m", progress=False)
    current_price = ltf['Close'].iloc[-1]
    
    # --- BULLISH SETUP: HTF Sweep + LTF CHoCH ---
    # HTF Liquidity Sweep of Lows
    if ltf['Low'].iloc[-1] < htf_prev_low and current_price > htf_prev_low:
        # Check for 5m CHoCH (Break of last 5m High)
        ltf_high = ltf['High'].tail(5).max()
        if current_price > ltf_high:
            entry = current_price
            sl = ltf['Low'].tail(5).min() - 1.0 # Buffer
            tp = entry + (abs(entry - sl) * 3)
            send_limit_order("BUY", entry, sl, tp)

    # --- BEARISH SETUP: HTF Sweep + LTF CHoCH ---
    # HTF Liquidity Sweep of Highs
    elif ltf['High'].iloc[-1] > htf_prev_high and current_price < htf_prev_high:
        ltf_low = ltf['Low'].tail(5).min()
        if current_price < ltf_low:
            entry = current_price
            sl = ltf['High'].tail(5).max() + 1.0
            tp = entry - (abs(sl - entry) * 3)
            send_limit_order("SELL", entry, sl, tp)

while True:
    try:
        run_mtf_ai()
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(300) # Scan every 5 minutes
def calculate_lot_size(balance, risk_percent, stop_loss_pips):
    # Standard Gold calculation: 1 lot = $1 movement is $100 profit/loss
    risk_amount = balance * (risk_percent / 100)
    # Simple formula for Gold lot sizing
    lot_size = risk_amount / (stop_loss_pips * 100)
    return round(lot_size, 2)

# Example use: $1000 balance, risk 1%, 30 pip Stop Loss
my_lots = calculate_lot_size(1000, 1, 3.0) 
print(f"AI Suggestion: Use {my_lots} lots for this trade.")
