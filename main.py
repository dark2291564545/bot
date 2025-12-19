import asyncio
import os
import sys
import logging
import subprocess
import psutil
import sqlite3
import hashlib
import json
import zipfile
import re
import signal
from contextlib import contextmanager
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
import aiohttp
from pathlib import Path
from dotenv import load_dotenv
from web_dashboard import create_web_dashboard, create_user_panel
from temporary_hosting import create_user_hosting, get_session_status, hosting_manager
from hosting_detector import hosting, print_startup_info
from file_sharing import share_manager
from code_formatter import code_formatter
from advanced_search import create_search_instance
from live_panel_complete import create_live_panel_app

if __name__ == "__main__":
    print("❌ Direct execution not allowed!")
    print("🔧 Please run: python bot_launcher.py")
    sys.exit(1)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID_STR = os.getenv('OWNER_ID')
ADMIN_ID_STR = os.getenv('ADMIN_ID')
YOUR_USERNAME = os.getenv('YOUR_USERNAME')
UPDATE_CHANNEL = os.getenv('UPDATE_CHANNEL')

if not TOKEN:
    logger.error("BOT_TOKEN not found in environment variables!")
    raise ValueError("BOT_TOKEN is required. Please set it in .env file or environment variables.")

if not OWNER_ID_STR or not ADMIN_ID_STR:
    logger.error("OWNER_ID or ADMIN_ID not found in environment variables!")
    raise ValueError("OWNER_ID and ADMIN_ID are required. Please set them in .env file.")

try:
    OWNER_ID = int(OWNER_ID_STR)
    ADMIN_ID = int(ADMIN_ID_STR)
except ValueError:
    logger.error("OWNER_ID or ADMIN_ID must be valid integers!")
    raise

YOUR_USERNAME = YOUR_USERNAME or '@DARK22v'
UPDATE_CHANNEL = UPDATE_CHANNEL or 'https://t.me/DARK22v'

BASE_DIR = Path(__file__).parent.absolute()
UPLOAD_BOTS_DIR = BASE_DIR / 'upload_bots'
IROTECH_DIR = BASE_DIR / 'inf'
DATABASE_PATH = IROTECH_DIR / 'bot_data.db'

FREE_USER_LIMIT = 20
SUBSCRIBED_USER_LIMIT = 50
ADMIN_LIMIT = 999
OWNER_LIMIT = float('inf')
SCRIPT_TIMEOUT = 3600
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_ZIP_SIZE = 100 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.py', '.js', '.zip'}
FILENAME_REGEX = re.compile(r'^[a-zA-Z0-9_\-\.]+$')

UPLOAD_BOTS_DIR.mkdir(exist_ok=True)
IROTECH_DIR.mkdir(exist_ok=True)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

bot_scripts = {}
user_subscriptions = {}
user_files = {}
user_favorites = {}
banned_users = set()
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False
bot_stats = {'total_uploads': 0, 'total_downloads': 0, 'total_runs': 0}

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()

def sanitize_filename(filename):
    if not filename:
        return None
    filename = os.path.basename(filename)
    if not FILENAME_REGEX.match(filename):
        return None
    if '..' in filename or filename.startswith('.'):
        return None
    return filename

def get_safe_file_path(user_id, filename):
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        raise ValueError("Invalid filename")
    
    user_folder = UPLOAD_BOTS_DIR / str(user_id)
    file_path = user_folder / safe_filename
    
    if not file_path.resolve().is_relative_to(user_folder.resolve()):
        raise ValueError("Path traversal detected")
    
    return file_path

def migrate_db():
    logger.info("Running database migrations...")
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            c.execute("PRAGMA table_info(user_files)")
            columns = [row[1] for row in c.fetchall()]
            if 'upload_date' not in columns:
                logger.info("Adding upload_date column to user_files table...")
                c.execute('ALTER TABLE user_files ADD COLUMN upload_date TEXT')
                logger.info("upload_date column added successfully.")
            
            c.execute("PRAGMA table_info(active_users)")
            columns = [row[1] for row in c.fetchall()]
            if 'join_date' not in columns:
                logger.info("Adding join_date column to active_users table...")
                c.execute('ALTER TABLE active_users ADD COLUMN join_date TEXT')
                logger.info("join_date column added successfully.")
            if 'last_active' not in columns:
                logger.info("Adding last_active column to active_users table...")
                c.execute('ALTER TABLE active_users ADD COLUMN last_active TEXT')
                logger.info("last_active column added successfully.")
        
        logger.info("Database migrations completed successfully.")
    except Exception as e:
        logger.error(f"Database migration error: {e}", exc_info=True)

