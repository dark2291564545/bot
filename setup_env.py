#!/usr/bin/env python3
"""
🔧 QUICK SETUP SCRIPT
Made by DARK SHADOW
"""

import os
import sys

def setup_env():
    print("=" * 60)
    print("  🤖 FILE HOST BOT - QUICK SETUP")
    print("  💫 MADE BY DARK SHADOW 💫")
    print("=" * 60)
    print()
    
    if os.path.exists('.env'):
        print("⚠️  .env file already exists!")
        overwrite = input("Do you want to overwrite it? (y/n): ").lower()
        if overwrite != 'y':
            print("❌ Setup cancelled.")
            return
    
    print("\n📝 Enter your bot configuration:\n")
    
    bot_token = input("🔑 Bot Token (from @BotFather): ").strip()
    if not bot_token:
        print("❌ Bot token is required!")
        sys.exit(1)
    
    owner_id = input("👑 Owner Telegram ID: ").strip()
    if not owner_id.isdigit():
        print("❌ Owner ID must be a number!")
        sys.exit(1)
    
    admin_id = input("👨‍💼 Admin Telegram ID: ").strip()
    if not admin_id.isdigit():
        print("❌ Admin ID must be a number!")
        sys.exit(1)
    
    username = input("📢 Your Username (default: @DARK22v): ").strip() or "@DARK22v"
    channel = input("📣 Your Channel Link (default: https://t.me/DARK22v): ").strip() or "https://t.me/DARK22v"
    
    env_content = f"""# ================================
# 🤖 BOT CONFIGURATION
# ================================
BOT_TOKEN={bot_token}
OWNER_ID={owner_id}
ADMIN_ID={admin_id}

# ================================
# 📢 CHANNEL & USERNAME
# ================================
YOUR_USERNAME={username}
UPDATE_CHANNEL={channel}

# ================================
# 🌐 WEB DASHBOARD (Optional)
# ================================
# JWT_SECRET=your_random_secret_key_here
# SESSION_TIMEOUT=3600

# ================================
# 🔧 ADVANCED SETTINGS (Optional)
# ================================
# LOG_LEVEL=INFO
# MAX_FILE_SIZE=52428800
# BACKUP_ENABLED=true
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("\n" + "=" * 60)
    print("✅ .env file created successfully!")
    print("=" * 60)
    print("\n📋 Next steps:")
    print("   1. Install dependencies: pip install -r requirements.txt")
    print("   2. Run the bot: python bot_launcher.py")
    print("\n💫 MADE BY DARK SHADOW 💫\n")

if __name__ == "__main__":
    try:
        setup_env()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
