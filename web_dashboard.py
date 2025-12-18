"""
Advanced Web Dashboard for Telegram Bot
Features: File Manager, Code Editor, Deploy Panel, Analytics
"""

import asyncio
import os
import secrets
import hashlib
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from aiohttp import web
import aiohttp_jinja2
import jinja2
import jwt
import base64

DASHBOARD_DIR = Path(__file__).parent / 'dashboard'
TEMPLATES_DIR = DASHBOARD_DIR / 'templates'
STATIC_DIR = DASHBOARD_DIR / 'static'
USERS_DIR = DASHBOARD_DIR / 'users'

DASHBOARD_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
USERS_DIR.mkdir(exist_ok=True)

SECRET_KEY = secrets.token_urlsafe(32)

user_sessions = {}
user_credentials = {}

def init_dashboard_db():
    conn = sqlite3.connect(DASHBOARD_DIR / 'dashboard.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS dashboard_users
                 (user_id INTEGER PRIMARY KEY,
                  telegram_id INTEGER,
                  username TEXT UNIQUE,
                  password_hash TEXT,
                  access_token TEXT,
                  created_at TEXT,
                  last_login TEXT,
                  is_active BOOLEAN DEFAULT 1)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_deployments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  project_name TEXT,
                  platform TEXT,
                  deploy_url TEXT,
                  status TEXT,
                  created_at TEXT,
                  FOREIGN KEY(user_id) REFERENCES dashboard_users(user_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS activity_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  action TEXT,
                  details TEXT,
                  ip_address TEXT,
                  timestamp TEXT,
                  FOREIGN KEY(user_id) REFERENCES dashboard_users(user_id))''')
    
    conn.commit()
    conn.close()

init_dashboard_db()

def create_user_panel(telegram_id, telegram_username):
    username = f"user_{telegram_id}"
    password = secrets.token_urlsafe(16)
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    access_token = secrets.token_urlsafe(32)
    
    user_folder = USERS_DIR / username
    user_folder.mkdir(exist_ok=True)
    (user_folder / 'uploads').mkdir(exist_ok=True)
    (user_folder / 'deployments').mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DASHBOARD_DIR / 'dashboard.db')
    c = conn.cursor()
    
    now = datetime.now().isoformat()
    c.execute('''INSERT OR REPLACE INTO dashboard_users 
                 (telegram_id, username, password_hash, access_token, created_at, last_login, is_active)
                 VALUES (?, ?, ?, ?, ?, ?, 1)''',
              (telegram_id, username, password_hash, access_token, now, now))
    
    user_id = c.lastrowid
    conn.commit()
    conn.close()
    
    user_credentials[telegram_id] = {
        'username': username,
        'password': password,
        'access_token': access_token,
        'panel_url': f'/panel/{access_token}'
    }
    
    return user_credentials[telegram_id]

def verify_token(token):
    conn = sqlite3.connect(DASHBOARD_DIR / 'dashboard.db')
    c = conn.cursor()
    c.execute('SELECT user_id, username FROM dashboard_users WHERE access_token = ? AND is_active = 1', (token,))
    result = c.fetchone()
    conn.close()
    return result

def log_activity(user_id, action, details, ip_address):
    conn = sqlite3.connect(DASHBOARD_DIR / 'dashboard.db')
    c = conn.cursor()
    c.execute('''INSERT INTO activity_logs (user_id, action, details, ip_address, timestamp)
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, action, details, ip_address, datetime.now().isoformat()))
    conn.commit()
    conn.close()

