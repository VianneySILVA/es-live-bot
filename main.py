import os, re, time, asyncio, requests, threading
from datetime import datetime
from collections import deque
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# --- Serveur web pour Render ---
app = Flask(__name__)
@app.route('/')
def home(): return "ES Bot LIVE - Anti-flood + BigTrade 100/200/350"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()

# --- CONFIG ENV ---
API_ID = int(os.getenv("API_ID", "30423183"))
API_HASH = os.getenv("API_HASH", "af1df27cec6c9f339bb6e9f9c192d814")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_GROUP = int(os.getenv("DEST_GROUP", "-1003813643708"))
SOURCE_BOT = os.getenv("SOURCE_BOT", "atas_alerts_bot")
STRING_SESSION = os.getenv("STRING_SESSION")

if not STRING_SESSION or not BOT_TOKEN:
    print("ERREUR: STRING_SESSION ou BOT_TOKEN manquant!")
    exit(1)

tg_client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# Anti-flood
flood_times = deque(maxlen=30)
flood_active_until = 0
cache = {}

DICT_ATAS = {
    "Put Wall": "🟥 PUT WALL = Mur support gamma",
    "Call Wall": "🟩 CALL WALL = Mur resistance gamma",
    "pTrans": "pTrans = Seuil intermediaire Put",
    "cTrans": "cTrans = Seuil intermediaire Call",
    "crosses": "⚡ CROSS = Cassure confirmee",
    "approaching": "👀 Approche mur",
    "backwardation": "🔴 BACKWARDATION = STRESS extreme",
    "contango": "🟢 CONTANGO = Calme",
    "Gamma flip": "🔄 GAMMA FLIP = Dealers changent de camp",
    "Dealer long gamma": "Dealer long gamma = Marche colle",
    "Dealer short gamma": "Dealer short gamma = Mouvements rapides",
    "VWAP": "VWAP = Prix moyen journee",
}

def get_es_price():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/ES=F?range=1d&interval=1m", headers={"User-Agent":"Mozilla/5.0"}, timeout=5).json()
        return float(r['chart']['result'][0]['meta']['regularMarketPrice'])
    except:
        return None

