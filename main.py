import os
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_GROUP = int(os.getenv("DEST_GROUP", "-1003813643708"))

async def handle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.channel_post:
        return
    txt = update.channel_post.text or update.channel_post.caption
    if not txt:
        return
    try:
        fr = GoogleTranslator(source='auto', target='fr').translate(txt)
    except:
        fr = txt
    await ctx.bot.send_message(chat_id=DEST_GROUP, text=fr)

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.ALL, handle))
print("Bot démarré...")
app.run_polling()
