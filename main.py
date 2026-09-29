import os, time, threading, requests, io
from flask import Flask
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("DEST_GROUP")
PORT = int(os.environ.get("PORT", 10000))
app = Flask(__name__)
@app.route('/')
def home(): return "ES V4 LIVE"

def get_es_ohlc():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/ES=F?range=1d&interval=5m"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=12).json()
        meta = r['chart']['result'][0]['meta']
        q = r['chart']['result'][0]['indicators']['quote'][0]
        o, h, l, c = q['open'], q['high'], q['low'], q['close']
        # filtre None et garde 80 dernières
        data = []
        for i in range(len(c)):
            if c[i] is None: continue
            data.append((o[i], h[i], l[i], c[i]))
        data = data[-80:]
        price = meta['regularMarketPrice']
        prev = meta.get('chartPreviousClose', price)
        day_high = max([x[1] for x in data]) if data else price
        day_low = min([x[2] for x in data]) if data else price
        return price, prev, day_high, day_low, data
    except Exception as e:
        print(f"Yahoo V4 err {e}", flush=True)
        return 7746, 7740, 7752, 7736, [(7740,7750,7735,7746)]*40

def make_candle_chart(price, prev, dh, dl, data):
    W, H = 900, 500
    top, bottom = 60, 40
    img = Image.new('RGB', (W, H), '#0B0E14')
    d = ImageDraw.Draw(img)
    # fond grille
    for y in range(top, H-bottom, 60):
        d.line([(0,y),(W,y)], fill='#1A1E28')
    ch = H - top - bottom
    all_l = min([x[2] for x in data]); all_h = max([x[1] for x in data])
    pad = (all_h - all_l)*0.15 if all_h!=all_l else 10
    mn, mx = all_l - pad, all_h + pad
    def y_of(v): return top + (mx - v)/(mx - mn)*ch

    n = len(data)
    cw = max(3, (W-20)//n - 2)
    for i, (o,h,l,c) in enumerate(data):
        x = 10 + i*(W-20)//n + (W-20)//n//2
        col = '#00E676' if c>=o else '#FF1744'
        d.line([(x, y_of(h)), (x, y_of(l))], fill='#8A8D93', width=1)
        d.rectangle([(x-cw//2, y_of(o)), (x+cw//2, y_of(c))], fill=col, outline=col)

    # textes
    pct = (price-prev)/prev*100 if prev else 0
    col_pct = '#00E676' if pct>=0 else '#FF1744'
    d.rectangle([(0,0),(W,50)], fill='#12151E')
    d.text((15,12), f"ES FUTURE {price:.2f} {pct:+.2f}%", fill='white')
    d.text((15, H-28), f"H:{dh:.2f} L:{dl:.2f} 5m x 80 | Vianos H24", fill='#8A8D93')
    d.text((W-140, 12), f"LIVE {time.strftime('%H:%M')}", fill=col_pct)

    buf = io.BytesIO(); img.save(buf, format='PNG'); buf.seek(0); return buf

def bot_loop():
    print("BOT V4 START", flush=True)
    while True:
        try:
            price, prev, dh, dl, data = get_es_ohlc()
            pct = (price-prev)/prev*100 if prev else 0
            caption = f"🟢 ES {price:.2f} ({pct:+.2f}%) | H:{dh:.0f} L:{dl:.0f} | H24 V4"
            chart = make_candle_chart(price, prev, dh, dl, data)
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            r = requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": chart}, timeout=20)
            print(f"V4 Sent {price} {r.status_code}", flush=True)
        except Exception as e:
            print(f"V4 err {e}", flush=True)
        time.sleep(900)

threading.Thread(target=bot_loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT)
