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

# --- 1. دالة حساب تاريخ الإنشاء الدقيق ---
def get_creation_date(user_id):
    try:
        uid = int(user_id)
        # إزاحة بمقدار 32 بت لاستخراج الطابع الزمني
        timestamp = uid >> 32
        if timestamp < 1451606400: # قبل عام 2016
            return "غير متاح"
        dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        return dt.strftime('%Y-%m-%d')
    except:
        return "N/A"

# --- 2. دالة تحويل كود الدولة إلى علم إيموجي ---
def get_country_emoji(country_code):
    if not country_code or country_code == 'N/A' or len(country_code) != 2:
        return "🌍"
    try:
        base = 127397
        return chr(ord(country_code[0].upper()) + base) + chr(ord(country_code[1].upper()) + base)
    except:
        return "🌍"

# --- 3. دالة جلب البيانات بمحرك مزدوج (لضمان ظهور العلم) ---
async def fetch_tiktok_data(username):
    url1 = f"https://www.tikwm.com/api/user/info?unique_id={username}"
    url2 = f"https://www.tiktokfull.com/api/user/info?unique_id={username}"
    
    async with httpx.AsyncClient() as client:
        try:
            # المحرك الأساسي
            response = await client.get(url1, timeout=15.0)
            if response.status_code == 200:
                res_json = response.json()
                data = res_json.get("data", {})
                
                # فحص الدولة: إذا كانت N/A ننتقل للمحرك الاحتياطي
                region = data.get('user', {}).get('region', 'N/A')
                if region == 'N/A':
                    logger.info(f"🌐 Region missing for {username}, checking backup source...")
                    response2 = await client.get(url2, timeout=10.0)
                    if response2.status_code == 200:
                        data2 = response2.json().get("data", {})
                        region2 = data2.get('user', {}).get('region')
                        if region2 and region2 != 'N/A':
                            if 'user' not in data: data['user'] = {}
                            data['user']['region'] = region2
                
                return data if res_json.get("code") == 0 else None
        except Exception as e:
            logger.error(f"API Error: {e}")
            return None

# --- 4. معالجات الرسائل ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "<b>مرحباً بك في بوت استخراج معلومات تيك توك!</b> 👋\n\n"
        "🔍 أرسل اسم المستخدم (Username) فقط.\n\n"
        "Powered by @Albaraa_1"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace('@', '').strip()
    if username.startswith('/'): return

    status_msg = await update.message.reply_text("🔎 جارٍ فحص قاعدة البيانات...")
    
    data = await fetch_tiktok_data(username)
    
    if data:
        user = data.get('user', {})
        stats = data.get('stats', {})
        user_id = user.get('id', 'N/A')
        
        # استخراج المنطقة والعلم
        region = user.get('region', 'N/A')
        flag = get_country_emoji(region)
        
        # استخراج التاريخ
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
        await status_msg.edit_text("❌ لم يتم العثور على الحساب. تأكد من اليوزر.")

# --- 5. التشغيل الرئيسي ---

def main():
    if not BOT_TOKEN: return
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    if WEBHOOK_URL:
        PORT = int(os.environ.get("PORT", 8443))
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
