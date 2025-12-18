import os
import sys
import base64
import hashlib
import time
from pathlib import Path

AUTHORIZED_HASH = "REPLACE_WITH_YOUR_HASH"

def verify_authorization():
    script_dir = Path(__file__).parent.absolute()
    auth_file = script_dir / ".bot_auth"
    
    if not auth_file.exists():
        print("❌ Authorization file not found!")
        print("🔧 Run setup.py first to configure the bot")
        sys.exit(1)
    
    try:
        with open(auth_file, 'r') as f:
            stored_hash = f.read().strip()
        
        current_time = int(time.time())
        time_hash = hashlib.sha256(f"{current_time // 86400}".encode()).hexdigest()
        
        if stored_hash != time_hash and stored_hash != AUTHORIZED_HASH:
            print("❌ Invalid authorization!")
            print("🔧 Please re-run setup.py")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Authorization error: {e}")
        sys.exit(1)

def check_environment():
    required_vars = ['BOT_TOKEN', 'OWNER_ID', 'ADMIN_ID']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print("❌ Missing environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\n🔧 Create a .env file with required variables")
        sys.exit(1)

def main():
    print("🚀 Starting Bot Launcher...")
    print("=" * 50)
    
    verify_authorization()
    print("✅ Authorization verified")
    
    check_environment()
    print("✅ Environment configured")
    
    print("=" * 50)
    print("🤖 Launching Telegram Bot...")
    print()
    
    try:
        import main as bot_main
        
        import asyncio
        asyncio.run(bot_main.main())
        
    except ImportError:
        print("❌ Bot module not found!")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
