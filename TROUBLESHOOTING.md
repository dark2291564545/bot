# 🆘 TROUBLESHOOTING GUIDE

**💫 MADE BY DARK SHADOW 💫**

---

## 📋 Quick Diagnostics

### Check Your Setup:
```bash
# 1. Check Python version
python --version
# Should be 3.8 or higher

# 2. Check if dependencies installed
pip list | grep aiogram
pip list | grep aiohttp

# 3. Check .env file exists
ls -la .env    # Linux/Mac
dir .env       # Windows

# 4. Test bot token
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Token:', os.getenv('BOT_TOKEN')[:10])"
```

---

## ❌ Common Errors & Solutions

### 1. "BOT_TOKEN not found"

**Error:**
```
ValueError: BOT_TOKEN is required. Please set it in .env file
```

**Solutions:**
```bash
# Option A: Run auto-installer
python install.py

# Option B: Create .env manually
# Copy this to .env file:
BOT_TOKEN=your_bot_token_from_botfather
OWNER_ID=your_telegram_id
ADMIN_ID=your_telegram_id
YOUR_USERNAME=@DARK22v
UPDATE_CHANNEL=https://t.me/DARK22v
```

**How to get Bot Token:**
1. Open Telegram
2. Search: @BotFather
3. Send: /newbot
4. Follow instructions
5. Copy the token (looks like: 123456:ABCdefGHIjklMNOpqrSTUvwxYZ)

**How to get your Telegram ID:**
1. Open Telegram
2. Search: @userinfobot
3. Send any message
4. Copy your ID (numbers only)

---

### 2. "Module not found" Errors

**Error:**
```
ModuleNotFoundError: No module named 'aiogram'
```

**Solution:**
```bash
# Install all dependencies
pip install -r requirements.txt

# If that fails, install manually:
pip install aiogram>=3.22.0
pip install aiohttp>=3.12.15
pip install python-dotenv>=1.1.1
pip install psutil>=7.1.1
pip install pyjwt>=2.8.0
pip install black>=24.0.0
```

**Still not working?**
```bash
# Try with python3
python3 -m pip install -r requirements.txt

# Or upgrade pip first
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### 3. "Direct execution not allowed"

**Error:**
```
❌ Direct execution not allowed!
🔧 Please run: python bot_launcher.py
```

**Solution:**
```bash
# DON'T run main.py directly!
# ❌ python main.py

# ✅ Use bot_launcher.py instead:
python bot_launcher.py
```

**Why?**
- `main.py` is protected for security
- `bot_launcher.py` does proper initialization
- This prevents accidental execution

---

### 4. "Admin Only Bot" Message

**Error:**
User sends /start but gets:
```
🔒 ADMIN ONLY BOT
⚠️ This bot is restricted to authorized administrators only.
```

**Solution:**
```bash
# This is INTENTIONAL!
# Bot is admin-only by design

# To use the bot:
# Make sure .env has YOUR Telegram ID:
OWNER_ID=your_actual_telegram_id
ADMIN_ID=your_actual_telegram_id

# To add more admins:
# Message bot as owner and use:
/addadmin user_telegram_id
```

---

### 5. Database Errors

**Error:**
```
sqlite3.OperationalError: unable to open database file
```

**Solution:**
```bash
# Create inf folder
mkdir inf

# Set permissions (Linux/Mac)
chmod 755 inf

# Run bot again
python bot_launcher.py
```

---

### 6. Port Already in Use

**Error:**
```
OSError: [Errno 98] Address already in use
```

**Solution:**
```bash
# Find process using port 5000
# Linux/Mac:
lsof -i :5000

# Windows:
netstat -ano | findstr :5000

# Kill the process
# Linux/Mac:
kill -9 <PID>

# Windows:
taskkill /PID <PID> /F

# Or change port in code (not recommended)
```

---

### 7. Web Panel Not Accessible

**Error:**
Panel URL doesn't work

**Solutions:**

**Local Testing:**
```
URL should be: http://localhost:8080/panel/{token}
NOT: https://localhost:8080/panel/{token}
```

**Cloud Deployment:**
```bash
# Check if platform detected correctly
# Bot logs should show:
🌐 Detected Platform: Railway
🔗 Base URL: https://your-app.railway.app

