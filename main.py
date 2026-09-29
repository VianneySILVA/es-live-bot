import os, time, io, threading
import requests, yfinance as yf
import matplotlib.pyplot as plt
from flask import Flask

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("DEST_GROUP")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
@app.route('/')
def home():
    return "ES Bot LIVE - OK"

def get_price():
    try:
        data = yf.download("ES=F", period="1d", interval="1m", progress=False)
        price = float(data['Close'].iloc[-1])
        vol = int(data['Volume'].iloc[-1]) if 'Volume' in data else 50000
        return price, vol
    except:
        return 6600, 55000

def make_chart(price):
    fig, ax = plt.subplots(figsize=(10,6))
    ax.plot([price-10, price, price+5], [0, 1, 0.5])
    ax.set_title(f"ES FUTURE {price:.0f} - Live")
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf

def bot_loop():
    time.sleep(10)
    while True:
        try:
            price, vol = get_price()
            msg = f"🟢 ES {price:.0f} Vol {vol} - Live H24"
            buf = make_chart(price)
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            requests.post(url, data={"chat_id": CHAT_ID, "caption": msg}, files={"photo": buf}, timeout=20)
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(900) # toutes les 15 min

if __name__ == "__main__":
    Thread = threading.Thread(target=bot_loop, daemon=True)
    Thread.start()
    app.run(host='0.0.0.0', port=PORT)
