import logging
import io
import random
import string
import threading
import os
import qrcode
import requests
import yt_dlp
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# -------------------------------------------------------------
# 1. Flask Web Server (Render Free Web Service සදහා)
# -------------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Dilshan Utility Bot is Online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# -------------------------------------------------------------
# 2. Configurations & Logging
# -------------------------------------------------------------
BOT_TOKEN = "8937338859:AAGZj7zyITjjYtOMZ-M6iZzweMchb2zPDCA"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

FAQ_RESPONSES = {
    "පැය": "අපගේ සේවාවන් පැය 24 පුරාම සක්‍රියයි.",
    "ගාස්තු": "අපගේ මූලික සේවාවන් සියල්ලම සම්පූර්ණයෙන්ම නොමිලේ ලබාගත හැක.",
    "සහාය": "ඕනෑම තාක්ෂණික ගැටලුවක් සඳහා Admin සම්බන්ධ කරගන්න: @Dilshan",
    "contact": "ඔබට අපගේ සහාය කණ්ඩායම support@example.com හරහා සම්බන්ධ කරගත හැක."
}

# -------------------------------------------------------------
# 3. Bot Functions
# -------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 QR Code Generator", callback_data='menu_qr')],
        [InlineKeyboardButton("🔑 Password Generator", callback_data='menu_pass')],
        [InlineKeyboardButton("🎥 Media Downloader", callback_data='menu_down')],
        [InlineKeyboardButton("📰 Latest News Alerts", callback_data='menu_news')],
        [InlineKeyboardButton("💬 Customer Service (FAQ)", callback_data='menu_faq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"👋 ආයුබෝවන් {update.effective_user.first_name}!\n\n"
        "**Dilshan All-In-One Utility Bot** වෙත සාදරයෙන් පිළිගනිමු.\n"
        "පහත Menu එකෙන් ඔබට අවශ්‍ය සේවාව තෝරන්න:"
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'menu_qr':
        await query.message.reply_text("📌 QR Code එකක් සෑදීමට: `/qr [ඔබගේ Link එක හෝ Text එක]` ලෙස යවන්න.\n\nඋදා: `/qr https://google.com`", parse_mode='Markdown')
    elif query.data == 'menu_pass':
        await query.message.reply_text("🔑 ආරක්ෂිත Password එකක් ලබාගැනීමට: `/genpass [දිග]` ලෙස යවන්න.\n\nඋදා: `/genpass 12`", parse_mode='Markdown')
    elif query.data == 'menu_down':
        await query.message.reply_text("🎥 Video/Media Download කරගැනීමට TikTok/YouTube Link එක කෙලින්ම Chat එකට යවන්න.")
    elif query.data == 'menu_news':
        await get_news(update, context)
    elif query.data == 'menu_faq':
        await query.message.reply_text("💬 **Customer Support / FAQ**\n\nඔබගේ ප්‍රශ්නය Chat එකට ටයිප් කර යවන්න (උදා: 'පැය', 'ගාස්තු', 'සහාය').", parse_mode='Markdown')

async def generate_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ කරුණාකර Text එකක් හෝ Link එකක් ලබාදෙන්න.\nඋදා: `/qr https://example.com`", parse_mode='Markdown')
        return

    text_to_encode = " ".join(context.args)
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(text_to_encode)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    bio = io.BytesIO()
    bio.name = 'qrcode.png'
    img.save(bio, 'PNG')
    bio.seek(0)

    await update.message.reply_photo(photo=bio, caption=f"✅ මෙන්න ඔබගේ QR Code එක:\n`{text_to_encode}`", parse_mode='Markdown')

async def generate_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    length = 12
    if context.args:
        try:
            length = int(context.args[0])
            if length < 6 or length > 32:
                await update.message.reply_text("⚠️ මුරපදයේ දිග 6ත් 32ත් අතර විය යුතුය.")
                return
        except ValueError:
            await update.message.reply_text("⚠️ කරුණාකර නිවැරදි අංකයක් ඇතුළත් කරන්න.")
            return

    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choice(characters) for _ in range(length))
    await update.message.reply_text(f"🔐 **ඔබගේ සුරක්ෂිත මුරපදය:**\n`{password}`", parse_mode='Markdown')

async def media_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        await handle_faq(update, context)
        return

    status_msg = await update.message.reply_text("⏳ Media එක Process වෙමින් පවතී, කරුණාකර රැඳී සිටින්න...")

    ydl_opts = {
        'format': 'best[filesize<50M]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        with open(filename, 'rb') as video_file:
            await update.message.reply_video(video=video_file, caption=f"✅ **Downloaded:** {info.get('title', 'Media')}")
        
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Download කරගැනීමට නොහැකි විය.\nදෝෂය: {str(e)[:100]}")

async def get_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fallback_news = (
        "📰 **අලුත්ම පුවත් සහ Updates:**\n\n"
        "1. **Tech Update:** Python 3.12 තාක්ෂණික මෙවලම්.\n"
        "2. **Bot Alert:** ඔබේ Dilshan All-In-One Bot එක සාර්ථකව ක්‍රියාත්මක වේ!\n"
        "3. **Tip:** ඕනෑම වේලාවක /start ලබාදී ප්‍රධාන මෙනුව ලබාගත හැක."
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(fallback_news, parse_mode='Markdown')
    else:
        await update.message.reply_text(fallback_news, parse_mode='Markdown')

async def handle_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.lower()
    for key, response in FAQ_RESPONSES.items():
        if key in user_text:
            await update.message.reply_text(f"💬 **Auto-Response:**\n{response}", parse_mode='Markdown')
            return
    await update.message.reply_text("🤖 මට ඔබ යැවූ පණිවිඩය තේරුම් ගැනීමට නොහැකි විය.\nප්‍රධාන Menu එක ලබාගැනීමට `/start` යවන්න.")

# -------------------------------------------------------------
# 4. Main Execution
# -------------------------------------------------------------
def main():
    # Start Flask Server in background thread
    threading.Thread(target=run_flask, daemon=True).start()

    # Start Telegram Bot
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("qr", generate_qr))
    app_bot.add_handler(CommandHandler("genpass", generate_password))
    app_bot.add_handler(CommandHandler("news", get_news))

    app_bot.add_handler(CallbackQueryHandler(button_handler))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, media_downloader))

    print("🤖 Dilshan Bot සාර්ථකව Run වේ...")
    app_bot.run_polling()

if __name__ == '__main__':
    main()
