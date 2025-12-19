"""
🚀 COMPLETE LIVE CONTROL PANEL
💫 MADE BY DARK SHADOW 💫

Full-featured web panel with:
- File upload (drag & drop + button)
- Code editor
- One-click run
- Dependencies manager
- Terminal
- Logs viewer
"""

import asyncio
import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
from aiohttp import web
import aiohttp

class LivePanel:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.upload_dir = self.base_dir / 'upload_bots'
        self.running_processes = {}
        self.upload_dir.mkdir(exist_ok=True)
    
    async def handle_file_upload(self, request):
        """Handle file upload from web panel"""
        try:
            reader = await request.multipart()
            user_id = None
            uploaded_files = []
            
            async for field in reader:
                if field.name == 'user_id':
                    user_id = await field.text()
                elif field.name == 'file':
                    filename = field.filename
                    if not filename:
                        continue
                    
                    # Create user folder
                    if not user_id:
                        user_id = 'default'
                    
                    user_folder = self.upload_dir / str(user_id)
                    user_folder.mkdir(exist_ok=True)
                    
                    # Save file
                    file_path = user_folder / filename
                    size = 0
                    with open(file_path, 'wb') as f:
                        while True:
                            chunk = await field.read_chunk()
                            if not chunk:
                                break
                            size += len(chunk)
                            f.write(chunk)
                    
                    uploaded_files.append({
                        'filename': filename,
                        'size': size,
                        'path': str(file_path)
                    })
            
            return web.json_response({
                'success': True,
                'message': f'✅ Uploaded {len(uploaded_files)} file(s)',
                'files': uploaded_files
            })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_list_files(self, request):
        """List all uploaded files"""
        try:
            user_id = request.match_info.get('user_id', 'default')
            user_folder = self.upload_dir / str(user_id)
            
            if not user_folder.exists():
                return web.json_response({
                    'success': True,
                    'files': []
                })
            
            files = []
            for file_path in user_folder.iterdir():
                if file_path.is_file():
                    files.append({
                        'name': file_path.name,
                        'size': file_path.stat().st_size,
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        'type': file_path.suffix
                    })
            
            return web.json_response({
                'success': True,
                'files': files,
                'count': len(files)
            })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_delete_file(self, request):
        """Delete a file"""
        try:
            data = await request.json()
            user_id = data.get('user_id', 'default')
            filename = data.get('filename')
            
            file_path = self.upload_dir / str(user_id) / filename
            
            if file_path.exists():
                file_path.unlink()
                return web.json_response({
                    'success': True,
                    'message': f'✅ Deleted {filename}'
                })
            else:
                return web.json_response({
                    'success': False,
                    'error': 'File not found'
                })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_read_file(self, request):
        """Read file content"""
        try:
            data = await request.json()
            user_id = data.get('user_id', 'default')
            filename = data.get('filename')
            
            # Check system files
            system_files = ['requirements.txt', '.env', 'main.py']
            if filename in system_files:
                file_path = self.base_dir / filename
            else:
                file_path = self.upload_dir / str(user_id) / filename
            
            if not file_path.exists():
                return web.json_response({
                    'success': False,
                    'error': 'File not found'
                })
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            return web.json_response({
                'success': True,
                'content': content,
                'filename': filename
            })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_save_file(self, request):
        """Save file content"""
        try:
            data = await request.json()
            user_id = data.get('user_id', 'default')
            filename = data.get('filename')
            content = data.get('content', '')
            
            # System files
            system_files = ['requirements.txt', '.env']
            if filename in system_files:
                file_path = self.base_dir / filename
            else:
                user_folder = self.upload_dir / str(user_id)
                user_folder.mkdir(exist_ok=True)
                file_path = user_folder / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return web.json_response({
                'success': True,
                'message': f'✅ Saved {filename}'
            })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_run_code(self, request):
        """Run code file"""
        try:
            data = await request.json()
            user_id = data.get('user_id', 'default')
            filename = data.get('filename')
            
            file_path = self.upload_dir / str(user_id) / filename
            
            if not file_path.exists():
                return web.json_response({
                    'success': False,
                    'error': 'File not found'
                })
            
            ext = file_path.suffix.lower()
            
            if ext == '.py':
                cmd = [sys.executable, str(file_path)]
            elif ext == '.js':
                cmd = ['node', str(file_path)]
            else:
                return web.json_response({
                    'success': False,
                    'error': 'Only .py and .js files supported'
                })
            
            # Run process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(file_path.parent)
            )
            
            process_id = f"{user_id}_{filename}_{datetime.now().timestamp()}"
            self.running_processes[process_id] = process
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=60.0
                )
                
                output = stdout.decode('utf-8', errors='ignore')
                error = stderr.decode('utf-8', errors='ignore')
                
                return web.json_response({
                    'success': process.returncode == 0,
                    'output': output,
                    'error': error,
                    'returncode': process.returncode,
                    'process_id': process_id
                })
            
            except asyncio.TimeoutError:
                process.kill()
                return web.json_response({
                    'success': False,
                    'error': 'Execution timeout (60s)',
                    'output': 'Process terminated due to timeout'
                })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_install_deps(self, request):
        """Install dependencies"""
        try:
            requirements = self.base_dir / 'requirements.txt'
            
            if not requirements.exists():
                return web.json_response({
                    'success': False,
                    'error': 'requirements.txt not found'
                })
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, '-m', 'pip', 'install', '-r', str(requirements),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()
            
            return web.json_response({
                'success': process.returncode == 0,
                'output': output,
                'message': '✅ Dependencies installed!' if process.returncode == 0 else '❌ Installation failed'
            })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_terminal(self, request):
        """Execute terminal command"""
        try:
            data = await request.json()
            command = data.get('command', '').strip()
            
            if not command:
                return web.json_response({
                    'success': False,
                    'error': 'Empty command'
                })
            
            # Block dangerous commands
            blocked = ['rm -rf', 'del /f', 'format', 'shutdown', 'reboot', 'mkfs']
            if any(cmd in command.lower() for cmd in blocked):
                return web.json_response({
                    'success': False,
                    'error': '❌ Dangerous command blocked for safety'
                })
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.base_dir)
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=15.0
                )
                
                output = stdout.decode('utf-8', errors='ignore')
                error = stderr.decode('utf-8', errors='ignore')
                
                return web.json_response({
                    'success': True,
                    'output': output + error
                })
            
            except asyncio.TimeoutError:
                process.kill()
                return web.json_response({
                    'success': False,
                    'error': 'Command timeout (15s)'
                })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_view_logs(self, request):
        """View bot logs"""
        try:
            log_file = self.base_dir / 'logs' / 'bot.log'
            
            if not log_file.exists():
                return web.json_response({
                    'success': True,
                    'logs': 'No logs available yet'
                })
            
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                recent = ''.join(lines[-200:])
            
            return web.json_response({
                'success': True,
                'logs': recent
            })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_panel_html(self, request):
        """Serve complete control panel HTML"""
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Bot Control Panel - Dark Shadow</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .header h1 { font-size: 3em; margin-bottom: 10px; }
        .header p { font-size: 1.3em; opacity: 0.95; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: rgba(255, 255, 255, 0.98);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
        }
        .card h2 {
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s;
            width: 100%;
            margin: 8px 0;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        button:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        button:active { transform: translateY(0); }
        button.success { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        button.danger { background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }
        button.warning { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        
        input[type="text"], input[type="number"], input[type="file"], textarea, select {
            width: 100%;
            padding: 14px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 15px;
            margin: 10px 0;
            transition: all 0.3s;
        }
        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        textarea {
            font-family: 'Consolas', 'Monaco', monospace;
            resize: vertical;
            min-height: 200px;
        }
        
        .output {
            background: #1e1e1e;
            color: #00ff00;
            padding: 20px;
            border-radius: 12px;
            font-family: 'Consolas', monospace;
            font-size: 14px;
            max-height: 500px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            margin: 15px 0;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
        }
        
        .status {
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            font-weight: 600;
            animation: fadeIn 0.3s;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border-left: 4px solid #28a745;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border-left: 4px solid #dc3545;
        }
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border-left: 4px solid #17a2b8;
        }
        
        .file-list {
            max-height: 400px;
            overflow-y: auto;
            margin: 15px 0;
        }
        .file-item {
            padding: 15px;
            background: #f8f9fa;
            margin: 8px 0;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s;
            border-left: 4px solid #667eea;
        }
        .file-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        .file-item button {
            width: auto;
            padding: 8px 16px;
            margin: 0 5px;
            font-size: 14px;
        }
        
        .drop-zone {
            border: 3px dashed #667eea;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            margin: 15px 0;
            background: rgba(102, 126, 234, 0.05);
        }
        .drop-zone:hover {
            background: rgba(102, 126, 234, 0.1);
            border-color: #764ba2;
        }
        .drop-zone.dragover {
            background: rgba(102, 126, 234, 0.2);
            border-color: #38ef7d;
        }
        
        .spinner {
            border: 5px solid #f3f3f3;
            border-top: 5px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
            display: none;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .hidden { display: none !important; }
        .tab-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab-buttons button {
            flex: 1;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Bot Control Panel</h1>
            <p>💫 MADE BY DARK SHADOW 💫</p>
            <p style="font-size:0.9em; margin-top:10px;">Complete Web-Based Bot Management System</p>
        </div>
        
        <!-- User ID Input -->
        <div class="card">
            <h2>👤 Your Details</h2>
            <input type="number" id="globalUserId" placeholder="Enter Your Telegram ID" value="">
            <div class="status info" style="font-size:14px;">
                ℹ️ Get your ID from @userinfobot on Telegram
            </div>
        </div>
        
        <div class="grid">
            <!-- File Upload & Manager -->
            <div class="card" style="grid-column: span 2;">
                <h2>📁 File Manager</h2>
                
                <div class="tab-buttons">
                    <button onclick="switchTab('upload')" class="success">📤 Upload Files</button>
                    <button onclick="switchTab('manage')" class="warning">📂 Manage Files</button>
                </div>
                
                <div id="uploadTab" class="tab-content active">
                    <div class="drop-zone" id="dropZone">
                        <h3>📤 Drop files here or click to browse</h3>
                        <p>Supports: .py, .js, .txt, .json, .zip</p>
                        <input type="file" id="fileInput" multiple hidden>
                    </div>
                    <div id="uploadStatus"></div>
                    <div class="spinner" id="uploadSpinner"></div>
                </div>
                
                <div id="manageTab" class="tab-content">
                    <button onclick="loadFiles()" class="success">🔄 Refresh File List</button>
                    <div id="fileListStatus"></div>
                    <div class="file-list" id="fileList"></div>
                </div>
            </div>
        </div>
        
        <div class="grid">
            <!-- Code Editor & Runner -->
            <div class="card">
                <h2>✏️ Code Editor & Runner</h2>
                <select id="editorFileSelect" onchange="loadFileToEditor()">
                    <option value="">-- Select file to edit --</option>
                </select>
                <textarea id="codeEditor" placeholder="Write or paste your code here..."></textarea>
                <input type="text" id="newFileName" placeholder="New filename (e.g., test.py)">
                <button onclick="saveCode()" class="success">💾 Save Code</button>
                <button onclick="runCode()" class="success">▶️ Run Code</button>
                <div id="editorStatus"></div>
                <div class="output" id="codeOutput"></div>
            </div>
            
            <!-- Dependencies Manager -->
            <div class="card">
                <h2>📦 Dependencies Manager</h2>
                <textarea id="requirements" rows="8" placeholder="requests==2.31.0
beautifulsoup4==4.12.0
pandas==2.0.0"></textarea>
                <button onclick="saveRequirements()" class="success">💾 Save requirements.txt</button>
                <button onclick="installDeps()" class="warning">⚡ Install All Dependencies</button>
                <div id="depsStatus"></div>
                <div class="spinner" id="depsSpinner"></div>
                <div class="output" id="depsOutput" style="display:none;"></div>
            </div>
        </div>
        
        <div class="grid">
            <!-- .env Manager -->
            <div class="card">
                <h2>⚙️ .env Configuration</h2>
                <textarea id="envEditor" rows="10" placeholder="BOT_TOKEN=your_token
OWNER_ID=123456
ADMIN_ID=123456
YOUR_USERNAME=@DARK22v
UPDATE_CHANNEL=https://t.me/DARK22v"></textarea>
                <button onclick="saveEnv()" class="success">💾 Save .env File</button>
                <button onclick="loadEnv()" class="warning">🔄 Reload .env</button>
                <div id="envStatus"></div>
            </div>
            
            <!-- Terminal -->
            <div class="card">
                <h2>💻 Terminal</h2>
                <input type="text" id="termInput" placeholder="Enter command (e.g., pip list, ls, dir)">
                <button onclick="runTerminal()" class="success">⚡ Execute Command</button>
                <div id="termStatus"></div>
                <div class="output" id="termOutput"></div>
                
                <div style="margin-top:20px; font-size:13px; color:#666;">
                    <b>Quick Commands:</b><br>
                    • pip list - Show installed packages<br>
                    • python --version - Python version<br>
                    • ls / dir - List files<br>
                    • pwd - Current directory
                </div>
            </div>
        </div>
        
        <div class="grid">
            <!-- Logs Viewer -->
            <div class="card" style="grid-column: span 2;">
                <h2>📋 Bot Logs (Auto-refresh every 5s)</h2>
                <button onclick="viewLogs()" class="warning">🔄 Refresh Now</button>
                <div class="output" id="logsOutput" style="max-height: 600px;"></div>
            </div>
        </div>
    </div>
    
    <script>
        let currentUserId = '';
        let refreshInterval = null;
        
        // Initialize
        window.onload = function() {
            const savedId = localStorage.getItem('telegramUserId');
            if (savedId) {
                document.getElementById('globalUserId').value = savedId;
                currentUserId = savedId;
            }
            
            document.getElementById('globalUserId').addEventListener('change', function() {
                currentUserId = this.value;
                localStorage.setItem('telegramUserId', currentUserId);
            });
            
            loadRequirements();
            loadEnv();
            loadFiles();
            viewLogs();
            
            // Auto-refresh logs
            refreshInterval = setInterval(viewLogs, 5000);
            
            // Drag & drop
            const dropZone = document.getElementById('dropZone');
            const fileInput = document.getElementById('fileInput');
            
            dropZone.onclick = () => fileInput.click();
            
            dropZone.ondragover = (e) => {
                e.preventDefault();
                dropZone.classList.add('dragover');
            };
            
            dropZone.ondragleave = () => {
                dropZone.classList.remove('dragover');
            };
            
            dropZone.ondrop = (e) => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
                handleFiles(e.dataTransfer.files);
            };
            
            fileInput.onchange = () => {
                handleFiles(fileInput.files);
            };
        };
        
        function switchTab(tab) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            if (tab === 'upload') {
                document.getElementById('uploadTab').classList.add('active');
            } else {
                document.getElementById('manageTab').classList.add('active');
            }
        }
        
        async function handleFiles(files) {
            if (!currentUserId) {
                showStatus('uploadStatus', '❌ Please enter your Telegram ID first', 'error');
                return;
            }
            
            const formData = new FormData();
            formData.append('user_id', currentUserId);
            
            for (let file of files) {
                formData.append('file', file);
            }
            
            const spinner = document.getElementById('uploadSpinner');
            const status = document.getElementById('uploadStatus');
            
            spinner.style.display = 'block';
            status.innerHTML = '<div class="status info">⏳ Uploading files...</div>';
            
            try {
                const response = await fetch('/api/upload-file', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                spinner.style.display = 'none';
                
                if (data.success) {
                    showStatus('uploadStatus', data.message, 'success');
                    setTimeout(() => {
                        switchTab('manage');
                        loadFiles();
                    }, 1000);
                } else {
                    showStatus('uploadStatus', '❌ ' + data.error, 'error');
                }
            } catch (error) {
                spinner.style.display = 'none';
                showStatus('uploadStatus', '❌ Upload failed: ' + error.message, 'error');
            }
        }
        
        async function loadFiles() {
            if (!currentUserId) {
                showStatus('fileListStatus', '❌ Please enter your Telegram ID', 'error');
                return;
            }
            
            try {
                const response = await fetch(`/api/list-files/${currentUserId}`);
                const data = await response.json();
                
                const fileList = document.getElementById('fileList');
                const select = document.getElementById('editorFileSelect');
                
                if (data.success && data.files.length > 0) {
                    fileList.innerHTML = data.files.map(file => `
                        <div class="file-item">
                            <div>
                                <b>${file.name}</b><br>
                                <small>${(file.size/1024).toFixed(2)} KB • ${new Date(file.modified).toLocaleString()}</small>
                            </div>
                            <div>
                                <button onclick="editFile('${file.name}')" class="success">✏️ Edit</button>
                                <button onclick="runFile('${file.name}')" class="success">▶️ Run</button>
                                <button onclick="deleteFile('${file.name}')" class="danger">🗑️ Delete</button>
                            </div>
                        </div>
                    `).join('');
                    
                    select.innerHTML = '<option value="">-- Select file --</option>' +
                        data.files.map(f => `<option value="${f.name}">${f.name}</option>`).join('');
                    
                    showStatus('fileListStatus', `✅ Found ${data.count} file(s)`, 'success');
                } else {
                    fileList.innerHTML = '<div class="status info">📂 No files uploaded yet</div>';
                    showStatus('fileListStatus', 'Upload some files to get started', 'info');
                }
            } catch (error) {
                showStatus('fileListStatus', '❌ Error: ' + error.message, 'error');
            }
        }
        
        async function editFile(filename) {
            document.getElementById('editorFileSelect').value = filename;
            await loadFileToEditor();
        }
        
        async function loadFileToEditor() {
            const filename = document.getElementById('editorFileSelect').value;
            if (!filename || !currentUserId) return;
            
            try {
                const response = await fetch('/api/read-file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename, user_id: currentUserId })
                });
                
                const data = await response.json();
                if (data.success) {
                    document.getElementById('codeEditor').value = data.content;
                    document.getElementById('newFileName').value = filename;
                    showStatus('editorStatus', `✅ Loaded ${filename}`, 'success');
                }
            } catch (error) {
                showStatus('editorStatus', '❌ ' + error.message, 'error');
            }
        }
        
        async function saveCode() {
            const filename = document.getElementById('newFileName').value.trim();
            const content = document.getElementById('codeEditor').value;
            
            if (!filename || !currentUserId) {
                showStatus('editorStatus', '❌ Enter filename and user ID', 'error');
                return;
            }
            
            try {
                const response = await fetch('/api/save-file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename, content, user_id: currentUserId })
                });
                
                const data = await response.json();
                if (data.success) {
                    showStatus('editorStatus', data.message, 'success');
                    loadFiles();
                } else {
                    showStatus('editorStatus', '❌ ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('editorStatus', '❌ ' + error.message, 'error');
            }
        }
        
        async function runCode() {
            const filename = document.getElementById('newFileName').value.trim() || 
                           document.getElementById('editorFileSelect').value;
            
            if (!filename || !currentUserId) {
                showStatus('editorStatus', '❌ Select a file first', 'error');
                return;
            }
            
            await runFile(filename);
        }
        
        async function runFile(filename) {
            const output = document.getElementById('codeOutput');
            output.textContent = '⏳ Running ' + filename + '...\\n';
            showStatus('editorStatus', '⏳ Executing...', 'info');
            
            try {
                const response = await fetch('/api/run-code', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename, user_id: currentUserId })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    output.textContent = '=== OUTPUT ===\\n' + (data.output || '(no output)');
                    showStatus('editorStatus', '✅ Execution completed!', 'success');
                } else {
                    output.textContent = '=== ERROR ===\\n' + (data.error || data.output);
                    showStatus('editorStatus', '❌ Execution failed', 'error');
                }
            } catch (error) {
                output.textContent = '❌ ' + error.message;
                showStatus('editorStatus', '❌ ' + error.message, 'error');
            }
        }
        
        async function deleteFile(filename) {
            if (!confirm(`Delete ${filename}?`)) return;
            
            try {
                const response = await fetch('/api/delete-file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename, user_id: currentUserId })
                });
                
                const data = await response.json();
                if (data.success) {
                    showStatus('fileListStatus', data.message, 'success');
                    loadFiles();
                }
            } catch (error) {
                showStatus('fileListStatus', '❌ ' + error.message, 'error');
            }
        }
        
        async function loadRequirements() {
            try {
                const response = await fetch('/api/read-file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: 'requirements.txt' })
                });
                const data = await response.json();
                if (data.success) {
                    document.getElementById('requirements').value = data.content;
                }
            } catch (error) {}
        }
        
        async function saveRequirements() {
            const content = document.getElementById('requirements').value;
            
            try {
                const response = await fetch('/api/save-file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: 'requirements.txt', content })
                });
                const data = await response.json();
                showStatus('depsStatus', data.message, data.success ? 'success' : 'error');
            } catch (error) {
                showStatus('depsStatus', '❌ ' + error.message, 'error');
            }
        }
        
        async function installDeps() {
            const spinner = document.getElementById('depsSpinner');
            const output = document.getElementById('depsOutput');
            
            spinner.style.display = 'block';
            output.style.display = 'none';
            showStatus('depsStatus', '⏳ Installing dependencies...', 'info');
            
            try {
                const response = await fetch('/api/install-deps');
                const data = await response.json();
                
                spinner.style.display = 'none';
                output.style.display = 'block';
                output.textContent = data.output || '';
                
                showStatus('depsStatus', data.message, data.success ? 'success' : 'error');
            } catch (error) {
                spinner.style.display = 'none';
                showStatus('depsStatus', '❌ ' + error.message, 'error');
            }
        }
        
        async function loadEnv() {
            try {
                const response = await fetch('/api/read-file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: '.env' })
                });
                const data = await response.json();
                if (data.success) {
                    document.getElementById('envEditor').value = data.content;
                    showStatus('envStatus', '✅ .env loaded', 'success');
                }
            } catch (error) {}
        }
        
        async function saveEnv() {
            const content = document.getElementById('envEditor').value;
            
            try {
                const response = await fetch('/api/save-file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: '.env', content })
                });
                const data = await response.json();
                showStatus('envStatus', data.message, data.success ? 'success' : 'error');
            } catch (error) {
                showStatus('envStatus', '❌ ' + error.message, 'error');
            }
        }
        
        async function runTerminal() {
            const command = document.getElementById('termInput').value.trim();
            const output = document.getElementById('termOutput');
            
            if (!command) {
                showStatus('termStatus', '❌ Enter a command', 'error');
                return;
            }
            
            output.textContent = '$ ' + command + '\\n⏳ Executing...\\n';
            showStatus('termStatus', '⏳ Running...', 'info');
            
            try {
                const response = await fetch('/api/terminal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    output.textContent += data.output || '(no output)';
                    showStatus('termStatus', '✅ Command executed', 'success');
                } else {
                    output.textContent += '❌ ' + data.error;
                    showStatus('termStatus', '❌ Failed', 'error');
                }
            } catch (error) {
                output.textContent += '❌ ' + error.message;
                showStatus('termStatus', '❌ ' + error.message, 'error');
            }
        }
        
        async function viewLogs() {
            try {
                const response = await fetch('/api/view-logs');
                const data = await response.json();
                
                const output = document.getElementById('logsOutput');
                if (data.success) {
                    output.textContent = data.logs || 'No logs yet';
                    output.scrollTop = output.scrollHeight;
                } else {
                    output.textContent = '❌ ' + data.error;
                }
            } catch (error) {
                document.getElementById('logsOutput').textContent = '❌ ' + error.message;
            }
        }
        
        function showStatus(elementId, message, type) {
            const el = document.getElementById(elementId);
            el.innerHTML = `<div class="status ${type}">${message}</div>`;
            setTimeout(() => {
                if (el.innerHTML.includes(message)) {
                    el.innerHTML = '';
                }
            }, 5000);
        }
    </script>
</body>
</html>
"""
        return web.Response(text=html, content_type='text/html')

def create_live_panel_app(base_dir):
    """Create live panel application with all routes"""
    panel = LivePanel(base_dir)
    app = web.Application()
    
    # HTML
    app.router.add_get('/', panel.handle_panel_html)
    app.router.add_get('/live', panel.handle_panel_html)
    
    # File operations
    app.router.add_post('/api/upload-file', panel.handle_file_upload)
    app.router.add_get('/api/list-files/{user_id}', panel.handle_list_files)
    app.router.add_post('/api/delete-file', panel.handle_delete_file)
    app.router.add_post('/api/read-file', panel.handle_read_file)
    app.router.add_post('/api/save-file', panel.handle_save_file)
    
    # Code execution
    app.router.add_post('/api/run-code', panel.handle_run_code)
    
    # Dependencies
    app.router.add_get('/api/install-deps', panel.handle_install_deps)
    
    # Terminal
    app.router.add_post('/api/terminal', panel.handle_terminal)
    
    # Logs
    app.router.add_get('/api/view-logs', panel.handle_view_logs)
    
    return panel, app
