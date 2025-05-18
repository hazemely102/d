import requests
import re
import urllib.parse
import pycountry
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatAction
from flask import Flask

# ------------------ الإعدادات الأساسية ------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------ التوكن والمتغيرات البيئية ------------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://YOUR_RENDER_URL.onrender.com")
PORT = int(os.environ.get("PORT", 8080))

# ------------------ إعداد فلاسك ------------------
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is alive and running!"

@flask_app.route('/healthz')
def health_check():
    return 'OK', 200

# ------------------ دوال البوت الأساسية ------------------
def escape_markdown(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|}{!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def get_country_name(code: str) -> str:
    try:
        return pycountry.countries.get(alpha_2=code.upper()).name
    except Exception:
        return code

def extract_tiktok_info(username: str) -> dict:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
    url = f"https://www.tiktok.com/@{username.lstrip('@')}"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        return {"error": f"فشل الاتصال: {str(e)}"}

    html = response.text
    info = {
        'username': re.search(r'"uniqueId":"(.*?)"', html).group(1),
        'name': re.search(r'"nickname":"(.*?)"', html).group(1).encode().decode('unicode_escape'),
        'followers': int(re.search(r'"followerCount":(\d+)', html).group(1)),
        'likes': int(re.search(r'"heartCount":(\d+)', html).group(1)),
        'videos': int(re.search(r'"videoCount":(\d+)', html).group(1)),
        'verified': 'true' in re.search(r'"verified":(true|false)', html).group(),
        'bio': re.search(r'"signature":"(.*?)"', html).group(1).replace('\\n', '\n'),
        'profile_url': url
    }
    return info

# ------------------ معالجات الأوامر ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا! أرسل لي اسم مستخدم تيك توك 🎬")

async def handle_tiktok_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    if not username:
        return await update.message.reply_text("⚠️ الرجاء إدخال اسم مستخدم صحيح")
    
    processing_msg = await update.message.reply_text("⏳ جاري البحث...")
    
    try:
        user_info = extract_tiktok_info(username)
        if 'error' in user_info:
            return await processing_msg.edit_text(user_info['error'])
        
# في دالة handle_tiktok_request، عدل الأسطر التالية:
        response = (
            f"*👤 المستخدم:* {escape_markdown(user_info['username'])}\n"  # أضيف ) هنا ▼
            f"*📛 الاسم:* {escape_markdown(user_info['name'])}\n"        # وأيضاً هنا ▼
            f"*👥 المتابعون:* {user_info['followers']:,}\n"
            f"*❤️ الإعجابات:* {user_info['likes']:,}\n"
            f"*🎥 الفيديوهات:* {user_info['videos']:,}\n"
            f"*✅ موثق:* {'نعم' if user_info['verified'] else 'لا'}\n"
            f"*📝 البايو:*\n{escape_markdown(user_info['bio'])}"         # وأضف ) هنا إذا كان هناك دالة
        )
        
        await processing_msg.edit_text(response, parse_mode=ParseMode.MARKDOWN_V2)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await processing_msg.edit_text("❌ حدث خطأ غير متوقع، الرجاء المحاولة لاحقًا")

# ------------------ التشغيل الرئيسي ------------------
def setup_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # تسجيل المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tiktok_request))
    
    # إعداد الويب هوك
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        secret_token='YOUR_SECRET_TOKEN'
    )

if __name__ == '__main__':
    if not BOT_TOKEN:
        raise ValueError("لم يتم تعيين TELEGRAM_BOT_TOKEN")
    
    # تشغيل الخدمة
    flask_app.run(host='0.0.0.0', port=PORT)
    setup_bot()
