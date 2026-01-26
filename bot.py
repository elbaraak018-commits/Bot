import os
import logging
import datetime
import httpx
import html
import re
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. قائمة الكلمات الدلالية (للمحاولة الثانية) ---
LOCATION_KEYWORDS = {
    "ksa": "SA", "saudi": "SA", "riyadh": "SA", "jeddah": "SA", "السعودية": "SA", "الرياض": "SA",
    "egypt": "EG", "cairo": "EG", "مصر": "EG", "القاهرة": "EG",
    "uae": "AE", "dubai": "AE", "الإمارات": "AE", "دبي": "AE",
    "kuwait": "KW", "الكويت": "KW", "jordan": "JO", "الأردن": "JO",
    "iraq": "IQ", "العراق": "IQ", "algeria": "DZ", "الجزائر": "DZ",
    "morocco": "MA", "المغرب": "MA", "syria": "SY", "سوريا": "SY",
    "palestine": "PS", "gaza": "PS", "فلسطين": "PS", "yemen": "YE", "اليمن": "YE",
    "turkey": "TR", "istanbul": "TR", "تركيا": "TR", "إسطنبول": "TR",
    "usa": "US", "أمريكا": "US", "uk": "GB", "london": "GB",
    "germany": "DE", "ألمانيا": "DE", "france": "FR", "فرنسا": "FR"
}

# --- 2. دوال مساعدة ---
def get_creation_date(user_id):
    try:
        uid = int(user_id)
        timestamp = uid >> 32
        if timestamp < 1451606400: return "غير متاح"
        dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        return dt.strftime('%Y-%m-%d')
    except: return "N/A"

def get_country_emoji(country_code):
    if not country_code or country_code in ['N/A', ''] or len(country_code) != 2:
        return "🌍"
    try:
        base = 127397
        return chr(ord(country_code[0].upper()) + base) + chr(ord(country_code[1].upper()) + base)
    except: return "🌍"

def detect_country_from_text(text):
    if not text: return None
    text_lower = text.lower()
    for keyword, code in LOCATION_KEYWORDS.items():
        if keyword in text_lower:
            return code
    return None

# --- 3. المحرك الذكي (API + Text + Video Analysis) ---
async def fetch_tiktok_data_smart(username):
    async with httpx.AsyncClient() as client:
        try:
            # أ) جلب بيانات المستخدم
            info_url = f"https://www.tikwm.com/api/user/info?unique_id={username}"
            response = await client.get(info_url, timeout=15.0)
            
            if response.status_code != 200: return None
            
            res_json = response.json()
            if res_json.get("code") != 0: return None
            
            data = res_json.get("data", {})
            user_info = data.get('user', {})
            
            # --- منطق تحديد الدولة ---
            region = user_info.get('region', 'N/A')
            
            # الحالة 1: الـ API أعطانا الدولة مباشرة -> ممتاز
            if region != 'N/A' and len(region) == 2:
                return data

            # الحالة 2: الـ API فشل، نبحث في البايو والاسم
            logger.info("⚠️ Region is N/A, checking Bio/Name...")
            bio_text = f"{user_info.get('signature', '')} {user_info.get('nickname', '')}"
            detected_code = detect_country_from_text(bio_text)
            
            if detected_code:
                user_info['region'] = detected_code
                logger.info(f"✅ Found region in Bio: {detected_code}")
                return data
            
            # الحالة 3: البايو فارغ! نفحص آخر فيديو (Last Resort)
            logger.info("⚠️ Bio is empty/useless, checking last video...")
            posts_url = f"https://www.tikwm.com/api/user/posts?unique_id={username}&count=1"
            posts_resp = await client.get(posts_url, timeout=10.0)
            
            if posts_resp.status_code == 200:
                posts_data = posts_resp.json()
                videos = posts_data.get("data", {}).get("videos", [])
                
                if videos and len(videos) > 0:
                    video_region = videos[0].get('region')
                    if video_region and len(video_region) == 2:
                        user_info['region'] = video_region
                        logger.info(f"✅ Found region from Video: {video_region}")
                    else:
                        user_info['region'] = "غير محدد (مخفي)"
                else:
                    # الحساب لا يملك فيديوهات أيضاً
                    user_info['region'] = "غير محدد (لا يوجد محتوى)"
            
            return data

        except Exception as e:
            logger.error(f"Error in smart fetch: {e}")
            return None

# --- 4. معالجة الرسالة وعرض النتائج ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace('@', '').strip()
    if username.startswith('/'): return

    status_msg = await update.message.reply_text("🔎 جاري البحث والتحليل العميق...")
    
    data = await fetch_tiktok_data_smart(username)
    
    if data:
        user = data.get('user', {})
        stats = data.get('stats', {})
        user_id = user.get('id', 'N/A')
        
        region = user.get('region', 'N/A')
        flag = get_country_emoji(region)
        creation_date = get_creation_date(user_id)

        # تجهيز النصوص
        signature = html.escape(user.get('signature', 'لا توجد'))
        if not signature.strip(): signature = "<i>(فارغ)</i>"
        
        nickname = html.escape(user.get('nickname', ''))
        unique_id = html.escape(user.get('uniqueId', ''))

        response = (
            f"👤 <b>اسم المستخدم:</b> <code>{unique_id}</code>\n"
            f"🆔 <b>المعرّف:</b> <code>{user_id}</code>\n"
            f"📛 <b>الاسم:</b> {nickname}\n"
            f"👥 <b>المتابعين:</b> {stats.get('followerCount', 0):,}\n"
            f"🏃 <b>يتابع:</b> {stats.get('followingCount', 0):,}\n"
            f"❤️ <b>الإعجابات:</b> {stats.get('heartCount', 0):,}\n"
            f"🎬 <b>الفيديوهات:</b> {stats.get('videoCount', 0)}\n"
            f"📅 <b>تاريخ الإنشاء:</b> <code>{creation_date}</code>\n"
            f"🌍 <b>الدولة:</b> {region} {flag}\n"
            f"🔒 <b>حساب خاص:</b> {'نعم ✅' if user.get('privateAccount') else 'لا ❌'}\n"
            f"📜 <b>السيرة:</b> {signature}\n\n"
            f"Powered by @Albaraa_1"
        )
        await status_msg.edit_text(response, parse_mode=ParseMode.HTML)
    else:
        await status_msg.edit_text("❌ لم يتم العثور على الحساب.")

# --- 5. التشغيل ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أرسل اليوزر..", parse_mode=ParseMode.HTML)

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
