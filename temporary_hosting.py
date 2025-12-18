"""
Advanced Temporary Hosting System
Features: Auto-expiry, Smart URL detection, Session management
"""

import asyncio
import subprocess
import time
import secrets
import json
from datetime import datetime, timedelta
from pathlib import Path

# Import hosting detector
try:
    from hosting_detector import hosting, get_hosting_info
except:
    # Fallback if detector not available
    class FallbackHosting:
        def get_config(self):
            return {'full_url': 'http://localhost:8080', 'platform': 'local', 'is_production': False}
    hosting = FallbackHosting()
    def get_hosting_info():
        return {'platform_name': '🏠 Local', 'url': 'http://localhost:8080', 'is_production': False}

class TemporaryHostingManager:
    def __init__(self):
        self.active_sessions = {}
        self.ngrok_process = None
        self.session_timeout = 900  # 15 minutes in seconds
        
    async def create_temporary_hosting(self, user_id, username, is_owner=False, is_admin=False):
        """Create temporary hosting with auto-expiry"""
        
        # Generate unique credentials
        session_id = secrets.token_urlsafe(16)
        password = secrets.token_urlsafe(12)
        
        # Get public URL from hosting detector
        public_url = hosting.get_config()['full_url']
        
        # Owner & Admin = Unlimited session, Free users = 15 min
        if is_owner:
            expires_at = datetime.now() + timedelta(days=365)  # 1 year for owner
            session_type = "UNLIMITED"
        elif is_admin:
            expires_at = datetime.now() + timedelta(hours=24)  # 24 hours for admin
            session_type = "EXTENDED"
        else:
            expires_at = datetime.now() + timedelta(seconds=self.session_timeout)  # 15 min for users
            session_type = "TEMPORARY"
        
        # Create session
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'username': username,
            'password': password,
            'public_url': public_url,
            'created_at': datetime.now(),
            'expires_at': expires_at,
            'last_activity': datetime.now(),
            'is_active': True,
            'is_owner': is_owner,
            'is_admin': is_admin,
            'session_type': session_type
        }
        
        self.active_sessions[user_id] = session_data
        
        # Start auto-cleanup task (but skip for owner)
        if not is_owner:
            asyncio.create_task(self.monitor_session(user_id))
        
        return session_data
    
    async def start_ngrok_tunnel(self, subdomain):
        """Start ngrok tunnel for public access"""
        
        try:
            # Try to start ngrok
            import aiohttp
            
            # Check if ngrok is running
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://localhost:4040/api/tunnels', timeout=aiohttp.ClientTimeout(total=2)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get('tunnels'):
                                public_url = data['tunnels'][0]['public_url']
                                print(f"✅ Ngrok tunnel found: {public_url}")
                                return public_url
            except:
                print("⚠️ Ngrok not running, using localhost...")
            
            # If ngrok not available, use localhost
            print("💡 Using localhost (limited to local network)")
            return "http://localhost:8080"
            
        except Exception as e:
            print(f"⚠️ Tunnel setup: {e}")
            # Always fallback to localhost
            return "http://localhost:8080"
    
    async def monitor_session(self, user_id):
        """Monitor session and auto-expire after inactivity"""
        
        while user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            
            # Skip monitoring for owner (unlimited session)
            if session.get('is_owner', False):
                await asyncio.sleep(300)  # Check every 5 minutes but never expire
                continue
            
            # Skip monitoring for admin (extended session)
            if session.get('is_admin', False):
                # Only check expiry, no inactivity timeout
                now = datetime.now()
                if now > session['expires_at']:
                    await self.terminate_session(user_id, reason="Extended session expired")
                    break
                await asyncio.sleep(60)
                continue
            
            # Check expiry time for regular users
            now = datetime.now()
            
            # Check if session expired
            if now > session['expires_at']:
                await self.terminate_session(user_id, reason="Session expired")
                break
            
            # Check inactivity (15 minutes) - Only for free users
            inactivity = (now - session['last_activity']).total_seconds()
            if inactivity > self.session_timeout:
                await self.terminate_session(user_id, reason="Inactivity timeout (15 minutes)")
                break
            
            # Sleep for 30 seconds before next check
            await asyncio.sleep(30)
    
    async def terminate_session(self, user_id, reason="Manual stop"):
        """Terminate hosting session"""
        
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            session['is_active'] = False
            session['terminated_at'] = datetime.now()
            session['termination_reason'] = reason
            
            # Log termination
            print(f"Session terminated for user {user_id}: {reason}")
            
            # Remove from active sessions
            del self.active_sessions[user_id]
    
    def update_activity(self, user_id):
        """Update last activity timestamp"""
        
        if user_id in self.active_sessions:
            self.active_sessions[user_id]['last_activity'] = datetime.now()
    
    def get_session_info(self, user_id):
        """Get session information"""
        
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            
            # Calculate remaining time
            now = datetime.now()
            remaining = (session['expires_at'] - now).total_seconds()
            
            return {
                'status': 'active',
                'public_url': session['public_url'],
                'username': session['username'],
                'password': session['password'],
                'created_at': session['created_at'].isoformat(),
                'remaining_minutes': int(remaining / 60),
                'remaining_seconds': int(remaining % 60)
            }
        
        return {'status': 'inactive'}
    
    async def extend_session(self, user_id, extra_minutes=15):
        """Extend session time"""
        
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            session['expires_at'] += timedelta(minutes=extra_minutes)
            session['last_activity'] = datetime.now()
            return True
        
        return False