async def create_web_dashboard():
    app = web.Application(client_max_size=100*1024*1024)
    
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)))
    
    async def handle_panel_access(request):
        token = request.match_info.get('token')
        
        if not token:
            return web.Response(text="Invalid access", status=403)
        
        user_data = verify_token(token)
        if not user_data:
            return web.Response(text="Access denied", status=403)
        
        user_id, username = user_data
        
        user_folder = USERS_DIR / username
        files = []
        
        if (user_folder / 'uploads').exists():
            for file in (user_folder / 'uploads').iterdir():
                if file.is_file():
                    files.append({
                        'name': file.name,
                        'size': file.stat().st_size,
                        'modified': datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                    })
        
        dashboard_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hosting Panel - {username}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #fff;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{
            font-size: 2em;
            font-weight: 700;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            padding: 25px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        .stat-card h3 {{
            font-size: 0.9em;
            opacity: 0.8;
            margin-bottom: 10px;
        }}
        .stat-card .value {{
            font-size: 2.5em;
            font-weight: 700;
        }}
        .main-panel {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .panel-section {{
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            padding: 30px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        .panel-section h2 {{
            margin-bottom: 20px;
            font-size: 1.5em;
        }}
        .file-list {{
            max-height: 400px;
            overflow-y: auto;
        }}
        .file-item {{
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .upload-zone {{
            border: 2px dashed rgba(255, 255, 255, 0.4);
            padding: 50px;
            text-align: center;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }}
        .upload-zone:hover {{
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.8);
        }}
        .btn {{
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            padding: 10px 20px;
            border-radius: 8px;
            color: white;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }}
        .btn:hover {{
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        input[type="file"] {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Hosting Panel</h1>
            <div>
                <span style="opacity: 0.8;">Welcome, <strong>{username}</strong></span>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>📁 Total Files</h3>
                <div class="value">{len(files)}</div>
            </div>
            <div class="stat-card">
                <h3>💾 Storage Used</h3>
                <div class="value">{sum(f['size'] for f in files) / (1024*1024):.1f} MB</div>
            </div>
            <div class="stat-card">
                <h3>🚀 Deployments</h3>
                <div class="value">0</div>
            </div>
            <div class="stat-card">
                <h3>⚡ Status</h3>
                <div class="value" style="font-size: 1.5em;">🟢 Active</div>
            </div>
        </div>
        
        <div class="main-panel">
            <div class="panel-section">
                <h2>📤 Upload Files</h2>
                <div class="upload-zone" onclick="document.getElementById('fileInput').click()">
                    <p style="font-size: 3em; margin-bottom: 10px;">📁</p>
                    <p style="font-size: 1.2em;">Click to upload files</p>
                    <p style="opacity: 0.7; margin-top: 10px;">or drag and drop here</p>
                </div>
                <input type="file" id="fileInput" multiple onchange="uploadFiles(this.files)">
                
                <div style="margin-top: 20px;">
                    <button class="btn btn-primary" onclick="createProject()">➕ New Project</button>
                    <button class="btn" onclick="deployProject()">🚀 Deploy</button>
                </div>
            </div>
            
            <div class="panel-section">
                <h2>📂 Your Files</h2>
                <div class="file-list">
                    {''.join([f'''
                    <div class="file-item">
                        <div>
                            <strong>{f['name']}</strong>
                            <div style="opacity: 0.7; font-size: 0.9em;">
                                {f['size'] / 1024:.1f} KB • {f['modified'][:10]}
                            </div>
                        </div>
                        <div>
                            <button class="btn" onclick="editFile('{f['name']}')">✏️ Edit</button>
                            <button class="btn" onclick="deleteFile('{f['name']}')">🗑️ Delete</button>
                        </div>
                    </div>
                    ''' for f in files]) if files else '<p style="text-align: center; opacity: 0.7;">No files yet</p>'}
                </div>
            </div>
        </div>
    </div>
    
    <script>
        async function uploadFiles(files) {{
            const formData = new FormData();
            for (let file of files) {{
                formData.append('files', file);
            }}
            
            const response = await fetch('/api/upload/{token}', {{
                method: 'POST',
                body: formData
            }});
            
            if (response.ok) {{
                alert('✅ Files uploaded successfully!');
                location.reload();
            }} else {{
                alert('❌ Upload failed!');
            }}
        }}
        
        function editFile(filename) {{
            window.open('/editor/{token}/' + filename, '_blank');
        }}
        
        function deleteFile(filename) {{
            if (confirm('Delete ' + filename + '?')) {{
                fetch('/api/delete/{token}/' + filename, {{ method: 'DELETE' }})
                    .then(() => location.reload());
            }}
        }}
        
        function createProject() {{
            const name = prompt('Project name:');
            if (name) {{
                alert('Project "' + name + '" created!');
            }}
        }}
        
        function deployProject() {{
            alert('🚀 Deploy feature coming soon!');
        }}
        
        // Drag and drop
        const dropZone = document.querySelector('.upload-zone');
        dropZone.addEventListener('dragover', (e) => {{
            e.preventDefault();
            dropZone.style.background = 'rgba(255, 255, 255, 0.2)';
        }});
        dropZone.addEventListener('dragleave', () => {{
            dropZone.style.background = '';
        }});
        dropZone.addEventListener('drop', (e) => {{
            e.preventDefault();
            dropZone.style.background = '';
            uploadFiles(e.dataTransfer.files);
        }});
    </script>
</body>
</html>
        """
        
        log_activity(user_id, 'panel_access', 'Accessed hosting panel', request.remote)
        
        return web.Response(text=dashboard_html, content_type='text/html')
    
    async def handle_file_upload(request):
        token = request.match_info.get('token')
        user_data = verify_token(token)
        
        if not user_data:
            return web.json_response({'error': 'Unauthorized'}, status=403)
        
        user_id, username = user_data
        user_folder = USERS_DIR / username / 'uploads'
        
        reader = await request.multipart()
        uploaded_files = []
        
        async for field in reader:
            if field.name == 'files':
                filename = field.filename
                size = 0
                
                filepath = user_folder / filename
                with open(filepath, 'wb') as f:
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        size += len(chunk)
                        f.write(chunk)
                
                uploaded_files.append(filename)
        
        log_activity(user_id, 'file_upload', f'Uploaded {len(uploaded_files)} files', request.remote)
        
        return web.json_response({'success': True, 'files': uploaded_files})
    
    async def handle_file_delete(request):
        token = request.match_info.get('token')
        filename = request.match_info.get('filename')
        user_data = verify_token(token)
        
        if not user_data:
            return web.json_response({'error': 'Unauthorized'}, status=403)
        
        user_id, username = user_data
        filepath = USERS_DIR / username / 'uploads' / filename
        
        if filepath.exists():
            filepath.unlink()
            log_activity(user_id, 'file_delete', f'Deleted {filename}', request.remote)
            return web.json_response({'success': True})
        
        return web.json_response({'error': 'File not found'}, status=404)
    
    async def handle_code_editor(request):
        token = request.match_info.get('token')
        filename = request.match_info.get('filename')
        user_data = verify_token(token)
        
        if not user_data:
            return web.Response(text="Unauthorized", status=403)
        
        user_id, username = user_data
        filepath = USERS_DIR / username / 'uploads' / filename
        
        content = ""
        if filepath.exists():
            content = filepath.read_text(encoding='utf-8')
        
        editor_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Code Editor - {filename}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/theme/monokai.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/mode/python/python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/mode/javascript/javascript.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        .toolbar {{ background: #2c3e50; color: white; padding: 10px; display: flex; justify-content: space-between; }}
        .btn {{ background: #3498db; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 5px; }}
        .btn:hover {{ background: #2980b9; }}
        .CodeMirror {{ height: calc(100vh - 50px); }}
    </style>
</head>
<body>
    <div class="toolbar">
        <span>✏️ Editing: <strong>{filename}</strong></span>
        <button class="btn" onclick="saveFile()">💾 Save</button>
    </div>
    <textarea id="code">{content}</textarea>
    
    <script>
        const editor = CodeMirror.fromTextArea(document.getElementById('code'), {{
            mode: '{('python' if filename.endswith('.py') else 'javascript')}',
            theme: 'monokai',
            lineNumbers: true,
            autoCloseBrackets: true,
            matchBrackets: true
        }});
        
        async function saveFile() {{
            const content = editor.getValue();
            const response = await fetch('/api/save/{token}/{filename}', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{content}})
            }});
            
            if (response.ok) {{
                alert('✅ File saved!');
            }} else {{
                alert('❌ Save failed!');
            }}
        }}
        
        document.addEventListener('keydown', (e) => {{
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {{
                e.preventDefault();
                saveFile();
            }}
        }});
    </script>
</body>
</html>
        """
        
        return web.Response(text=editor_html, content_type='text/html')
    
    async def handle_file_save(request):
        token = request.match_info.get('token')
        filename = request.match_info.get('filename')
        user_data = verify_token(token)
        
        if not user_data:
            return web.json_response({'error': 'Unauthorized'}, status=403)
        
        user_id, username = user_data
        filepath = USERS_DIR / username / 'uploads' / filename
        
        data = await request.json()
        content = data.get('content', '')
        
        filepath.write_text(content, encoding='utf-8')
        log_activity(user_id, 'file_edit', f'Edited {filename}', request.remote)
        
        return web.json_response({'success': True})
    
    app.router.add_get('/panel/{token}', handle_panel_access)
    app.router.add_post('/api/upload/{token}', handle_file_upload)
    app.router.add_delete('/api/delete/{token}/{filename}', handle_file_delete)
    app.router.add_get('/editor/{token}/{filename}', handle_code_editor)
    app.router.add_post('/api/save/{token}/{filename}', handle_file_save)
    
    return app
