import os, time, threading, requests
from flask import Flask

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("DEST_GROUP")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot OK - LIVE"

def bot_loop():
    print(f"LOOP START - TOKEN={bool(BOT_TOKEN)} CHAT={CHAT_ID}", flush=True)
    time.sleep(3)
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": "🟢 TEST LIVE - Bot enfin vivant !"}, timeout=20)
        print(f"TELEGRAM {r.status_code} {r.text}", flush=True)
    except Exception as e:
        print(f"EXCEPTION {e}", flush=True)
    
    while True:
        time.sleep(60)
        print("alive...", flush=True)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    print("Flask start", flush=True)
    app.run(host='0.0.0.0', port=PORT)
