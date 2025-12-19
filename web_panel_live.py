"""
🌐 ADVANCED WEB PANEL WITH LIVE FEATURES
💫 MADE BY DARK SHADOW 💫

Features:
- Install dependencies via web (one-click)
- Upload/Edit requirements.txt
- Upload/Edit .env file
- Run code with live output
- View logs in real-time
- Terminal access
- File manager
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

class WebPanel:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.upload_dir = self.base_dir / 'upload_bots'
        self.running_processes = {}
    
    async def handle_install_deps(self, request):
        """Install dependencies from requirements.txt"""
        try:
            user_id = request.match_info.get('user_id')
            
            requirements_file = self.base_dir / 'requirements.txt'
            if not requirements_file.exists():
                return web.json_response({
                    'success': False,
                    'error': 'requirements.txt not found'
                })
            
            # Run pip install in background
            process = await asyncio.create_subprocess_exec(
                sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file),
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
    
    async def handle_upload_requirements(self, request):
        """Upload/Update requirements.txt"""
        try:
            data = await request.post()
            
            if 'file' in data:
                # File upload
                file_field = data['file']
                content = file_field.file.read().decode('utf-8')
            else:
                # Text content
                content = (await request.json()).get('content', '')
            
            requirements_file = self.base_dir / 'requirements.txt'
            with open(requirements_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return web.json_response({
                'success': True,
                'message': '✅ requirements.txt updated!'
            })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_upload_env(self, request):
        """Upload/Update .env file"""
        try:
            data = await request.json()
            content = data.get('content', '')
            
            env_file = self.base_dir / '.env'
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return web.json_response({
                'success': True,
                'message': '✅ .env file updated!'
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
            filename = data.get('filename', '')
            user_id = data.get('user_id')
            
            # Allow reading specific files
            allowed_files = ['requirements.txt', '.env', 'main.py', 'bot_launcher.py']
            
            if filename in allowed_files:
                file_path = self.base_dir / filename
            elif user_id:
                file_path = self.upload_dir / str(user_id) / filename
            else:
                return web.json_response({
                    'success': False,
                    'error': 'Invalid file path'
                })
            
            if not file_path.exists():
                return web.json_response({
                    'success': False,
                    'error': 'File not found'
                })
            
            with open(file_path, 'r', encoding='utf-8') as f:
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
    
    async def handle_run_code(self, request):
        """Run Python/JS code with live output"""
        try:
            data = await request.json()
            user_id = data.get('user_id')
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
                    'error': 'Unsupported file type'
                })
            
            # Start process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(file_path.parent)
            )
            
            # Store process for later kill
            process_id = f"{user_id}_{filename}"
            self.running_processes[process_id] = process
            
            # Read output with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=30.0
                )
                
                output = stdout.decode('utf-8', errors='ignore')
                error = stderr.decode('utf-8', errors='ignore')
                
                return web.json_response({
                    'success': process.returncode == 0,
                    'output': output,
                    'error': error,
                    'return_code': process.returncode,
                    'process_id': process_id
                })
            
            except asyncio.TimeoutError:
                process.kill()
                return web.json_response({
                    'success': False,
                    'error': 'Process timeout (30s)',
                    'output': 'Execution timeout - process terminated'
                })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_stop_process(self, request):
        """Stop running process"""
        try:
            data = await request.json()
            process_id = data.get('process_id')
            
            if process_id in self.running_processes:
                process = self.running_processes[process_id]
                process.kill()
                del self.running_processes[process_id]
                
                return web.json_response({
                    'success': True,
                    'message': '✅ Process stopped'
                })
            
            return web.json_response({
                'success': False,
                'error': 'Process not found'
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
                    'logs': 'No logs yet'
                })
            
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Read last 100 lines
                lines = f.readlines()
                recent_logs = ''.join(lines[-100:])
            
            return web.json_response({
                'success': True,
                'logs': recent_logs
            })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_terminal_command(self, request):
        """Execute terminal command"""
        try:
            data = await request.json()
            command = data.get('command', '').strip()
            
            if not command:
                return web.json_response({
                    'success': False,
                    'error': 'Empty command'
                })
            
            # Security: Block dangerous commands
            blocked_cmds = ['rm', 'del', 'format', 'shutdown', 'reboot', 'mkfs']
            if any(cmd in command.lower() for cmd in blocked_cmds):
                return web.json_response({
                    'success': False,
                    'error': '❌ Dangerous command blocked'
                })
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.base_dir)
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=10.0
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
                    'error': 'Command timeout (10s)'
                })
        
        except Exception as e:
            return web.json_response({
                'success': False,
                'error': str(e)
            })
    
    async def handle_panel_html(self, request):
        """Serve web panel HTML"""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bot Control Panel - Dark Shadow</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .card h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: transform 0.2s, box-shadow 0.2s;
            width: 100%;
            margin: 5px 0;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        button.danger {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        button.success {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        
        textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            resize: vertical;
            margin: 10px 0;
        }
        
        input[type="text"], input[type="file"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            margin: 10px 0;
        }
        
        .output {
            background: #1e1e1e;
            color: #00ff00;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            margin: 10px 0;
        }
        
        .status {
            padding: 10px;
            border-radius: 8px;
            margin: 10px 0;
            font-weight: bold;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .file-list {
            max-height: 300px;
            overflow-y: auto;
            margin: 10px 0;
        }
        
        .file-item {
            padding: 10px;
            background: #f8f9fa;
            margin: 5px 0;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .file-item:hover {
            background: #e9ecef;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
            display: none;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Bot Control Panel</h1>
            <p>💫 MADE BY DARK SHADOW 💫</p>
        </div>
        
        <div class="grid">
            <!-- Dependencies Card -->
            <div class="card">
                <h2>📦 Dependencies Manager</h2>
                <button onclick="installDeps()" class="success">
                    ⚡ Install All Dependencies
                </button>
                <div id="depStatus"></div>
                <div class="spinner" id="depSpinner"></div>
                <div class="output" id="depOutput" style="display:none;"></div>
            </div>
            
            <!-- Requirements.txt Editor -->
            <div class="card">
                <h2>📝 Requirements.txt Editor</h2>
                <textarea id="requirementsContent" rows="10" placeholder="Loading..."></textarea>
                <button onclick="saveRequirements()" class="success">
                    💾 Save requirements.txt
                </button>
                <input type="file" id="reqFile" accept=".txt" onchange="uploadRequirements()">
                <div id="reqStatus"></div>
            </div>
            
            <!-- .env File Editor -->
            <div class="card">
                <h2>⚙️ .env File Editor</h2>
                <textarea id="envContent" rows="10" placeholder="BOT_TOKEN=your_token_here
OWNER_ID=your_id
ADMIN_ID=your_id
YOUR_USERNAME=@DARK22v
UPDATE_CHANNEL=https://t.me/DARK22v"></textarea>
                <button onclick="saveEnv()" class="success">
                    💾 Save .env File
                </button>
                <div id="envStatus"></div>
            </div>
        </div>
        
        <div class="grid">
            <!-- Code Runner -->
            <div class="card">
                <h2>▶️ Code Runner</h2>
                <input type="text" id="fileToRun" placeholder="Enter filename (e.g., test.py)">
                <input type="number" id="userId" placeholder="Your User ID">
                <button onclick="runCode()" class="success">
                    ▶️ Run Code
                </button>
                <button onclick="stopCode()" class="danger">
                    🛑 Stop Execution
                </button>
                <div id="runStatus"></div>
                <div class="output" id="codeOutput"></div>
            </div>
            
            <!-- Terminal -->
            <div class="card">
                <h2>💻 Terminal</h2>
                <input type="text" id="terminalInput" placeholder="Enter command (e.g., ls, dir, pip list)">
                <button onclick="runTerminal()" class="success">
                    ⚡ Execute Command
                </button>
                <div id="termStatus"></div>
                <div class="output" id="termOutput"></div>
            </div>
            
            <!-- Logs Viewer -->
            <div class="card">
                <h2>📋 Bot Logs</h2>
                <button onclick="viewLogs()" class="success">
                    🔄 Refresh Logs
                </button>
                <div class="output" id="logsOutput" style="max-height: 500px;"></div>
            </div>
        </div>
    </div>
    
    <script>
        let currentProcessId = null;
        
        // Load requirements.txt on page load
        window.onload = function() {
            loadRequirements();
            loadEnv();
        };
        
        async function loadRequirements() {
            try {
                const response = await fetch('/api/read-file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: 'requirements.txt' })
                });
                const data = await response.json();
                if (data.success) {
                    document.getElementById('requirementsContent').value = data.content;
                }
            } catch (error) {
                console.error('Error loading requirements:', error);
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
                    document.getElementById('envContent').value = data.content;
                }
            } catch (error) {
                console.error('Error loading .env:', error);
            }
        }
        
        async function installDeps() {
            const spinner = document.getElementById('depSpinner');
            const output = document.getElementById('depOutput');
            const status = document.getElementById('depStatus');
            
            spinner.style.display = 'block';
            output.style.display = 'none';
            status.innerHTML = '<div class="status">⏳ Installing dependencies...</div>';
            
            try {
                const response = await fetch('/api/install-deps/0');
                const data = await response.json();
                
                spinner.style.display = 'none';
                output.style.display = 'block';
                output.textContent = data.output || '';
                
                if (data.success) {
                    status.innerHTML = '<div class="status success">✅ ' + data.message + '</div>';
                } else {
                    status.innerHTML = '<div class="status error">❌ ' + (data.error || data.message) + '</div>';
                }
            } catch (error) {
                spinner.style.display = 'none';
                status.innerHTML = '<div class="status error">❌ Error: ' + error.message + '</div>';
            }
        }
        
        async function saveRequirements() {
            const content = document.getElementById('requirementsContent').value;
            const status = document.getElementById('reqStatus');
            
            status.innerHTML = '<div class="status">⏳ Saving...</div>';
            
            try {
                const response = await fetch('/api/upload-requirements', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content })
                });
                const data = await response.json();
                
                if (data.success) {
                    status.innerHTML = '<div class="status success">' + data.message + '</div>';
                } else {
                    status.innerHTML = '<div class="status error">❌ ' + data.error + '</div>';
                }
            } catch (error) {
                status.innerHTML = '<div class="status error">❌ Error: ' + error.message + '</div>';
            }
        }
        
        async function uploadRequirements() {
            const fileInput = document.getElementById('reqFile');
            const file = fileInput.files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            const status = document.getElementById('reqStatus');
            status.innerHTML = '<div class="status">⏳ Uploading...</div>';
            
            try {
                const response = await fetch('/api/upload-requirements', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (data.success) {
                    status.innerHTML = '<div class="status success">' + data.message + '</div>';
                    loadRequirements();
                } else {
                    status.innerHTML = '<div class="status error">❌ ' + data.error + '</div>';
                }
            } catch (error) {
                status.innerHTML = '<div class="status error">❌ Error: ' + error.message + '</div>';
            }
        }
        
        async function saveEnv() {
            const content = document.getElementById('envContent').value;
            const status = document.getElementById('envStatus');
            
            status.innerHTML = '<div class="status">⏳ Saving...</div>';
            
            try {
                const response = await fetch('/api/upload-env', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content })
                });
                const data = await response.json();
                
                if (data.success) {
                    status.innerHTML = '<div class="status success">' + data.message + '</div>';
                } else {
                    status.innerHTML = '<div class="status error">❌ ' + data.error + '</div>';
                }
            } catch (error) {
                status.innerHTML = '<div class="status error">❌ Error: ' + error.message + '</div>';
            }
        }
        
        async function runCode() {
            const filename = document.getElementById('fileToRun').value;
            const userId = document.getElementById('userId').value;
            const output = document.getElementById('codeOutput');
            const status = document.getElementById('runStatus');
            
            if (!filename || !userId) {
                status.innerHTML = '<div class="status error">❌ Please enter filename and user ID</div>';
                return;
            }
            
            status.innerHTML = '<div class="status">⏳ Running code...</div>';
            output.textContent = '⏳ Executing...\\n';
            
            try {
                const response = await fetch('/api/run-code', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename, user_id: userId })
                });
                const data = await response.json();
                
                currentProcessId = data.process_id;
                
                if (data.success) {
                    status.innerHTML = '<div class="status success">✅ Execution completed</div>';
                    output.textContent = '=== OUTPUT ===\\n' + (data.output || '(no output)');
                } else {
                    status.innerHTML = '<div class="status error">❌ Execution failed</div>';
                    output.textContent = '=== ERROR ===\\n' + (data.error || data.output || 'Unknown error');
                }
            } catch (error) {
                status.innerHTML = '<div class="status error">❌ Error: ' + error.message + '</div>';
                output.textContent = '❌ ' + error.message;
            }
        }
        
        async function stopCode() {
            if (!currentProcessId) {
                document.getElementById('runStatus').innerHTML = '<div class="status error">❌ No running process</div>';
                return;
            }
            
            try {
                const response = await fetch('/api/stop-process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ process_id: currentProcessId })
                });
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('runStatus').innerHTML = '<div class="status success">' + data.message + '</div>';
                    currentProcessId = null;
                } else {
                    document.getElementById('runStatus').innerHTML = '<div class="status error">❌ ' + data.error + '</div>';
                }
            } catch (error) {
                document.getElementById('runStatus').innerHTML = '<div class="status error">❌ Error: ' + error.message + '</div>';
            }
        }
        
        async function runTerminal() {
            const command = document.getElementById('terminalInput').value;
            const output = document.getElementById('termOutput');
            const status = document.getElementById('termStatus');
            
            if (!command) {
                status.innerHTML = '<div class="status error">❌ Please enter a command</div>';
                return;
            }
            
            status.innerHTML = '<div class="status">⏳ Executing...</div>';
            output.textContent = '$ ' + command + '\\n';
            
            try {
                const response = await fetch('/api/terminal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command })
                });
                const data = await response.json();
                
                if (data.success) {
                    status.innerHTML = '<div class="status success">✅ Command executed</div>';
                    output.textContent += data.output || '(no output)';
                } else {
                    status.innerHTML = '<div class="status error">❌ Command failed</div>';
                    output.textContent += '❌ ' + (data.error || 'Unknown error');
                }
            } catch (error) {
                status.innerHTML = '<div class="status error">❌ Error: ' + error.message + '</div>';
                output.textContent += '❌ ' + error.message;
            }
        }
        
        async function viewLogs() {
            const output = document.getElementById('logsOutput');
            output.textContent = '⏳ Loading logs...';
            
            try {
                const response = await fetch('/api/view-logs');
                const data = await response.json();
                
                if (data.success) {
                    output.textContent = data.logs || 'No logs available';
                } else {
                    output.textContent = '❌ ' + (data.error || 'Error loading logs');
                }
            } catch (error) {
                output.textContent = '❌ Error: ' + error.message;
            }
        }
        
        // Auto-refresh logs every 5 seconds
        setInterval(viewLogs, 5000);
    </script>
</body>
</html>
"""
        return web.Response(text=html, content_type='text/html')

def create_web_panel_app(base_dir):
    """Create web panel application"""
    panel = WebPanel(base_dir)
    app = web.Application()
    
    # API Routes
    app.router.add_get('/api/install-deps/{user_id}', panel.handle_install_deps)
    app.router.add_post('/api/upload-requirements', panel.handle_upload_requirements)
    app.router.add_post('/api/upload-env', panel.handle_upload_env)
    app.router.add_post('/api/read-file', panel.handle_read_file)
    app.router.add_post('/api/run-code', panel.handle_run_code)
    app.router.add_post('/api/stop-process', panel.handle_stop_process)
    app.router.add_get('/api/view-logs', panel.handle_view_logs)
    app.router.add_post('/api/terminal', panel.handle_terminal_command)
    
    # HTML Routes
    app.router.add_get('/', panel.handle_panel_html)
    app.router.add_get('/panel', panel.handle_panel_html)
    app.router.add_get('/panel/{token}', panel.handle_panel_html)
    
    return app

# For backward compatibility
def create_web_dashboard():
    return create_web_panel_app(Path.cwd())

def create_user_panel(user_id, username):
    return {
        'panel_url': f'/panel',
        'username': username,
        'user_id': user_id
    }
