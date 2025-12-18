# 🚀 QUICK SETUP GUIDE

**💫 MADE BY DARK SHADOW 💫**

---

## 📋 Prerequisites

- Python 3.8 or higher
- Telegram Bot Token (from @BotFather)
- Your Telegram User ID

---

## ⚡ Quick Setup (3 Steps)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Bot
```bash
python setup_env.py
```

This will ask you for:
- 🔑 Bot Token (from @BotFather)
- 👑 Your Telegram ID (Owner)
- 👨‍💼 Admin Telegram ID
- 📢 Your Username (default: @DARK22v)
- 📣 Your Channel Link (default: https://t.me/DARK22v)

### Step 3: Run Bot
```bash
python bot_launcher.py
```

---

## 🔧 Manual Setup (.env file)

If you prefer manual setup, create a `.env` file:

```env
BOT_TOKEN=your_bot_token_here
OWNER_ID=your_owner_telegram_id_here
ADMIN_ID=your_admin_telegram_id_here
YOUR_USERNAME=@DARK22v
UPDATE_CHANNEL=https://t.me/DARK22v
```

---

## 🌐 Deploy to Cloud

### Railway
```bash
railway login
railway init
railway up
```

### Heroku
```bash
heroku login
heroku create your-bot-name
git push heroku main
```

### Render
1. Connect your GitHub repo
2. Set environment variables from `.env`
3. Deploy!

---

## 📊 Features After Setup

✅ File upload & management  
✅ Script execution (Python/JS)  
✅ Web-based file manager  
✅ Temporary hosting sessions  
✅ Auto platform detection  
✅ Admin panel  
✅ Premium subscriptions  

---

## 🆘 Common Issues

### Issue: "BOT_TOKEN not found"
**Solution**: Run `python setup_env.py` first

### Issue: "Direct execution not allowed"
**Solution**: Always use `python bot_launcher.py`

### Issue: "Module not found"
**Solution**: Run `pip install -r requirements.txt`

---

## 📞 Support

- **Channel**: https://t.me/DARK22v
- **Creator**: @DARK22v

---

**💫 MADE BY DARK SHADOW 💫**
