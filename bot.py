import requests
import re
import urllib.parse
import pycountry
import logging
import os
import time
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatAction
from flask import Flask

# --- إعدادات التسجيل ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- التوكن الخاص بالبوت ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# --- إعداد خادم الويب البسيط ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is alive and running!"

@flask_app.route('/healthz')
def health_check():
    return 'OK', 200

def run_webserver():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# --- نظام إبقاء النشاط ---
def keep_alive():
    while True:
        try:
            requests.get("https://d-b7ad.onrender.com/healthz")
            logger.info("تم إرسال طلب إبقاء النشاط")
        except Exception as e:
            logger.error(f"فشل في إبقاء النشاط: {e}")
        time.sleep(300)  # كل 5 دقائق

# --- دوال البوت ---
def escape_markdown_v2(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-.=|{}!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def get_country_name_from_code(code):
    try:
        country = pycountry.countries.get(alpha_2=code.upper())
        return country.name if country else code
    except Exception:
        return code

def get_tiktok_user_info(username):
    username = username.lstrip('@')
    url = f"https://www.tiktok.com/@{username}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        return {"error": f"فشل في جلب الصفحة: {str(e)}"}

    html_content = response.text
    info = {}

    # استخراج البيانات
    patterns = {
        'username': r'"uniqueId":"(.*?)"',
        'full_name': r'"nickname":"(.*?)"',
        'followers': r'"followerCount":(\d+)',
        'likes': r'"heartCount":(\d+)',
        'videos': r'"videoCount":(\d+)',
        'region': r'"region":"(.*?)"',
        'profile_picture': r'"avatarLarger":"(.*?)"',
        'bio': r'"signature":"(.*?)"',
        'verified': r'"verified":(true|false)',
        'privateAccount': r'"privateAccount":(true|false)'
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, html_content)
        if match:
            value = match.group(1)
            if key in ['followers', 'likes', 'videos']:
                info[key] = int(value)
            elif key in ['verified', 'privateAccount']:
                info[key] = value.lower() == 'true'
            else:
                info[key] = value.replace('\\n', '\n').replace('\\u002F', '/')
        else:
            info[key] = None

    # معالجة الروابط الاجتماعية
    social_links = []
    if info.get('bio'):
        # استخراج الروابط المباشرة
        links = re.findall(r'(https?://\S+)', info['bio'])
        social_links.extend([f"🔗 {link}" for link in links])

    info['social_links'] = social_links
    info['profile_url'] = url
    return info

def format_user_info_for_telegram(info: dict) -> str:
    if "error" in info:
        return f"❌ خطأ: {info['error']}"

    escaped_fields = {k: escape_markdown_v2(str(v)) for k, v in info.items() if v}
    
    message = [
        f"*👤 اسم المستخدم:* `{escaped_fields.get('username', 'N/A')}`",
        f"*📛 الاسم الكامل:* {escaped_fields.get('full_name', 'N/A')}",
        f"*✅ موثق:* {'نعم' if info.get('verified') else 'لا'}",
        f"*👥 المتابعون:* {escaped_fields.get('followers', 0):,}",
        f"*❤️ الإعجابات:* {escaped_fields.get('likes', 0):,}",
        f"*🎥 الفيديوهات:* {escaped_fields.get('videos', 0):,}",
        f"*🔗 الرابط:* [اضغط هنا]({info['profile_url']})"
    ]

    if info.get('social_links'):
        message.append("\n*📌 الروابط الاجتماعية:*")
        message.extend([f"‎• {link}" for link in info['social_links']])

    return "\n".join(message)

# --- معالجات الأوامر ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحبًا! أرسل لي اسم مستخدم تيك توك للحصول على معلوماته.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    msg = await update.message.reply_text("⏳ جاري البحث...")
    
    user_info = get_tiktok_user_info(username)
    response = format_user_info_for_telegram(user_info)
    
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=msg.message_id,
        text=response,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

# --- تشغيل البوت ---
def run_bot_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

# --- التشغيل الرئيسي ---
if __name__ == '__main__':
    # تشغيل خادم الويب
    web_thread = Thread(target=run_webserver, daemon=True)
    web_thread.start()

    # تشغيل نظام إبقاء النشاط
    keep_alive_thread = Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()

    # تشغيل البوت
    logger.info("🚀 بدء تشغيل البوت...")
    run_bot_app()
