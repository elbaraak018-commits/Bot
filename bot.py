import os
import logging
import datetime
import httpx
import html
import json
import re
from bs4 import BeautifulSoup
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def get_country_emoji(country_code):
    if not country_code or len(country_code) != 2:
        return "🌍"
    base = 127397
    return chr(ord(country_code[0].upper()) + base) + chr(ord(country_code[1].upper()) + base)

# --- دالة استخراج الدولة الاحترافية ---
async def get_tiktok_region_advanced(username):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    url = f"https://www.tiktok.com/@{username}"
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        try:
            response = await client.get(url, timeout=15.0)
            if response.status_code != 200:
                return "N/A"
            
            # البحث عن بيانات JSON داخل كود الصفحة
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tag = soup.find('script', id='__UNIVERSAL_DATA_FOR_REHYDRATION__')
            
            if script_tag:
                data_json = json.loads(script_tag.string)
                # المسار المباشر للدولة في نظام تيك توك الجديد
                region = data_json.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {}).get("userInfo", {}).get("user", {}).get("region", "N/A")
                return region
            
            # طريقة احتياطية بالـ Regex إذا تغير الـ ID الخاص بالوسم
            match = re.search(r'"region":"([A-Z]{2})"', response.text)
            if match:
                return match.group(1)
                
        except Exception as e:
            logger.error(f"Scraping Error: {e}")
    return "N/A"

# --- الدالة الرئيسية لجلب البيانات ---
async def fetch_all_data(username):
    # نجمع بين الـ API للبيانات الإحصائية والـ Scraping للدولة
    async with httpx.AsyncClient() as client:
        info_url = f"https://www.tikwm.com/api/user/info?unique_id={username}"
        try:
            resp = await client.get(info_url)
            api_data = resp.json().get("data", {})
            
            # جلب الدولة بالطريقة المضمونة
            real_region = await get_tiktok_region_advanced(username)
            
            if api_data:
                api_data['user']['region'] = real_region
                return api_data
        except:
            return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace('@', '').strip()
    if username.startswith('/'): return

    status_msg = await update.message.reply_text("🔍 جاري الفحص الدقيق للملف الشخصي...")
    
    data = await fetch_all_data(username)
    
    if data:
        user = data.get('user', {})
        stats = data.get('stats', {})
        region = user.get('region', 'N/A')
        
        res = (
            f"👤 <b>الحساب:</b> <code>{user.get('uniqueId')}</code>\n"
            f"🌍 <b>الدولة (مضمون):</b> {region} {get_country_emoji(region)}\n"
            f"👥 <b>المتابعين:</b> {stats.get('followerCount'):,}\n"
            f"📅 <b>تاريخ الإنشاء:</b> <code>{datetime.datetime.fromtimestamp(int(user.get('id')) >> 32).strftime('%Y-%m-%d') if user.get('id').isdigit() else 'N/A'}</code>\n"
            f"🔒 <b>الخصوصية:</b> {'حساب خاص 🔐' if user.get('privateAccount') else 'عام 🔓'}\n"
        )
        await status_msg.edit_text(res, parse_mode=ParseMode.HTML)
    else:
        await status_msg.edit_text("❌ تعذر العثور على بيانات.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("أرسل اليوزر الآن:")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
