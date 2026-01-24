import os
import telebot
import requests
import datetime
from flask import Flask, request

# --- الإعدادات ---
TOKEN = os.environ.get('BOT_TOKEN')
URL = os.environ.get('SERVER_URL')
APIFY_TOKEN = os.environ.get('APIFY_TOKEN')

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# دالة لتحويل الـ ID إلى تاريخ إنشاء الحساب (تقريبي)
def get_creation_date(user_id):
    try:
        binary_id = bin(int(user_id))[2:].zfill(64)
        timestamp = int(binary_id[:31], 2)
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return "N/A"

def fetch_tiktok_data(username):
    # استخدام Apify TikTok Scraper (كمثال لـ Actor شهير)
    api_url = f"https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    payload = {
        "usernames": [username],
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False
    }
    
    response = requests.post(api_url, json=payload)
    if response.status_code == 201 or response.status_code == 200:
        data = response.json()
        if data:
            return data[0] # إرجاع أول نتيجة
    return None

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=URL + '/' + TOKEN)
    return "Webhook status: Active", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً بك! أرسل اسم المستخدم (Username) وسأجلب لك كافة التفاصيل.")

@bot.message_handler(func=lambda message: True)
def handle_info(message):
    username = message.text.replace('@', '').strip()
    wait_msg = bot.reply_to(message, "⏳ جارٍ الاتصال بـ Apify وفحص الحساب... انتظر قليلاً.")
    
    user_data = fetch_tiktok_data(username)
    
    if user_data:
        user_id = user_data.get('authorMeta', {}).get('id', 'N/A')
        
        caption = (
            f"👤 **اسم المستخدم:** `{user_data.get('authorMeta', {}).get('name')}`\n"
            f"🆔 **المعرّف:** `{user_id}`\n"
            f"📛 **الاسم:** {user_data.get('authorMeta', {}).get('nickName')}\n"
            f"👥 **المتابعين:** {user_data.get('authorMeta', {}).get('fans')}\n"
            f"🏃 **يتابع:** {user_data.get('authorMeta', {}).get('following')}\n"
            f"❤️ **الإعجابات:** {user_data.get('authorMeta', {}).get('heart')}\n"
            f"🎬 **الفيديوهات:** {user_data.get('authorMeta', {}).get('video')}\n"
            f"📅 **تاريخ الإنشاء:** {get_creation_date(user_id)}\n"
            f"🌍 **الدولة:** {user_data.get('authorMeta', {}).get('region', 'N/A')}\n"
            f"🔒 **حساب خاص:** {'نعم ✅' if user_data.get('authorMeta', {}).get('private') else 'لا ❌'}\n"
            f"📜 **السيرة الذاتية:** {user_data.get('authorMeta', {}).get('signature', 'لا يوجد')}\n"
            f"--- \n"
            f"⚡ تم الاستخراج بواسطة Apify API"
        )
        bot.edit_message_text(caption, message.chat.id, wait_msg.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("❌ فشل جلب البيانات. تأكد من صحة اليوزر أو رصيد Apify.", message.chat.id, wait_msg.message_id)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
