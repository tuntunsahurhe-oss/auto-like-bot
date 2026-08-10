#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║           FREXY AUTO LIKE - Premium Bot                         ║
║           Free Fire Auto Like Bot                               ║
║           POWERED BY FREXY                                      ║
╚══════════════════════════════════════════════════════════════════╝

Features:
- Bangladesh Timezone (UTC+6)
- JWT pre-calls at 4:10, 4:11, 4:12 AM
- Auto-like at 4:50 AM daily (5 likes per UID)
- 3 videos: success, zero-likes, error
- Single group restriction
- Premium quote formatting with before/after likes
- Target likes with progress tracking
- Region must be provided BEFORE UID in all commands
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

BOT_TOKEN = "8535184265:AAEsBNmUY1I6GBuQd33yAGjCW-Cmk1WPWJ4"  # Get from @BotFather
ADMIN_ID = 6417430059  # Your Telegram numeric ID

# API Configuration
API_BASE = "https://like-api-frexy.up.railway.app"

# ALLOWED GROUP - Bot will ONLY work in this group
ALLOWED_GROUP_ID = -1003765179070  # Replace with your group ID

# REQUIRED CHANNELS - EMPTY (No verification)
REQUIRED_CHANNELS = []

# Bangladesh Timezone
BANGLADESH_TZ = pytz.timezone('Asia/Dhaka')

# Schedule times (Bangladesh Time)
JWT_CALL_TIMES = [(4, 10), (4, 11), (4, 12)]  # (hour, minute)
AUTO_LIKE_HOUR = 4
AUTO_LIKE_MINUTE = 50

# Video URLs (GitHub hosted) - ONLY 3 VIDEOS
VIDEOS = {
    "success": "https://sharevideo.org/Yg8vtFojdNJJjfl/watch",
    "zero_likes": "https://raw.githubusercontent.com/yourusername/yourrepo/main/zero.mp4",
    "error": "https://raw.githubusercontent.com/yourusername/yourrepo/main/error.mp4"
}

# Valid Free Fire regions
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
# DATA MANAGER - JSON File Storage
# ═══════════════════════════════════════════════════════════════════

DATA_DIR = "bot_data"
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "users": os.path.join(DATA_DIR, "users.json"),
    "auto_like": os.path.join(DATA_DIR, "auto_like.json"),
    "target_like": os.path.join(DATA_DIR, "target_like.json"),
    "daily_usage": os.path.join(DATA_DIR, "daily_usage.json"),
    "unlimited": os.path.join(DATA_DIR, "unlimited.json"),
    "broadcast_users": os.path.join(DATA_DIR, "broadcast_users.json"),
    "like_history": os.path.join(DATA_DIR, "like_history.json"),
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
    """Get current time in Bangladesh timezone"""
    return datetime.now(BANGLADESH_TZ)


def get_bd_date():
    """Get current date in Bangladesh timezone"""
    return get_bd_time().strftime("%Y-%m-%d")


def format_bold(text):
    """Format text with bold styling"""
    lines = text.split("\n")
    formatted_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            clean = stripped.replace("*", "").replace("_", "").strip()
            if clean:
                formatted_lines.append(f"*{clean}*")
            else:
                formatted_lines.append("")
        else:
            formatted_lines.append("")
    return "\n".join(formatted_lines)


def format_quote(text):
    """Format text as a premium quote with borders and styling"""
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
    """Check if group is the allowed group"""
    return chat_id == ALLOWED_GROUP_ID


def add_broadcast_user(user_id):
    """Add user to broadcast list"""
    users = load_data("broadcast_users")
    users[str(user_id)] = True
    save_data("broadcast_users", users)


def get_broadcast_users():
    """Get all broadcast user IDs"""
    users = load_data("broadcast_users")
    return [int(uid) for uid in users.keys()]


# ═══════════════════════════════════════════════════════════════════
# AUTO-LIKE & TARGET-LIKE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def add_auto_like(uid, region, days):
    """Add UID to auto-like list with duration in days"""
    auto = load_data("auto_like")
    auto[str(uid)] = {
        "region": region.upper(),
        "days_left": int(days),
        "total_days": int(days),
        "likes_sent": 0,
        "added_at": get_bd_time().isoformat()
    }
    save_data("auto_like", auto)