# Global instance
hosting_manager = TemporaryHostingManager()


async def create_user_hosting(user_id, username, is_owner=False, is_admin=False):
    """Create temporary hosting for user"""
    
    session = await hosting_manager.create_temporary_hosting(user_id, username, is_owner, is_admin)
    
    # Get hosting info
    host_info = get_hosting_info()
    
    # Different messages based on user type
    if is_owner:
        duration_text = "♾️ <b>UNLIMITED</b> (Never Expires)"
        note_text = "• 👑 Owner privilege - Unlimited access\n• No inactivity timeout\n• Session never expires"
    elif is_admin:
        duration_text = "⏰ <b>24 Hours</b> (Extended)"
        note_text = "• 👨‍💼 Admin privilege - Extended session\n• No inactivity timeout\n• Auto-renews on activity"
    else:
        duration_text = "⏱️ <b>15 Minutes</b> (Free)"
        note_text = "• Session auto-expires after <b>15 min inactivity</b>\n• Click '🔄 Extend' to add 15 more minutes\n• Upgrade to Premium for longer sessions"
    
    # Format message
    message = f"""
╔═══════════════════════════════════╗
    🌐 <b>FILE MANAGER IS READY!</b> 🌐
╚═══════════════════════════════════╝

<b>✨ Your {'Unlimited' if is_owner else 'Extended' if is_admin else 'Temporary'} Hosting Created!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>🔗 ACCESS URL:</b>

<code>{session['public_url']}/panel/{session['session_id']}</code>

<b>💡 Click link above to open in browser!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>🔐 CREDENTIALS:</b>

👤 <b>Username:</b> <code>{session['username']}</code>
🔑 <b>Password:</b> <code>{session['password']}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>⏰ SESSION INFO:</b>

⏱️ <b>Duration:</b> {duration_text}
🕒 <b>Created:</b> {session['created_at'].strftime('%H:%M:%S')}
⚡ <b>Status:</b> 🟢 Active
🏷️ <b>Type:</b> {session['session_type']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>🌍 HOSTING INFO:</b>

🏠 <b>Platform:</b> {host_info['platform_name']}
🔗 <b>Mode:</b> {'Production 🌍' if host_info['is_production'] else 'Development 🏠'}
📡 <b>Public Access:</b> {'✅ Yes' if host_info['is_production'] else '⚠️ Local Only'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>⚠️ IMPORTANT:</b>

{note_text}
• All files saved automatically
• {'HTTPS' if host_info['is_production'] else 'HTTP'} connection
• Works on any device with browser

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>🎯 FEATURES:</b>

📤 Upload files (Drag & Drop)
✏️ Code editor (Syntax highlighting)
📁 File manager (Full control)
🚀 Deploy projects (One-click)
📊 Analytics dashboard
💾 Auto-save enabled

<b>🎊 Your hosting is LIVE now!</b>
"""
    
    return {
        'message': message,
        'session': session
    }


async def get_session_status(user_id):
    """Get current session status"""
    
    info = hosting_manager.get_session_info(user_id)
    
    if info['status'] == 'active':
        return f"""
╔═══════════════════════════════════╗
    ⏰ <b>SESSION STATUS</b> ⏰
╚═══════════════════════════════════╝

<b>🟢 ACTIVE SESSION</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>⏱️ TIME REMAINING:</b>

⏰ <b>{info['remaining_minutes']}:{info['remaining_seconds']:02d}</b> minutes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>🔗 ACCESS:</b>

<code>{info['public_url']}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>💡 TIP:</b>

Click "🔄 Extend" to add 15 more minutes!
"""
    else:
        return """
╔═══════════════════════════════════╗
    ⏰ <b>SESSION STATUS</b> ⏰
╚═══════════════════════════════════╝

<b>🔴 NO ACTIVE SESSION</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>📌 CREATE NEW SESSION:</b>

Use /panel command to create a new
temporary hosting session.

<b>Duration:</b> 15 minutes
<b>Features:</b> Full access
<b>Security:</b> Auto-expire
"""
