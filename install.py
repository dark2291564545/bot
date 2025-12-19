#!/usr/bin/env python3
"""
🚀 AUTOMATIC BOT SETUP SCRIPT
💫 MADE BY DARK SHADOW 💫

This script will:
1. Check Python version
2. Install all dependencies automatically
3. Create .env file with your details
4. Create necessary folders
5. Test the installation
6. Launch the bot
"""

import sys
import subprocess
import os
from pathlib import Path

def print_banner():
    """Print welcome banner"""
    print("\n" + "="*60)
    print("  🤖 TELEGRAM FILE HOST BOT - AUTO SETUP")
    print("  💫 MADE BY DARK SHADOW 💫")
    print("="*60 + "\n")

def check_python_version():
    """Check if Python version is compatible"""
    print("🔍 Checking Python version...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required. You have {version.major}.{version.minor}")
        print("\n📥 Download Python from: https://www.python.org/downloads/")
        sys.exit(1)
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK!")
    return True

def install_dependencies():
    """Install all required packages"""
    print("\n📦 Installing dependencies...")
    print("⏳ This may take a few minutes...\n")
    
    try:
        # Upgrade pip first
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade", "pip"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        
        # Install requirements
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("❌ Installation failed!")
            print("\n📋 Error details:")
            print(result.stderr)
            print("\n💡 Try manually: pip install -r requirements.txt")
            return False
        
        print("✅ All dependencies installed successfully!")
        return True
    
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        print("\n💡 Manual installation:")
        print("   pip install -r requirements.txt")
        return False

def create_env_file():
    """Interactive .env file creation"""
    print("\n⚙️  CONFIGURATION SETUP")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    if os.path.exists('.env'):
        overwrite = input("\n⚠️  .env file already exists. Overwrite? (y/n): ").lower()
        if overwrite != 'y':
            print("✅ Keeping existing .env file")
            return True
    
    print("\n📝 Please provide the following information:\n")
    
    # Get bot token
    print("1️⃣  BOT TOKEN")
    print("   How to get: https://t.me/BotFather")
    print("   Send /newbot to BotFather and copy the token")
    bot_token = input("   Enter Bot Token: ").strip()
    
    if not bot_token or len(bot_token) < 40:
        print("❌ Invalid bot token!")
        return False
    
    # Get owner ID
    print("\n2️⃣  OWNER TELEGRAM ID")
    print("   How to get: https://t.me/userinfobot")
    print("   Forward any message to @userinfobot")
    owner_id = input("   Enter Your Telegram ID: ").strip()
    
    if not owner_id.isdigit():
        print("❌ Telegram ID must be numbers only!")
        return False
    
    # Get admin ID (same as owner by default)
    print("\n3️⃣  ADMIN TELEGRAM ID")
    use_same = input(f"   Use same as owner ({owner_id})? (y/n): ").lower()
    
    if use_same == 'y':
        admin_id = owner_id
    else:
        admin_id = input("   Enter Admin Telegram ID: ").strip()
        if not admin_id.isdigit():
            print("❌ Telegram ID must be numbers only!")
            return False
    
    # Optional settings
    print("\n4️⃣  CHANNEL/USERNAME (Optional)")
    username = input("   Your Username (default: @DARK22v): ").strip() or "@DARK22v"
    channel = input("   Your Channel (default: https://t.me/DARK22v): ").strip() or "https://t.me/DARK22v"
    
    # Create .env content
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
# 🌐 WEB DASHBOARD (Auto-configured)
# ================================
# JWT_SECRET will be auto-generated
# SESSION_TIMEOUT=3600

# ================================
# 🔧 ADVANCED SETTINGS (Optional)
# ================================
# LOG_LEVEL=INFO
# MAX_FILE_SIZE=52428800
# BACKUP_ENABLED=true
"""
    
    # Write .env file
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("\n✅ .env file created successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Error creating .env file: {e}")
        return False

def create_folders():
    """Create necessary directories"""
    print("\n📁 Creating required folders...")
    
    folders = ['upload_bots', 'inf', 'logs', 'backups']
    
    for folder in folders:
        Path(folder).mkdir(exist_ok=True)
        print(f"   ✅ {folder}/")
    
    print("✅ All folders created!")
    return True

def test_installation():
    """Test if bot can be imported"""
    print("\n🧪 Testing installation...")
    
    try:
        # Test imports
        test_code = """
import asyncio
from aiogram import Bot
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('BOT_TOKEN')
if token:
    print("OK")
else:
    print("ERROR: BOT_TOKEN not found")
"""
        
        result = subprocess.run(
            [sys.executable, "-c", test_code],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "OK" in result.stdout:
            print("✅ Installation test passed!")
            return True
        else:
            print("⚠️  Warning: Bot token might not be loaded correctly")
            print("   But you can still try running the bot")
            return True
    
    except Exception as e:
        print(f"⚠️  Test warning: {e}")
        print("   You can still try running the bot")
        return True

def show_next_steps():
    """Show what to do next"""
    print("\n" + "="*60)
    print("  ✅ SETUP COMPLETE!")
    print("="*60)
    
    print("\n📋 NEXT STEPS:\n")
    print("1️⃣  Start the bot:")
    print("   python bot_launcher.py")
    print()
    print("2️⃣  Test the bot:")
    print("   Open Telegram and send /start to your bot")
    print()
    print("3️⃣  Deploy to cloud (optional):")
    print("   See COMPLETE_SUMMARY.md for hosting options")
    print()
    print("4️⃣  Check features:")
    print("   See NEW_FEATURES.md for all features")
    
    print("\n" + "="*60)
    print("  💫 MADE BY DARK SHADOW 💫")
    print("  📢 Channel: https://t.me/DARK22v")
    print("="*60 + "\n")

def main():
    """Main setup function"""
    print_banner()
    
    # Step 1: Check Python
    if not check_python_version():
        return
    
    # Step 2: Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed at dependency installation")
        print("💡 Try running manually: pip install -r requirements.txt")
        return
    
    # Step 3: Create .env
    if not create_env_file():
        print("\n❌ Setup failed at configuration")
        return
    
    # Step 4: Create folders
    if not create_folders():
        print("\n❌ Setup failed at folder creation")
        return
    
    # Step 5: Test installation
    test_installation()
    
    # Step 6: Show next steps
    show_next_steps()
    
    # Ask to launch
    launch = input("🚀 Launch bot now? (y/n): ").lower()
    if launch == 'y':
        print("\n🚀 Starting bot...\n")
        try:
            subprocess.run([sys.executable, "bot_launcher.py"])
        except KeyboardInterrupt:
            print("\n\n👋 Bot stopped by user")
        except Exception as e:
            print(f"\n❌ Error launching bot: {e}")
            print("💡 Try manually: python bot_launcher.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("\n📧 Report this error to: @DARK22v")
        sys.exit(1)
