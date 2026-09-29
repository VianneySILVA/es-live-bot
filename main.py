import os, time, threading, requests, io
from flask import Flask
from PIL import Image, ImageDraw

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("DEST_GROUP")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
@app.route('/')
def home(): return "ES Bot V3 LIVE"

def get_es_data():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/ES=F?range=1d&interval=5m"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        result = r['chart']['result'][0]
        price = result['meta']['regularMarketPrice']
        closes = result['indicators']['quote'][0]['close']
        closes = [c for c in closes if c is not None][-50:] # 50 dernières bougies
        return float(price), closes
    except Exception as e:
        print(f"Yahoo err {e}", flush=True)
        return 6650.0, [6640,6645,6650,6648,6650]

def make_chart_image(closes, price):
    W, H = 800, 400
    img = Image.new('RGB', (W, H), 'black')
    draw = ImageDraw.Draw(img)
    # grille
    for i in range(0, W, 80): draw.line([(i,0),(i,H)], fill="#222222")
    for i in range(0, H, 80): draw.line([(0,i),(W,i)], fill="#222222")

    if len(closes) > 1:
        mn, mx = min(closes), max(closes)
        pad = (mx-mn)*0.2 if mx!=mn else 10
        mn -= pad; mx += pad
        points = []
        for idx, c in enumerate(closes):
            x = int(idx/(len(closes)-1)*(W-20)+10)
            y = int(H - 20 - (c-mn)/(mx-mn)*(H-40))
            points.append((x,y))
        draw.line(points, fill="#00FF88", width=3)
        # dernier prix
        draw.ellipse([(points[-1][0]-6, points[-1][1]-6),(points[-1][0]+6, points[-1][1]+6)], fill="#00FF88")

    draw.text((15,10), f"ES FUTURE {price:.2f} - Live H24", fill="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

def bot_loop():
    print("BOT V3 START", flush=True)
    while True:
        try:
            price, closes = get_es_data()
            msg = f"🟢 ES {price:.2f} | H24 LIVE | {time.strftime('%H:%M')} - Vianos"
            chart = make_chart_image(closes, price)

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            r = requests.post(url, data={"chat_id": CHAT_ID, "caption": msg}, files={"photo": chart}, timeout=20)
            print(f"Sent ES {price} -> {r.status_code}", flush=True)
        except Exception as e:
            print(f"Loop err {e}", flush=True)
        time.sleep(900)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT)
