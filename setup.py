import os
import sys
import hashlib
import time
import getpass
from pathlib import Path

def create_env_file():
    print("=" * 60)
    print("🔧 BOT CONFIGURATION SETUP")
    print("=" * 60)
    
    env_path = Path(".env")
    
    if env_path.exists():
        overwrite = input("\n⚠️  .env file already exists. Overwrite? (y/N): ").lower()
        if overwrite != 'y':
            print("📝 Using existing .env file")
            return
    
    print("\n📝 Enter your bot configuration:")
    print("-" * 60)
    
    bot_token = input("🤖 Bot Token (from @BotFather): ").strip()
    owner_id = input("👑 Owner Telegram ID: ").strip()
    admin_id = input("👨‍💼 Admin Telegram ID (press Enter for same as owner): ").strip() or owner_id
    username = input("📱 Your Telegram Username (e.g., @username): ").strip()
    channel = input("📢 Update Channel URL (optional): ").strip() or "https://t.me/YourChannel"
    
    env_content = f"""# Bot Configuration
BOT_TOKEN={bot_token}
OWNER_ID={owner_id}
ADMIN_ID={admin_id}
YOUR_USERNAME={username}
UPDATE_CHANNEL={channel}

# Database Configuration
DATABASE_PATH=./inf/bot_data.db

# Optional: Advanced Settings
# SCRIPT_TIMEOUT=3600
# MAX_FILE_SIZE=52428800
# MAX_ZIP_SIZE=104857600
"""
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print("\n✅ .env file created successfully!")

def create_auth_file():
    print("\n" + "=" * 60)
    print("🔐 AUTHORIZATION SETUP")
    print("=" * 60)
    
    password = getpass.getpass("\n🔑 Create a launcher password (hidden): ")
    confirm = getpass.getpass("🔑 Confirm password: ")
    
    if password != confirm:
        print("❌ Passwords don't match!")
        sys.exit(1)
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    auth_file = Path(".bot_auth")
    with open(auth_file, 'w') as f:
        f.write(password_hash)
    
    print("✅ Authorization configured!")
    print(f"🔐 Password hash: {password_hash[:16]}...")

def create_directories():
    dirs = ['upload_bots', 'inf', 'logs', 'backups']
    
    print("\n" + "=" * 60)
    print("📁 CREATING DIRECTORIES")
    print("=" * 60)
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        print(f"✅ Created: {dir_name}/")

def create_gitignore():
    gitignore_content = """# Environment
.env
.bot_auth
venv/
env/
ENV/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Database
*.db
*.db-journal
inf/

# Uploads & Logs
upload_bots/
logs/
backups/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""
    
    with open(".gitignore", 'w') as f:
        f.write(gitignore_content)
    
    print("\n✅ .gitignore created")

def install_dependencies():
    print("\n" + "=" * 60)
    print("📦 INSTALLING DEPENDENCIES")
    print("=" * 60)
    
    install = input("\n📦 Install Python dependencies now? (Y/n): ").lower()
    
    if install != 'n':
        import subprocess
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print("✅ Dependencies installed successfully!")
        except subprocess.CalledProcessError:
            print("⚠️  Failed to install dependencies")
            print("💡 Run manually: pip install -r requirements.txt")

def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        🤖 TELEGRAM BOT - SETUP WIZARD 🚀                  ║
║                                                           ║
║        Secure File Host & Script Runner Bot              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    if not sys.stdin.isatty():
        print("⚠️  Running in non-interactive mode (deployment environment)")
        print("✅ Skipping interactive setup - use environment variables instead")
        create_directories()
        create_gitignore()
        print("\n✅ Non-interactive setup completed")
        print("💡 Configure bot using environment variables in Render dashboard")
        return
    
    try:
        create_env_file()
        
        create_auth_file()
        
        create_directories()
        
        create_gitignore()
        
        install_dependencies()
        
        print("\n" + "=" * 60)
        print("✅ SETUP COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        print("""
🎉 Your bot is ready to launch!

📋 Next Steps:
   1. Review your .env file configuration
   2. Run the bot: python bot_launcher.py
   3. Keep your .env and .bot_auth files secure!

🔐 Security Tips:
   - Never share your BOT_TOKEN
   - Keep .bot_auth file secret
   - Don't commit .env to git
   - Use strong passwords

🚀 To start the bot:
   python bot_launcher.py

📚 For deployment guides, check DEPLOYMENT.md

Happy coding! 🎊
        """)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
