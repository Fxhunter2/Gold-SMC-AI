import yfinance as yf
import requests
import time
import os
import pandas as pd

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MARKETS = {
    "XAUUSD": "GC=F", "EURUSD": "EURUSD=X", 
    "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD", "XRPUSD": "XRP-USD"
}

active_trades = {}

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def get_data(symbol, tf, period):
    df = yf.download(symbol, period=period, interval=tf, progress=False)
    if not df.empty and isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def run_advanced_smc(name, symbol):
    # 1. HTF BIAS (Daily) - Trend & Structure
    df_daily = get_data(symbol, "1d", "60d")
    if df_daily.empty: return
    daily_trend = "BULLISH" if df_daily['Close'].iloc[-1] > df_daily['Close'].iloc[-20] else "BEARISH"

    # 2. ANALYSIS TF (4H & 1H) - Liquidity & Order Blocks
    df_htf = get_data(symbol, "1h", "15d")
    if df_htf.empty: return
    bsl = df_htf['High'].iloc[-50:].max()  # Buy-side Liquidity
    ssl = df_htf['Low'].iloc[-50:].min()   # Sell-side Liquidity

    # 3. ENTRY TF (15m & 5m) - Confirmation
    df_ltf = get_data(symbol, "5m", "3d")
    if df_ltf.empty: return
    curr_p = df_ltf['Close'].iloc[-1]

    # --- MONITOR TRADES ---
    if name in active_trades:
        trade = active_trades[name]
        point_diff = abs(curr_p - trade['entry']) * (10000 if "USD=X" in symbol else 100)
        
        if (trade['side'] == "BUY" and curr_p >= trade['tp']) or (trade['side'] == "SELL" and curr_p <= trade['tp']):
            send_alert(f"✅ *TAKE PROFIT HIT: {name}*\n💰 Result: +{point_diff:.0f} Points\nNote: Gold SMC AI is designed to make a profit from the Forex and Crypto market.")
            del active_trades[name]
        elif (trade['side'] == "BUY" and curr_p <= trade['sl']) or (trade['side'] == "SELL" and curr_p >= trade['sl']):
            send_alert(f"❌ *STOP LOSS HIT: {name}*\nNote: Losing is part of the trading process—stay disciplined.")
            del active_trades[name]
        return

    # --- EXECUTION LOGIC ---
    # LONG SCALP: Bias Bullish + SSL Sweep + LTF CHoCH
    if daily_trend == "BULLISH" and df_ltf['Low'].iloc[-1] < ssl:
        if curr_p > df_ltf['High'].iloc[-10:-1].max(): # CHoCH
            entry = curr_p
            tp = entry + (12.00 if name == "XAUUSD" else 0.1200 if "USD" in name else entry * 0.05)
            sl = df_ltf['Low'].iloc[-1]
            active_trades[name] = {'side': 'BUY', 'entry': entry, 'tp': tp, 'sl': sl}
            send_alert(f"🚀 *SMC BUY SIGNAL: {name}*\n📍 Entry: {entry:.2f}\n🎯 TP (1200+ pts): {tp:.2f}\n🛡️ SL: {sl:.2f}")

    # SHORT SCALP: Bias Bearish + BSL Sweep + LTF CHoCH
    elif daily_trend == "BEARISH" and df_ltf['High'].iloc[-1] > bsl:
        if curr_p < df_ltf['Low'].iloc[-10:-1].min(): # CHoCH
            entry = curr_p
            tp = entry - (12.00 if name == "XAUUSD" else 0.1200 if "USD" in name else entry * 0.05)
            sl = df_ltf['High'].iloc[-1]
            active_trades[name] = {'side': 'SELL', 'entry': entry, 'tp': tp, 'sl': sl}
            send_alert(f"🚀 *SMC SELL SIGNAL: {name}*\n📍 Entry: {entry:.2f}\n🎯 TP (1200+ pts): {tp:.2f}\n🛡️ SL: {sl:.2f}")

# --- LOOP ---
send_alert("🧠 *SMC Multi-TF Bot Active on Railway*\nAnalyzing Daily Bias, 1H Zones, and 5m Entries.")
while True:
    for name, symbol in MARKETS.items():
        try:
            run_advanced_smc(name, symbol)
            time.sleep(2)
        except Exception as e:
            print(f"Error on {name}: {e}")
    time.sleep(300)
