import os
import logging
import time
import datetime
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. إعدادات السجلات (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. جلب المتغيرات
BOT_TOKEN = os.getenv("BOT_TOKEN")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # رابط موقعك على ريندر

# 3. دوال مساعدة
def get_creation_date(user_id):
    try:
        binary_id = bin(int(user_id))[2:].zfill(64)
        timestamp = int(binary_id[:31], 2)
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except: return "N/A"

async def fetch_tiktok_data(username):
    # استخدام Actor: clockworks/tiktok-scraper
    api_url = f"https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    payload = {"usernames": [username], "resultsPerPage": 1, "shouldDownloadVideos": False}
    try:
        response = requests.post(api_url, json=payload, timeout=60)
        if response.status_code in [200, 201]:
            data = response.json()
            return data[0] if data else None
    except Exception as e:
        logger.error(f"Apify Error: {e}")
    return None

# 4. معالجات الأوامر (Handlers)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **أهلاً بك في بوت معلومات تيك توك المطور!**\n\n"
        "🔍 أرسل اسم المستخدم (Username) فقط وسأجلب لك التفاصيل.\n\n"
        "Powered by @Albaraa_1"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace('@', '').strip()
    if username.startswith('/'): return

    status_msg = await update.message.reply_text("⏳ جارٍ استخراج البيانات من Apify...")
    
    user_data = await fetch_tiktok_data(username)
    
    if user_data:
        author = user_data.get('authorMeta', {})
        user_id = author.get('id', 'N/A')
        
        caption = (
            f"👤 **اسم المستخدم:** `{author.get('name')}`\n"
            f"🆔 **المعرّف:** `{user_id}`\n"
            f"📛 **الاسم:** {author.get('nickName')}\n"
            f"👥 **المتابعين:** {author.get('fans'):,}\n"
            f"🏃 **يتابع:** {author.get('following'):,}\n"
            f"❤️ **الإعجابات:** {author.get('heart'):,}\n"
            f"🎬 **الفيديوهات:** {author.get('video')}\n"
            f"📅 **تاريخ الإنشاء:** {get_creation_date(user_id)}\n"
            f"🌍 **الدولة:** {author.get('region', 'N/A')}\n\n"
            f"Powered by @Albaraa_1"
        )
        await status_msg.edit_text(caption, parse_mode='Markdown')
    else:
        await status_msg.edit_text("❌ فشل جلب البيانات. تأكد من اليوزر أو رصيد Apify.\n\nPowered by @Albaraa_1")

# 5. التشغيل الرئيسي (Main)
def main():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN missing!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    if WEBHOOK_URL:
        PORT = int(os.environ.get("PORT", 8443))
        # المكتبة ستقوم بكل العمل نيابة عنك هنا
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
