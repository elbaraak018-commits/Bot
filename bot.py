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

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- دالة العلم (الحل الصحيح والنهائي) ---
def get_country_emoji(country_code):
    """تحويل كود الدولة (ISO 3166-1 alpha-2) إلى إيموجي العلم"""
    if not country_code or country_code == 'N/A':
        return "🌍"
    
    # التأكد من أن الكود حرفين فقط (مثل TR لتركيا في حالة CZN Burak)
    code = str(country_code).strip().upper()
    if len(code) != 2:
        return "🌍"
    
    try:
        base = 127397
        return chr(ord(code[0]) + base) + chr(ord(code[1]) + base)
    except Exception:
        return "🌍"

# --- جلب البيانات عبر API قوي ومجاني ---
async def fetch_tiktok_data(username):
    # استخدام محرك بحث يقوم بعمل Scrape مباشر للبيانات الأساسية
    # هذا الرابط يعتبر "ثغرة" مستقرة لجلب بيانات البروفايل كاملة
    url = f"https://www.tikwm.com/api/user/info?unique_id={username}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("code") == 0:
                    return res_json.get("data")
    except Exception as e:
        logger.error(f"Fetch Error: {e}")
    return None

# --- المعالجات ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace('@', '').strip()
    if username.startswith('/') or not username: return

    status_msg = await update.message.reply_text("⚡️ جاري سحب البيانات الموثقة...")  
  
    data = await fetch_tiktok_data(username)  
  
    if data:  
        user = data.get('user', {})  
        stats = data.get('stats', {})  
        
        # استخراج المنطقة (Region) بشكل مباشر وموثوق
        # في حسابات مثل CZN Burak، الـ API يعيد 'TR'
        region = user.get('region') 
        
        # إذا كانت المنصة لا توفر 'region' في الرد السريع، نستخدم 'language' كمرجع تقني للموقع
        if not region:
            region = user.get('language')

        flag = get_country_emoji(region)
        
        # تحويل التاريخ من Timestamp (Snowflake ID)
        user_id = user.get('id', '0')
        creation_date = "غير متاح"
        try:
            timestamp = int(user_id) >> 32
            creation_date = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).strftime('%Y-%m-%d')
        except: pass

        response = (  
            f"👤 <b>اسم المستخدم:</b> <code>{html.escape(user.get('uniqueId', ''))}</code>\n"  
            f"🆔 <b>المعرّف:</b> <code>{user_id}</code>\n"  
            f"📛 <b>الاسم:</b> {html.escape(user.get('nickname', ''))}\n"  
            f"👥 <b>المتابعين:</b> {stats.get('followerCount', 0):,}\n"  
            f"❤️ <b>الإعجابات:</b> {stats.get('heartCount', 0):,}\n"  
            f"📅 <b>تاريخ الإنشاء:</b> <code>{creation_date}</code>\n"  
            f"🌍 <b>الدولة:</b> {region} {flag}\n"  
            f"🔒 <b>الحساب:</b> {'خاص 🔐' if user.get('privateAccount') else 'عام ✅'}\n"  
            f"📜 <b>السيرة:</b> {html.escape(user.get('signature', 'لا توجد'))}\n\n"  
            f"Powered by @Albaraa_1"  
        )  
        await status_msg.edit_text(response, parse_mode=ParseMode.HTML)  
    else:  
        await status_msg.edit_text("❌ خطأ: لم أتمكن من الوصول لبيانات هذا المستخدم حالياً.")

# --- التشغيل ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("أرسل يوزر تيك توك الآن:")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
