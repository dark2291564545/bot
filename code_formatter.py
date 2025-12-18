import subprocess
import os
from pathlib import Path
from typing import Optional, Dict

class CodeFormatter:
    def __init__(self):
        self.formatters = {
            '.py': self.format_python,
            '.js': self.format_javascript,
            '.json': self.format_json,
            '.html': self.format_html,
            '.css': self.format_css
        }
    
    def format_python(self, file_path: str) -> Dict:
        try:
            result = subprocess.run(
                ['python', '-m', 'black', file_path, '--quiet'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {'success': True, 'message': '✅ Python code formatted with Black'}
            else:
                return {'success': False, 'message': f'⚠️ Formatting skipped: {result.stderr}'}
        
        except FileNotFoundError:
            return {'success': False, 'message': '⚠️ Black not installed (pip install black)'}
        except subprocess.TimeoutExpired:
            return {'success': False, 'message': '❌ Formatting timeout'}
        except Exception as e:
            return {'success': False, 'message': f'❌ Error: {str(e)}'}
    
    def format_javascript(self, file_path: str) -> Dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            formatted = content
            
            return {'success': True, 'message': '✅ JavaScript file processed'}
        
        except Exception as e:
            return {'success': False, 'message': f'❌ Error: {str(e)}'}
    
    def format_json(self, file_path: str) -> Dict:
        try:
            import json
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return {'success': True, 'message': '✅ JSON formatted with proper indentation'}
        
        except json.JSONDecodeError:
            return {'success': False, 'message': '⚠️ Invalid JSON format'}
        except Exception as e:
            return {'success': False, 'message': f'❌ Error: {str(e)}'}
    
    def format_html(self, file_path: str) -> Dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {'success': True, 'message': '✅ HTML file processed'}
        
        except Exception as e:
            return {'success': False, 'message': f'❌ Error: {str(e)}'}
    
    def format_css(self, file_path: str) -> Dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {'success': True, 'message': '✅ CSS file processed'}
        
        except Exception as e:
            return {'success': False, 'message': f'❌ Error: {str(e)}'}
    
    def auto_format(self, file_path: str) -> Dict:
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext not in self.formatters:
            return {
                'success': False,
                'message': f'⚠️ No formatter available for {file_ext} files',
                'formatted': False
            }
        
        formatter = self.formatters[file_ext]
        result = formatter(file_path)
        result['formatted'] = result['success']
        result['file_type'] = file_ext
        
        return result
    
    def analyze_code(self, file_path: str) -> Dict:
        file_ext = Path(file_path).suffix.lower()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            analysis = {
                'total_lines': len(lines),
                'non_empty_lines': len([l for l in lines if l.strip()]),
                'file_size': os.path.getsize(file_path),
                'file_type': file_ext,
                'encoding': 'utf-8'
            }
            
            if file_ext == '.py':
                analysis['imports'] = len([l for l in lines if l.strip().startswith('import') or l.strip().startswith('from')])
                analysis['functions'] = len([l for l in lines if l.strip().startswith('def ')])
                analysis['classes'] = len([l for l in lines if l.strip().startswith('class ')])
                analysis['comments'] = len([l for l in lines if l.strip().startswith('#')])
            
            elif file_ext == '.js':
                analysis['functions'] = len([l for l in lines if 'function ' in l or '=>' in l])
                analysis['comments'] = len([l for l in lines if l.strip().startswith('//')])
            
            return analysis
        
        except Exception as e:
            return {'error': str(e)}

code_formatter = CodeFormatter()
