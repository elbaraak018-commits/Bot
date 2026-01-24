import os
import logging
import datetime
import httpx
import html
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات ---
# تأكد من وضع هذه المتغيرات في إعدادات Render (Environment Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# إعداد السجلات (Logging) لسهولة تتبع الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- الدوال المساعدة ---

def get_creation_date(user_id):
    """حساب تاريخ إنشاء الحساب تقريبياً بناءً على الـ ID"""
    try:
        binary_id = bin(int(user_id))[2:].zfill(64)
        timestamp = int(binary_id[:31], 2)
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return "N/A"

def get_country_emoji(country_code):
    """تحويل كود الدولة النصي (مثلاً FR) إلى علم (🇫🇷)"""
    if not country_code or len(country_code) != 2:
        return "🌍"
    try:
        base = 127397
        return chr(ord(country_code[0].upper()) + base) + chr(ord(country_code[1].upper()) + base)
    except:
        return "🌍"

async def fetch_tiktok_data(username):
    """جلب البيانات من TikWM API"""
    url = f"https://www.tikwm.com/api/user/info?unique_id={username}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    return data.get("data")
    except Exception as e:
        logger.error(f"TikWM Error: {e}")
    return None

# --- معالجات الأوامر (Handlers) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الأمر /start"""
    welcome_text = (
        "<b>مرحباً بك في بوت استخراج معلومات تيك توك!</b> 👋\n\n"
        "🔍 أرسل اسم المستخدم (Username) الخاص بالحساب وسأقوم بجلب كافة التفاصيل.\n\n"
        "Powered by @Albaraa_1"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية (البحث عن اليوزر)"""
    username = update.message.text.replace('@', '').strip()
    
    # تجاهل الأوامر الأخرى
    if username.startswith('/'):
        return

    status_msg = await update.message.reply_text("🔎 جارٍ فحص قاعدة بيانات تيك توك...")
    
    try:
        user_data = await fetch_tiktok_data(username)
        
        if user_data:
            user = user_data.get('user', {})
            stats = user_data.get('stats', {})
            user_id = user.get('id', 'N/A')
            
            # معالجة بيانات الموقع والعلم
            region_code = user.get('region', 'N/A')
            flag = get_country_emoji(region_code)

            # حماية النصوص من كسر التنسيق (HTML Escape)
            nickname = html.escape(user.get('nickname', 'N/S'))
            signature = html.escape(user.get('signature', 'لا توجد'))
            unique_id = html.escape(user.get('uniqueId', ''))

            response_caption = (
                f"👤 <b>اسم المستخدم:</b> <code>{unique_id}</code>\n"
                f"🆔 <b>المعرّف:</b> <code>{user_id}</code>\n"
                f"📛 <b>الاسم:</b> {nickname}\n"
                f"👥 <b>المتابعين:</b> {stats.get('followerCount', 0):,}\n"
                f"🏃 <b>يتابع:</b> {stats.get('followingCount', 0):,}\n"
                f"❤️ <b>الإعجابات:</b> {stats.get('heartCount', 0):,}\n"
                f"🎬 <b>الفيديوهات:</b> {stats.get('videoCount', 0)}\n"
                f"📅 <b>تاريخ الإنشاء:</b> {get_creation_date(user_id)}\n"
                f"🌍 <b>الدولة:</b> {region_code} {flag}\n"
                f"🔒 <b>حساب خاص:</b> {'نعم ✅' if user.get('privateAccount') else 'لا ❌'}\n"
                f"📜 <b>السيرة:</b> {signature}\n\n"
                f"Powered by @Albaraa_1"
            )
            
            await status_msg.edit_text(response_caption, parse_mode=ParseMode.HTML)
        else:
            await status_msg.edit_text("❌ لم يتم العثور على الحساب.\nتأكد من كتابة اليوزر بشكل صحيح.")
            
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        await status_msg.edit_text("⚠️ حدث خطأ أثناء معالجة البيانات، حاول مرة أخرى.")

# --- تشغيل البوت ---

def main():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN not found in environment variables!")
        return

    # بناء التطبيق
    app = Application.builder().token(BOT_TOKEN).build()

    # إضافة الأوامر والمستقبلات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # تشغيل البوت بنظام Webhook لـ Render أو Polling للتجربة المحلية
    if WEBHOOK_URL:
        PORT = int(os.environ.get("PORT", 8443))
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
        logger.info(f"Bot started via Webhook on port {PORT}")
    else:
        app.run_polling()
        logger.info("Bot started via Polling")

if __name__ == "__main__":
    main()
