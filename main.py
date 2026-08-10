#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║           FREXY AUTO LIKE - Premium Bot                         ║
║           Free Fire Auto Like Bot                               ║
║           POWERED BY FREXY                                      ║
╚══════════════════════════════════════════════════════════════════╝

Features:
- Group based auto-like setup
- Live updates in group
- Video hosting support
- Bangladesh Timezone
- Premium formatting
"""

import os
import json
import random
import asyncio
import logging
import aiohttp
import pytz
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from aiohttp import web

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION - EDIT THESE VALUES
# ═══════════════════════════════════════════════════════════════════

BOT_TOKEN = "8307741402:AAFp_k2nOq_hKheUOONX6e0kCcmTL6AstxY"
ADMIN_ID = 6417430059

# API Configuration
API_BASE = "https://like-api-frexy.up.railway.app"

# Allowed Groups (Bot will work in these groups)
ALLOWED_GROUPS = [
    -1003982689528,  # Your main group
]

# Video Hosting URLs (Upload your videos here and put the links)
# You can use: imgur.com, gdrive, or any video hosting
VIDEOS = {
    "success": "https://your-video-host.com/success.mp4",
    "zero_likes": "https://your-video-host.com/zero.mp4",
    "error": "https://your-video-host.com/error.mp4",
    "auto_like": "https://your-video-host.com/auto.mp4",
    "target_like": "https://your-video-host.com/target.mp4"
}

# Bangladesh Timezone
BANGLADESH_TZ = pytz.timezone('Asia/Dhaka')

# Schedule times (BD Time)
RESET_HOUR = 4
RESET_MINUTE = 0
AUTO_LIKE_HOUR = 4
AUTO_LIKE_MINUTE = 50
JWT_CALL_TIMES = [(4, 10), (4, 11), (4, 12)]

# Valid regions
VALID_REGIONS = ["BD", "IND", "BR", "US", "SAC", "NA", "RU"]

# ═══════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# DATA MANAGER
# ═══════════════════════════════════════════════════════════════════

DATA_DIR = "bot_data"
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "auto_like": os.path.join(DATA_DIR, "auto_like.json"),
    "target_like": os.path.join(DATA_DIR, "target_like.json"),
    "daily_usage": os.path.join(DATA_DIR, "daily_usage.json"),
    "unlimited": os.path.join(DATA_DIR, "unlimited.json"),
    "broadcast_users": os.path.join(DATA_DIR, "broadcast_users.json"),
    "group_settings": os.path.join(DATA_DIR, "group_settings.json"),
}


def load_data(key):
    path = FILES.get(key)
    if not path:
        return {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_data(key, data):
    path = FILES.get(key)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_bd_time():
    return datetime.now(BANGLADESH_TZ)


def get_bd_date():
    return get_bd_time().strftime("%Y-%m-%d")


def format_quote(text):
    """Premium quote formatting"""
    lines = text.split("\n")
    max_len = max([len(line.strip()) for line in lines if line.strip()], default=40)
    max_len = max(max_len, 40)
    border = "═" * (max_len + 4)
    
    formatted = f"╔{border}╗\n"
    for line in lines:
        if line.strip():
            padded = line.strip().ljust(max_len)
            formatted += f"║ {padded} ║\n"
        else:
            formatted += f"║ {' ' * max_len} ║\n"
    formatted += f"╚{border}╝"
    return formatted


def is_admin(user_id):
    return user_id == ADMIN_ID


def is_group_allowed(chat_id):
    return chat_id in ALLOWED_GROUPS


def add_broadcast_user(user_id):
    users = load_data("broadcast_users")
    users[str(user_id)] = True
    save_data("broadcast_users", users)


def get_broadcast_users():
    users = load_data("broadcast_users")
    return [int(uid) for uid in users.keys()]


# ═══════════════════════════════════════════════════════════════════
# AUTO-LIKE & TARGET-LIKE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def add_auto_like(uid, region, days, group_id):
    """Add UID to auto-like list with group info"""
    auto = load_data("auto_like")
    auto[str(uid)] = {
        "region": region.upper(),
        "days_left": int(days),
        "total_days": int(days),
        "likes_sent": 0,
        "group_id": group_id,
        "added_at": get_bd_time().isoformat(),
        "status": "Active"
    }
    save_data("auto_like", auto)


def remove_auto_like(uid):
    auto = load_data("auto_like")
    if str(uid) in auto:
        del auto[str(uid)]
        save_data("auto_like", auto)


def get_auto_like_list():
    return load_data("auto_like")


def add_target_like(uid, region, target_limit, group_id):
    """Add UID with target likes limit"""
    targets = load_data("target_like")
    targets[str(uid)] = {
        "region": region.upper(),
        "target_limit": int(target_limit),
        "likes_sent": 0,
        "group_id": group_id,
        "added_at": get_bd_time().isoformat(),
        "status": "Active"
    }
    save_data("target_like", targets)


def remove_target_like(uid):
    targets = load_data("target_like")
    if str(uid) in targets:
        del targets[str(uid)]
        save_data("target_like", targets)


def add_unlimited(uid, region):
    unlimited = load_data("unlimited")
    unlimited[str(uid)] = {
        "region": region.upper(),
        "added_at": get_bd_time().isoformat()
    }
    save_data("unlimited", unlimited)


def remove_unlimited(uid):
    unlimited = load_data("unlimited")
    if str(uid) in unlimited:
        del unlimited[str(uid)]
        save_data("unlimited", unlimited)


def is_unlimited(uid):
    unlimited = load_data("unlimited")
    return str(uid) in unlimited


def can_use_like(user_id):
    if is_admin(user_id):
        return True
    usage = load_data("daily_usage")
    uid = str(user_id)
    today = get_bd_date()
    if uid not in usage:
        return True
    return usage[uid].get("date") != today


def mark_like_used(user_id):
    if is_admin(user_id):
        return
    usage = load_data("daily_usage")
    uid = str(user_id)
    usage[uid] = {"date": get_bd_date(), "count": 1}
    save_data("daily_usage", usage)


def reset_daily_usage():
    save_data("daily_usage", {})
    logger.info("Daily usage reset at 4:00 AM BD Time")


# ═══════════════════════════════════════════════════════════════════
# API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def send_like_api(uid, region, is_jwt_call=False):
    try:
        if is_jwt_call:
            url = f"{API_BASE.rstrip('/')}/jwt"
        else:
            url = f"{API_BASE.rstrip('/')}/like"
        
        params = {
            "uid": str(uid),
            "server_name": region.upper(),
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                if resp.status != 200:
                    return {"error": "API is currently not working.", "status": 0}
                data = await resp.json()
                return data
    except Exception as e:
        logger.error(f"API Error: {e}")
        return {"error": "API is currently under maintenance.", "status": 0}


# ═══════════════════════════════════════════════════════════════════
# COMMAND HANDLERS - GROUP BASED
# ═══════════════════════════════════════════════════════════════════

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    add_broadcast_user(user.id)

    if chat.type == "private" and not is_admin(user.id):
        await update.message.reply_text(
            "❌ ACCESS DENIED!\n\nOnly admin can use in private.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if chat.type in ["group", "supergroup"] and not is_group_allowed(chat.id):
        await update.message.reply_text(
            "❌ ACCESS DENIED!\n\nThis bot is not authorized in this group.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    text = (
        "✨ WELCOME TO FREXY AUTO LIKE ✨\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  🎮 Premium Free Fire Bot\n"
        "  ⚡ Powered by FREXY\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  📌 Admin Commands:\n"
        "  /autolike <region> <uid> <days>\n"
        "  /tlike <region> <uid> <target>\n"
        "  /autolist - View auto likes\n"
        "  /tlist - View target likes\n"
        "  /stats - Bot statistics\n\n"
        "  📌 User Commands:\n"
        "  /like <region> <uid>\n\n"
        "  ⚡ POWERED BY FREXY"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type == "private" and not is_admin(user.id):
        await update.message.reply_text(
            "❌ ACCESS DENIED!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if chat.type in ["group", "supergroup"] and not is_group_allowed(chat.id):
        await update.message.reply_text(
            "❌ ACCESS DENIED!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if is_admin(user.id):
        text = (
            "🔐 ADMIN COMMANDS 🔐\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  /autolike <region> <uid> <days>\n"
            "  → Add auto-like UID\n\n"
            "  /removeauto <uid>\n"
            "  → Remove auto-like\n\n"
            "  /autolist\n"
            "  → View auto-like list\n\n"
            "  /tlike <region> <uid> <target>\n"
            "  → Add target-like\n\n"
            "  /removetlike <uid>\n"
            "  → Remove target-like\n\n"
            "  /tlist\n"
            "  → View target-like list\n\n"
            "  /unlimit <uid> <region>\n"
            "  → Unlimited likes\n\n"
            "  /removeunlimit <uid>\n"
            "  → Remove unlimited\n\n"
            "  /broadcast <message>\n"
            "  → Broadcast to users\n\n"
            "  /stats\n"
            "  → Bot statistics\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ⚡ POWERED BY FREXY"
        )
    else:
        text = (
            "🎮 USER COMMANDS 🎮\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  /like <region> <uid>\n"
            "  → Get 1 like\n\n"
            "  Example:\n"
            "  /like BD 123456789\n\n"
            "  🌍 Valid Regions:\n"
            "  BD, IND, BR, US, SAC, NA, RU\n\n"
            "  ⚠️ Rules:\n"
            "  • 1 like per day\n"
            "  • Resets at 4:00 AM\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ⚡ POWERED BY FREXY"
        )
    
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def like_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User command: /like <region> <uid>"""
    user = update.effective_user
    chat = update.effective_chat
    add_broadcast_user(user.id)

    if chat.type == "private" and not is_admin(user.id):
        await update.message.reply_text(
            "❌ ACCESS DENIED!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if chat.type in ["group", "supergroup"] and not is_group_allowed(chat.id):
        await update.message.reply_text(
            "❌ ACCESS DENIED!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if len(context.args) < 2:
        text = (
            "❌ INVALID FORMAT ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ✅ Correct: /like <region> <uid>\n"
            "  📌 Example: /like BD 123456789\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  🌍 Regions: BD, IND, BR, US, SAC, NA, RU"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    region = context.args[0].upper()
    uid = context.args[1]

    if region not in VALID_REGIONS:
        text = f"❌ Invalid Region! Available: {', '.join(VALID_REGIONS)}"
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not uid.isdigit():
        text = "❌ UID must be numbers only!"
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Check if UID in auto or target list
    auto_list = get_auto_like_list()
    targets = load_data("target_like")

    if str(uid) in auto_list:
        days_left = auto_list[str(uid)].get("days_left", 0)
        text = (
            f"⚠️ UID HAS ACTIVE AUTO-LIKE ⚠️\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  🆔 UID: {uid}\n"
            f"  📅 Days Left: {days_left}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  💡 Auto-likes delivered daily at 4:50 AM"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if str(uid) in targets:
        likes_sent = targets[str(uid)].get("likes_sent", 0)
        target_limit = targets[str(uid)].get("target_limit", 0)
        text = (
            f"⚠️ UID HAS ACTIVE TARGET-LIKE ⚠️\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  🆔 UID: {uid}\n"
            f"  📈 Progress: {likes_sent}/{target_limit}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  💡 Target-likes delivered daily at 4:50 AM"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Check daily limit
    if not is_unlimited(uid) and not can_use_like(user.id):
        text = (
            "⏳ DAILY LIMIT REACHED ⏳\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ❌ You used your daily like!\n"
            "  🔄 Resets at 4:00 AM BD Time\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  💡 Try again tomorrow!"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Send like
    msg = await update.message.reply_text(
        format_quote("⏳ PROCESSING...\n\nSending like to UID: " + uid),
        parse_mode=ParseMode.MARKDOWN
    )

    result = await send_like_api(uid, region)

    if result.get("error"):
        error_text = (
            f"❌ ERROR ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  ❌ {result['error'][:35]}\n"
            f"  🆔 UID: {uid}\n"
            f"  🌍 Region: {region}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ⚡ POWERED BY FREXY"
        )
        try:
            await context.bot.send_video(
                chat_id=chat.id,
                video=VIDEOS["error"],
                caption=format_quote(error_text),
                parse_mode=ParseMode.MARKDOWN
            )
            await msg.delete()
        except Exception as e:
            await msg.edit_text(format_quote(error_text), parse_mode=ParseMode.MARKDOWN)
        return

    if result.get("status") in [1, 2]:
        player_name = result.get("PlayerNickname", "Unknown")
        likes_before = result.get("LikesbeforeCommand", "N/A")
        likes_after = result.get("LikesafterCommand", "N/A")
        likes_given = result.get("LikesGivenByAPI", 0)
        
        likes_before_int = int(likes_before) if str(likes_before).isdigit() else 0
        video_url = VIDEOS["zero_likes"] if likes_before_int == 0 else VIDEOS["success"]

        success_text = (
            f"✅ LIKE SENT ✅\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  👤 Name: {player_name}\n"
            f"  🌍 Region: {region}\n"
            f"  🆔 UID: {uid}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  📉 Before: {likes_before}\n"
            f"  📈 After: {likes_after}\n"
            f"  ➕ Given: {likes_given}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  ⏰ {get_bd_time().strftime('%I:%M %p')}\n"
            "  ⚡ POWERED BY FREXY"
        )

        if not is_unlimited(uid):
            mark_like_used(user.id)

        try:
            await context.bot.send_video(
                chat_id=chat.id,
                video=video_url,
                caption=format_quote(success_text),
                parse_mode=ParseMode.MARKDOWN
            )
            await msg.delete()
        except Exception as e:
            await msg.edit_text(format_quote(success_text), parse_mode=ParseMode.MARKDOWN)
    else:
        error_text = (
            f"❌ FAILED ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  ❌ Could not send likes\n"
            f"  🆔 UID: {uid}\n"
            f"  🌍 Region: {region}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ⚡ POWERED BY FREXY"
        )
        try:
            await context.bot.send_video(
                chat_id=chat.id,
                video=VIDEOS["error"],
                caption=format_quote(error_text),
                parse_mode=ParseMode.MARKDOWN
            )
            await msg.delete()
        except Exception as e:
            await msg.edit_text(format_quote(error_text), parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════
# ADMIN COMMANDS - GROUP BASED
# ═══════════════════════════════════════════════════════════════════

async def autolike_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/autolike <region> <uid> <days> - Add auto-like from group"""
    user = update.effective_user
    chat = update.effective_chat

    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ You are not authorized!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if chat.type in ["group", "supergroup"] and not is_group_allowed(chat.id):
        await update.message.reply_text(
            "❌ Group not authorized!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if len(context.args) < 3:
        text = (
            "❌ INVALID FORMAT ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ✅ /autolike <region> <uid> <days>\n"
            "  📌 Example: /autolike BD 123456789 30\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  🌍 Regions: BD, IND, BR, US, SAC, NA, RU"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    region = context.args[0].upper()
    uid = context.args[1]
    days = context.args[2]

    if region not in VALID_REGIONS:
        await update.message.reply_text(
            f"❌ Invalid Region! Available: {', '.join(VALID_REGIONS)}",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not uid.isdigit() or not days.isdigit():
        await update.message.reply_text(
            "❌ UID and Days must be numbers!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Add auto-like with group info
    add_auto_like(uid, region, days, chat.id)
    
    text = (
        f"✅ AUTO-LIKE ADDED ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🆔 UID: {uid}\n"
        f"  🌍 Region: {region}\n"
        f"  📅 Duration: {days} Days\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ⏰ Daily at 4:50 AM (BD Time)\n"
        "  📌 5 likes per day\n"
        "  📢 Updates will be posted here\n\n"
        "  ⚡ POWERED BY FREXY"
    )
    
    # Send video with the announcement
    try:
        await context.bot.send_video(
            chat_id=chat.id,
            video=VIDEOS["auto_like"],
            caption=format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )


async def removeauto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ You are not authorized!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not context.args:
        text = "✅ /removeauto <uid>\nExample: /removeauto 123456789"
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    uid = context.args[0]
    remove_auto_like(uid)
    
    text = (
        f"✅ AUTO-LIKE REMOVED ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🆔 UID: {uid}\n"
        "  ✅ Removed from auto-like list\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ⚡ POWERED BY FREXY"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def autolist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ You are not authorized!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    auto_list = get_auto_like_list()
    if not auto_list:
        text = "📋 AUTO-LIKE LIST 📋\n\nList is empty!"
    else:
        lines = ["📋 AUTO-LIKE LIST 📋", "", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
        for uid, info in list(auto_list.items())[:20]:
            region = info.get('region', 'N/A')
            days_left = info.get('days_left', 0)
            likes_sent = info.get('likes_sent', 0)
            status = info.get('status', 'Active')
            lines.append(f"  🆔 {uid} | 🌍 {region} | 📅 {days_left}d | 📊 {likes_sent}")
        if len(auto_list) > 20:
            lines.append(f"  ... and {len(auto_list)-20} more")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("  ⚡ POWERED BY FREXY")
        text = "\n".join(lines)

    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def tlike_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tlike <region> <uid> <target> - Add target-like from group"""
    user = update.effective_user
    chat = update.effective_chat

    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ You are not authorized!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if chat.type in ["group", "supergroup"] and not is_group_allowed(chat.id):
        await update.message.reply_text(
            "❌ Group not authorized!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if len(context.args) < 3:
        text = (
            "❌ INVALID FORMAT ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ✅ /tlike <region> <uid> <target>\n"
            "  📌 Example: /tlike BD 123456789 100\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  🎯 Target = Total likes needed"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    region = context.args[0].upper()
    uid = context.args[1]
    target_limit = context.args[2]

    if region not in VALID_REGIONS:
        await update.message.reply_text(
            f"❌ Invalid Region! Available: {', '.join(VALID_REGIONS)}",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not uid.isdigit() or not target_limit.isdigit():
        await update.message.reply_text(
            "❌ UID and Target must be numbers!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    add_target_like(uid, region, target_limit, chat.id)
    
    text = (
        f"✅ TARGET-LIKE ADDED ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🆔 UID: {uid}\n"
        f"  🌍 Region: {region}\n"
        f"  🎯 Target: {target_limit} Likes\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ⏰ Daily at 4:50 AM (BD Time)\n"
        "  📌 5 likes per day\n"
        "  🔄 Stops when target reached\n"
        "  📢 Updates will be posted here\n\n"
        "  ⚡ POWERED BY FREXY"
    )
    
    try:
        await context.bot.send_video(
            chat_id=chat.id,
            video=VIDEOS["target_like"],
            caption=format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )


async def removetlike_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ You are not authorized!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not context.args:
        text = "✅ /removetlike <uid>\nExample: /removetlike 123456789"
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    uid = context.args[0]
    remove_target_like(uid)
    
    text = (
        f"✅ TARGET-LIKE REMOVED ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🆔 UID: {uid}\n"
        "  ✅ Removed from target-like list\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ⚡ POWERED BY FREXY"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def tlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ You are not authorized!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    targets = load_data("target_like")
    if not targets:
        text = "📋 TARGET-LIKE LIST 📋\n\nList is empty!"
    else:
        lines = ["📋 TARGET-LIKE LIST 📋", "", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
        for uid, info in list(targets.items())[:20]:
            region = info.get('region', 'N/A')
            likes_sent = info.get('likes_sent', 0)
            target_limit = info.get('target_limit', 0)
            lines.append(f"  🆔 {uid} | 🌍 {region} | 🎯 {likes_sent}/{target_limit}")
        if len(targets) > 20:
            lines.append(f"  ... and {len(targets)-20} more")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("  ⚡ POWERED BY FREXY")
        text = "\n".join(lines)

    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def unlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ You are not authorized!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if len(context.args) < 2:
        text = "✅ /unlimit <uid> <region>\nExample: /unlimit 123456789 BD"
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    uid = context.args[0]
    region = context.args[1].upper()
    add_unlimited(uid, region)
    
    text = (
        f"✅ UNLIMITED ADDED ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🆔 UID: {uid}\n"
        f"  🌍 Region: {region}\n"
        "  ♾️ No daily limit!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ⚡ POWERED BY FREXY"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def removeunlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ You are not authorized!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not context.args:
        text = "✅ /removeunlimit <uid>\nExample: /removeunlimit 123456789"
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    uid = context.args[0]
    remove_unlimited(uid)
    
    text = (
        f"✅ UNLIMITED REMOVED ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🆔 UID: {uid}\n"
        "  ✅ Removed from unlimited\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ⚡ POWERED BY FREXY"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ You are not authorized!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not context.args:
        text = "✅ /broadcast <message>"
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    message = " ".join(context.args)
    users = get_broadcast_users()
    sent = 0
    failed = 0

    status_msg = await update.message.reply_text(
        "📢 Broadcasting...",
        parse_mode=ParseMode.MARKDOWN
    )

    for uid in users:
        try:
            broadcast_text = (
                f"📢 ADMIN ANNOUNCEMENT 📢\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  {message}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "  ⚡ POWERED BY FREXY"
            )
            await context.bot.send_message(
                uid,
                format_quote(broadcast_text),
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1

    text = (
        f"✅ BROADCAST COMPLETE ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  ✅ Sent: {sent}\n"
        f"  ❌ Failed: {failed}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ⚡ POWERED BY FREXY"
    )
    await status_msg.edit_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ You are not authorized!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    users = load_data("broadcast_users")
    auto_list = get_auto_like_list()
    targets = load_data("target_like")
    unlimited = load_data("unlimited")
    usage = load_data("daily_usage")

    text = (
        f"📊 BOT STATISTICS 📊\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  👥 Users: {len(users)}\n"
        f"  📊 Today's Active: {len(usage)}\n"
        f"  🔄 Auto-Like UIDs: {len(auto_list)}\n"
        f"  🎯 Target-Like UIDs: {len(targets)}\n"
        f"  ♾️ Unlimited UIDs: {len(unlimited)}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  ⏰ BD Time: {get_bd_time().strftime('%I:%M %p')}\n"
        f"  📅 Date: {get_bd_date()}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ⚡ POWERED BY FREXY"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


# ═══════════════════════════════════════════════════════════════════
# SCHEDULER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def run_jwt_pre_calls(application):
    """Send JWT calls at 4:10, 4:11, 4:12 AM"""
    while True:
        bd_now = get_bd_time()
        
        next_call_time = None
        for hour, minute in JWT_CALL_TIMES:
            call_time = bd_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if call_time > bd_now:
                next_call_time = call_time
                break
        
        if not next_call_time:
            hour, minute = JWT_CALL_TIMES[0]
            next_call_time = bd_now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=1)
        
        wait_seconds = (next_call_time - bd_now).total_seconds()
        logger.info(f"Next JWT call at {next_call_time.strftime('%H:%M')} BD Time")
        await asyncio.sleep(wait_seconds)

        current_time = get_bd_time()
        call_index = -1
        for idx, (h, m) in enumerate(JWT_CALL_TIMES):
            if h == current_time.hour and m == current_time.minute:
                call_index = idx
                break
        
        if call_index >= 0:
            try:
                result = await send_like_api("999999999", "BD", is_jwt_call=True)
                logger.info(f"JWT call #{call_index + 1}: {result}")
                
                status_text = (
                    f"📡 JWT CALL #{call_index + 1}\n\n"
                    f"Status: {'✅ Success' if result.get('status') in [1,2] else '❌ Failed'}\n"
                    f"Time: {get_bd_time().strftime('%I:%M %p')} BD"
                )
                await application.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=format_quote(status_text),
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"JWT call failed: {e}")


async def run_daily_reset(application):
    """Reset daily usage at 4:00 AM"""
    while True:
        bd_now = get_bd_time()
        target = bd_now.replace(hour=RESET_HOUR, minute=RESET_MINUTE, second=0, microsecond=0)
        if target <= bd_now:
            target += timedelta(days=1)
        await asyncio.sleep((target - bd_now).total_seconds())
        reset_daily_usage()


async def run_auto_like(application):
    """Send auto likes and target likes at 4:50 AM"""
    while True:
        bd_now = get_bd_time()
        target = bd_now.replace(hour=AUTO_LIKE_HOUR, minute=AUTO_LIKE_MINUTE, second=0, microsecond=0)
        if target <= bd_now:
            target += timedelta(days=1)
        await asyncio.sleep((target - bd_now).total_seconds())

        logger.info("Starting auto-like run at 4:50 AM BD Time")

        # Process Auto Likes
        auto_list = get_auto_like_list()
        updated_auto_list = {}
        
        for uid, info in list(auto_list.items()):
            days_left = info.get("days_left", 0)
            if days_left <= 0:
                continue

            region = info.get("region", "BD")
            group_id = info.get("group_id")
            
            results = await send_bulk_likes(uid, region, count=5)
            success_count = sum(1 for r in results if r.get("status") in [1, 2])
            
            new_days = days_left - 1
            if new_days > 0:
                info["days_left"] = new_days
                info["likes_sent"] = info.get("likes_sent", 0) + success_count
                updated_auto_list[uid] = info
                status_text = "✅ Active"
            else:
                status_text = "⏰ Expired"
                logger.info(f"Auto-like expired for UID: {uid}")

            # Send update to group
            if group_id:
                try:
                    if success_count > 0:
                        video_url = VIDEOS["success"]
                        first_result = results[0] if results else {}
                        likes_before = first_result.get("LikesbeforeCommand", "N/A")
                        likes_after = first_result.get("LikesafterCommand", "N/A")
                    else:
                        video_url = VIDEOS["error"]
                        likes_before = "N/A"
                        likes_after = "N/A"
                    
                    update_text = (
                        f"🔄 AUTO-LIKE UPDATE 🔄\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"  🆔 UID: {uid}\n"
                        f"  🌍 Region: {region}\n"
                        f"  📊 Sent: {success_count}/5\n"
                        f"  📉 Before: {likes_before}\n"
                        f"  📈 After: {likes_after}\n"
                        f"  📅 Days Left: {new_days}\n"
                        f"  📌 Status: {status_text}\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"  ⏰ {get_bd_time().strftime('%I:%M %p')}\n"
                        "  ⚡ POWERED BY FREXY"
                    )
                    
                    await application.bot.send_video(
                        chat_id=group_id,
                        video=video_url,
                        caption=format_quote(update_text),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Failed to send auto-like update: {e}")
            
            await asyncio.sleep(1)
        
        save_data("auto_like", updated_auto_list)

        # Process Target Likes
        targets = load_data("target_like")
        updated_targets = {}
        
        for uid, info in list(targets.items()):
            target_limit = info.get("target_limit", 0)
            likes_sent = info.get("likes_sent", 0)
            group_id = info.get("group_id")

            if likes_sent >= target_limit:
                continue

            region = info.get("region", "BD")
            
            results = await send_bulk_likes(uid, region, count=5)
            success_count = sum(1 for r in results if r.get("status") in [1, 2])
            
            if success_count > 0:
                likes_sent += success_count
                status_text = "✅ Progress"
            else:
                status_text = "❌ Failed"

            if likes_sent < target_limit:
                info["likes_sent"] = likes_sent
                updated_targets[uid] = info
            else:
                status_text = "✅ Complete"
                logger.info(f"Target limit reached for UID: {uid}")

            # Send update to group
            if group_id:
                try:
                    if success_count > 0:
                        video_url = VIDEOS["target_like"]
                        first_result = results[0] if results else {}
                        likes_before = first_result.get("LikesbeforeCommand", "N/A")
                        likes_after = first_result.get("LikesafterCommand", "N/A")
                    else:
                        video_url = VIDEOS["error"]
                        likes_before = "N/A"
                        likes_after = "N/A"
                    
                    update_text = (
                        f"🎯 TARGET-LIKE UPDATE 🎯\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"  🆔 UID: {uid}\n"
                        f"  🌍 Region: {region}\n"
                        f"  📊 Sent: {success_count}/5\n"
                        f"  📉 Before: {likes_before}\n"
                        f"  📈 After: {likes_after}\n"
                        f"  🎯 Progress: {likes_sent}/{target_limit}\n"
                        f"  📌 Status: {status_text}\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"  ⏰ {get_bd_time().strftime('%I:%M %p')}\n"
                        "  ⚡ POWERED BY FREXY"
                    )
                    
                    await application.bot.send_video(
                        chat_id=group_id,
                        video=video_url,
                        caption=format_quote(update_text),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Failed to send target-like update: {e}")
            
            await asyncio.sleep(1)
        
        save_data("target_like", updated_targets)


async def send_bulk_likes(uid, region, count=5):
    """Send multiple likes"""
    results = []
    for i in range(count):
        result = await send_like_api(uid, region)
        results.append(result)
        await asyncio.sleep(1)
    return results


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

async def main_async():
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("like", like_cmd))
    application.add_handler(CommandHandler("autolike", autolike_cmd))
    application.add_handler(CommandHandler("removeauto", removeauto_cmd))
    application.add_handler(CommandHandler("autolist", autolist_cmd))
    application.add_handler(CommandHandler("tlike", tlike_cmd))
    application.add_handler(CommandHandler("removetlike", removetlike_cmd))
    application.add_handler(CommandHandler("tlist", tlist_cmd))
    application.add_handler(CommandHandler("unlimit", unlimit_cmd))
    application.add_handler(CommandHandler("removeunlimit", removeunlimit_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))

    # Start schedulers
    asyncio.create_task(run_jwt_pre_calls(application))
    asyncio.create_task(run_daily_reset(application))
    asyncio.create_task(run_auto_like(application))

    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("🤖 Bot started successfully!")

    # Web server for health check
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 Web server on port {port}")

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def main():
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║           FREXY AUTO LIKE - Premium Bot                         ║
    ║           Free Fire Auto Like Bot                               ║
    ║           POWERED BY FREXY                                      ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