def remove_auto_like(uid):
    """Remove UID from auto-like list"""
    auto = load_data("auto_like")
    if str(uid) in auto:
        del auto[str(uid)]
        save_data("auto_like", auto)


def get_auto_like_list():
    """Get all auto-like UIDs"""
    return load_data("auto_like")


def add_target_like(uid, region, target_limit):
    """Add UID with target likes limit"""
    targets = load_data("target_like")
    targets[str(uid)] = {
        "region": region.upper(),
        "target_limit": int(target_limit),
        "likes_sent": 0,
        "added_at": get_bd_time().isoformat()
    }
    save_data("target_like", targets)


def remove_target_like(uid):
    """Remove UID from target like list"""
    targets = load_data("target_like")
    if str(uid) in targets:
        del targets[str(uid)]
        save_data("target_like", targets)


def add_unlimited(uid, region):
    """Add UID to unlimited likes list"""
    unlimited = load_data("unlimited")
    unlimited[str(uid)] = {
        "region": region.upper(),
        "likes_sent": 0,
        "added_at": get_bd_time().isoformat()
    }
    save_data("unlimited", unlimited)


def remove_unlimited(uid):
    """Remove UID from unlimited list"""
    unlimited = load_data("unlimited")
    if str(uid) in unlimited:
        del unlimited[str(uid)]
        save_data("unlimited", unlimited)


def is_unlimited(uid):
    """Check if UID has unlimited likes"""
    unlimited = load_data("unlimited")
    return str(uid) in unlimited


def can_use_like(user_id):
    """Check if user can use /like today - ADMIN ALWAYS BYPASSED"""
    if is_admin(user_id):
        return True
    usage = load_data("daily_usage")
    uid = str(user_id)
    today = get_bd_date()
    if uid not in usage:
        return True
    return usage[uid].get("date") != today


def mark_like_used(user_id):
    """Mark that user has used /like today - SKIP ADMIN"""
    if is_admin(user_id):
        return
    usage = load_data("daily_usage")
    uid = str(user_id)
    usage[uid] = {"date": get_bd_date(), "count": 1}
    save_data("daily_usage", usage)


def reset_daily_usage():
    """Reset daily usage"""
    save_data("daily_usage", {})
    logger.info("Daily usage reset")


# ═══════════════════════════════════════════════════════════════════
# FREE FIRE API CLIENT
# ═══════════════════════════════════════════════════════════════════

async def send_like_api(uid, region, is_jwt_call=False):
    """Call the API to send likes"""
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
                    logger.error(f"API HTTP Error: Status code {resp.status}")
                    return {"error": "API is currently not working or returned invalid status.", "status": 0}
                
                data = await resp.json()
                return data
    except Exception as e:
        logger.error(f"Internal API Connection Error: {e}")
        return {"error": "API is currently not working or under maintenance.", "status": 0}


async def send_bulk_likes(uid, region, count=5):
    """Send multiple likes to a UID"""
    results = []
    for i in range(count):
        result = await send_like_api(uid, region)
        results.append(result)
        await asyncio.sleep(1)  # 1-second gap between calls
    return results


