"""
Cloud Hosting Detection & Auto-Configuration
Automatically detects hosting platform and configures URLs
"""

import os
import socket
import subprocess
from pathlib import Path

class HostingDetector:
    def __init__(self):
        self.platform = self.detect_platform()
        self.base_url = self.get_base_url()
        self.port = self.get_port()
        
    def detect_platform(self):
        """Auto-detect hosting platform"""
        
        # Railway
        if os.getenv('RAILWAY_ENVIRONMENT'):
            return 'railway'
        
        # Heroku
        if os.getenv('DYNO'):
            return 'heroku'
        
        # Render
        if os.getenv('RENDER'):
            return 'render'
        
        # Vercel
        if os.getenv('VERCEL'):
            return 'vercel'
        
        # Google Cloud
        if os.getenv('GAE_INSTANCE') or os.getenv('GOOGLE_CLOUD_PROJECT'):
            return 'gcp'
        
        # AWS
        if os.getenv('AWS_EXECUTION_ENV'):
            return 'aws'
        
        # Replit
        if os.getenv('REPL_ID'):
            return 'replit'
        
        # Glitch
        if os.getenv('PROJECT_NAME') and 'glitch' in str(os.getenv('PROJECT_DOMAIN', '')).lower():
            return 'glitch'
        
        # PythonAnywhere
        if 'pythonanywhere' in socket.gethostname().lower():
            return 'pythonanywhere'
        
        # Local
        return 'local'
    
    def get_base_url(self):
        """Get base URL based on platform"""
        
        platform_urls = {
            'railway': self._get_railway_url(),
            'heroku': self._get_heroku_url(),
            'render': self._get_render_url(),
            'vercel': self._get_vercel_url(),
            'gcp': self._get_gcp_url(),
            'replit': self._get_replit_url(),
            'glitch': self._get_glitch_url(),
            'pythonanywhere': self._get_pythonanywhere_url(),
            'local': 'http://localhost'
        }
        
        return platform_urls.get(self.platform, 'http://localhost')
    
    def get_port(self):
        """Get port based on platform"""
        
        # Most platforms provide PORT env variable
        if os.getenv('PORT'):
            return int(os.getenv('PORT'))
        
        # Platform-specific ports
        platform_ports = {
            'railway': 8080,
            'heroku': int(os.getenv('PORT', 8080)),
            'render': 10000,
            'vercel': 3000,
            'gcp': 8080,
            'replit': 8080,
            'glitch': 3000,
            'pythonanywhere': 8080,
            'local': 8080
        }
        
        return platform_ports.get(self.platform, 8080)
    
    def _get_railway_url(self):
        """Get Railway public URL"""
        # Railway provides RAILWAY_STATIC_URL or we construct it
        static_url = os.getenv('RAILWAY_STATIC_URL')
        if static_url:
            return f"https://{static_url}"
        
        # Construct from project details
        project = os.getenv('RAILWAY_PROJECT_ID', 'unknown')[:8]
        service = os.getenv('RAILWAY_SERVICE_NAME', 'app')
        return f"https://{service}-{project}.up.railway.app"
    
    def _get_heroku_url(self):
        """Get Heroku app URL"""
        app_name = os.getenv('HEROKU_APP_NAME')
        if app_name:
            return f"https://{app_name}.herokuapp.com"
        return "http://localhost"
    
    def _get_render_url(self):
        """Get Render service URL"""
        render_external_url = os.getenv('RENDER_EXTERNAL_URL')
        if render_external_url:
            return render_external_url
        
        service_name = os.getenv('RENDER_SERVICE_NAME', 'app')
        return f"https://{service_name}.onrender.com"
    
    def _get_vercel_url(self):
        """Get Vercel deployment URL"""
        vercel_url = os.getenv('VERCEL_URL')
        if vercel_url:
            return f"https://{vercel_url}"
        return "http://localhost"
    
    def _get_gcp_url(self):
        """Get Google Cloud App Engine URL"""
        project = os.getenv('GOOGLE_CLOUD_PROJECT')
        if project:
            return f"https://{project}.appspot.com"
        return "http://localhost"
    
    def _get_replit_url(self):
        """Get Replit app URL"""
        repl_slug = os.getenv('REPL_SLUG')
        repl_owner = os.getenv('REPL_OWNER')
        if repl_slug and repl_owner:
            return f"https://{repl_slug}.{repl_owner}.repl.co"
        return "http://localhost"
    
    def _get_glitch_url(self):
        """Get Glitch project URL"""
        project_domain = os.getenv('PROJECT_DOMAIN')
        if project_domain:
            return f"https://{project_domain}.glitch.me"
        return "http://localhost"
    
    def _get_pythonanywhere_url(self):
        """Get PythonAnywhere URL"""
        username = os.getenv('USER', 'user')
        return f"https://{username}.pythonanywhere.com"
    
    def get_full_url(self):
        """Get complete URL with port"""
        if self.platform == 'local':
            return f"{self.base_url}:{self.port}"
        else:
            # Production platforms use standard HTTPS port
            return self.base_url
    
    def get_config(self):
        """Get complete hosting configuration"""
        return {
            'platform': self.platform,
            'base_url': self.base_url,
            'port': self.port,
            'full_url': self.get_full_url(),
            'is_production': self.platform != 'local',
            'supports_websocket': self.platform not in ['vercel'],
            'bind_address': '0.0.0.0' if self.platform != 'local' else 'localhost'
        }

# Global instance
hosting = HostingDetector()

def get_hosting_info():
    """Get hosting information for bot messages"""
    config = hosting.get_config()
    
    platform_names = {
        'railway': '🚂 Railway',
        'heroku': '🟣 Heroku',
        'render': '🎨 Render',
        'vercel': '▲ Vercel',
        'gcp': '☁️ Google Cloud',
        'aws': '📦 AWS',
        'replit': '🔄 Replit',
        'glitch': '🎏 Glitch',
        'pythonanywhere': '🐍 PythonAnywhere',
        'local': '🏠 Local'
    }
    
    return {
        'platform_name': platform_names.get(config['platform'], '🌐 Unknown'),
        'platform': config['platform'],
        'url': config['full_url'],
        'is_production': config['is_production']
    }

def print_startup_info():
    """Print startup information"""
    config = hosting.get_config()
    info = get_hosting_info()
    
    print("\n" + "="*60)
    print("🚀 BOT HOSTING CONFIGURATION")
    print("="*60)
    print(f"Platform: {info['platform_name']}")
    print(f"Environment: {'🌍 Production' if config['is_production'] else '🏠 Development'}")
    print(f"Base URL: {config['base_url']}")
    print(f"Port: {config['port']}")
    print(f"Bind Address: {config['bind_address']}")
    print(f"Full URL: {config['full_url']}")
    print("="*60 + "\n")
    
    return config
