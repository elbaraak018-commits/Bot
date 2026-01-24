import os
import logging
import datetime
import httpx
import html # سنستخدم الـ HTML بدلاً من Markdown لأنه أكثر استقراراً
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_creation_date(user_id):
    try:
        binary_id = bin(int(user_id))[2:].zfill(64)
        timestamp = int(binary_id[:31], 2)
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except: return "N/A"

async def fetch_tiktok_data(username):
    url = f"https://www.tikwm.com/api/user/info?unique_id={username}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=25.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    return data.get("data")
    except Exception as e:
        logger.error(f"TikWM Error: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت استخراج معلومات تيك توك!\n"
        "أرسل اسم المستخدم (Username) فقط.\n\n"
        "Powered by @Albaraa_1"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace('@', '').strip()
    if username.startswith('/'): return

    status_msg = await update.message.reply_text("🔎 جارٍ فحص قاعدة بيانات تيك توك...")
    
    try:
        user_data = await fetch_tiktok_data(username)
        
        if user_data:
            user = user_data.get('user', {})
            stats = user_data.get('stats', {})
            user_id = user.get('id', 'N/A')
            
            # استخدام html.escape لتجنب كسر التنسيق بسبب رموز السيرة الذاتية
            nickname = html.escape(user.get('nickname', 'N/A'))
            signature = html.escape(user.get('signature', 'لا توجد'))
            unique_id = html.escape(user.get('uniqueId', ''))

            caption = (
                f"👤 <b>اسم المستخدم:</b> <code>{unique_id}</code>\n"
                f"🆔 <b>المعرّف:</b> <code>{user_id}</code>\n"
                f"📛 <b>الاسم:</b> {nickname}\n"
                f"👥 <b>المتابعين:</b> {stats.get('followerCount', 0):,}\n"
                f"🏃 <b>يتابع:</b> {stats.get('followingCount', 0):,}\n"
                f"❤️ <b>الإعجابات:</b> {stats.get('heartCount', 0):,}\n"
                f"🎬 <b>الفيديوهات:</b> {stats.get('videoCount', 0)}\n"
                f"📅 <b>تاريخ الإنشاء:</b> {get_creation_date(user_id)}\n"
                f"🌍 <b>الدولة:</b> {user.get('region', 'N/A')}\n"
                f"🔒 <b>حساب خاص:</b> {'نعم ✅' if user.get('privateAccount') else 'لا ❌'}\n"
                f"📜 <b>السيرة:</b> {signature}\n\n"
                f"Powered by @Albaraa_1"
            )
            # تم التغيير إلى HTML لضمان عدم حدوث خطأ Entity Parse
            await status_msg.edit_text(caption, parse_mode=ParseMode.HTML)
        else:
            await status_msg.edit_text("❌ لم يتم العثور على الحساب.\n\nPowered by @Albaraa_1")
            
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        await status_msg.edit_text("⚠️ حدث خطأ أثناء معالجة البيانات النصية للحساب.")

def main():
    if not BOT_TOKEN: return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    if WEBHOOK_URL:
        PORT = int(os.environ.get("PORT", 8443))
        app.run_webhook(
            listen="0.0.0.0", port=PORT, url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
