import telebot
import requests
import json
import time
import pytz
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from threading import Thread

# --- FLASK SERVER FOR RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    # Render সাধারণত 'PORT' এনভায়রনমেন্ট ভেরিয়েবল প্রদান করে
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- CONFIGURATION ---
TOKEN = '8307741402:AAEPJN82CkJund-ER1tqe5oMMcZ8RnYkdw4' # এখানে আপনার টোকেন দিন
ADMIN_IDS = [6417430059]  # আপনার আইডি দিন
GROUP_ID = -1003982689528 # আপনার গ্রুপ আইডি দিন
API_URL = "https://like-api-frexy.onrender.com/like"
JWT_URL = "https://like-api-frexy.onrender.com/jwt"
DB_FILE = 'database.json'

bot = telebot.TeleBot(TOKEN)
bd_tz = pytz.timezone('Asia/Dhaka')

# ডাটাবেস লোড এবং সেভ
def load_db():
    try:
        if not os.path.exists(DB_FILE):
            with open(DB_FILE, 'w') as f:
                json.dump([], f)
            return []
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# এডমিন চেক ফাংশন
def is_admin(message):
    return message.from_user.id in ADMIN_IDS

# গ্রুপ অথবা এডমিনের পার্সোনাল চ্যাট চেক
def is_allowed_chat(message):
    if message.chat.type == 'private':
        return is_admin(message)
    return message.chat.id == GROUP_ID

# লাইক পাঠানোর ফাংশন
def send_like_request(uid, region):
    try:
        response = requests.get(f"{API_URL}?uid={uid}&server_name={region}", timeout=20)
        return response.json()
    except:
        return None

# ফরম্যাটেড সাকসেস মেসেজ
def get_success_msg(data, uid, region):
    name = data.get('player_name', '—͞INFERNOㅤ々')
    before = data.get('before_likes', '0')
    after = data.get('after_likes', '0')
    try:
        sent = int(after) - int(before)
    except:
        sent = 21 # Default

    return f"""╭━━━━━━━━━━━━━━━━✦
│✅  ᴀᴜᴛᴏ ʟɪᴋᴇ sᴇɴᴅ sᴜᴄᴄᴇss
╰━━━━━━━━━━━━━━━━✦
╭━━━ 🌸 ᴘʟᴀʏᴇʀ ɪɴꜰᴏ ━━━✦
┃👤 𝐍𝐀𝐌𝐄 : {name}
┃🆔 𝐔𝐈𝐃        : {uid}
┃🌍 𝐑𝐄𝐆𝐈𝐎𝐍    : {region}
╰━━━━━━━━━━━━━━━━✦

╭━━ 💝 ʟɪᴋᴇ ᴅᴇᴛᴀɪʟs ━━━✦
┃♑️ 𝐁𝐄𝐅𝐎𝐑𝐄      : {before}
┃💟 𝐀𝐅𝐓𝐄𝐑        : {after}
┃➕ 𝐒𝐄𝐍𝐓           : +{sent}
╰━━━━━━━━━━━━━━━━✦
╭━━━━━━━━━━━━━━━━✦
│✨ ᴘᴏᴡᴇʀᴇᴅ ʙʏ @Frexy1only
╰━━━━━━━━━━━━━━━━✦"""

# কমান্ড হ্যান্ডলারসমূহ
@bot.message_handler(commands=['autolike'])
def autolike(message):
    if not is_allowed_chat(message) or not is_admin(message): return
    try:
        parts = message.text.split()
        region = parts[1].upper()
        uid = parts[2]
        
        db = load_db()
        if any(item['uid'] == uid for item in db):
            bot.reply_to(message, "❌ এই UID আগে থেকেই লিস্টে আছে।")
            return
            
        now = datetime.now(bd_tz).strftime("%I:%M %p")
        db.append({"uid": uid, "region": region, "time": now})
        save_db(db)
        
        # প্রথমবার সাথে সাথে লাইক
        res = send_like_request(uid, region)
        if res:
            bot.send_message(message.chat.id, get_success_msg(res, uid, region))
        else:
            bot.reply_to(message, "✅ লিস্টে এড হয়েছে।")
    except:
        bot.reply_to(message, "❌ ব্যবহার: /autolike (region) (uid) day")

@bot.message_handler(commands=['deletelike'])
def deletelike(message):
    if not is_allowed_chat(message) or not is_admin(message): return
    try:
        uid = message.text.split()[1]
        db = load_db()
        new_db = [item for item in db if item['uid'] != uid]
        save_db(new_db)
        bot.reply_to(message, f"✅ UID: {uid} ডিলিট করা হয়েছে।")
    except:
        bot.reply_to(message, "❌ ব্যবহার: /deletelike (uid)")

@bot.message_handler(commands=['autolist'])
def autolist(message):
    if not is_allowed_chat(message) or not is_admin(message): return
    db = load_db()
    if not db:
        bot.reply_to(message, "📭 লিস্ট খালি।")
        return
        
    res_msg = "Auto Like List  🌄\n━━━━━━━━━━━━━━━━\n"
    for i, item in enumerate(db, 1):
        res_msg += f"#{i}\n💚 UID : {item['uid']} \n🌍 REGION : {item['region']}\n🕜 TIME : {item['time']}\n━━━━━━━━━━━━━━━━\n"
    bot.send_message(message.chat.id, res_msg)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    if not is_allowed_chat(message): return
    bot.reply_to(message, "/autolike, /deletelike, /autolist, /targetlike")

# --- Scheduler Jobs ---
def daily_jwt_call():
    for _ in range(3):
        try: requests.get(JWT_URL, timeout=10)
        except: pass
        time.sleep(2)

def daily_auto_like():
    db = load_db()
    for item in db:
        res = send_like_request(item['uid'], item['region'])
        if res:
            try: bot.send_message(GROUP_ID, get_success_msg(res, item['uid'], item['region']))
            except: pass
        time.sleep(60)

# Scheduler Setup
scheduler = BackgroundScheduler(timezone=bd_tz)
scheduler.add_job(daily_jwt_call, 'cron', hour=4, minute=10)
scheduler.add_job(daily_auto_like, 'cron', hour=5, minute=0)
scheduler.start()

if __name__ == '__main__':
    # Flask সার্ভার চালু করা (রেন্ডারের পোর্টের জন্য)
    keep_alive()
    print("Bot is starting...")
    # বোট পোলিং শুরু
    bot.infinity_polling()
