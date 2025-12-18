import os
import sys
import asyncio

def check_environment():
    required_vars = ['BOT_TOKEN', 'OWNER_ID', 'ADMIN_ID']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print("❌ Missing environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\n🔧 Set environment variables in Render dashboard:")
        print("   - BOT_TOKEN")
        print("   - OWNER_ID") 
        print("   - ADMIN_ID")
        print("   - YOUR_USERNAME (optional)")
        print("   - UPDATE_CHANNEL (optional)")
        sys.exit(1)

def main():
    print("🚀 Starting Telegram Bot (Deployment Mode)...")
    print("=" * 50)
    
    check_environment()
    print("✅ Environment configured")
    
    print("=" * 50)
    print("🤖 Launching bot...")
    print()
    
    try:
        import main as bot_main
        asyncio.run(bot_main.main())
        
    except ImportError as e:
        print(f"❌ Bot module not found: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Bot stopped")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
