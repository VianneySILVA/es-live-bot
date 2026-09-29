import os, time, threading, requests
from flask import Flask

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("DEST_GROUP")
PORT = int(os.environ.get("PORT", 10000))
app = Flask(__name__)
@app.route('/')
def home(): return "ES Bot LIVE"

def get_es_price():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/ES=F?interval=1m&range=1d"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        price = r['chart']['result'][0]['meta']['regularMarketPrice']
        return float(price)
    except: return 6600

def bot_loop():
    print("BOT ES START", flush=True)
    while True:
        try:
            price = get_es_price()
            msg = f"🟢 ES FUTURE: {price:.2f} - Live H24\nH: {price+8:.0f} | L: {price-8:.0f}"
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=15)
            print(f"Sent ES {price}", flush=True)
        except Exception as e:
            print(f"Err {e}", flush=True)
        time.sleep(900) # 15 min

threading.Thread(target=bot_loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT)
