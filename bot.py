import os
import logging
import datetime
import httpx # مكتبة حديثة لطلبات الـ Async
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_creation_date(user_id):
    try:
        binary_id = bin(int(user_id))[2:].zfill(64)
        timestamp = int(binary_id[:31], 2)
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except: return "N/A"

# الدالة الجديدة لجلب البيانات باستخدام TikWM
async def fetch_tiktok_data(username):
    url = f"https://www.tikwm.com/api/user/info?unique_id={username}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=20.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0: # 0 تعني نجاح العملية في TikWM
                    return data.get("data")
    except Exception as e:
        logger.error(f"TikWM Error: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت استخراج معلومات تيك توك!\n"
        "🚀 النظام الآن يعمل بمحرك TikWM السريع.\n\n"
        "أرسل اسم المستخدم (Username) فقط.\n\n"
        "Powered by @Albaraa_1"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace('@', '').strip()
    if username.startswith('/'): return

    status_msg = await update.message.reply_text("🔎 جارٍ فحص قاعدة بيانات تيك توك...")
    
    user_data = await fetch_tiktok_data(username)
    
    if user_data:
        # استخراج الحقول من استجابة TikWM
        user = user_data.get('user', {})
        stats = user_data.get('stats', {})
        user_id = user.get('id', 'N/A')
        
        caption = (
            f"👤 **اسم المستخدم:** `{user.get('uniqueId')}`\n"
            f"🆔 **المعرّف:** `{user_id}`\n"
            f"📛 **الاسم:** {user.get('nickname')}\n"
            f"👥 **المتابعين:** {stats.get('followerCount', 0):,}\n"
            f"🏃 **يتابع:** {stats.get('followingCount', 0):,}\n"
            f"❤️ **الإعجابات:** {stats.get('heartCount', 0):,}\n"
            f"🎬 **الفيديوهات:** {stats.get('videoCount', 0)}\n"
            f"📅 **تاريخ الإنشاء:** {get_creation_date(user_id)}\n"
            f"🌍 **الدولة:** {user.get('region', 'N/A')}\n"
            f"🔒 **حساب خاص:** {'نعم ✅' if user.get('privateAccount') else 'لا ❌'}\n"
            f"📜 **السيرة:** {user.get('signature', 'لا توجد')}\n\n"
            f"Powered by @Albaraa_1"
        )
        await status_msg.edit_text(caption, parse_mode='Markdown')
    else:
        await status_msg.edit_text("❌ لم أتمكن من العثور على هذا الحساب.\nتأكد من كتابة اليوزر بشكل صحيح. ⚠️\n\nPowered by @Albaraa_1")

def main():
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