# If wrong, check environment variables
```

---

### 8. File Upload Fails

**Error:**
```
❌ Only .py, .js, and .zip files are supported!
```

**Solution:**
- Bot only accepts these file types (security)
- Rename your file to have correct extension
- Or modify ALLOWED_EXTENSIONS in main.py (not recommended)

---

### 9. Black Formatter Not Found

**Error:**
```
⚠️ Black not installed (pip install black)
```

**Solution:**
```bash
# Install Black
pip install black>=24.0.0

# Or disable auto-format
# Edit code_formatter.py and return success=False
```

---

### 10. Railway/Heroku Deployment Fails

**Error:**
Build fails on deployment

**Solutions:**

**Check requirements.txt:**
```bash
# Make sure it has all packages
cat requirements.txt

# Should include:
aiogram>=3.22.0
aiohttp>=3.12.15
python-dotenv>=1.1.1
# ... etc
```

**Check Python version:**
```bash
# Add runtime.txt (for Heroku)
echo "python-3.11.0" > runtime.txt

# Or .python-version (for Railway)
echo "3.11" > .python-version
```

**Check Procfile:**
```bash
# Should be:
web: python bot_launcher.py
```

**Environment Variables:**
- Make sure all .env variables are set in dashboard
- BOT_TOKEN, OWNER_ID, ADMIN_ID are REQUIRED

---

## 🔍 Error Log Locations

### Where to find error logs:

**Console Output:**
```bash
# Run bot and watch logs
python bot_launcher.py

# Logs show:
# INFO: messages
# WARNING: warnings
# ERROR: errors with details
```

**Log Files:**
```
logs/bot.log          # General logs
logs/error.log        # Error logs only
```

**Check logs:**
```bash
# View last 50 lines
tail -50 logs/bot.log      # Linux/Mac
Get-Content logs/bot.log -Tail 50  # Windows PowerShell
```

---

## 🧪 Testing Commands

### Test if bot is working:

```bash
# 1. Test Python imports
python -c "import aiogram; print('Aiogram OK')"

# 2. Test .env loading
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('BOT_TOKEN' in os.environ)"

# 3. Test database
python -c "import sqlite3; conn = sqlite3.connect('inf/bot_data.db'); print('DB OK')"

# 4. Test bot connection
python -c "from aiogram import Bot; import os; from dotenv import load_dotenv; load_dotenv(); bot = Bot(token=os.getenv('BOT_TOKEN')); print('Bot OK')"
```

---

## 📞 Getting Help

### Before asking for help, collect this info:

```bash
# 1. Python version
python --version

# 2. Operating System
# Windows/Linux/Mac?

# 3. Error message
# Copy FULL error message

# 4. What you tried
# List all steps you've done

# 5. Bot logs
# Last 20 lines of logs
```

### Where to get help:

1. **GitHub Issues** (if using GitHub repo)
2. **Telegram Channel:** https://t.me/DARK22v
3. **Creator:** @DARK22v

### What to include:

```
❌ Bad: "Bot not working"

✅ Good:
"Getting error: ModuleNotFoundError: No module named 'aiogram'
Python version: 3.10.5
OS: Windows 11
Tried: pip install -r requirements.txt
Error persists"
```

---

## 🚀 Quick Fixes Checklist

Before asking for help, try these:

- [ ] Python 3.8+ installed?
- [ ] Ran `pip install -r requirements.txt`?
- [ ] Created `.env` file with all variables?
- [ ] BOT_TOKEN is valid and from @BotFather?
- [ ] OWNER_ID and ADMIN_ID are YOUR Telegram IDs?
- [ ] Running `python bot_launcher.py` (not main.py)?
- [ ] Folders `inf/` and `upload_bots/` exist?
- [ ] No other process using port 5000/8080?
- [ ] Checked logs for specific error messages?

---

## 💡 Pro Tips

### Prevent Issues:

1. **Always use virtual environment:**
```bash
# Create venv
python -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install
pip install -r requirements.txt
```

2. **Keep backups:**
```bash
# Backup database
cp inf/bot_data.db inf/bot_data.db.backup

# Backup .env
cp .env .env.backup
```

3. **Update regularly:**
```bash
# Update pip
pip install --upgrade pip

# Update packages
pip install --upgrade -r requirements.txt
```

---

**💫 MADE BY DARK SHADOW 💫**

**Most problems are solved by:**
1. Running `python install.py`
2. Checking `.env` file has correct values
3. Using `python bot_launcher.py` (not main.py)