def tradui_message(raw, es_price):
    low = raw.lower()

    # --- BIG TRADE avec vrais commentaires 100/200/350 ---
    if "bigtrade" in low and "volume greater than" in low:
        m_vol = re.search(r'greater than (\d+[,\.]?\d*)', raw)
        m_price = re.search(r'at (\d+[,\.]?\d*)', raw)
        side = "BUY" if "(buy)" in low else "SELL" if "(sell)" in low else "?"
        vol = float(m_vol.group(1).replace(',', '.')) if m_vol else 0
        price_str = m_price.group(1) if m_price else "N/A"

        if vol < 100:
            return None

        try:
            p = float(price_str.replace(',', '.'))
            if es_price and abs(es_price - p) > 80:
                return None
        except:
            pass

        if vol >= 350:
            niveau = f"🐋 BALEINE {vol:.0f} CONTRATS - {side} à {price_str}"
            detail = (
                f"C'est un institutionnel. 350 lots ES = ~25M$ en une fois.\n"
                f"Si {side} BUY: Il défend violemment. Si ES reste au-dessus de {price_str} 2-3min après, c'est ABSORPTION = short squeeze probable.\n"
                f"Si {side} SELL: Distribution. Si ES n'arrive plus à monter après, c'est le top local.\n"
                f"👉 ACTION: N'entre PAS market. Attends retest de {price_str}. Si ça tient, entre avec stop 10-12pts. TP 25-35pts. Mets BE vite."
            )
        elif vol >= 200:
            niveau = f"🔥 FLUX LOURD {vol:.0f} CONTRATS - {side} à {price_str}"
            detail = (
                f"200 lots = ~15M$. C'est un algo de desk prop ou iceberg qui s'affiche.\n"
                f"1 seul = impulsion pour casser un high/low.\n"
                f"3x 200+ {side} sur {price_str} en 2 min = MUR. Le marché va coller ici.\n"
                f"👉 ACTION: Biais {side.lower()} sur pullback de 8-10pts vers {price_str}. Pas de chase. Vise 20-30pts, BE rapide. Si ES casse {price_str} contre ce flux, c'est FAKE, inverse."
            )
        else:
            niveau = f"💰 BigTrade {vol:.0f} - {side} à {price_str}"
            detail = (
                f"100 lots = ~7M$. Seuil où les pros entrent.\n"
                f"Un seul 100 = normal à l'open US, juste à noter.\n"
                f"Si tu as 3x 100+ {side} à {price_str} en <60s = ACCUMULATION. Quelqu'un construit.\n"
                f"👉 ACTION: Marque {price_str} comme support/résistance intraday. Si ES y revient, regarde la réaction. Pas de trade direct, observation. Si ça tient 2 fois, tu peux tenter petit avec stop 6pts."
            )

        return f"🤖 *BIG TRADE - {datetime.now().strftime('%H:%M:%S')}*\n{niveau}\n{detail}\n\nBrut: `{raw[:120]}`\nES: {es_price}\n"

    # --- GAMMA WALLS avec filtre distance ---
    m_prix = re.search(r'(\d{4,5}(\.\d+)?)', raw)
    prix_mur = float(m_prix.group(1).replace(',', '.')) if m_prix else None
    dist_txt = ""
    if prix_mur and es_price:
        dist = abs(es_price - prix_mur)
        if dist > 350 and not any(k in low for k in ["cross", "backwardation", "flip", "ivr 100"]):
            print(f"Filtre >350 ignoré: dist {dist:.0f}")
            return None
        if dist <= 100: dist_txt = f"🔴 CRITIQUE {dist:.0f}pts"
        elif dist <= 200: dist_txt = f"🟠 IMPORTANT {dist:.0f}pts"
        elif dist <= 350: dist_txt = f"🟡 WATCH {dist:.0f}pts"

    expl = [v for k,v in DICT_ATAS.items() if k.lower() in low]
    if not expl: expl = ["Alerte ATAS"]

    return f"🤖 *ATAS {dist_txt} - {datetime.now().strftime('%H:%M:%S')}*\nBrut: `{raw}`\n{chr(10).join(expl)}\n\nES: {es_price} | Mur: {prix_mur}\n"

async def send_to_private(text):
    if not text:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": DEST_GROUP, "text": text, "parse_mode": "Markdown"}, timeout=8)
    except Exception as e:
        print(f"Send fail: {e}")

@tg_client.on(events.NewMessage)
async def handler(event):
    global flood_active_until
    try:
        sender = await event.get_sender()
        username = getattr(sender, 'username', '') or ''
        if SOURCE_BOT.lower() not in username.lower():
            chat = await event.get_chat()
            if SOURCE_BOT.lower() not in (getattr(chat, 'username', '') or '').lower():
                return
    except:
        return

    raw = event.message.text
    if not raw:
        return
    now = time.time()

    # FLOOD 10 en 5 sec = reload ATAS
    flood_times.append(now)
    count_5s = sum(1 for t in flood_times if now - t <= 5)
    if count_5s > 10:
        if now > flood_active_until:
            flood_active_until = now + 15
            print(f"FLOOD {count_5s} en 5s -> PAUSE 15s")
            await send_to_private(f"🔄 *RELOAD ATAS détecté* - {count_5s} alertes en 5s (comme sur ta photo). Je filtre 15s.")
        return
    if now < flood_active_until:
        return

    key = re.sub(r'\d+(\.\d+)?', 'X', raw)
    if key in cache and now - cache[key] < 180:
        if not any(k in raw.lower() for k in ["cross", "backwardation", "flip", "bigtrade"]):
            return
    cache[key] = now

    es = get_es_price()
    msg = tradui_message(raw, es)
    await send_to_private(msg)

async def main():
    while True:
        try:
            print(f"=== ES Interpreter START - FINAL 100/200/350 + VRAIS COMMENTS ===", flush=True)
            await tg_client.start()
            await send_to_private("✅ *ES Bot FINAL en ligne*\nAnti-flood 10/5s actif + BigTrade 100/200/350 avec vrais commentaires.")
            await tg_client.run_until_disconnected()
        except Exception as e:
            print(f"Perdu: {e} - retry 5s", flush=True)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
