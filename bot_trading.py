import os
import time
import pandas as pd
from binance.client import Client
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from dotenv import load_dotenv
import requests

# =======================
# 1. LOAD KONFIGURASI
# =======================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
USE_TESTNET = os.getenv("USE_TESTNET", "True").lower() == "true"
AUTO_TRADE = os.getenv("AUTO_TRADE", "False").lower() == "true"

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=USE_TESTNET)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]  # kamu bisa tambahkan lebih banyak

# =======================
# 2. KIRIM PESAN TELEGRAM
# =======================
def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Gagal kirim pesan Telegram:", e)

# =======================
# 3. DAPATKAN DATA HARGA
# =======================
def get_klines(symbol, interval="1m", limit=50):
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            "timestamp","open","high","low","close","volume","close_time",
            "quote_asset_volume","trades","taker_base_vol","taker_quote_vol","ignore"
        ])
        df["close"] = df["close"].astype(float)
        return df
    except Exception as e:
        print(f"Gagal ambil data {symbol}:", e)
        return None

# =======================
# 4. GENERATE SINYAL
# =======================
def generate_signal(df):
    close = df["close"]
    ema = EMAIndicator(close, window=14).ema_indicator()
    rsi = RSIIndicator(close, window=14).rsi()
    
    latest_close = close.iloc[-1]
    latest_ema = ema.iloc[-1]
    latest_rsi = rsi.iloc[-1]
    
    if latest_close > latest_ema and latest_rsi < 70:
        return "BUY"
    elif latest_close < latest_ema and latest_rsi > 30:
        return "SELL"
    else:
        return "HOLD"

# =======================
# 5. AUTO TRADE (OPSIONAL)
# =======================
def execute_trade(symbol, side, qty=0.001):
    try:
        if not AUTO_TRADE:
            return f"Auto-trade dimatikan. Sinyal: {side} ({symbol})"
        order = client.create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=qty
        )
        return f"✅ {side} {symbol} berhasil dieksekusi!"
    except Exception as e:
        return f"❌ Gagal trade {symbol}: {e}"

# =======================
# 6. LOOP UTAMA
# =======================
send_telegram_message("🤖 Bot sinyal trading aktif dan terhubung ke Binance Testnet!")

while True:
    for symbol in SYMBOLS:
        df = get_klines(symbol)
        if df is None:
            continue
        signal = generate_signal(df)
        last_price = df['close'].iloc[-1]

        msg = f"📊 {symbol}\nHarga: {last_price:.2f}\nSinyal: {signal}"
        print(msg)
        send_telegram_message(msg)

        if signal in ["BUY", "SELL"]:
            result = execute_trade(symbol, signal)
            print(result)
            send_telegram_message(result)

        time.sleep(3)  # jeda antar coin

    time.sleep(60)  # perbarui tiap 1 menit
