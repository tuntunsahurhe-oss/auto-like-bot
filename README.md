# FREXY AUTO LIKE BOT 🤖

A Premium Free Fire Auto Like Bot for Telegram with advanced features.

---

## ✨ Features

- **🇧🇩 Bangladesh Timezone** - All schedules follow BD time (UTC+6)
- **🔄 Auto Like** - Daily auto-like at 4:50 AM (5 likes per UID)
- **🎯 Target Like** - Send likes until target reached
- **📡 JWT Pre-Calls** - 3 calls at 4:10, 4:11, 4:12 AM
- **📹 Video Support** - 3 premium videos for different scenarios
- **📊 Progress Tracking** - Shows before/after likes
- **🚫 Single Group** - Bot works in only one authorized group
- **🔒 Private Mode** - Only admin can use in private chat
- **🎨 Premium Formatting** - Beautiful quote-style messages

---

## 📋 Commands

### User Commands
| Command | Format | Example | Description |
|---------|--------|---------|-------------|
| `/start` | - | `/start` | Welcome message |
| `/help` | - | `/help` | Show all commands |
| `/like` | `/like <region> <uid>` | `/like BD 123456789` | Send 1 like (daily limit) |

### Admin Commands
| Command | Format | Example | Description |
|---------|--------|---------|-------------|
| `/autolike` | `/autolike <region> <uid> <days>` | `/autolike BD 123456789 30` | Add auto-like (daily) |
| `/removeauto` | `/removeauto <uid>` | `/removeauto 123456789` | Remove auto-like |
| `/autolist` | - | `/autolist` | List all auto-like UIDs |
| `/tlike` | `/tlike <region> <uid> <target>` | `/tlike BD 123456789 100` | Add target-like |
| `/removetlike` | `/removetlike <uid>` | `/removetlike 123456789` | Remove target-like |
| `/tlist` | - | `/tlist` | List all target-like UIDs |
| `/unlimit` | `/unlimit <uid> <region>` | `/unlimit 123456789 BD` | Add unlimited likes |
| `/removeunlimit` | `/removeunlimit <uid>` | `/removeunlimit 123456789` | Remove unlimited |
| `/broadcast` | `/broadcast <message>` | `/broadcast Hello!` | Broadcast to all users |
| `/stats` | - | `/stats` | Bot statistics |

---

## 🌍 Valid Regions

| Region Code | Description |
|-------------|-------------|
| BD | Bangladesh |
| IND | India |
| BR | Brazil |
| US | United States |
| SAC | South America Central |
| NA | North America |
| RU | Russia |

---

## ⏰ Schedule (BD Time)

| Time | Action |
|------|--------|
| 4:10 AM | JWT Pre-Call #1 |
| 4:11 AM | JWT Pre-Call #2 |
| 4:12 AM | JWT Pre-Call #3 |
| 4:50 AM | Auto-Like & Target-Like |

---

## 🎬 Videos

The bot uses 3 videos hosted on GitHub:

1. **success.mp4** - When likes are sent successfully
2. **zero.mp4** - When account has 0 likes
3. **error.mp4** - When API returns an error

---

## 🚀 Deployment on Render

### Step 1: Upload Files to GitHub
