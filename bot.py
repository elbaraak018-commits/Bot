import os
import logging
import datetime
import httpx
import html
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- دالة التاريخ المطورة (TikTok Snowflake ID) ---
def get_creation_date(user_id):
    try:
        uid = int(user_id)
        # تيك توك يستخدم أول 32 بت للطابع الزمني (Timestamp)
        # نقوم بإزاحة الـ ID بمقدار 32 بت لليمين للحصول على الوقت
        timestamp = uid >> 32
        
        # تصحيح: تيك توك بدأ فعلياً في 2016، أي تاريخ قبل ذلك هو خطأ في الحساب
        if timestamp < 1451606400: 
            return "غير متاح"
            
        dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        return dt.strftime('%Y-%m-%d')
    except:
        return "N/A"

# --- دالة العلم (تحويل كود الدولة لإيموجي) ---
def get_country_emoji(country_code):
    if not country_code or country_code == 'N/A' or len(country_code) != 2:
        return "🌍"
    base = 127397
    return chr(ord(country_code[0].upper()) + base) + chr(ord(country_code[1].upper()) + base)

# --- جلب البيانات من محرك مستقر ---
async def fetch_tiktok_data(username):
    # محرك TikWM يعطي نتائج جيدة إذا تم طلبه بشكل صحيح
    url = f"https://www.tikwm.com/api/user/info?unique_id={username}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=20.0)
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("code") == 0:
                    return res_json.get("data")
    except Exception as e:
        logger.error(f"Fetch Error: {e}")
    return None

# --- المعالجات ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>مرحباً بك في بوت استخراج معلومات تيك توك!</b> 👋\n\n"
        "أرسل اسم المستخدم (Username) فقط.\n\n"
        "Powered by @Albaraa_1",
        parse_mode=ParseMode.HTML
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace('@', '').strip()
    if username.startswith('/'): return

    status_msg = await update.message.reply_text("🔎 جارٍ فحص السجلات...")
    
    data = await fetch_tiktok_data(username)
    
    if data:
        user = data.get('user', {})
        stats = data.get('stats', {})
        user_id = user.get('id', 'N/A')
        
        # استخراج المنطقة والعلم
        region = user.get('region', 'N/A')
        flag = get_country_emoji(region)
        
        # حساب التاريخ بالمعادلة الجديدة
        creation_date = get_creation_date(user_id)

        response = (
            f"👤 <b>اسم المستخدم:</b> <code>{html.escape(user.get('uniqueId', ''))}</code>\n"
            f"🆔 <b>المعرّف:</b> <code>{user_id}</code>\n"
            f"📛 <b>الاسم:</b> {html.escape(user.get('nickname', ''))}\n"
            f"👥 <b>المتابعين:</b> {stats.get('followerCount', 0):,}\n"
            f"🏃 <b>يتابع:</b> {stats.get('followingCount', 0):,}\n"
            f"❤️ <b>الإعجابات:</b> {stats.get('heartCount', 0):,}\n"
            f"🎬 <b>الفيديوهات:</b> {stats.get('videoCount', 0)}\n"
            f"📅 <b>تاريخ الإنشاء:</b> <code>{creation_date}</code>\n"
            f"🌍 <b>الدولة:</b> {region} {flag}\n"
            f"🔒 <b>حساب خاص:</b> {'نعم ✅' if user.get('privateAccount') else 'لا ❌'}\n"
            f"📜 <b>السيرة:</b> {html.escape(user.get('signature', 'لا توجد'))}\n\n"
            f"Powered by @Albaraa_1"
        )
        await status_msg.edit_text(response, parse_mode=ParseMode.HTML)
    else:
        await status_msg.edit_text("❌ لم يتم العثور على الحساب. جرب يوزر آخر.")

# --- التشغيل ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    if WEBHOOK_URL:
        PORT = int(os.environ.get("PORT", 8443))
        app.run_webhook(listen="0.0.0.0", port=PORT, url_path=BOT_TOKEN, webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