def init_db():
    logger.info(f"Initializing database at: {DATABASE_PATH}")
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                         (user_id INTEGER PRIMARY KEY, expiry TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS user_files
                         (user_id INTEGER, file_name TEXT, file_type TEXT, upload_date TEXT,
                          PRIMARY KEY (user_id, file_name))''')
            c.execute('''CREATE TABLE IF NOT EXISTS active_users
                         (user_id INTEGER PRIMARY KEY, join_date TEXT, last_active TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS admins
                         (user_id INTEGER PRIMARY KEY)''')
            c.execute('''CREATE TABLE IF NOT EXISTS banned_users
                         (user_id INTEGER PRIMARY KEY, banned_date TEXT, reason TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS favorites
                         (user_id INTEGER, file_name TEXT, PRIMARY KEY (user_id, file_name))''')
            c.execute('''CREATE TABLE IF NOT EXISTS bot_stats
                         (stat_name TEXT PRIMARY KEY, stat_value INTEGER)''')
            
            c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (OWNER_ID,))
            if ADMIN_ID != OWNER_ID:
                c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (ADMIN_ID,))
            
            for stat in ['total_uploads', 'total_downloads', 'total_runs']:
                c.execute('INSERT OR IGNORE INTO bot_stats (stat_name, stat_value) VALUES (?, 0)', (stat,))
        
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}", exc_info=True)

def load_data():
    logger.info("Loading data from database...")
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            c.execute('SELECT user_id, expiry FROM subscriptions')
            for user_id, expiry in c.fetchall():
                try:
                    user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
                except ValueError:
                    logger.warning(f"Invalid expiry date for user {user_id}")
            
            c.execute('SELECT user_id, file_name, file_type FROM user_files')
            for user_id, file_name, file_type in c.fetchall():
                if user_id not in user_files:
                    user_files[user_id] = []
                user_files[user_id].append((file_name, file_type))
            
            c.execute('SELECT user_id FROM active_users')
            active_users.update(user_id for (user_id,) in c.fetchall())
            
            c.execute('SELECT user_id FROM admins')
            admin_ids.update(user_id for (user_id,) in c.fetchall())
            
            c.execute('SELECT user_id FROM banned_users')
            banned_users.update(user_id for (user_id,) in c.fetchall())
            
            c.execute('SELECT user_id, file_name FROM favorites')
            for user_id, file_name in c.fetchall():
                if user_id not in user_favorites:
                    user_favorites[user_id] = []
                user_favorites[user_id].append(file_name)
            
            c.execute('SELECT stat_name, stat_value FROM bot_stats')
            for stat_name, stat_value in c.fetchall():
                bot_stats[stat_name] = stat_value
        
        logger.info(f"Data loaded: {len(active_users)} users, {len(banned_users)} banned, {len(admin_ids)} admins.")
    except Exception as e:
        logger.error(f"Error loading data: {e}", exc_info=True)

init_db()
migrate_db()
load_data()

async def is_admin_user(user_id: int, callback_query=None) -> bool:
    if user_id not in admin_ids:
        if callback_query:
            await callback_query.answer("🔒 Admin Only Bot!", show_alert=True)
        return False
    return True

def get_user_file_limit(user_id):
    if user_id == OWNER_ID: return OWNER_LIMIT
    if user_id in admin_ids: return ADMIN_LIMIT
    if user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now():
        return SUBSCRIBED_USER_LIMIT
    return FREE_USER_LIMIT

def get_main_keyboard(user_id):
    if user_id in admin_ids:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Updates", url=UPDATE_CHANNEL)],
            [InlineKeyboardButton(text="🌐 Web Panel", callback_data="get_web_panel"),
             InlineKeyboardButton(text="📤 Upload File", callback_data="upload_file")],
            [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
             InlineKeyboardButton(text="⭐ Favorites", callback_data="my_favorites")],
            [InlineKeyboardButton(text="🔍 Smart Search", callback_data="advanced_search"),
             InlineKeyboardButton(text="📤 My Shares", callback_data="view_shares")],
            [InlineKeyboardButton(text="📊 Stats", callback_data="statistics"),
             InlineKeyboardButton(text="🎯 Features", callback_data="all_features")],
            [InlineKeyboardButton(text="👨‍💼 Admin Panel", callback_data="admin_panel"),
             InlineKeyboardButton(text="💬 Contact", url=f"https://t.me/{YOUR_USERNAME.replace('@', '')}")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Updates Channel", url=UPDATE_CHANNEL)],
            [InlineKeyboardButton(text="🌐 Get Web Panel", callback_data="get_web_panel")],
            [InlineKeyboardButton(text="📤 Upload File", callback_data="upload_file"),
             InlineKeyboardButton(text="📁 My Files", callback_data="check_files")],
            [InlineKeyboardButton(text="⭐ Favorites", callback_data="my_favorites"),
             InlineKeyboardButton(text="🔍 Search", callback_data="search_files")],
            [InlineKeyboardButton(text="⚡ Speed", callback_data="bot_speed"),
             InlineKeyboardButton(text="📊 Stats", callback_data="statistics")],
            [InlineKeyboardButton(text="💎 Premium", callback_data="get_premium"),
             InlineKeyboardButton(text="ℹ️ Help", callback_data="help_info")],
            [InlineKeyboardButton(text="🎯 Features", callback_data="all_features"),
             InlineKeyboardButton(text="💬 Contact", url=f"https://t.me/{YOUR_USERNAME.replace('@', '')}")]
        ])
    return keyboard

def get_admin_panel_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 User Stats", callback_data="admin_total_users"),
         InlineKeyboardButton(text="📁 Files Stats", callback_data="admin_total_files")],
        [InlineKeyboardButton(text="🚀 Running Scripts", callback_data="admin_running_scripts"),
         InlineKeyboardButton(text="💎 Premium Users", callback_data="admin_premium_users")],
        [InlineKeyboardButton(text="➕ Add Admin", callback_data="admin_add_admin"),
         InlineKeyboardButton(text="➖ Remove Admin", callback_data="admin_remove_admin")],
        [InlineKeyboardButton(text="🚫 Ban User", callback_data="admin_ban_user"),
         InlineKeyboardButton(text="✅ Unban User", callback_data="admin_unban_user")],
        [InlineKeyboardButton(text="📊 Bot Analytics", callback_data="admin_analytics"),
         InlineKeyboardButton(text="⚙️ System Info", callback_data="admin_system_status")],
        [InlineKeyboardButton(text="🔒 Lock/Unlock", callback_data="lock_bot"),
         InlineKeyboardButton(text="📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton(text="🗑️ Clean Files", callback_data="admin_clean_files"),
         InlineKeyboardButton(text="💾 Backup DB", callback_data="admin_backup_db")],
        [InlineKeyboardButton(text="📝 View Logs", callback_data="admin_view_logs"),
         InlineKeyboardButton(text="🔄 Restart Bot", callback_data="admin_restart_bot")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
    ])
    return keyboard

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in admin_ids:
        await message.answer(
            "🔒 <b>ADMIN ONLY BOT</b>\n\n"
            "⚠️ This bot is restricted to authorized administrators only.\n\n"
            "👑 <b>Owner:</b> @DARK22v\n"
            "📢 <b>Channel:</b> https://t.me/DARK22v\n\n"
            "<i>💫 MADE BY DARK SHADOW 💫</i>",
            parse_mode="HTML"
        )
        logger.warning(f"Unauthorized access attempt by user {user_id} (@{message.from_user.username})")
        return
    
    if user_id in banned_users:
        await message.answer("🚫 <b>You are banned from using this bot!</b>\n\nContact admin for more info.", parse_mode="HTML")
        return
    
    active_users.add(user_id)
    
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute('INSERT OR REPLACE INTO active_users (user_id, join_date, last_active) VALUES (?, ?, ?)', 
                      (user_id, now, now))
    except Exception as e:
        logger.error(f"Error saving active user: {e}")
    
    welcome_text = f"""
╔═══════════════════════╗
    🌟 <b>WELCOME TO FILE HOST BOT</b> 🌟
╚═══════════════════════╝

👋 <b>Hi,</b> {message.from_user.full_name}!

🆔 <b>Your ID:</b> <code>{user_id}</code>
📦 <b>Upload Limit:</b> {get_user_file_limit(user_id)} files
💎 <b>Account:</b> {'Premium ✨' if user_id in user_subscriptions else 'Free 🆓'}

━━━━━━━━━━━━━━━━━━━━
<b>🎯 FREE USER FEATURES:</b>

📤 <b>Upload Files</b> - Upload Python, JS, ZIP files
📁 <b>Manage Files</b> - View, delete, organize
⭐ <b>Add Favorites</b> - Quick access to files
🔍 <b>Search Files</b> - Find files easily
▶️ <b>Run Scripts</b> - Execute Python/JS code
🛑 <b>Stop Scripts</b> - Control running code
📊 <b>View Stats</b> - Your usage statistics
⚡ <b>Speed Test</b> - Check bot response
📥 <b>Download Files</b> - Get your files
💾 <b>File Info</b> - Size, type, date details
ℹ️ <b>Help & Support</b> - Get assistance
🎯 <b>Feature List</b> - Explore all features

━━━━━━━━━━━━━━━━━━━━
<b>✨ Start exploring now! ✨</b>

<i>💫 MADE BY DARK SHADOW 💫</i>
"""
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")

@dp.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    welcome_text = f"""
╔═══════════════════════╗
    🏠 <b>MAIN MENU</b> 🏠
╚═══════════════════════╝

👤 <b>User:</b> {callback.from_user.full_name}
🆔 <b>ID:</b> <code>{user_id}</code>
📦 <b>Files:</b> {len(user_files.get(user_id, []))}/{get_user_file_limit(user_id)}

Use buttons below to navigate 👇
"""
    await callback.message.edit_text(welcome_text, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "upload_file")
async def callback_upload_file(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    if bot_locked and user_id not in admin_ids:
        await callback.answer("🔒 Bot is locked for maintenance!", show_alert=True)
        return
    
    current_files = len(user_files.get(user_id, []))
    limit = get_user_file_limit(user_id)
    
    upload_text = f"""
╔═══════════════════════╗
    📤 <b>UPLOAD FILES</b> 📤
╚═══════════════════════╝

📊 <b>Current Usage:</b> {current_files}/{limit} files

📝 <b>Supported Formats:</b>
🐍 Python (.py)
🟨 JavaScript (.js)
📦 ZIP Archives (.zip)

━━━━━━━━━━━━━━━━━━━━
<b>💡 How to Upload:</b>

1️⃣ Send your file to the bot
2️⃣ Wait for upload confirmation
3️⃣ File will be saved automatically

⚡ <b>Upload limit:</b> {limit} files
🔥 <b>Quick & Easy!</b>
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(upload_text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "check_files")
async def callback_check_files(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    files = user_files.get(user_id, [])
    
    if not files:
        text = """
╔═══════════════════════╗
    📁 <b>MY FILES</b> 📁
╚═══════════════════════╝

📭 <b>No files found!</b>

Upload your first file to get started! 🚀
"""
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Upload File", callback_data="upload_file")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
        ])
    else:
        text = f"""
╔═══════════════════════╗
    📁 <b>MY FILES ({len(files)})</b> 📁
╚═══════════════════════╝

"""
        buttons = []
        for i, (file_name, file_type) in enumerate(files, 1):
            icon = "🐍" if file_type == "py" else "🟨" if file_type == "js" else "📦"
            text += f"{i}. {icon} <code>{file_name}</code>\n"
            
            is_favorite = file_name in user_favorites.get(user_id, [])
            star = "⭐" if is_favorite else "☆"
            
            buttons.append([
                InlineKeyboardButton(text=f"▶️ Run {file_name[:15]}", callback_data=f"run_script:{file_name}"),
                InlineKeyboardButton(text=f"{star}", callback_data=f"toggle_fav:{file_name}")
            ])
            buttons.append([
                InlineKeyboardButton(text=f"ℹ️ Info {file_name[:15]}", callback_data=f"file_info:{file_name}"),
                InlineKeyboardButton(text=f"🗑️ Delete", callback_data=f"delete_file:{file_name}")
            ])
        
        buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")])
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "my_favorites")
async def callback_my_favorites(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    favorites = user_favorites.get(user_id, [])
    
    if not favorites:
        text = """
╔═══════════════════════╗
    ⭐ <b>FAVORITES</b> ⭐
╚═══════════════════════╝

💭 No favorite files yet!

Add files to favorites for quick access! 🚀
"""
        buttons = [[InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]]
    else:
        text = f"""
╔═══════════════════════╗
    ⭐ <b>FAVORITES ({len(favorites)})</b> ⭐
╚═══════════════════════╝

"""
        buttons = []
        for i, file_name in enumerate(favorites, 1):
            text += f"{i}. ⭐ <code>{file_name}</code>\n"
            buttons.append([
                InlineKeyboardButton(text=f"▶️ {file_name[:20]}", callback_data=f"run_script:{file_name}"),
                InlineKeyboardButton(text=f"❌", callback_data=f"toggle_fav:{file_name}")
            ])
        
        buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")])
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "advanced_search")
async def callback_advanced_search(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    text = """
╔═══════════════════════╗
    🔍 <b>ADVANCED SEARCH</b> 🔍
╚═══════════════════════╝

<b>Search Features:</b>

🔤 <b>Smart Search</b>
   Search by filename OR file content
   Usage: /search keyword

📝 <b>Content Search</b>
   Find text inside your files
   Supports regex patterns

📂 <b>File Type Filter</b>
   Search by extension (.py, .js, .zip)

📊 <b>Size Filter</b>
   Find large or small files

📅 <b>Recent Files</b>
   Files modified in last 7 days

<b>Examples:</b>
• <code>/search function</code> - Find "function" in names/content
• <code>/search import.*requests</code> - Regex search
• <code>/search .py</code> - All Python files

💡 Try: /search &lt;your_query&gt;
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
         InlineKeyboardButton(text="🏠 Home", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "view_shares")
async def callback_view_shares(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    shares = share_manager.get_user_shares(user_id)
    
    if not shares:
        text = """
╔═══════════════════════╗
    📤 <b>MY SHARES</b> 📤
╚═══════════════════════╝

No active share links found.

💡 <b>How to share files:</b>
1. Go to My Files
2. Select a file
3. Click "Share" button
4. Choose expiry time

<b>Share Options:</b>
⏰ 1 Hour - Quick access
📅 24 Hours - Day access
📆 7 Days - Week access
♾️ 30 Days - Long-term
"""
    else:
        text = f"""
╔═══════════════════════╗
    📤 <b>MY SHARES</b> 📤
╚═══════════════════════╝

<b>Total Active Shares:</b> {len(shares)}

"""
        for share in shares[:8]:
            status = "🔴 Expired" if share['is_expired'] else "🟢 Active"
            text += f"""
📄 <b>{share['filename']}</b>
   {status} • {share['hours_left']}h left
   📥 {share['downloads']} downloads

"""
        
        if len(shares) > 8:
            text += f"\n<i>... and {len(shares) - 8} more</i>\n"
        
        text += "\n💡 Use /myshares for full list with links"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
         InlineKeyboardButton(text="🏠 Home", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "search_files")
async def callback_search_files(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    files = user_files.get(user_id, [])
    
    text = f"""
╔═══════════════════════╗
    🔍 <b>SEARCH FILES</b> 🔍
╚═══════════════════════╝

📊 <b>Total Files:</b> {len(files)}

<b>File Types:</b>
🐍 Python: {sum(1 for f in files if f[1] == 'py')}
🟨 JavaScript: {sum(1 for f in files if f[1] == 'js')}
📦 ZIP: {sum(1 for f in files if f[1] == 'zip')}

━━━━━━━━━━━━━━━━━━━━
To search, use:
<code>/search filename</code>
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 View All Files", callback_data="check_files")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "bot_speed")
async def callback_bot_speed(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    start_time = datetime.now()
    await callback.answer("⚡ Testing...")
    end_time = datetime.now()
    speed = (end_time - start_time).total_seconds() * 1000
    
    if speed < 100:
        status = "🟢 Excellent"
        emoji = "🚀"
    elif speed < 300:
        status = "🟡 Good"
        emoji = "⚡"
    else:
        status = "🔴 Slow"
        emoji = "🐌"
    
    text = f"""
╔═══════════════════════╗
    ⚡ <b>SPEED TEST</b> ⚡
╚═══════════════════════╝

{emoji} <b>Response Time:</b> {speed:.2f}ms
📊 <b>Status:</b> {status}

🖥️ <b>Server Info:</b>
• CPU: {psutil.cpu_percent()}%
• Memory: {psutil.virtual_memory().percent}%
• Uptime: Online ✅

✨ Bot is running smoothly!
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Test Again", callback_data="bot_speed"),
         InlineKeyboardButton(text="🏠 Home", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "statistics")
async def callback_statistics(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    user_file_count = len(user_files.get(user_id, []))
    user_fav_count = len(user_favorites.get(user_id, []))
    limit = get_user_file_limit(user_id)
    is_premium = user_id in user_subscriptions
    
    text = f"""
╔═══════════════════════╗
    📊 <b>YOUR STATISTICS</b> 📊
╚═══════════════════════╝

👤 <b>User:</b> {callback.from_user.full_name}
🆔 <b>ID:</b> <code>{user_id}</code>

━━━━━━━━━━━━━━━━━━━━
📦 <b>FILE STATISTICS:</b>

📁 Total Files: {user_file_count}/{limit}
⭐ Favorites: {user_fav_count}
💎 Account: {'Premium ✨' if is_premium else 'Free 🆓'}
🚀 Running: {sum(1 for k in bot_scripts if k.startswith(f"{user_id}_"))}

━━━━━━━━━━━━━━━━━━━━
📈 <b>USAGE:</b>

📤 Uploads: {bot_stats.get('total_uploads', 0)}
📥 Downloads: {bot_stats.get('total_downloads', 0)}
▶️ Script Runs: {bot_stats.get('total_runs', 0)}

{'✅ Bot Status: Active' if not bot_locked else '🔒 Bot: Maintenance'}
"""
    
    if user_id in admin_ids:
        text += f"\n━━━━━━━━━━━━━━━━━━━━\n👑 <b>ADMIN STATS:</b>\n"
        text += f"👥 Total Users: {len(active_users)}\n"
        text += f"📁 Total Files: {sum(len(files) for files in user_files.values())}\n"
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "help_info")
async def callback_help_info(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    text = """
╔═══════════════════════╗
    ℹ️ <b>HELP & INFO</b> ℹ️
╚═══════════════════════╝

<b>🎯 HOW TO USE:</b>

1️⃣ <b>Upload Files:</b>
   • Click 'Upload File'
   • Send your .py, .js, or .zip file
   • File will be saved automatically

2️⃣ <b>Run Scripts:</b>
   • Go to 'My Files'
   • Click 'Run' on any file
   • Monitor script execution

3️⃣ <b>Manage Files:</b>
   • View all files in 'My Files'
   • Add to favorites with ⭐
   • Delete unwanted files

4️⃣ <b>Search:</b>
   • Use /search [filename]
   • Quick file lookup

━━━━━━━━━━━━━━━━━━━━
<b>💡 COMMANDS:</b>

/start - Start the bot
/help - Show this help
/search - Search files
/stats - Your statistics
/premium - Premium info

<b>Need help? Contact owner! 💬</b>

<i>💫 MADE BY DARK SHADOW 💫</i>
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Features", callback_data="all_features")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "all_features")
async def callback_all_features(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    text = """
╔═══════════════════════╗
    🎯 <b>ALL FEATURES</b> 🎯
╚═══════════════════════╝

<b>✨ FREE USER FEATURES (12+):</b>

1. 📤 Upload Files (Python, JS, ZIP)
2. 📁 View & Manage Files
3. ⭐ Add to Favorites
4. 🔍 Search Files by Name
5. ▶️ Run Python Scripts
6. ▶️ Run JavaScript Scripts
7. 🛑 Stop Running Scripts
8. 📊 View Your Statistics
9. ⚡ Bot Speed Test
10. 📥 Download Your Files
11. 💾 View File Information
12. ℹ️ Help & Support
13. 🎯 Feature Discovery

━━━━━━━━━━━━━━━━━━━━
<b>💎 PREMIUM FEATURES:</b>

• 50 file upload limit (vs 20)
• Priority support
• Advanced analytics
• Faster processing
• Premium badge

━━━━━━━━━━━━━━━━━━━━
<b>🔥 Upgrade to Premium!</b>
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Get Premium", callback_data="get_premium")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "get_premium")
async def callback_get_premium(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    text = """
╔═══════════════════════╗
    💎 <b>PREMIUM PLAN</b> 💎
╚═══════════════════════╝

<b>✨ PREMIUM BENEFITS:</b>

📦 50 File Upload Limit
⚡ Priority Processing
🚀 Faster Response Time
📊 Advanced Analytics
💬 Priority Support
⭐ Premium Badge
🎯 Exclusive Features
🌐 Enhanced Web Panel Access

━━━━━━━━━━━━━━━━━━━━
<b>💰 PRICING:</b>

1 Month: $5
3 Months: $12 (Save 20%)
1 Year: $40 (Save 33%)

━━━━━━━━━━━━━━━━━━━━
<b>Contact owner to upgrade! 💬</b>
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Contact Owner", url=f"https://t.me/{YOUR_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "get_web_panel")
async def callback_get_web_panel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    username = callback.from_user.username or callback.from_user.first_name
    
    # Check if user is owner or admin
    is_owner = (user_id == OWNER_ID)
    is_admin = (user_id in admin_ids)
    
    try:
        result = await create_user_hosting(user_id, username, is_owner, is_admin)
        
        # Create keyboard
        if is_owner:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👑 Open Panel", url=result['session']['public_url'])],
                [InlineKeyboardButton(text="⏰ Status", callback_data="check_session_status")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
            ])
        elif is_admin:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👨‍💼 Open Panel", url=result['session']['public_url'])],
                [InlineKeyboardButton(text="⏰ Status", callback_data="check_session_status")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
            ])
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Open Panel", url=result['session']['public_url'])],
                [InlineKeyboardButton(text="🔄 Extend", callback_data="extend_session"),
                 InlineKeyboardButton(text="⏰ Status", callback_data="check_session_status")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
            ])
        
        await callback.message.edit_text(result['message'], parse_mode="HTML", reply_markup=keyboard)
        await callback.answer("✅ Panel created!")
        
    except Exception as e:
        logger.error(f"Panel creation error: {e}")
        await callback.answer(f"❌ Error", show_alert=True)

@dp.callback_query(F.data == "extend_session")
async def callback_extend_session(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    # Owner & Admin cannot extend (already unlimited/extended)
    if user_id == OWNER_ID or user_id in admin_ids:
        await callback.answer("👑 Your session is already unlimited!", show_alert=True)
        return
    
    # Extend session
    success = await hosting_manager.extend_session(user_id, extra_minutes=15)
    
    if success:
        await callback.answer("✅ Session extended by 15 minutes!", show_alert=True)
        
        # Update status
        status = await get_session_status(user_id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Extend Again", callback_data="extend_session"),
             InlineKeyboardButton(text="⏰ Status", callback_data="check_session_status")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
        ])
        
        try:
            await callback.message.edit_text(status, parse_mode="HTML", reply_markup=keyboard)
        except:
            pass
    else:
        await callback.answer("❌ No active session found!", show_alert=True)

@dp.callback_query(F.data == "check_session_status")
async def callback_check_session_status(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    try:
        status = await get_session_status(user_id)
        
        # Create keyboard based on user type
        if user_id == OWNER_ID:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👑 Owner Session Active", callback_data="noop")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
            ])
        elif user_id in admin_ids:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👨‍💼 Admin Session Active", callback_data="noop")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
            ])
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Extend Session", callback_data="extend_session")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
            ])
        
        await callback.message.edit_text(status, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Status check error: {e}")
        await callback.answer("❌ Error checking status", show_alert=True)

@dp.callback_query(F.data == "noop")
async def callback_noop(callback: types.CallbackQuery):
    await callback.answer()

@dp.callback_query(F.data == "admin_panel")
async def callback_admin_panel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in admin_ids:
        await callback.answer("❌ Admin access required!", show_alert=True)
        return
    
    text = """
╔═══════════════════════╗
    👑 <b>ADMIN PANEL</b> 👑
╚═══════════════════════╝

<b>🎛️ CONTROL CENTER:</b>

Manage users, files, system settings
and monitor bot performance.

<b>📊 17+ Admin Features Available!</b>

Select an option below to continue...
"""
    
    await callback.message.edit_text(text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("toggle_fav:"))
async def callback_toggle_favorite(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    file_name = callback.data.split(":", 1)[1]
    
    if user_id not in user_favorites:
        user_favorites[user_id] = []
    
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            if file_name in user_favorites[user_id]:
                user_favorites[user_id].remove(file_name)
                c.execute('DELETE FROM favorites WHERE user_id = ? AND file_name = ?', (user_id, file_name))
                await callback.answer("❌ Removed from favorites!", show_alert=True)
            else:
                user_favorites[user_id].append(file_name)
                c.execute('INSERT OR IGNORE INTO favorites (user_id, file_name) VALUES (?, ?)', (user_id, file_name))
                await callback.answer("⭐ Added to favorites!", show_alert=True)
        
        await callback_check_files(callback)
        
    except Exception as e:
        logger.error(f"Error toggling favorite: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)

@dp.callback_query(F.data.startswith("file_info:"))
async def callback_file_info(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    file_name = callback.data.split(":", 1)[1]
    
    try:
        file_path = get_safe_file_path(user_id, file_name)
    except ValueError as e:
        await callback.answer(f"❌ {str(e)}", show_alert=True)
        return
    
    if not file_path.exists():
        await callback.answer("❌ File not found!", show_alert=True)
        return
    
    try:
        file_size = file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        file_ext = file_path.suffix
        modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        
        is_favorite = file_name in user_favorites.get(user_id, [])
        
        file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
        
        code_analysis = code_formatter.analyze_code(str(file_path))
        
        analysis_text = ""
        if 'total_lines' in code_analysis:
            analysis_text = f"\n📊 <b>Analysis:</b> {code_analysis['total_lines']} lines"
            if 'functions' in code_analysis:
                analysis_text += f", {code_analysis['functions']} functions"
        
        text = f"""
╔═══════════════════════╗
    ℹ️ <b>FILE INFO</b> ℹ️
╚═══════════════════════╝

📄 <b>Name:</b> <code>{file_name}</code>

📦 <b>Type:</b> {file_ext.upper()} File
💾 <b>Size:</b> {file_size_mb:.2f} MB ({file_size} bytes)
📅 <b>Modified:</b> {modified_time.strftime('%Y-%m-%d %H:%M')}
⭐ <b>Favorite:</b> {'Yes ✨' if is_favorite else 'No'}{analysis_text}

🔐 <b>SHA256:</b> <code>{file_hash}...</code>
"""
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Run", callback_data=f"run_script:{file_name}"),
             InlineKeyboardButton(text="📤 Share", callback_data=f"share_file:{file_name}")],
            [InlineKeyboardButton(text="✨ Format Code", callback_data=f"format_code:{file_name}"),
             InlineKeyboardButton(text="🗑️ Delete", callback_data=f"delete_file:{file_name}")],
            [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
             InlineKeyboardButton(text="🏠 Home", callback_data="back_to_main")]
        ])
        
        await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)

@dp.message(F.document)
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in admin_ids:
        await message.answer("🔒 <b>Admin Only Bot</b>\n\n<i>💫 MADE BY DARK SHADOW 💫</i>", parse_mode="HTML")
        return
    
    if user_id in banned_users:
        await message.answer("🚫 You are banned from using this bot!")
        return
    
    if bot_locked and user_id not in admin_ids:
        await message.answer("🔒 Bot is currently locked!")
        return
    
    document = message.document
    file_name = document.file_name
    
    safe_filename = sanitize_filename(file_name)
    if not safe_filename:
        await message.answer("❌ Invalid filename! Use only letters, numbers, dash, underscore and dot.")
        return
    
    file_ext = os.path.splitext(safe_filename)[1].lower()
    
    if file_ext not in ALLOWED_EXTENSIONS:
        await message.answer("❌ Only .py, .js, and .zip files are supported!")
        return
    
    if document.file_size > MAX_FILE_SIZE:
        await message.answer(f"❌ File too large! Maximum size: {MAX_FILE_SIZE / (1024*1024):.0f} MB")
        return
    
    current_files = len(user_files.get(user_id, []))
    limit = get_user_file_limit(user_id)
    
    if current_files >= limit:
        await message.answer(f"❌ Upload limit reached! ({current_files}/{limit})\n\n💎 Upgrade to premium for more space!")
        return
    
    user_folder = UPLOAD_BOTS_DIR / str(user_id)
    user_folder.mkdir(exist_ok=True)
    
    try:
        file_path = get_safe_file_path(user_id, safe_filename)
    except ValueError as e:
        await message.answer(f"❌ {str(e)}")
        return
    
    try:
        file_size_kb = document.file_size / 1024
        
        status_msg = await message.answer(
            f"📤 <b>Preparing upload...</b>\n\n"
            f"📄 File: <code>{safe_filename}</code>\n"
            f"💾 Size: {file_size_kb:.2f} KB\n\n"
            f"▓░░░░░░░░░ 0%",
            parse_mode="HTML"
        )
        
        await status_msg.edit_text(
            f"📥 <b>Downloading...</b>\n\n"
            f"📄 File: <code>{safe_filename}</code>\n"
            f"💾 Size: {file_size_kb:.2f} KB\n\n"
            f"▓▓▓░░░░░░░ 30%",
            parse_mode="HTML"
        )
        
        await bot.download(document, destination=file_path)
        
        await status_msg.edit_text(
            f"💾 <b>Saving to database...</b>\n\n"
            f"📄 File: <code>{safe_filename}</code>\n"
            f"💾 Size: {file_size_kb:.2f} KB\n\n"
            f"▓▓▓▓▓▓▓░░░ 70%",
            parse_mode="HTML"
        )
        
        if user_id not in user_files:
            user_files[user_id] = []
        
        user_files[user_id].append((safe_filename, file_ext[1:]))
        
        with get_db_connection() as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute('INSERT OR REPLACE INTO user_files (user_id, file_name, file_type, upload_date) VALUES (?, ?, ?, ?)',
                      (user_id, safe_filename, file_ext[1:], now))
            c.execute('UPDATE bot_stats SET stat_value = stat_value + 1 WHERE stat_name = ?', ('total_uploads',))
        
        bot_stats['total_uploads'] = bot_stats.get('total_uploads', 0) + 1
        
        await status_msg.edit_text(
            f"✅ <b>Finalizing...</b>\n\n"
            f"📄 File: <code>{safe_filename}</code>\n"
            f"💾 Size: {file_size_kb:.2f} KB\n\n"
            f"▓▓▓▓▓▓▓▓▓▓ 100%",
            parse_mode="HTML"
        )
        
        if file_ext == '.zip':
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 Extract ZIP", callback_data=f"extract_zip:{safe_filename}"),
                 InlineKeyboardButton(text="⭐ Add Favorite", callback_data=f"toggle_fav:{safe_filename}")],
                [InlineKeyboardButton(text="ℹ️ File Info", callback_data=f"file_info:{safe_filename}"),
                 InlineKeyboardButton(text="🗑️ Delete", callback_data=f"delete_file:{safe_filename}")],
                [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
                 InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
            ])
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Run Now", callback_data=f"run_script:{safe_filename}"),
                 InlineKeyboardButton(text="⭐ Add Favorite", callback_data=f"toggle_fav:{safe_filename}")],
                [InlineKeyboardButton(text="ℹ️ File Info", callback_data=f"file_info:{safe_filename}"),
                 InlineKeyboardButton(text="🗑️ Delete", callback_data=f"delete_file:{safe_filename}")],
                [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
                 InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
            ])
        
        await status_msg.edit_text(
            f"""
╔═══════════════════════╗
    ✅ <b>UPLOAD SUCCESS!</b> ✅
╚═══════════════════════╝

📄 <b>File:</b> <code>{safe_filename}</code>
📦 <b>Type:</b> {file_ext[1:].upper()}
💾 <b>Size:</b> {document.file_size / 1024:.2f} KB
📊 <b>Usage:</b> {current_files + 1}/{limit}

🎉 File uploaded successfully!
✨ <b>Tip:</b> Click "Share" to create a temporary link!
""",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        await message.answer(f"❌ Upload failed: {str(e)}")

@dp.callback_query(F.data.startswith("run_script:"))
async def callback_run_script(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    file_name = callback.data.split(":", 1)[1]
    
    try:
        file_path = get_safe_file_path(user_id, file_name)
    except ValueError as e:
        await callback.answer(f"❌ {str(e)}", show_alert=True)
        return
    
    if not file_path.exists():
        await callback.answer("❌ File not found!", show_alert=True)
        return
    
    script_key = f"{user_id}_{file_name}"
    
    if script_key in bot_scripts:
        await callback.answer("⚠️ Script is already running!", show_alert=True)
        return
    
    file_ext = file_path.suffix.lower()
    
    if file_ext not in ['.py', '.js']:
        await callback.answer("❌ Can only run .py or .js files!", show_alert=True)
        return
    
    try:
        user_folder = UPLOAD_BOTS_DIR / str(user_id)
        log_file_path = user_folder / f"{file_path.stem}.log"
        log_file = open(log_file_path, 'w', encoding='utf-8')
        
        if file_ext == '.py':
            process = subprocess.Popen(
                [sys.executable, str(file_path)],
                cwd=str(user_folder),
                stdout=log_file,
                stderr=log_file,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
        elif file_ext == '.js':
            process = subprocess.Popen(
                ['node', str(file_path)],
                cwd=str(user_folder),
                stdout=log_file,
                stderr=log_file,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
        else:
            log_file.close()
            await callback.answer("❌ Cannot run this file type!", show_alert=True)
            return
        
        bot_scripts[script_key] = {
            'process': process,
            'file_name': file_name,
            'script_owner_id': user_id,
            'start_time': datetime.now(),
            'user_folder': str(user_folder),
            'type': file_ext[1:],
            'log_file': log_file
        }
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE bot_stats SET stat_value = stat_value + 1 WHERE stat_name = ?', ('total_runs',))
        
        bot_stats['total_runs'] = bot_stats.get('total_runs', 0) + 1
        
        asyncio.create_task(monitor_script_timeout(script_key, SCRIPT_TIMEOUT))
        
        await callback.answer(f"✅ Script started! (PID: {process.pid})", show_alert=True)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛑 Stop Script", callback_data=f"stop_script:{script_key}")],
            [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
             InlineKeyboardButton(text="🏠 Home", callback_data="back_to_main")]
        ])
        
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        
    except FileNotFoundError as e:
        logger.error(f"Executable not found: {e}")
        await callback.answer(f"❌ {'Python' if file_ext == '.py' else 'Node.js'} not installed!", show_alert=True)
    except Exception as e:
        logger.error(f"Error running script: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)

async def monitor_script_timeout(script_key, timeout):
    await asyncio.sleep(timeout)
    
    if script_key in bot_scripts:
        logger.warning(f"Script {script_key} exceeded timeout, terminating...")
        try:
            script_info = bot_scripts[script_key]
            process = script_info['process']
            log_file = script_info.get('log_file')
            
            if log_file and not log_file.closed:
                log_file.write(f"\n\n[SYSTEM] Script terminated after {timeout}s timeout\n")
                log_file.close()
            
            terminate_process_tree(process.pid)
            
            del bot_scripts[script_key]
        except Exception as e:
            logger.error(f"Error in timeout handler: {e}")

def terminate_process_tree(pid):
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        
        try:
            parent.terminate()
        except psutil.NoSuchProcess:
            pass
        
        gone, alive = psutil.wait_procs(children + [parent], timeout=3)
        
        for p in alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        logger.warning(f"Process {pid} already terminated")
    except Exception as e:
        logger.error(f"Error terminating process tree: {e}")

@dp.callback_query(F.data.startswith("stop_script:"))
async def callback_stop_script(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    script_key = callback.data.split(":", 1)[1]
    
    if script_key not in bot_scripts:
        await callback.answer("❌ Script not found or already stopped!", show_alert=True)
        return
    
    try:
        script_info = bot_scripts[script_key]
        process = script_info['process']
        log_file = script_info.get('log_file')
        
        if log_file and not log_file.closed:
            log_file.write("\n\n[SYSTEM] Script stopped by user\n")
            log_file.close()
        
        terminate_process_tree(process.pid)
        
        del bot_scripts[script_key]
        
        await callback.answer("✅ Script stopped successfully!", show_alert=True)
        
        if callback.from_user.id in admin_ids:
            await callback.message.edit_text("🛑 Script stopped!", parse_mode="HTML")
        else:
            await callback_back_to_main(callback)
        
    except Exception as e:
        logger.error(f"Error stopping script: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)

@dp.callback_query(F.data.startswith("extract_zip:"))
async def callback_extract_zip(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    file_name = callback.data.split(":", 1)[1]
    
    try:
        zip_path = get_safe_file_path(user_id, file_name)
    except ValueError as e:
        await callback.answer(f"❌ {str(e)}", show_alert=True)
        return
    
    if not zip_path.exists():
        await callback.answer("❌ ZIP file not found!", show_alert=True)
        return
    
    if zip_path.stat().st_size > MAX_ZIP_SIZE:
        await callback.answer(f"❌ ZIP file too large! Max: {MAX_ZIP_SIZE/(1024*1024):.0f} MB", show_alert=True)
        return
    
    if not zipfile.is_zipfile(zip_path):
        await callback.answer("❌ Invalid ZIP file!", show_alert=True)
        return
    
    try:
        status_text = f"""
╔═══════════════════════╗
    📦 <b>EXTRACTING ZIP</b> 📦
╚═══════════════════════╝

📄 File: <code>{file_name}</code>
⏳ Status: <b>Extracting...</b>

Please wait...
"""
        await callback.message.edit_text(status_text, parse_mode="HTML")
        
        user_folder = UPLOAD_BOTS_DIR / str(user_id)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            all_files = zip_ref.namelist()
            
            if len(all_files) > 100:
                await callback.answer("❌ Too many files in ZIP (max 100)!", show_alert=True)
                return
            
            total_size = sum(info.file_size for info in zip_ref.infolist())
            if total_size > MAX_ZIP_SIZE * 2:
                await callback.answer("❌ Extracted size too large!", show_alert=True)
                return
            
            for file_info in zip_ref.infolist():
                extract_name = os.path.basename(file_info.filename)
                if extract_name and not file_info.is_dir():
                    safe_name = sanitize_filename(extract_name)
                    if safe_name:
                        extract_path = user_folder / safe_name
                        if extract_path.resolve().is_relative_to(user_folder.resolve()):
                            with zip_ref.open(file_info) as source:
                                with open(extract_path, 'wb') as target:
                                    target.write(source.read())
        
        registered_files = []
        with get_db_connection() as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            
            for extracted_file in all_files:
                if extracted_file.endswith('/'):
                    continue
                
                file_path = Path(extracted_file)
                file_ext = file_path.suffix.lower()
                
                if file_ext in ['.py', '.js']:
                    just_name = sanitize_filename(file_path.name)
                    if not just_name:
                        continue
                    
                    if user_id not in user_files:
                        user_files[user_id] = []
                    
                    user_files[user_id].append((just_name, file_ext[1:]))
                    
                    c.execute('INSERT OR REPLACE INTO user_files (user_id, file_name, file_type, upload_date) VALUES (?, ?, ?, ?)',
                              (user_id, just_name, file_ext[1:], now))
                    
                    registered_files.append(just_name)
            
            if user_id in user_files:
                user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
            
            c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
            c.execute('DELETE FROM favorites WHERE user_id = ? AND file_name = ?', (user_id, file_name))
        
        if zip_path.exists():
            zip_path.unlink()
        
        registered_text = "\n".join([f"  • <code>{f}</code>" for f in registered_files[:10]])
        if len(registered_files) > 10:
            registered_text += f"\n  ... and {len(registered_files) - 10} more files"
        elif len(registered_files) == 0:
            registered_text = "  <i>No .py or .js files found</i>"
        
        current_count = len(user_files.get(user_id, []))
        limit = get_user_file_limit(user_id)
        
        success_text = f"""
╔═══════════════════════╗
    ✅ <b>EXTRACTION SUCCESS!</b> ✅
╚═══════════════════════╝

📄 <b>ZIP File:</b> <code>{file_name}</code>
📊 <b>Total Extracted:</b> {len(all_files)} files
✅ <b>Registered:</b> {len(registered_files)} files (.py, .js)
🗑️ <b>ZIP Deleted:</b> Automatically

<b>📋 Registered Files:</b>
{registered_text}

📦 <b>Your Files:</b> {current_count}/{limit}

✨ Extraction completed successfully!
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
             InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
        ])
        
        await callback.message.edit_text(success_text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer("✅ ZIP extracted & registered!")
        
    except zipfile.BadZipFile:
        await callback.answer("❌ Corrupted ZIP file!", show_alert=True)
    except Exception as e:
        logger.error(f"Error extracting ZIP: {e}", exc_info=True)
        await callback.answer(f"❌ Extraction failed: {str(e)}", show_alert=True)

@dp.callback_query(F.data.startswith("delete_file:"))
async def callback_delete_file(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    file_name = callback.data.split(":", 1)[1]
    
    try:
        file_path = get_safe_file_path(user_id, file_name)
    except ValueError as e:
        await callback.answer(f"❌ {str(e)}", show_alert=True)
        return
    
    try:
        if file_path.exists():
            file_path.unlink()
        
        if user_id in user_files:
            user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
        
        if file_name in user_favorites.get(user_id, []):
            user_favorites[user_id].remove(file_name)
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
            c.execute('DELETE FROM favorites WHERE user_id = ? AND file_name = ?', (user_id, file_name))
        
        await callback.answer("✅ File deleted successfully!", show_alert=True)
        await callback_check_files(callback)
        
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)

@dp.callback_query(F.data == "admin_total_users")
async def callback_admin_total_users(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    user_list = "\n".join([f"• <code>{uid}</code>" for uid in list(active_users)[:15]])
    text = f"""
╔═══════════════════════╗
    👥 <b>USER STATISTICS</b> 👥
╚═══════════════════════╝

📊 <b>Total Users:</b> {len(active_users)}
🚫 <b>Banned:</b> {len(banned_users)}
✅ <b>Active:</b> {len(active_users) - len(banned_users)}

<b>📝 Recent Users (15):</b>
{user_list}

{'...' if len(active_users) > 15 else ''}
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_total_files")
async def callback_admin_total_files(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    total_files = sum(len(files) for files in user_files.values())
    py_files = sum(1 for files in user_files.values() for f in files if f[1] == 'py')
    js_files = sum(1 for files in user_files.values() for f in files if f[1] == 'js')
    zip_files = sum(1 for files in user_files.values() for f in files if f[1] == 'zip')
    
    text = f"""
╔═══════════════════════╗
    📁 <b>FILE STATISTICS</b> 📁
╚═══════════════════════╝

📊 <b>Total Files:</b> {total_files}

<b>📦 By Type:</b>
🐍 Python: {py_files}
🟨 JavaScript: {js_files}
📦 ZIP: {zip_files}

<b>📈 Top Users:</b>
"""
    
    top_users = sorted(user_files.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    for user_id, files in top_users:
        text += f"• User <code>{user_id}</code>: {len(files)} files\n"
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_running_scripts")
async def callback_admin_running_scripts(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    if not bot_scripts:
        text = """
╔═══════════════════════╗
    🚀 <b>RUNNING SCRIPTS</b> 🚀
╚═══════════════════════╝

💤 No scripts running currently
"""
        buttons = []
    else:
        text = f"""
╔═══════════════════════╗
    🚀 <b>RUNNING ({len(bot_scripts)})</b> 🚀
╚═══════════════════════╝

"""
        buttons = []
        for script_key, info in bot_scripts.items():
            runtime = (datetime.now() - info['start_time']).total_seconds()
            text += f"🔸 <code>{info['file_name']}</code>\n"
            text += f"   PID: {info['process'].pid} | User: {info['script_owner_id']}\n"
            text += f"   Runtime: {int(runtime)}s\n\n"
            buttons.append([InlineKeyboardButton(
                text=f"🛑 Stop {info['file_name'][:15]}", 
                callback_data=f"stop_script:{script_key}"
            )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")])
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_premium_users")
async def callback_admin_premium_users(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    premium_users = [(u, data) for u, data in user_subscriptions.items() if data['expiry'] > datetime.now()]
    
    if not premium_users:
        text = """
╔═══════════════════════╗
    💎 <b>PREMIUM USERS</b> 💎
╚═══════════════════════╝

No active premium subscriptions.
"""
    else:
        text = f"""
╔═══════════════════════╗
    💎 <b>PREMIUM ({len(premium_users)})</b> 💎
╚═══════════════════════╝

"""
        for user_id, data in premium_users:
            expiry_date = data['expiry'].strftime('%Y-%m-%d')
            text += f"💎 User <code>{user_id}</code>\n   Expires: {expiry_date}\n\n"
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Premium", callback_data="add_premium")],
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_analytics")
async def callback_admin_analytics(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    text = f"""
╔═══════════════════════╗
    📊 <b>BOT ANALYTICS</b> 📊
╚═══════════════════════╝

<b>📈 GLOBAL STATS:</b>

📤 Total Uploads: {bot_stats.get('total_uploads', 0)}
📥 Total Downloads: {bot_stats.get('total_downloads', 0)}
▶️ Script Runs: {bot_stats.get('total_runs', 0)}
👥 Total Users: {len(active_users)}
📁 Total Files: {sum(len(files) for files in user_files.values())}
🚀 Running Now: {len(bot_scripts)}
⭐ Total Favorites: {sum(len(favs) for favs in user_favorites.values())}

<b>💎 PREMIUM:</b>
Active: {len([u for u in user_subscriptions if user_subscriptions[u]['expiry'] > datetime.now()])}
Expired: {len([u for u in user_subscriptions if user_subscriptions[u]['expiry'] <= datetime.now()])}

<b>🛡️ SECURITY:</b>
Banned Users: {len(banned_users)}
Admins: {len(admin_ids)}
Bot Status: {'🔒 Locked' if bot_locked else '✅ Active'}
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_system_status")
async def callback_admin_system_status(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    text = f"""
╔═══════════════════════╗
    ⚙️ <b>SYSTEM STATUS</b> ⚙️
╚═══════════════════════╝

<b>💻 CPU:</b>
Usage: {cpu}%
{'🟢 Normal' if cpu < 70 else '🟡 High' if cpu < 90 else '🔴 Critical'}

<b>🧠 MEMORY:</b>
Used: {memory.percent}%
Free: {memory.available / (1024**3):.1f} GB
Total: {memory.total / (1024**3):.1f} GB

<b>💾 DISK:</b>
Used: {disk.percent}%
Free: {disk.free / (1024**3):.1f} GB
Total: {disk.total / (1024**3):.1f} GB

<b>🤖 BOT STATUS:</b>
Status: {'🔒 Locked' if bot_locked else '✅ Running'}
Scripts: {len(bot_scripts)} active
Uptime: ✅ Online
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_system_status")],
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_add_admin")
async def callback_admin_add_admin(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    text = """
╔═══════════════════════╗
    ➕ <b>ADD ADMIN</b> ➕
╚═══════════════════════╝

To add a new admin, use:
<code>/addadmin USER_ID</code>

<b>Example:</b>
<code>/addadmin 123456789</code>

The user will get full admin privileges!
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_remove_admin")
async def callback_admin_remove_admin(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    text = f"""
╔═══════════════════════╗
    ➖ <b>REMOVE ADMIN</b> ➖
╚═══════════════════════╝

<b>Current Admins ({len(admin_ids)}):</b>

"""
    
    for admin_id in admin_ids:
        text += f"👑 <code>{admin_id}</code>\n"
    
    text += "\n<b>To remove:</b>\n<code>/removeadmin USER_ID</code>"
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_ban_user")
async def callback_admin_ban_user(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    text = f"""
╔═══════════════════════╗
    🚫 <b>BAN USER</b> 🚫
╚═══════════════════════╝

<b>Currently Banned:</b> {len(banned_users)} users

To ban a user, use:
<code>/ban USER_ID REASON</code>

<b>Example:</b>
<code>/ban 123456789 Spam</code>

Banned users cannot use the bot!
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_unban_user")
async def callback_admin_unban_user(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    text = f"""
╔═══════════════════════╗
    ✅ <b>UNBAN USER</b> ✅
╚═══════════════════════╝

<b>Banned Users:</b> {len(banned_users)}

"""
    
    if banned_users:
        text += "<b>List:</b>\n"
        for ban_id in list(banned_users)[:10]:
            text += f"🚫 <code>{ban_id}</code>\n"
    
    text += "\n<b>To unban:</b>\n<code>/unban USER_ID</code>"
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "lock_bot")
async def callback_lock_bot(callback: types.CallbackQuery):
    global bot_locked
    
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    bot_locked = not bot_locked
    status = "🔒 LOCKED" if bot_locked else "🔓 UNLOCKED"
    
    await callback.answer(f"Bot is now {status}!", show_alert=True)
    await callback_admin_panel(callback)

@dp.callback_query(F.data == "broadcast")
async def callback_broadcast(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    text = f"""
╔═══════════════════════╗
    📢 <b>BROADCAST</b> 📢
╚═══════════════════════╝

Send a message to all users!

<b>Total Recipients:</b> {len(active_users)}

<b>Command:</b>
<code>/broadcast Your message here</code>

⚠️ Use this feature responsibly!
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "add_premium")
async def callback_add_premium(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    text = """
╔═══════════════════════╗
    💎 <b>ADD PREMIUM</b> 💎
╚═══════════════════════╝

Give premium access to users!

<b>Command:</b>
<code>/addpremium USER_ID DAYS</code>

<b>Examples:</b>
<code>/addpremium 123456789 30</code> (30 days)
<code>/addpremium 987654321 7</code> (7 days)

Premium benefits:
• 50 file limit (vs 20)
• Priority support
• Premium badge
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_clean_files")
async def callback_admin_clean_files(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    text = """
╔═══════════════════════╗
    🗑️ <b>CLEAN FILES</b> 🗑️
╚═══════════════════════╝

Clean old or unused files from the system.

<b>Options:</b>
• Delete files older than 30 days
• Remove files from banned users
• Clean temp/log files

<b>Command:</b>
<code>/clean OPTION</code>

⚠️ This action cannot be undone!
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_backup_db")
async def callback_admin_backup_db(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    try:
        backup_path = IROTECH_DIR / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        with get_db_connection() as conn:
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
        
        await callback.answer("✅ Database backed up!", show_alert=True)
        
        await callback.message.answer_document(
            FSInputFile(backup_path),
            caption="💾 <b>Database Backup</b>\n\nCreated: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            parse_mode="HTML"
        )
        
        backup_path.unlink()
        
    except Exception as e:
        logger.error(f"Backup error: {e}")
        await callback.answer(f"❌ Backup failed: {str(e)}", show_alert=True)

@dp.callback_query(F.data == "admin_view_logs")
async def callback_admin_view_logs(callback: types.CallbackQuery):
    if callback.from_user.id not in admin_ids:
        await callback.answer("❌ Admin only!", show_alert=True)
        return
    
    text = """
╔═══════════════════════╗
    📝 <b>SYSTEM LOGS</b> 📝
╚═══════════════════════╝

View bot logs and activity.

<b>Available Logs:</b>
• Error logs
• User activity
• Script executions
• Admin actions

Logs are stored in the system directory.
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_restart_bot")
async def callback_admin_restart_bot(callback: types.CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("❌ Owner only!", show_alert=True)
        return
    
    text = """
╔═══════════════════════╗
    🔄 <b>RESTART BOT</b> 🔄
╚═══════════════════════╝

⚠️ <b>WARNING:</b>
This will restart the entire bot!

All running scripts will be stopped.
Users may experience brief downtime.

<b>Only use if necessary!</b>

Use <code>/restart</code> to confirm.
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()

@dp.message(Command("addadmin"))
async def cmd_add_admin(message: types.Message):
    if message.from_user.id not in admin_ids:
        await message.answer("❌ Permission denied!")
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Usage: /addadmin USER_ID")
            return
        
        new_admin_id = int(args[1])
        
        if new_admin_id in admin_ids:
            await message.answer(f"✅ User {new_admin_id} is already an admin!")
            return
        
        admin_ids.add(new_admin_id)
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (new_admin_id,))

        await message.answer(f"✅ User <code>{new_admin_id}</code> added as admin!", parse_mode="HTML")
        
    except ValueError:
        await message.answer("❌ Invalid USER_ID!")
    except Exception as e:
        logger.error(f"Error adding admin: {e}")
        await message.answer(f"❌ Error: {str(e)}")

@dp.message(Command("removeadmin"))
async def cmd_remove_admin(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Only owner can remove admins!")
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Usage: /removeadmin USER_ID")
            return
        
        remove_admin_id = int(args[1])
        
        if remove_admin_id == OWNER_ID:
            await message.answer("❌ Cannot remove owner!")
            return
        
        if remove_admin_id not in admin_ids:
            await message.answer(f"❌ User {remove_admin_id} is not an admin!")
            return
        
        admin_ids.remove(remove_admin_id)
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM admins WHERE user_id = ?', (remove_admin_id,))

        await message.answer(f"✅ User <code>{remove_admin_id}</code> removed from admins!", parse_mode="HTML")
        
    except ValueError:
        await message.answer("❌ Invalid USER_ID!")
    except Exception as e:
        logger.error(f"Error removing admin: {e}")
        await message.answer(f"❌ Error: {str(e)}")

@dp.message(Command("addpremium"))
async def cmd_add_premium(message: types.Message):
    if message.from_user.id not in admin_ids:
        await message.answer("❌ Permission denied!")
        return
    
    try:
        args = message.text.split()
        if len(args) != 3:
            await message.answer("Usage: /addpremium USER_ID DAYS")
            return
        
        user_id = int(args[1])
        days = int(args[2])
        
        if days <= 0:
            await message.answer("❌ Days must be greater than 0!")
            return
        
        expiry = datetime.now() + timedelta(days=days)
        user_subscriptions[user_id] = {'expiry': expiry}
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)',
                      (user_id, expiry.isoformat()))

        await message.answer(
            f"✅ <b>Premium Added!</b>\n\n"
            f"User: <code>{user_id}</code>\n"
            f"Duration: {days} days\n"
            f"Expires: {expiry.strftime('%Y-%m-%d %H:%M')}",
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer("❌ Invalid input!")
    except Exception as e:
        logger.error(f"Error adding premium: {e}")
        await message.answer(f"❌ Error: {str(e)}")

@dp.message(Command("ban"))
async def cmd_ban_user(message: types.Message):
    if message.from_user.id not in admin_ids:
        await message.answer("❌ Permission denied!")
        return
    
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 2:
            await message.answer("Usage: /ban USER_ID [REASON]")
            return
        
        ban_user_id = int(args[1])
        reason = args[2] if len(args) > 2 else "No reason provided"
        
        if ban_user_id in admin_ids:
            await message.answer("❌ Cannot ban an admin!")
            return
        
        banned_users.add(ban_user_id)
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO banned_users (user_id, banned_date, reason) VALUES (?, ?, ?)',
                      (ban_user_id, datetime.now().isoformat(), reason))

        await message.answer(f"🚫 User <code>{ban_user_id}</code> has been banned!\n\nReason: {reason}", parse_mode="HTML")
        
    except ValueError:
        await message.answer("❌ Invalid USER_ID!")
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        await message.answer(f"❌ Error: {str(e)}")

@dp.message(Command("unban"))
async def cmd_unban_user(message: types.Message):
    if message.from_user.id not in admin_ids:
        await message.answer("❌ Permission denied!")
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Usage: /unban USER_ID")
            return
        
        unban_user_id = int(args[1])
        
        if unban_user_id not in banned_users:
            await message.answer(f"❌ User {unban_user_id} is not banned!")
            return
        
        banned_users.remove(unban_user_id)
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM banned_users WHERE user_id = ?', (unban_user_id,))

        await message.answer(f"✅ User <code>{unban_user_id}</code> has been unbanned!", parse_mode="HTML")
        
    except ValueError:
        await message.answer("❌ Invalid USER_ID!")
    except Exception as e:
        logger.error(f"Error unbanning user: {e}")
        await message.answer(f"❌ Error: {str(e)}")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    if message.from_user.id not in admin_ids:
        await message.answer("❌ Permission denied!")
        return
    
    try:
        broadcast_text = message.text.replace("/broadcast", "", 1).strip()
        
        if not broadcast_text:
            await message.answer("Usage: /broadcast Your message here")
            return
        
        sent_count = 0
        failed_count = 0
        
        status_msg = await message.answer(f"📢 Broadcasting to {len(active_users)} users...")
        
        for user_id in active_users:
            if user_id in banned_users:
                continue
            
            try:
                await bot.send_message(user_id, f"📢 <b>Announcement:</b>\n\n{broadcast_text}", parse_mode="HTML")
                sent_count += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {e}")
                failed_count += 1
        
        await status_msg.edit_text(
            f"✅ <b>Broadcast Complete!</b>\n\n"
            f"✅ Sent: {sent_count}\n"
            f"❌ Failed: {failed_count}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error broadcasting: {e}")
        await message.answer(f"❌ Error: {str(e)}")

@dp.message(Command("panel"))
async def cmd_get_panel(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    if user_id not in admin_ids:
        await message.answer("🔒 <b>Admin Only Command</b>\n\n<i>💫 MADE BY DARK SHADOW 💫</i>", parse_mode="HTML")
        return
    
    is_owner = (user_id == OWNER_ID)
    is_admin = (user_id in admin_ids)
    
    try:
        result = await create_user_hosting(user_id, username, is_owner, is_admin)
        
        # Create keyboard with extend option
        if is_owner:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👑 Owner Panel", url=result['session']['public_url'])],
                [InlineKeyboardButton(text="⏰ Check Status", callback_data="check_session_status")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
            ])
        elif is_admin:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👨‍💼 Admin Panel", url=result['session']['public_url'])],
                [InlineKeyboardButton(text="⏰ Check Status", callback_data="check_session_status")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
            ])
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Open Panel", url=result['session']['public_url'])],
                [InlineKeyboardButton(text="🔄 Extend +15 min", callback_data="extend_session"),
                 InlineKeyboardButton(text="⏰ Status", callback_data="check_session_status")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
            ])
        
        await message.answer(result['message'], parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Panel creation error: {e}")
        await message.answer(f"❌ Error creating panel: {str(e)}")

@dp.message(Command("live"))
async def cmd_live_panel(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in admin_ids:
        await message.answer("🔒 <b>Admin Only Command</b>\n\n<i>💫 MADE BY DARK SHADOW 💫</i>", parse_mode="HTML")
        return
    
    config = hosting.get_config()
    base_url = config['base_url']
    live_panel_url = f"{base_url}/live"
    
    text = f"""
╔═══════════════════════╗
    🚀 <b>LIVE CONTROL PANEL</b> 🚀
╚═══════════════════════╝

<b>🔗 Panel URL:</b>
<code>{live_panel_url}</code>

<b>✨ Features:</b>

📦 <b>Dependencies Manager</b>
   • One-click install all dependencies
   • Upload requirements.txt
   • Edit requirements.txt online

⚙️ <b>.env File Manager</b>
   • Edit .env file in browser
   • Save configuration instantly

▶️ <b>Code Runner</b>
   • Run Python/JavaScript files
   • View live output
   • Stop running processes

💻 <b>Terminal Access</b>
   • Execute commands
   • View real-time output
   • Safe command blocking

📋 <b>Logs Viewer</b>
   • Real-time bot logs
   • Auto-refresh every 5 seconds

━━━━━━━━━━━━━━━━━━━━
<b>🔐 Security:</b> Admin-only access
<b>🌐 Platform:</b> {config['platform']}

<i>💫 MADE BY DARK SHADOW 💫</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Open Live Panel", url=live_panel_url)],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
    ])
    
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in admin_ids:
        await message.answer("🔒 <b>Admin Only Command</b>\n\n<i>💫 MADE BY DARK SHADOW 💫</i>", parse_mode="HTML")
        return
    
    text = """
╔═══════════════════════╗
    ℹ️ <b>HELP & INFO</b> ℹ️
╚═══════════════════════╝

<b>🎯 HOW TO USE:</b>

1️⃣ <b>Upload Files:</b>
   • Click 'Upload File'
   • Send your .py, .js, or .zip file
   • File will be saved automatically

2️⃣ <b>Run Scripts:</b>
   • Go to 'My Files'
   • Click 'Run' on any file
   • Monitor script execution

3️⃣ <b>Manage Files:</b>
   • View all files in 'My Files'
   • Add to favorites with ⭐
   • Delete unwanted files

4️⃣ <b>Search:</b>
   • Use /search [filename]
   • Quick file lookup

━━━━━━━━━━━━━━━━━━━━
<b>💡 COMMANDS:</b>

/start - Start the bot
/help - Show this help
/search - Search files
/stats - Your statistics
/premium - Premium info

<b>Need help? Contact owner! 💬</b>

<i>💫 MADE BY DARK SHADOW 💫</i>
"""
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Features", callback_data="all_features")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
    ])
    
    await message.answer(text, reply_markup=back_keyboard, parse_mode="HTML")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in admin_ids:
        await message.answer("🔒 <b>Admin Only Command</b>\n\n<i>💫 MADE BY DARK SHADOW 💫</i>", parse_mode="HTML")
        return
    
    user_file_count = len(user_files.get(user_id, []))
    user_fav_count = len(user_favorites.get(user_id, []))
    is_premium = user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now()
    
    text = f"""
╔═══════════════════════╗
    📊 <b>YOUR STATISTICS</b> 📊
╚═══════════════════════╝

<b>👤 USER INFO:</b>

🆔 User ID: <code>{user_id}</code>
👤 Name: {message.from_user.full_name}
📦 Files Uploaded: {user_file_count}/{get_user_file_limit(user_id)}
⭐ Favorites: {user_fav_count}
💎 Account: {'Premium ✨' if is_premium else 'Free 🆓'}
🚀 Running: {sum(1 for k in bot_scripts if k.startswith(f"{user_id}_"))}

━━━━━━━━━━━━━━━━━━━━
📈 <b>USAGE:</b>

📤 Uploads: {bot_stats.get('total_uploads', 0)}
📥 Downloads: {bot_stats.get('total_downloads', 0)}
▶️ Script Runs: {bot_stats.get('total_runs', 0)}

{'✅ Bot Status: Active' if not bot_locked else '🔒 Bot: Maintenance'}
"""
    
    if user_id in admin_ids:
        text += f"\n━━━━━━━━━━━━━━━━━━━━\n👑 <b>ADMIN STATS:</b>\n"
        text += f"👥 Total Users: {len(active_users)}\n"
        text += f"📁 Total Files: {sum(len(files) for files in user_files.values())}\n"
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_main")]
    ])
    
    await message.answer(text, reply_markup=back_keyboard, parse_mode="HTML")

async def schedule_auto_backup():
    while True:
        await asyncio.sleep(86400)
        
        try:
            backup_path = IROTECH_DIR / f"auto_backup_{datetime.now().strftime('%Y%m%d')}.db"
            
            with get_db_connection() as conn:
                backup_conn = sqlite3.connect(backup_path)
                conn.backup(backup_conn)
                backup_conn.close()
            
            logger.info(f"✅ Auto-backup created: {backup_path.name}")
            
            backups = sorted(IROTECH_DIR.glob("auto_backup_*.db"))
            if len(backups) > 7:
                for old_backup in backups[:-7]:
                    old_backup.unlink()
                    logger.info(f"🗑️ Deleted old backup: {old_backup.name}")
                    
        except Exception as e:
            logger.error(f"Auto-backup error: {e}")

async def cleanup_old_scripts():
    while True:
        await asyncio.sleep(300)
        
        try:
            for script_key, info in list(bot_scripts.items()):
                runtime = (datetime.now() - info['start_time']).total_seconds()
                
                if runtime > SCRIPT_TIMEOUT:
                    logger.warning(f"Terminating long-running script: {script_key}")
                    
                    process = info['process']
                    log_file = info.get('log_file')
                    
                    if log_file and not log_file.closed:
                        log_file.write(f"\n[SYSTEM] Script auto-terminated after {runtime:.0f}s\n")
                        log_file.close()
                    
                    terminate_process_tree(process.pid)
                    del bot_scripts[script_key]
                    
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

async def web_server():
    from live_panel_complete import create_live_panel_app
    
    main_app = web.Application()
    
    dashboard_app = await create_web_dashboard()
    live_panel, live_panel_app = create_live_panel_app(BASE_DIR)
    
    async def handle_root(request):
        uptime = (datetime.now() - bot_start_time).total_seconds()
        
        health_data = {
            "status": "online",
            "bot_name": "Advanced File Host Bot v2.0",
            "uptime_seconds": int(uptime),
            "uptime_human": f"{int(uptime//3600)}h {int((uptime%3600)//60)}m",
            "total_users": len(active_users),
            "active_scripts": len(bot_scripts),
            "total_files": sum(len(files) for files in user_files.values()),
            "bot_locked": bot_locked,
            "version": "2.0.0",
            "features": {
                "web_panel": True,
                "code_editor": True,
                "file_manager": True,
                "analytics": True
            }
        }
        
        return web.json_response(health_data)
    
    async def handle_health(request):
        return web.json_response({"status": "healthy", "timestamp": datetime.now().isoformat()})
    
    async def handle_stats(request):
        stats_data = {
            "users": {
                "total": len(active_users),
                "banned": len(banned_users),
                "premium": len([u for u in user_subscriptions if user_subscriptions[u]['expiry'] > datetime.now()])
            },
            "files": {
                "total": sum(len(files) for files in user_files.values()),
                "by_type": {
                    "python": sum(1 for files in user_files.values() for f in files if f[1] == 'py'),
                    "javascript": sum(1 for files in user_files.values() for f in files if f[1] == 'js'),
                    "zip": sum(1 for files in user_files.values() for f in files if f[1] == 'zip')
                }
            },
            "scripts": {
                "running": len(bot_scripts),
                "total_runs": bot_stats.get('total_runs', 0)
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        }
        
        return web.json_response(stats_data)
    
    # Mount live panel routes FIRST (priority)
    for route in live_panel_app.router.routes():
        path = route.resource.canonical
        main_app.router.add_route(route.method, path, route.handler)
        logger.info(f"✅ Live Panel Route: {route.method} {path}")
    
    # Mount dashboard routes
    for route in dashboard_app.router.routes():
        path = route.resource.canonical
        main_app.router.add_route(route.method, path, route.handler)
    
    # Main routes
    main_app.router.add_get('/', handle_root)
    main_app.router.add_get('/health', handle_health)
    main_app.router.add_get('/stats', handle_stats)
    
    config = hosting.get_config()
    bind_address = config['bind_address']
    port = config['port']
    base_url = config['base_url']
    
    runner = web.AppRunner(main_app)
    await runner.setup()
    
    site = web.TCPSite(runner, bind_address, port)
    await site.start()
    logger.info(f"🌐 Web Server started on {bind_address}:{port}")
    logger.info(f"📊 Health: {base_url}/health")
    logger.info(f"📈 Stats: {base_url}/stats")
    logger.info(f"🎨 Panel: {base_url}/panel/{{token}}")
    logger.info(f"🚀 Live Panel: {base_url}/live")
    
    # Debug: Log all registered routes
    logger.info("📋 Registered Routes:")
    for route in main_app.router.routes():
        logger.info(f"  {route.method:6} {route.resource.canonical}")

@dp.callback_query(F.data.startswith("share_file:"))
async def callback_share_file(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    file_name = callback.data.split(":", 1)[1]
    
    try:
        file_path = get_safe_file_path(user_id, file_name)
    except ValueError as e:
        await callback.answer(f"❌ {str(e)}", show_alert=True)
        return
    
    if not file_path.exists():
        await callback.answer("❌ File not found!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏰ 1 Hour", callback_data=f"share_1h:{file_name}"),
         InlineKeyboardButton(text="📅 24 Hours", callback_data=f"share_24h:{file_name}")],
        [InlineKeyboardButton(text="📆 7 Days", callback_data=f"share_7d:{file_name}"),
         InlineKeyboardButton(text="♾️ 30 Days", callback_data=f"share_30d:{file_name}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data=f"file_info:{file_name}")]
    ])
    
    text = f"""
╔═══════════════════════╗
    📤 <b>SHARE FILE</b> 📤
╚═══════════════════════╝

📄 <b>File:</b> <code>{file_name}</code>

Choose expiry time for the share link:

⏰ <b>1 Hour</b> - Quick temporary access
📅 <b>24 Hours</b> - Short-term sharing
📆 <b>7 Days</b> - Week-long access
♾️ <b>30 Days</b> - Long-term sharing

<i>Links expire automatically and can be revoked anytime.</i>
"""
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("share_1h:") | F.data.startswith("share_24h:") | F.data.startswith("share_7d:") | F.data.startswith("share_30d:"))
async def callback_create_share(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    data_parts = callback.data.split(":", 1)
    expiry_type = data_parts[0]
    file_name = data_parts[1]
    
    expiry_hours = {
        "share_1h": 1,
        "share_24h": 24,
        "share_7d": 168,
        "share_30d": 720
    }[expiry_type]
    
    try:
        file_path = get_safe_file_path(user_id, file_name)
    except ValueError as e:
        await callback.answer(f"❌ {str(e)}", show_alert=True)
        return
    
    if not file_path.exists():
        await callback.answer("❌ File not found!", show_alert=True)
        return
    
    share_data = share_manager.create_share_link(
        user_id=user_id,
        file_path=str(file_path),
        filename=file_name,
        expiry_hours=expiry_hours
    )
    
    config = hosting.get_config()
    base_url = config['base_url']
    share_url = f"{base_url}/share/{share_data['token']}"
    
    expiry_text = {
        "share_1h": "1 hour",
        "share_24h": "24 hours",
        "share_7d": "7 days",
        "share_30d": "30 days"
    }[expiry_type]
    
    text = f"""
╔═══════════════════════╗
    ✅ <b>LINK CREATED</b> ✅
╚═══════════════════════╝

📄 <b>File:</b> <code>{file_name}</code>
🔗 <b>Share Link:</b>
<code>{share_url}</code>

⏰ <b>Expires In:</b> {expiry_text}
📅 <b>Expires On:</b> {share_data['expiry'].strftime('%Y-%m-%d %H:%M')}
🔐 <b>File ID:</b> <code>{share_data['file_id']}</code>

💡 <b>Tip:</b> Share this link with anyone. It will expire automatically.

📊 Use /myshares to view all active shares.
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Copy Link", url=share_url)],
        [InlineKeyboardButton(text="🗑️ Revoke Link", callback_data=f"revoke_share:{share_data['file_id']}")],
        [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
         InlineKeyboardButton(text="🏠 Home", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("✅ Share link created!")

@dp.callback_query(F.data.startswith("format_code:"))
async def callback_format_code(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_admin_user(user_id, callback):
        return
    
    file_name = callback.data.split(":", 1)[1]
    
    try:
        file_path = get_safe_file_path(user_id, file_name)
    except ValueError as e:
        await callback.answer(f"❌ {str(e)}", show_alert=True)
        return
    
    if not file_path.exists():
        await callback.answer("❌ File not found!", show_alert=True)
        return
    
    await callback.answer("⏳ Formatting code...", show_alert=False)
    
    result = code_formatter.auto_format(str(file_path))
    
    if result['formatted']:
        text = f"""
╔═══════════════════════╗
    ✅ <b>CODE FORMATTED</b> ✅
╚═══════════════════════╝

📄 <b>File:</b> <code>{file_name}</code>
✨ <b>Status:</b> {result['message']}
📝 <b>Type:</b> {result['file_type']} file

Your code has been automatically formatted with professional standards!
"""
    else:
        text = f"""
╔═══════════════════════╗
    ⚠️ <b>FORMATTING INFO</b> ⚠️
╚═══════════════════════╝

📄 <b>File:</b> <code>{file_name}</code>
📝 <b>Status:</b> {result['message']}

{result.get('hint', '')}
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ️ File Info", callback_data=f"file_info:{file_name}"),
         InlineKeyboardButton(text="▶️ Run", callback_data=f"run_script:{file_name}")],
        [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
         InlineKeyboardButton(text="🏠 Home", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@dp.message(Command("search"))
async def cmd_advanced_search(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in admin_ids:
        await message.answer("🔒 <b>Admin Only Command</b>\n\n<i>💫 MADE BY DARK SHADOW 💫</i>", parse_mode="HTML")
        return
    
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Usage: /search <query>\n\nExample: /search function")
            return
        
        query = args[1]
        user_folder = UPLOAD_BOTS_DIR / str(user_id)
        
        if not user_folder.exists():
            await message.answer("❌ No files uploaded yet!")
            return
        
        searcher = create_search_instance(str(user_folder))
        results = searcher.smart_search(query, limit=10)
        
        if results['total_results'] == 0:
            await message.answer(f"❌ No results found for: <code>{query}</code>", parse_mode="HTML")
            return
        
        text = f"""
╔═══════════════════════╗
    🔍 <b>SEARCH RESULTS</b> 🔍
╚═══════════════════════╝

🔎 <b>Query:</b> <code>{query}</code>
📊 <b>Total Results:</b> {results['total_results']}

"""
        
        if results['filename_matches']:
            text += "<b>📄 Filename Matches:</b>\n"
            for match in results['filename_matches'][:5]:
                text += f"  • <code>{match['file_name']}</code>\n"
            text += "\n"
        
        if results['content_matches']:
            text += "<b>📝 Content Matches:</b>\n"
            for match in results['content_matches'][:5]:
                text += f"  • <code>{match['file_name']}</code> ({match['match_count']} matches)\n"
                if match.get('preview'):
                    text += f"    <i>{match['preview'][:50]}...</i>\n"
            text += "\n"
        
        text += "<i>💡 Tip: Use /search &lt;keyword&gt; to find files by name or content!</i>"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
             InlineKeyboardButton(text="🏠 Home", callback_data="back_to_main")]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        await message.answer(f"❌ Error: {str(e)}")

@dp.message(Command("myshares"))
async def cmd_my_shares(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in admin_ids:
        await message.answer("🔒 <b>Admin Only Command</b>\n\n<i>💫 MADE BY DARK SHADOW 💫</i>", parse_mode="HTML")
        return
    
    shares = share_manager.get_user_shares(user_id)
    
    if not shares:
        text = """
╔═══════════════════════╗
    📤 <b>MY SHARES</b> 📤
╚═══════════════════════╝

No active share links found.

💡 Share files from File Info menu!
"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
             InlineKeyboardButton(text="🏠 Home", callback_data="back_to_main")]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        return
    
    text = f"""
╔═══════════════════════╗
    📤 <b>MY SHARES</b> 📤
╚═══════════════════════╝

<b>Total Active Shares:</b> {len(shares)}

"""
    
    for share in shares[:10]:
        status = "🔴 Expired" if share['is_expired'] else "🟢 Active"
        text += f"""
📄 <b>{share['filename']}</b>
   {status} • {share['hours_left']}h left
   📥 Downloads: {share['downloads']}
   🆔 ID: <code>{share['file_id']}</code>

"""
    
    if len(shares) > 10:
        text += f"\n<i>... and {len(shares) - 10} more shares</i>\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 My Files", callback_data="check_files"),
         InlineKeyboardButton(text="🏠 Home", callback_data="back_to_main")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

bot_start_time = datetime.now()

async def keep_alive():
    """Keep Render service alive by self-pinging"""
    import aiohttp
    
    config = hosting.get_config()
    base_url = config['base_url']
    
    # Only run on production (not local)
    if not config['is_production']:
        return
    
    logger.info("🔄 Keep-alive service started")
    
    while True:
        try:
            await asyncio.sleep(840)  # 14 minutes (Render timeout is 15 min)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/health", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        logger.info("✅ Keep-alive ping successful")
                    else:
                        logger.warning(f"⚠️ Keep-alive ping failed: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Keep-alive error: {e}")

async def main():
    logger.info("🚀 Starting Advanced File Host Bot...")
    logger.info("💫 MADE BY DARK SHADOW 💫")
    
    print_startup_info()
    
    asyncio.create_task(web_server())
    asyncio.create_task(schedule_auto_backup())
    asyncio.create_task(cleanup_old_scripts())
    asyncio.create_task(keep_alive())  # Keep service alive
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("❌ Direct execution not allowed!")
    print("🔧 Please run: python bot_launcher.py")
    sys.exit(1)
