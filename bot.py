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

# --- دالة التاريخ (Snowflake ID) ---
def get_creation_date(user_id):
    try:
        uid = int(user_id)
        timestamp = uid >> 32
        if timestamp < 1451606400: return "غير متاح"
        dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        return dt.strftime('%Y-%m-%d')
    except:
        return "N/A"

# --- دالة العلم ---
def get_country_emoji(country_code):
    if not country_code or country_code in ['N/A', ''] or len(country_code) != 2:
        return "🌍"
    try:
        base = 127397
        return chr(ord(country_code[0].upper()) + base) + chr(ord(country_code[1].upper()) + base)
    except:
        return "🌍"

# --- الدالة الذكية لجلب البيانات ---
async def fetch_tiktok_data(username):
    async with httpx.AsyncClient() as client:
        try:
            # 1. محاولة جلب معلومات الحساب الأساسية
            info_url = f"https://www.tikwm.com/api/user/info?unique_id={username}"
            response = await client.get(info_url, timeout=15.0)
            user_data = None
            
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("code") == 0:
                    user_data = res_json.get("data", {})

            if not user_data: return None

            # 2. الخدعة: إذا كانت الدولة مفقودة، نبحث في فيديوهات المستخدم
            region = user_data.get('user', {}).get('region', 'N/A')
            
            if region == 'N/A':
                logger.info(f"🕵️ Region N/A for {username}, checking latest video...")
                # جلب آخر الفيديوهات
                posts_url = f"https://www.tikwm.com/api/user/posts?unique_id={username}&count=5"
                posts_resp = await client.get(posts_url, timeout=15.0)
                
                if posts_resp.status_code == 200:
                    posts_json = posts_resp.json()
                    videos = posts_json.get("data", {}).get("videos", [])
                    
                    if videos and len(videos) > 0:
                        # نأخذ الدولة من آخر فيديو
                        video_region = videos[0].get('region')
                        if video_region and len(video_region) == 2:
                            logger.info(f"✅ Found region from video: {video_region}")
                            user_data['user']['region'] = video_region
            
            return user_data

        except Exception as e:
            logger.error(f"API Error: {e}")
            return None

# --- معالجة الرسالة ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace('@', '').strip()
    if username.startswith('/'): return

    status_msg = await update.message.reply_text("🔎 جارٍ التحقيق العميق لجلب الدولة...")
    
    data = await fetch_tiktok_data(username)
    
    if data:
        user = data.get('user', {})
        stats = data.get('stats', {})
        user_id = user.get('id', 'N/A')
        
        region = user.get('region', 'N/A')
        flag = get_country_emoji(region)
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
        await status_msg.edit_text("❌ لم يتم العثور على الحساب.")

# --- التشغيل ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أرسل اليوزر لجلب التفاصيل.", parse_mode=ParseMode.HTML)

def main():
    if not BOT_TOKEN: return
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
