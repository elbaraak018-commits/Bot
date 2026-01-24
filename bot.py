import os
import telebot
import requests
import datetime
import time
from flask import Flask, request

# --- الإعدادات ---
TOKEN = os.environ.get('BOT_TOKEN')
URL = os.environ.get('SERVER_URL')
APIFY_TOKEN = os.environ.get('APIFY_TOKEN')

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# دالة تعيين الـ Webhook بأمان
def set_webhook_safe():
    webhook_url = f"{URL}/{TOKEN}"
    try:
        # فحص الحالة الحالية قبل التغيير لتجنب خطأ 429
        current_info = bot.get_webhook_info()
        if current_info.url != webhook_url:
            bot.remove_webhook()
            time.sleep(1)
            bot.set_webhook(url=webhook_url)
            print(f"✅ Webhook set successfully")
    except Exception as e:
        print(f"⚠️ Webhook Error: {e}")

# دالة حساب تاريخ إنشاء الحساب تقريبياً
def get_creation_date(user_id):
    try:
        binary_id = bin(int(user_id))[2:].zfill(64)
        timestamp = int(binary_id[:31], 2)
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return "N/A"

# جلب البيانات من Apify
def fetch_tiktok_data(username):
    api_url = f"https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    payload = {
        "usernames": [username],
        "resultsPerPage": 1,
        "shouldDownloadVideos": False
    }
    try:
        response = requests.post(api_url, json=payload, timeout=60)
        if response.status_code in [200, 201]:
            data = response.json()
            return data[0] if data else None
    except:
        return None
    return None

# --- المسارات (Routes) ---

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    return "Forbidden", 403

@app.route("/")
def index():
    return "Bot is Online!", 200

# --- الأوامر (Handlers) ---

# 1. رسالة الترحيب (يجب أن تكون في البداية)
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 أهلاً بك في بوت استخراج معلومات تيك توك!\n\n"
        "🔍 فقط أرسل لي **اسم المستخدم (Username)** وسأقوم بجلب كافة التفاصيل لك.\n\n"
        "Powered by @Albaraa_1"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# 2. معالج الرسائل النصية (البحث)
@bot.message_handler(func=lambda message: True)
def handle_tiktok_search(message):
    username = message.text.replace('@', '').strip()
    
    # تجاهل الأوامر الأخرى
    if username.startswith('/'): return

    wait_msg = bot.reply_to(message, "⏳ جارٍ جلب البيانات من تيك توك... انتظر قليلاً.")
    
    user_data = fetch_tiktok_data(username)
    
    if user_data:
        author = user_data.get('authorMeta', {})
        user_id = author.get('id', 'N/A')
        
        caption = (
            f"👤 **اسم المستخدم:** `{author.get('name')}`\n"
            f"🆔 **المعرّف:** `{user_id}`\n"
            f"📛 **الاسم:** {author.get('nickName')}\n"
            f"👥 **المتابعين:** {author.get('fans'):,}\n"
            f"🏃 **يتابع:** {author.get('following'):,}\n"
            f"❤️ **الإعجابات:** {author.get('heart'):,}\n"
            f"🎬 **الفيديوهات:** {author.get('video')}\n"
            f"📅 **تاريخ الإنشاء:** {get_creation_date(user_id)}\n"
            f"🌍 **الدولة:** {author.get('region', 'N/A')}\n"
            f"🔒 **حساب خاص:** {'نعم ✅' if author.get('private') else 'لا ❌'}\n"
            f"📜 **السيرة:** {author.get('signature', 'لا توجد')}\n\n"
            f"Powered by @Albaraa_1"
        )
        bot.edit_message_text(caption, message.chat.id, wait_msg.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("❌ فشل جلب البيانات. تأكد من اليوزر أو رصيد Apify.\n\nPowered by @Albaraa_1", message.chat.id, wait_msg.message_id)

if __name__ == "__main__":
    set_webhook_safe()
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
