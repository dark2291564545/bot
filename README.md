# 🤖 Telegram File Host Bot

**💫 MADE BY DARK SHADOW 💫**

Advanced admin-only Telegram bot with file management, code formatting, file sharing, and web panel.

---

## 🚀 INSTALLATION (Super Easy!)

### Option 1: Automatic Installation (Recommended)

```bash
python install.py
```

Follow the prompts and you're done! ✅

### Option 2: Manual Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file
python setup_env.py

# 3. Run bot
python bot_launcher.py
```

---

## 📋 Prerequisites

- **Python 3.8+** → https://python.org/downloads
- **Telegram Bot Token** → Get from @BotFather
- **Your Telegram ID** → Get from @userinfobot

---

## ⚙️ Configuration

Create `.env` file with:

```env
BOT_TOKEN=your_bot_token_from_botfather
OWNER_ID=your_telegram_id
ADMIN_ID=your_telegram_id
YOUR_USERNAME=@DARK22v
UPDATE_CHANNEL=https://t.me/DARK22v
```

---

## 🎯 Features

### 🔒 Admin-Only Access
- Only authorized users can use the bot
- Owner and admins have full access
- Regular users see "Admin Only Bot" message

### 📁 File Management
- Upload `.py`, `.js`, `.zip` files
- Auto code formatting (Python with Black)
- Code analysis (lines, functions, classes)
- Run scripts directly from Telegram

### 📤 File Sharing
- Create temporary share links
- Expiry options: 1h, 24h, 7d, 30d
- Download tracking
- Revoke links anytime
- Command: `/myshares`

### 🔍 Advanced Search
- Search in filenames AND content
- Regex support
- Line number previews
- Command: `/search keyword`

### 🌐 Web Panel
- Browser-based file manager
- Code editor with syntax highlighting
- Drag & drop uploads
- Owner: Never expires
- Admin: 24-hour sessions
- Command: `/panel`

### 👨‍💼 Admin Features
- Add/remove admins
- Ban/unban users
- Broadcast messages
- System monitoring
- Premium management

---

## 📝 Commands

```
/start      - Start bot
/help       - Help & info
/stats      - Your statistics
/panel      - Get web panel
/live       - Live Control Panel (NEW!)
/search     - Smart search
/myshares   - View share links

Admin Only:
/addadmin    - Add admin
/removeadmin - Remove admin
/ban         - Ban user
/unban       - Unban user
/broadcast   - Send message to all
```

---

## 🚀 NEW! Live Control Panel

Access via `/live` command for:

### 📦 Dependencies Manager
- ✅ One-click install all dependencies
- ✅ Upload requirements.txt file
- ✅ Edit requirements.txt in browser
- ✅ View installation output live

### ⚙️ .env File Manager  
- ✅ Edit .env in browser
- ✅ Save instantly
- ✅ No need to access server

### ▶️ Code Runner
- ✅ Run Python/JS files from web
- ✅ View live output
- ✅ Stop running processes
- ✅ 30-second timeout protection

### 💻 Terminal Access
- ✅ Execute shell commands
- ✅ Real-time output
- ✅ Dangerous commands blocked
- ✅ Safe sandbox execution

### 📋 Real-time Logs
- ✅ View bot logs live
- ✅ Auto-refresh every 5 seconds
- ✅ Last 100 lines shown

---

## 🐛 Troubleshooting

### Common Issues:

**"BOT_TOKEN not found"**
```bash
python install.py  # Run auto-installer
```

**"Module not found"**
```bash
pip install -r requirements.txt
```

**"Direct execution not allowed"**
```bash
python bot_launcher.py  # Use launcher, not main.py
```

**"Admin Only Bot" message**
- This is intentional!
- Make sure .env has YOUR Telegram ID
- Use /addadmin to add more admins

📚 **Full troubleshooting:** See `TROUBLESHOOTING.md`

---

## 🌐 Deployment

### Railway (Recommended)
```bash
railway login
railway init
railway up
```

### Heroku
```bash
heroku create your-bot-name
git push heroku main
```

### Render
1. Connect GitHub repo
2. Add environment variables
3. Deploy!

**Platform auto-detection** - No code changes needed! ✅

---

## 📂 Project Structure

```
bot/
├── main.py                  # Main bot code
├── bot_launcher.py          # Secure launcher
├── web_dashboard.py         # Web panel
├── file_sharing.py          # Share links
├── code_formatter.py        # Auto-format
├── advanced_search.py       # Smart search
├── temporary_hosting.py     # Sessions
├── hosting_detector.py      # Platform detection
├── install.py               # Auto installer (NEW!)
├── requirements.txt         # Dependencies
├── .env                     # Configuration
└── inf/                     # Database
    └── bot_data.db
```

---

## 🔐 Security

- ✅ Admin-only access
- ✅ Path traversal protection
- ✅ Input sanitization
- ✅ ZIP bomb protection
- ✅ SHA-256 file hashing
- ✅ Process isolation
- ✅ Secure launcher
- ✅ JWT authentication

---

## 📊 Stats

- **22 Files** - Clean, modular code
- **11 Commands** - Fully featured
- **36+ Callbacks** - Interactive UI
- **4 Premium Features** - File sharing, auto-format, smart search, code analysis
- **100% Admin Protected** - Secure

---

## 📞 Support

- **Channel:** https://t.me/DARK22v
- **Creator:** @DARK22v
- **Issues:** Check `TROUBLESHOOTING.md`

---

## 📚 Documentation

- `SETUP_GUIDE.md` - Quick start guide
- `TROUBLESHOOTING.md` - Error solutions
- `NEW_FEATURES.md` - Feature documentation
- `ADMIN_ONLY_CONFIG.md` - Admin system
- `COMPLETE_SUMMARY.md` - Full summary

---

## 🌟 What Makes This Bot Special

✅ **One-Command Setup** - `python install.py`  
✅ **Admin-Only** - Complete privacy  
✅ **Auto-Format** - Professional code  
✅ **File Sharing** - Secure temporary links  
✅ **Smart Search** - Find anything instantly  
✅ **Web Panel** - Browser management  
✅ **Platform-Independent** - Deploy anywhere  
✅ **Enterprise Security** - Production-ready  

---

## 🎯 Quick Start Checklist

- [ ] Install Python 3.8+
- [ ] Download all bot files
- [ ] Run `python install.py`
- [ ] Get bot token from @BotFather
- [ ] Get your Telegram ID from @userinfobot
- [ ] Enter details when prompted
- [ ] Bot launches automatically!
- [ ] Send `/start` to your bot
- [ ] Enjoy! 🎉

---

## 🌟 Credits

**💫 MADE BY DARK SHADOW 💫**

- **Channel:** https://t.me/DARK22v
- **Creator:** @DARK22v

---

**⭐ Star this project if you find it useful!**
