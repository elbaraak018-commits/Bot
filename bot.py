import os
import httpx
import html
import logging
import datetime
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- جلب الإعدادات من متغيرات النظام ---
# هنا البوت سيبحث عن المتغير في النظام ولن يجد التوكن مكشوفاً في الكود
BOT_TOKEN = os.getenv("BOT_TOKEN")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

def get_flag(code):
    if not code or len(str(code)) != 2: return "🌍"
    try:
        code = str(code).upper()
        base = 127397
        return chr(ord(code[0]) + base) + chr(ord(code[1]) + base)
    except: return "🌍"

async def fetch_tiktok_apify(username):
    # نستخدم المتغير الذي جلبناه من النظام
    if not APIFY_TOKEN:
        logging.error("خطأ: لم يتم ضبط APIFY_TOKEN في متغيرات البيئة!")
        return None

    api_url = f"https://api.apify.com/v2/actor-tasks/apify~tiktok-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    
    payload = {
        "usernames": [username],
        "resultsPerPage": 1,
        "shouldDownloadVideos": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, json=payload)
            if response.status_code in [200, 201]:
                results = response.json()
                return results[0] if results else None
    except Exception as e:
        logging.error(f"Apify Error: {e}")
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace('@', '').strip()
    if not username: return

    status_msg = await update.message.reply_text("🔎 جاري سحب البيانات الموثقة...")
    
    data = await fetch_tiktok_apify(username)
    
    if data:
        user = data.get('authorMeta', {})
        user_id = user.get('id', '0')
        region = user.get('region', 'N/A')
        flag = get_flag(region)
        
        # تحويل التاريخ
        try:
            timestamp = int(user_id) >> 32
            date_str = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).strftime('%Y-%m-%d')
        except: date_str = "غير متاح"

        response = (
            f"👤 <b>اليوزر:</b> <code>{user.get('name')}</code>\n"
            f"🆔 <b>المعرف:</b> <code>{user_id}</code>\n"
            f"🌍 <b>الدولة:</b> {region} {flag}\n"
            f"👥 <b>المتابعين:</b> {user.get('fans', 0):,}\n"
            f"📅 <b>الإنشاء:</b> <code>{date_str}</code>\n"
            f"📜 <b>البايو:</b> {html.escape(user.get('signature', 'لا يوجد'))}\n\n"
            f"<b>تم الربط بنجاح عبر Apify المتغيرات</b>"
        )
        await status_msg.edit_text(response, parse_mode=ParseMode.HTML)
    else:
        await status_msg.edit_text("❌ لم تظهر بيانات، تأكد من ضبط APIFY_TOKEN في السيرفر.")

def main():
    if not BOT_TOKEN:
        print("خطأ: BOT_TOKEN غير موجود!")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ البوت يعمل الآن بنظام المتغيرات المحمي...")
    app.run_polling()

if __name__ == "__main__":
    main()