# ═══════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    chat = update.effective_chat
    add_broadcast_user(user.id)

    # Private chat restricted to admin only
    if chat.type == "private" and not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ ACCESS DENIED!\n\nThis bot is private. Only administrators can use it in private chat."),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Group chat - only allowed group
    if chat.type in ["group", "supergroup"] and not is_group_allowed(chat.id):
        await update.message.reply_text(
            format_bold("❌ ACCESS DENIED!\n\nThis bot only works in the authorized group."),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    text = (
        "✨ WELCOME TO FREXY AUTO LIKE ✨\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  🎮 Premium Free Fire Bot\n"
        "  ⚡ Powered by FREXY\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  💡 Use /help for commands\n"
        "  📌 Region must be BEFORE UID\n\n"
        "  Example: /like BD 123456789"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user = update.effective_user
    chat = update.effective_chat

    if chat.type == "private" and not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ ACCESS DENIED!\n\nOnly administrators can use this bot in private chat."),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if chat.type in ["group", "supergroup"] and not is_group_allowed(chat.id):
        await update.message.reply_text(
            format_bold("❌ ACCESS DENIED!\n\nThis bot only works in the authorized group."),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if is_admin(user.id):
        text = (
            "🔐 ADMIN COMMANDS - FREXY 🔐\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  🔧 Admin Commands:\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  📌 FORMAT: region uid days\n\n"
            "  /autolike <region> <uid> <days>\n"
            "  → Auto daily like\n\n"
            "  /removeauto <uid>\n"
            "  → Remove auto like\n\n"
            "  /autolist\n"
            "  → List auto UIDs\n\n"
            "  /tlike <region> <uid> <target>\n"
            "  → Target likes\n\n"
            "  /removetlike <uid>\n"
            "  → Remove target like\n\n"
            "  /tlist\n"
            "  → List target UIDs\n\n"
            "  /unlimit <uid> <region>\n"
            "  → Unlimited likes\n\n"
            "  /removeunlimit <uid>\n"
            "  → Remove unlimited\n\n"
            "  /broadcast <message>\n"
            "  → Message all users\n\n"
            "  /stats\n"
            "  → Bot statistics\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ⚡ POWERED BY FREXY"
        )
    else:
        text = (
            "🎮 USER COMMANDS - FREXY 🎮\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  📌 FORMAT: region uid\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  /like <region> <uid>\n"
            "  → Get likes\n\n"
            "  Example:\n"
            "  /like BD 123456789\n\n"
            "  🌍 Valid Regions:\n"
            "  BD, IND, BR, US, SAC, NA, RU\n\n"
            "  ⚠️ Rules:\n"
            "  • 1 like per day per user\n"
            "  • Resets at 4:00 AM\n"
            "  • Works in authorized group\n"
            "  • Region MUST be before UID\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ⚡ POWERED BY FREXY"
        )
    
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def like_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /like command - FORMAT: /like <region> <uid>"""
    user = update.effective_user
    chat = update.effective_chat
    add_broadcast_user(user.id)

    # Private chat restricted to admin only
    if chat.type == "private" and not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ ACCESS DENIED!\n\nOnly administrators can use this bot in private chat."),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Group chat - only allowed group
    if chat.type in ["group", "supergroup"] and not is_group_allowed(chat.id):
        await update.message.reply_text(
            format_bold("❌ ACCESS DENIED!\n\nThis bot only works in the authorized group."),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if len(context.args) < 2:
        text = (
            "❌ INVALID COMMAND ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ✅ Correct Format:\n"
            "  /like <region> <uid>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  📌 Examples:\n"
            "  /like BD 123456789\n"
            "  /like IND 987654321\n\n"
            "  🌍 Valid Regions:\n"
            "  BD, IND, BR, US, SAC, NA, RU\n\n"
            "  ⚠️ Region MUST be before UID!"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    region = context.args[0].upper()
    uid = context.args[1]

    if region not in VALID_REGIONS:
        text = (
            "❌ INVALID REGION ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  🌍 Valid Regions:\n"
            "  BD, IND, BR, US, SAC, NA, RU\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  💡 Example: /like BD 123456789"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not uid.isdigit():
        text = (
            "❌ INVALID UID ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ❌ UID must be numbers only\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  💡 Example: /like BD 123456789"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Check if UID is in auto-like or target-like
    auto_list = get_auto_like_list()
    targets = load_data("target_like")

    if str(uid) in auto_list:
        days_left = auto_list[str(uid)].get("days_left", 0)
        region_auto = auto_list[str(uid)].get("region", "N/A")
        text = (
            "⚠️ AUTO-LIKE ACTIVE ⚠️\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ❌ This UID has active\n"
            "     auto-like setup.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"  🆔 UID: {uid}\n"
            f"  🌍 Region: {region_auto}\n"
            f"  📅 Remaining: {days_left} Days\n\n"
            "  💡 Auto-likes are delivered\n"
            "     daily at 4:50 AM"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if str(uid) in targets:
        likes_sent = targets[str(uid)].get("likes_sent", 0)
        target_limit = targets[str(uid)].get("target_limit", 0)
        region_target = targets[str(uid)].get("region", "N/A")
        text = (
            "⚠️ TARGET-LIKE ACTIVE ⚠️\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ❌ This UID has active\n"
            "     target-like setup.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"  🆔 UID: {uid}\n"
            f"  🌍 Region: {region_target}\n"
            f"  📈 Progress: {likes_sent}/{target_limit}\n\n"
            "  💡 Target-likes are delivered\n"
            "     daily at 4:50 AM"
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
            "  ❌ You already used your\n"
            "     daily like today!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  🔄 Resets at 4:00 AM\n"
            "  ⏰ Bangladesh Time\n\n"
            "  💡 Try again tomorrow!"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    processing_text = (
        "⏳ PROCESSING REQUEST ⏳\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🎮 UID: {uid}\n"
        f"  🌍 Region: {region}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  ⏳ Please wait...\n"
        "  🚀 Sending like..."
    )
    msg = await update.message.reply_text(
        format_quote(processing_text),
        parse_mode=ParseMode.MARKDOWN
    )

    result = await send_like_api(uid, region)

    if result.get("error"):
        error_text = (
            "❌ ERROR ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  ❌ {result['error'][:35]}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"  🎮 UID: {uid}\n"
            f"  🌍 Region: {region}\n\n"
            "  ⚡ POWERED BY FREXY"
        )
        # Send error video
        try:
            await context.bot.send_video(
                chat_id=chat.id,
                video=VIDEOS["error"],
                caption=format_quote(error_text),
                parse_mode=ParseMode.MARKDOWN
            )
            await msg.delete()
        except Exception as e:
            logger.error(f"Error sending video: {e}")
            await msg.edit_text(
                format_quote(error_text),
                parse_mode=ParseMode.MARKDOWN
            )
        return

    if result.get("status") in [1, 2]:
        player_name = result.get("PlayerNickname", "Unknown")
        likes_before = result.get("LikesbeforeCommand", "N/A")
        likes_after = result.get("LikesafterCommand", "N/A")
        likes_given = result.get("LikesGivenByAPI", 0)
        current_time = get_bd_time().strftime("%I:%M %p")
        current_date = get_bd_time().strftime("%d-%m-%Y")

        # Check if it's a zero-likes account
        likes_before_int = int(likes_before) if str(likes_before).isdigit() else 0
        video_url = VIDEOS["zero_likes"] if likes_before_int == 0 else VIDEOS["success"]

        success_text = (
            "✅ LIKE SENT SUCCESSFULLY ✅\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  👤 Name: {player_name}\n"
            f"  🌍 Server: {region}\n"
            f"  🆔 UID: {uid}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  📉 Before: {likes_before}\n"
            f"  📈 After: {likes_after}\n"
            f"  ➕ Given: {likes_given}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  📅 {current_date}\n"
            f"  ⏰ {current_time}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ⚡ POWERED BY FREXY"
        )

        if not is_unlimited(uid):
            mark_like_used(user.id)

        # Send the video with caption
        try:
            await context.bot.send_video(
                chat_id=chat.id,
                video=video_url,
                caption=format_quote(success_text),
                parse_mode=ParseMode.MARKDOWN
            )
            await msg.delete()
        except Exception as e:
            logger.error(f"Error sending video: {e}")
            await msg.edit_text(
                format_quote(success_text),
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        error_text = (
            "❌ FAILED ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ❌ Could not send likes\n"
            "  API is currently down\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"  🎮 UID: {uid}\n"
            f"  🌍 Region: {region}\n\n"
            "  ⚡ POWERED BY FREXY"
        )
        # Send error video
        try:
            await context.bot.send_video(
                chat_id=chat.id,
                video=VIDEOS["error"],
                caption=format_quote(error_text),
                parse_mode=ParseMode.MARKDOWN
            )
            await msg.delete()
        except Exception as e:
            logger.error(f"Error sending video: {e}")
            await msg.edit_text(
                format_quote(error_text),
                parse_mode=ParseMode.MARKDOWN
            )


# ═══════════════════════════════════════════════════════════════════
# ADMIN COMMANDS - ALL WITH REGION FIRST
# ═══════════════════════════════════════════════════════════════════

async def autolike_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /autolike command - FORMAT: /autolike <region> <uid> <days>"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if len(context.args) < 3:
        text = (
            "❌ INVALID COMMAND ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ✅ Correct Format:\n"
            "  /autolike <region> <uid> <days>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  📌 Example:\n"
            "  /autolike BD 123456789 30\n\n"
            "  🌍 Region must be first!\n"
            "  📅 Days = Duration"
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
            format_bold(f"❌ Invalid Region. Available: {', '.join(VALID_REGIONS)}"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not uid.isdigit() or not days.isdigit():
        await update.message.reply_text(
            format_bold("❌ UID and Days must be numbers!"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    add_auto_like(uid, region, days)
    
    text = (
        "✅ AUTO LIKE ADDED ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🆔 UID: {uid}\n"
        f"  🌍 Region: {region}\n"
        f"  📅 Duration: {days} Days\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ⏰ Daily at 4:50 AM\n"
        "  📌 5 likes per day\n\n"
        "  ⚡ POWERED BY FREXY"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def removeauto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removeauto command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not context.args:
        text = (
            "❌ INVALID COMMAND ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ✅ Correct Format:\n"
            "  /removeauto <uid>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  📌 Example:\n"
            "  /removeauto 123456789"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    uid = context.args[0]
    remove_auto_like(uid)
    
    text = (
        "✅ AUTO LIKE REMOVED ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🆔 UID: {uid}\n"
        "  ✅ Removed from auto-list\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  ⚡ POWERED BY FREXY"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def autolist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /autolist command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    auto_list = get_auto_like_list()
    if not auto_list:
        text = (
            "📋 AUTO-LIKE LIST 📋\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  📋 List is empty!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  💡 Add with:\n"
            "  /autolike BD 123456789 30"
        )
    else:
        lines = [
            "📋 AUTO-LIKE LIST 📋",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        for uid, info in list(auto_list.items())[:15]:
            days_left = info.get('days_left', 0)
            region = info.get('region', 'N/A')
            likes_sent = info.get('likes_sent', 0)
            lines.append(f"  🆔 {uid} | 🌍 {region} | 📅 {days_left}d | 📊 {likes_sent}")
        if len(auto_list) > 15:
            lines.append(f"  ... and {len(auto_list)-15} more")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("  ⚡ POWERED BY FREXY")
        text = "\n".join(lines)

    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def tlike_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tlike command - FORMAT: /tlike <region> <uid> <target>"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if len(context.args) < 3:
        text = (
            "❌ INVALID COMMAND ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ✅ Correct Format:\n"
            "  /tlike <region> <uid> <target>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  📌 Example:\n"
            "  /tlike BD 123456789 100\n\n"
            "  🌍 Region must be first!\n"
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
            format_bold(f"❌ Invalid Region. Available: {', '.join(VALID_REGIONS)}"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not uid.isdigit() or not target_limit.isdigit():
        await update.message.reply_text(
            format_bold("❌ UID and Target must be numbers!"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    add_target_like(uid, region, target_limit)
    
    text = (
        "✅ TARGET LIKE ADDED ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🆔 UID: {uid}\n"
        f"  🌍 Region: {region}\n"
        f"  🎯 Target: {target_limit} Likes\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ⏰ Daily at 4:50 AM\n"
        "  📌 5 likes per day\n"
        "  🔄 Stops when target reached\n\n"
        "  ⚡ POWERED BY FREXY"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def removetlike_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removetlike command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not context.args:
        text = (
            "❌ INVALID COMMAND ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ✅ Correct Format:\n"
            "  /removetlike <uid>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  📌 Example:\n"
            "  /removetlike 123456789"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    uid = context.args[0]
    remove_target_like(uid)
    
    text = (
        "✅ TARGET LIKE REMOVED ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🆔 UID: {uid}\n"
        "  ✅ Removed from target-list\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  ⚡ POWERED BY FREXY"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def tlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tlist command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    targets = load_data("target_like")
    if not targets:
        text = (
            "📋 TARGET-LIKE LIST 📋\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  📋 List is empty!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  💡 Add with:\n"
            "  /tlike BD 123456789 100"
        )
    else:
        lines = [
            "📋 TARGET-LIKE LIST 📋",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        for uid, info in list(targets.items())[:15]:
            likes_sent = info.get('likes_sent', 0)
            target_limit = info.get('target_limit', 0)
            region = info.get('region', 'N/A')
            progress = f"{likes_sent}/{target_limit}"
            lines.append(f"  🆔 {uid} | 🌍 {region} | 🎯 {progress}")
        if len(targets) > 15:
            lines.append(f"  ... and {len(targets)-15} more")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("  ⚡ POWERED BY FREXY")
        text = "\n".join(lines)

    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def unlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unlimit command - FORMAT: /unlimit <uid> <region>"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if len(context.args) < 2:
        text = (
            "❌ INVALID COMMAND ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ✅ Correct Format:\n"
            "  /unlimit <uid> <region>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  📌 Example:\n"
            "  /unlimit 123456789 BD"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    uid = context.args[0]
    region = context.args[1].upper()
    add_unlimited(uid, region)
    
    text = (
        "✅ UNLIMITED LIKE ADDED ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🆔 UID: {uid}\n"
        f"  🌍 Region: {region}\n"
        "  ♾️ No daily limit\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  ⚡ POWERED BY FREXY"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def removeunlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removeunlimit command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not context.args:
        text = (
            "❌ INVALID COMMAND ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ✅ Correct Format:\n"
            "  /removeunlimit <uid>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  📌 Example:\n"
            "  /removeunlimit 123456789"
        )
        await update.message.reply_text(
            format_quote(text),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    uid = context.args[0]
    remove_unlimited(uid)
    
    text = (
        "✅ UNLIMITED LIKE REMOVED ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🆔 UID: {uid}\n"
        "  ✅ Removed from unlimited\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  ⚡ POWERED BY FREXY"
    )
    await update.message.reply_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not context.args:
        text = (
            "❌ INVALID COMMAND ❌\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  ✅ Correct Format:\n"
            "  /broadcast <message>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  📌 Example:\n"
            "  /broadcast Hello everyone!"
        )
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
        format_bold("📢 Broadcasting..."),
        parse_mode=ParseMode.MARKDOWN
    )

    for uid in users:
        try:
            broadcast_text = (
                "📢 ADMIN ANNOUNCEMENT 📢\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  {message}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
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
            logger.error(f"Broadcast failed for {uid}: {e}")

    text = (
        "✅ BROADCAST COMPLETE ✅\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  ✅ Sent: {sent}\n"
        f"  ❌ Failed: {failed}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  ⚡ POWERED BY FREXY"
    )
    await status_msg.edit_text(
        format_quote(text),
        parse_mode=ParseMode.MARKDOWN
    )


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            format_bold("❌ You are not authorized!"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    users = load_data("broadcast_users")
    auto_list = get_auto_like_list()
    targets = load_data("target_like")
    unlimited = load_data("unlimited")
    usage = load_data("daily_usage")

    text = (
        "📊 BOT STATISTICS 📊\n\n"
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
# SCHEDULER - JWT Calls & Auto Like
# ═══════════════════════════════════════════════════════════════════

async def run_jwt_pre_calls(application):
    """Send JWT calls at 4:10, 4:11, 4:12 AM"""
    while True:
        bd_now = get_bd_time()
        
        # Find next JWT call time
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
        logger.info(f"Next JWT call scheduled at {next_call_time.strftime('%H:%M')} (in {wait_seconds/3600:.1f} hours)")
        await asyncio.sleep(wait_seconds)

        current_time = get_bd_time()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        call_index = -1
        for idx, (h, m) in enumerate(JWT_CALL_TIMES):
            if h == current_hour and m == current_minute:
                call_index = idx
                break
        
        if call_index >= 0:
            logger.info(f"Starting JWT pre-call #{call_index + 1} at {current_time.strftime('%H:%M')}")
            
            try:
                result = await send_like_api("999999999", "BD", is_jwt_call=True)
                logger.info(f"JWT call #{call_index + 1}: {result}")
                
                try:
                    status_text = (
                        f"📡 JWT PRE-CALL #{call_index + 1} 📡\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"  📊 Status: {'✅ Success' if result.get('status') in [1,2] else '❌ Failed'}\n"
                        f"  ⏰ Time: {get_bd_time().strftime('%I:%M %p')}\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "  ⚡ POWERED BY FREXY"
                    )
                    await application.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=format_quote(status_text),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Failed to send JWT status to admin: {e}")
            except Exception as e:
                logger.error(f"JWT call #{call_index + 1} failed: {e}")
        
        current_time = get_bd_time()
        last_hour, last_minute = JWT_CALL_TIMES[-1]
        if current_time.hour > last_hour or (current_time.hour == last_hour and current_time.minute > last_minute):
            try:
                await application.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=format_quote(
                        "✅ JWT PRE-CALLS COMPLETE ✅\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "  ✅ All 3 JWT calls sent!\n"
                        "  🔄 Ready for auto-like at\n"
                        "  ⏰ 4:50 AM\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "  ⚡ POWERED BY FREXY"
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info("JWT completion message sent to admin")
            except Exception as e:
                logger.error(f"Failed to send completion message: {e}")


async def run_auto_like(application):
    """Send auto likes and target likes daily at 4:50 AM"""
    while True:
        bd_now = get_bd_time()
        target = bd_now.replace(
            hour=AUTO_LIKE_HOUR,
            minute=AUTO_LIKE_MINUTE,
            second=0,
            microsecond=0
        )
        if target <= bd_now:
            target += timedelta(days=1)
        
        wait_seconds = (target - bd_now).total_seconds()
        logger.info(f"Next auto-like run scheduled in {wait_seconds/3600:.1f} hours")
        await asyncio.sleep(wait_seconds)

        logger.info("Starting auto-like run at 4:50 AM")
        
        admin_report = [
            "📊 DAILY AUTO-LIKE REPORT 📊",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]

        # Part 1: Auto Likes
        auto_list = get_auto_like_list()
        updated_auto_list = {}
        
        if auto_list:
            admin_report.append("  📅 ACTIVE AUTO LIKES:")
            
        for uid, info in list(auto_list.items()):
            days_left = info.get("days_left", 0)
            if days_left <= 0:
                continue

            region = info.get("region", "BD")
            
            results = await send_bulk_likes(uid, region, count=5)
            success_count = sum(1 for r in results if r.get("status") in [1, 2])
            
            if success_count > 0:
                logger.info(f"Auto-like: {success_count}/5 likes sent to {uid} ({region})")
                status_text = f"✅ {success_count}/5"
            else:
                logger.error(f"Auto-like failed for {uid}")
                status_text = "❌ 0/5"

            new_days = days_left - 1
            if new_days > 0:
                info["days_left"] = new_days
                info["likes_sent"] = info.get("likes_sent", 0) + success_count
                updated_auto_list[uid] = info
                admin_report.append(f"  🆔 {uid} | 🌍 {region} | {status_text} | 📅 {new_days}d")
            else:
                logger.info(f"Auto-like expired for UID: {uid}")
                admin_report.append(f"  🆔 {uid} | 🌍 {region} | {status_text} | ⏰ EXPIRED")
            
            # Send to group with video
            try:
                if success_count > 0:
                    first_result = results[0] if results else {}
                    likes_before = first_result.get("LikesbeforeCommand", "0")
                    likes_before_int = int(likes_before) if str(likes_before).isdigit() else 0
                    likes_after = first_result.get("LikesafterCommand", "N/A")
                    video_url = VIDEOS["zero_likes"] if likes_before_int == 0 else VIDEOS["success"]
                else:
                    video_url = VIDEOS["error"]
                    likes_before = "N/A"
                    likes_after = "N/A"
                
                sent_text = (
                    f"✅ AUTO-LIKE SENT ✅\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  🆔 UID: {uid}\n"
                    f"  🌍 Region: {region}\n"
                    f"  📊 Sent: {success_count}/5\n"
                    f"  📉 Before: {likes_before}\n"
                    f"  📈 After: {likes_after}\n"
                    f"  📅 Days Left: {new_days}\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  ⏰ {get_bd_time().strftime('%I:%M %p')}\n"
                    "  ⚡ POWERED BY FREXY"
                )
                await application.bot.send_video(
                    chat_id=ALLOWED_GROUP_ID,
                    video=video_url,
                    caption=format_quote(sent_text),
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to send auto-like update to group: {e}")
            
            await asyncio.sleep(1)
        
        save_data("auto_like", updated_auto_list)

        admin_report.append("")

        # Part 2: Target Likes
        targets = load_data("target_like")
        updated_targets = {}
        
        if targets:
            admin_report.append("  📈 ACTIVE TARGET LIKES:")
            
        for uid, info in list(targets.items()):
            target_limit = info.get("target_limit", 0)
            likes_sent = info.get("likes_sent", 0)

            if likes_sent >= target_limit:
                continue

            region = info.get("region", "BD")
            
            results = await send_bulk_likes(uid, region, count=5)
            success_count = sum(1 for r in results if r.get("status") in [1, 2])
            
            if success_count > 0:
                logger.info(f"Target-like: {success_count}/5 likes sent to {uid} ({region})")
                likes_sent += success_count
                status_text = f"✅ {success_count}/5"
            else:
                logger.error(f"Target-like failed for {uid}")
                status_text = "❌ 0/5"

            if likes_sent < target_limit:
                info["likes_sent"] = likes_sent
                updated_targets[uid] = info
                admin_report.append(f"  🆔 {uid} | 🌍 {region} | {status_text} | {likes_sent}/{target_limit}")
                
                # Send progress to group with video
                try:
                    if success_count > 0:
                        first_result = results[0] if results else {}
                        likes_before = first_result.get("LikesbeforeCommand", "0")
                        likes_before_int = int(likes_before) if str(likes_before).isdigit() else 0
                        likes_after = first_result.get("LikesafterCommand", "N/A")
                        video_url = VIDEOS["zero_likes"] if likes_before_int == 0 else VIDEOS["success"]
                    else:
                        video_url = VIDEOS["error"]
                        likes_before = "N/A"
                        likes_after = "N/A"
                    
                    progress_text = (
                        f"📈 TARGET-LIKE PROGRESS 📈\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"  🆔 UID: {uid}\n"
                        f"  🌍 Region: {region}\n"
                        f"  📊 Sent: {success_count}/5\n"
                        f"  📉 Before: {likes_before}\n"
                        f"  📈 After: {likes_after}\n"
                        f"  🎯 Progress: {likes_sent}/{target_limit}\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"  ⏰ {get_bd_time().strftime('%I:%M %p')}\n"
                        "  ⚡ POWERED BY FREXY"
                    )
                    await application.bot.send_video(
                        chat_id=ALLOWED_GROUP_ID,
                        video=video_url,
                        caption=format_quote(progress_text),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Failed to send target-like update to group: {e}")
            else:
                logger.info(f"Target limit ({target_limit}) reached for UID: {uid}")
                admin_report.append(f"  🆔 {uid} | 🌍 {region} | {status_text} | ✅ COMPLETE")
            
            await asyncio.sleep(1)

        save_data("target_like", updated_targets)

        admin_report.append("")
        admin_report.append(f"  ⏰ {get_bd_time().strftime('%I:%M %p')}")
        admin_report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        admin_report.append("  ⚡ POWERED BY FREXY")

        # Send report to Admin
        report_text = "\n".join(admin_report)
        try:
            await application.bot.send_message(
                chat_id=ADMIN_ID,
                text=format_quote(report_text),
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info("Daily admin report sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send Admin private report: {e}")


# ═══════════════════════════════════════════════════════════════════
# MAIN (Async Server Startup)
# ═══════════════════════════════════════════════════════════════════

async def main_async():
    # Build application
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("like", like_cmd))

    # Admin commands
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

    # Start scheduler tasks
    asyncio.create_task(run_jwt_pre_calls(application))
    asyncio.create_task(run_auto_like(application))

    # Initialize and start Telegram Bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Telegram Bot polling started.")

    # Render Port Binding Setup
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running successfully!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Port binding web server started on port {port}")

    try:
        while True:
            await asyncio.sleep(3600)
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
