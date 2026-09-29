import os, re, json, time, asyncio, requests, tempfile, threading
from datetime import datetime
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# --- Mini serveur web pour Render ---
app = Flask(__name__)
@app.route('/')
def home():
    return "ES Bot is running - OK"

def run_web():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web, daemon=True).start()

# --- CONFIG depuis Render ENV ---
API_ID = int(os.getenv("API_ID", "30423183"))
API_HASH = os.getenv("API_HASH", "af1df27cec6c9f339bb6e9f9c192d814")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_GROUP = int(os.getenv("DEST_GROUP", "-1003813643708"))
SOURCE_BOT = os.getenv("SOURCE_BOT", "atas_alerts_bot")
STRING_SESSION = os.getenv("STRING_SESSION")

if not STRING_SESSION:
    print("ERREUR: STRING_SESSION manquant dans Render Environment!")
    exit(1)
if not BOT_TOKEN:
    print("ERREUR: BOT_TOKEN manquant!")
    exit(1)

tg_client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

DATA_DIR = os.path.join(tempfile.gettempdir(), 'es_data')
os.makedirs(DATA_DIR, exist_ok=True)

DICT_ATAS = {
    "Put Wall": "🟥 PUT WALL = Mur support gamma. Cassure baissiere = acceleration.",
    "Call Wall": "🟩 CALL WALL = Mur resistance gamma. Cassure haussiere = acceleration.",
    "pTrans": "pTrans = Seuil gamma intermediaire Put.",
    "cTrans": "cTrans = Seuil gamma intermediaire Call.",
    "crosses": "⚡ CROSS = Cassure confirmee. Changement de regime.",
    "approaching": "👀 Approche d'un mur. On observe.",
    "backwardation": "🔴 BACKWARDATION = STRESS extreme.",
    "contango": "🟢 CONTANGO = Calme.",
    "IVR 100": "🔥 IVR 100% = Volatilite max.",
    "IVR very low": "💤 IVR tres bas = Breakout imminent.",
    "Gamma flip": "🔄 GAMMA FLIP = Dealers changent de camp.",
    "Dealer long gamma": "Dealer long gamma = Marche colle.",
    "Dealer short gamma": "Dealer short gamma = Mouvements rapides.",
    "VWAP": "VWAP = Prix moyen journee."
}

def tradui_reelle(atas_text, es_price=""):
    low = atas_text.lower()
    expl = [v for k,v in DICT_ATAS.items() if k.lower() in low]
    if not expl: expl = ["Alerte ATAS detectee."]
    if "backwardation" in low or ("put wall" in low and "cross" in low):
        action = "👉 ACTION: Ne BUY pas. Attends SHORT pullback. Stop 15-20pts."
    elif "call wall" in low and "cross" in low:
        action = "👉 ACTION: Biais LONG sur pullback."
    elif "approaching" in low:
        action = "👉 ACTION: Reste en dehors."
    else:
        action = "👉 ACTION: Note le niveau."
    return f"🤖 *ALERTE - {datetime.now().strftime('%H:%M:%S')}*\nBrut: `{atas_text}`\n{chr(10).join(expl)}\n\n{action}\nES: {es_price}\n"

last_atas_msg = time.time()
flood_buffer = []
flood_mode = False
cache = {}

async def send_to_private(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": DEST_GROUP, "text": text, "parse_mode":"Markdown"}, timeout=10)
    except Exception as e:
        print(f"Send fail: {e}")

@tg_client.on(events.NewMessage)
async def handler(event):
    global flood_mode, flood_buffer, last_atas_msg
    sender = await event.get_sender()
    username = getattr(sender, 'username', '') or ''
    if SOURCE_BOT.lower() not in username.lower():
        try:
            chat = await event.get_chat()
            if SOURCE_BOT.lower() not in (getattr(chat,'username','') or '').lower():
                return
        except: return
    raw = event.message.text
    if not raw: return
    last_atas_msg = time.time()
    flood_buffer.append((time.time(), raw))
    flood_buffer = [x for x in flood_buffer if time.time()-x[0] < 20]
    if len(flood_buffer) > 6 and not flood_mode:
        flood_mode = True
        await send_to_private("🔄 *ATAS SYNC...* Flood detecte, je filtre.")
        return
    if flood_mode:
        if time.time() - flood_buffer[-1][0] > 25:
            resume = "\n".join([f"- {t}" for _,t in flood_buffer[-15:]])
            await send_to_private(f"🔄 *SYNC TERMINEE - {len(flood_buffer)} alertes*\n{resume}")
            flood_buffer.clear()
            flood_mode = False
        return
    key = re.sub(r'\d+(\.\d+)?', 'X', raw)
    if key in cache and time.time()-cache[key] < 300:
        if not any(k in raw.lower() for k in ["crosses","backwardation","ivr 100"]): return
    cache[key]=time.time()
    es_price="N/A"
    try:
        r=requests.get("https://query1.finance.yahoo.com/v8/finance/chart/ES=F?range=1d&interval=1m",headers={"User-Agent":"Mozilla/5.0"},timeout=5).json()
        es_price=f"{r['chart']['result'][0]['meta']['regularMarketPrice']:.2f}"
    except: pass
    await send_to_private(tradui_reelle(raw, es_price))

async def watchdog():
    global last_atas_msg
    while True:
        await asyncio.sleep(60)
        if time.time() - last_atas_msg > 900:
            if 9 <= datetime.now().hour <= 23:
                await send_to_private("🔌 *DECONNEXION* - Plus de signal ATAS depuis 15 min.")
                last_atas_msg = time.time()+600

async def main():
    while True:
        try:
            print(f"=== ES Interpreter START - Ecoute @{SOURCE_BOT} -> {DEST_GROUP} ===", flush=True)
            await tg_client.start()
            tg_client.loop.create_task(watchdog())
            await tg_client.run_until_disconnected()
        except Exception as e:
            print(f"Connexion perdue: {e} - Reconnexion 5s...", flush=True)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
