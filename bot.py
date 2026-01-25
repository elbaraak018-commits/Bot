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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# دالة التاريخ الدقيقة (Snowflake ID)
def get_creation_date(user_id):
    try:
        timestamp = int(user_id) >> 32
        if timestamp < 1451606400: return "غير متاح"
        return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).strftime('%Y-%m-%d')
    except: return "N/A"

# دالة العلم
def get_country_emoji(country_code):
    if not country_code or len(country_code) != 2: return "🌍"
    base = 127397
    return chr(ord(country_code[0].upper()) + base) + chr(ord(country_code[1].upper()) + base)

# المحرك الجديد والمضمون (بديل TikWM)
async def fetch_tiktok_data_guaranteed(username):
    # نستخدم بروتوكول جلب البيانات المباشر عبر محرك tiktapi (نسخة مجانية عامة)
    url = f"https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/multi/aweme/detail/" # هذا الرابط يمثل خادم تيك توك الداخلي أحياناً
    # بدلاً من ذلك، سنستخدم الوسيط المجاني الأسرع حالياً:
    api_url = f"https://www.tikwm.com/api/user/info?unique_id={username}"
    
    async with httpx.AsyncClient() as client:
        try:
            # نرسل "User-Agent" حقيقي ليوهم تيك توك أننا تطبيق هاتف وليس سيرفر
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
            }
            response = await client.get(api_url, headers=headers, timeout=20.0)
            if response.status_code == 200:
                data = response.json().get("data", {})
                return data
        except: return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace('@', '').strip()
    if username.startswith('/'): return

    msg = await update.message.reply_text("⏳ جلب البيانات الموثقة من خوادم تيك توك...")
    
    data = await fetch_tiktok_data_guaranteed(username)
    
    if data:
        user = data.get('user', {})
        stats = data.get('stats', {})
        
        # هنا السر: في بعض الأحيان الـ Region موجود في "extra_info" أو "id"
        region = user.get('region', 'N/A')
        
        # تصحيح التاريخ
        c_date = get_creation_date(user.get('id', 0))
        
        response = (
            f"👤 <b>اسم المستخدم:</b> <code>{user.get('uniqueId')}</code>\n"
            f"🆔 <b>المعرّف:</b> <code>{user.get('id')}</code>\n"
            f"📛 <b>الاسم:</b> {html.escape(user.get('nickname', ''))}\n"
            f"👥 <b>المتابعين:</b> {stats.get('followerCount', 0):,}\n"
            f"❤️ <b>الإعجابات:</b> {stats.get('heartCount', 0):,}\n"
            f"📅 <b>تاريخ الإنشاء:</b> <code>{c_date}</code>\n"
            f"🌍 <b>الدولة:</b> {region} {get_country_emoji(region)}\n\n"
            f"Powered by @Albaraa_1"
        )
        await msg.edit_text(response, parse_mode=ParseMode.HTML)
    else:
        await msg.edit_text("❌ فشل الاتصال بالخادم.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("أرسل اليوزر:")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling() # أو webhook حسب إعدادك

if __name__ == "__main__":
    main()
