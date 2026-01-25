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

# --- دالة العلم المطورة (مع نظام استنتاج) ---
def get_country_emoji(country_code, language_code=None):
    # إذا لم يوجد كود دولة، نستخدم كود اللغة كخيار احتياطي
    code = country_code if country_code and country_code != 'N/A' else language_code
    
    if not code or len(str(code)) < 2:
        return "🌍"
    
    try:
        # تنظيف الكود (أخذ أول حرفين فقط مثل SA أو AR)
        code = str(code)[:2].upper()
        # تحويل الحروف إلى رموز تعبيرية (Flags)
        base = 127397
        return chr(ord(code[0]) + base) + chr(ord(code[1]) + base)
    except:
        return "🌍"

# --- دالة التاريخ (TikTok Snowflake) ---
def get_creation_date(user_id):
    try:
        uid = int(user_id)
        timestamp = uid >> 32
        if timestamp < 1451606400: # قبل 2016
            return "غير متاح"
        dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        return dt.strftime('%Y-%m-%d')
    except:
        return "N/A"

# --- محرك جلب البيانات الجديد (أكثر استقراراً) ---
async def fetch_tiktok_data(username):
    # نستخدم TikWM كقاعدة لكن مع إعدادات Header متقدمة لتجنب الحظر
    url = f"https://www.tikwm.com/api/user/info?unique_id={username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url)
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
        "<b>مرحباً بك في بوت استخراج معلومات تيك توك المطور!</b> 🚀\n\n"
        "أرسل اسم المستخدم (Username) وسأجلب لك كافة التفاصيل.\n\n"
        "Powered by @Albaraa_1",
        parse_mode=ParseMode.HTML
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace('@', '').strip()
    if username.startswith('/') or len(username) < 2: return

    status_msg = await update.message.reply_text("🔎 جارٍ فحص السجلات وجلب البيانات...")  
  
    data = await fetch_tiktok_data(username)  
  
    if data:  
        user = data.get('user', {})  
        stats = data.get('stats', {})  
        user_id = user.get('id', 'N/A')  
          
        # حل مشكلة العلم: التحقق من المنطقة ثم اللغة
        region = user.get('region', 'N/A')
        lang = user.get('language', 'N/A')
        flag = get_country_emoji(region, lang)
          
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
            f"🌍 <b>الدولة/اللغة:</b> {region if region != 'N/A' else lang} {flag}\n"  
            f"🔒 <b>حساب خاص:</b> {'نعم ✅' if user.get('privateAccount') else 'لا ❌'}\n"  
            f"📜 <b>السيرة:</b> {html.escape(user.get('signature', 'لا توجد'))}\n\n"  
            f"Powered by @Albaraa_1"  
        )  
        await status_msg.edit_text(response, parse_mode=ParseMode.HTML)  
    else:  
        await status_msg.edit_text("❌ عذراً، لم أتمكن من العثور على هذا الحساب أو أن الخدمة مشغولة حالياً.")

# --- التشغيل ---
def main():
    if not BOT_TOKEN:
        print("خطأ: BOT_TOKEN غير موجود في متغيرات البيئة!")
        return

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
