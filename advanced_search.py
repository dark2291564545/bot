import re
from pathlib import Path
from typing import List, Dict
import mimetypes

class AdvancedSearch:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
    
    def search_in_file_content(self, search_term: str, case_sensitive: bool = False) -> List[Dict]:
        results = []
        
        flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            for file_path in self.base_dir.rglob('*'):
                if not file_path.is_file():
                    continue
                
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if mime_type and not mime_type.startswith('text'):
                    continue
                
                if file_path.suffix in ['.db', '.sqlite', '.pyc', '.exe']:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        matches = []
                        for line_num, line in enumerate(content.split('\n'), 1):
                            if re.search(search_term, line, flags):
                                matches.append({
                                    'line_number': line_num,
                                    'line_content': line.strip()[:100]
                                })
                        
                        if matches:
                            results.append({
                                'file_path': str(file_path.relative_to(self.base_dir)),
                                'file_name': file_path.name,
                                'match_count': len(matches),
                                'matches': matches[:5]
                            })
                
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        except Exception as e:
            return []
        
        return results
    
    def search_by_extension(self, extensions: List[str]) -> List[Dict]:
        results = []
        
        for file_path in self.base_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix in extensions:
                results.append({
                    'file_name': file_path.name,
                    'file_path': str(file_path.relative_to(self.base_dir)),
                    'size': file_path.stat().st_size,
                    'modified': file_path.stat().st_mtime
                })
        
        return results
    
    def search_by_size(self, min_size: int = 0, max_size: int = None) -> List[Dict]:
        results = []
        
        for file_path in self.base_dir.rglob('*'):
            if file_path.is_file():
                size = file_path.stat().st_size
                
                if size >= min_size:
                    if max_size is None or size <= max_size:
                        results.append({
                            'file_name': file_path.name,
                            'file_path': str(file_path.relative_to(self.base_dir)),
                            'size': size,
                            'size_mb': round(size / (1024 * 1024), 2)
                        })
        
        return sorted(results, key=lambda x: x['size'], reverse=True)
    
    def search_recent_files(self, days: int = 7) -> List[Dict]:
        from datetime import datetime, timedelta
        
        results = []
        cutoff_time = (datetime.now() - timedelta(days=days)).timestamp()
        
        for file_path in self.base_dir.rglob('*'):
            if file_path.is_file():
                mtime = file_path.stat().st_mtime
                
                if mtime >= cutoff_time:
                    results.append({
                        'file_name': file_path.name,
                        'file_path': str(file_path.relative_to(self.base_dir)),
                        'modified': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'size': file_path.stat().st_size
                    })
        
        return sorted(results, key=lambda x: x['modified'], reverse=True)
    
    def smart_search(self, query: str, limit: int = 20) -> Dict:
        filename_matches = []
        content_matches = []
        
        query_lower = query.lower()
        
        for file_path in self.base_dir.rglob('*'):
            if not file_path.is_file():
                continue
            
            if query_lower in file_path.name.lower():
                filename_matches.append({
                    'file_name': file_path.name,
                    'file_path': str(file_path.relative_to(self.base_dir)),
                    'match_type': 'filename',
                    'size': file_path.stat().st_size
                })
        
        content_results = self.search_in_file_content(query, case_sensitive=False)
        for result in content_results[:limit]:
            content_matches.append({
                'file_name': result['file_name'],
                'file_path': result['file_path'],
                'match_type': 'content',
                'match_count': result['match_count'],
                'preview': result['matches'][0]['line_content'] if result['matches'] else ''
            })
        
        return {
            'query': query,
            'filename_matches': filename_matches[:limit],
            'content_matches': content_matches,
            'total_results': len(filename_matches) + len(content_matches)
        }

def create_search_instance(base_dir: str):
    return AdvancedSearch(base_dir)
