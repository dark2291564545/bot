import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
import secrets

SECRET_KEY = secrets.token_urlsafe(32)

class FileShareManager:
    def __init__(self):
        self.active_shares = {}
    
    def create_share_link(self, user_id: int, file_path: str, filename: str, expiry_hours: int = 24) -> Dict:
        file_id = hashlib.sha256(f"{user_id}_{filename}_{datetime.now().timestamp()}".encode()).hexdigest()[:16]
        
        expiry_time = datetime.now() + timedelta(hours=expiry_hours)
        
        payload = {
            'file_id': file_id,
            'user_id': user_id,
            'filename': filename,
            'file_path': file_path,
            'exp': expiry_time.timestamp(),
            'created': datetime.now().timestamp()
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        
        self.active_shares[file_id] = {
            'user_id': user_id,
            'filename': filename,
            'file_path': file_path,
            'token': token,
            'expiry': expiry_time,
            'created': datetime.now(),
            'downloads': 0,
            'max_downloads': None
        }
        
        return {
            'file_id': file_id,
            'token': token,
            'expiry': expiry_time,
            'share_url': f"/share/{token}"
        }
    
    def verify_share_token(self, token: str) -> Optional[Dict]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            file_id = payload['file_id']
            
            if file_id not in self.active_shares:
                return None
            
            share_data = self.active_shares[file_id]
            
            if datetime.now() > share_data['expiry']:
                del self.active_shares[file_id]
                return None
            
            if share_data.get('max_downloads') and share_data['downloads'] >= share_data['max_downloads']:
                return None
            
            share_data['downloads'] += 1
            
            return {
                'file_path': share_data['file_path'],
                'filename': share_data['filename'],
                'user_id': share_data['user_id'],
                'downloads': share_data['downloads']
            }
        
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def revoke_share(self, file_id: str) -> bool:
        if file_id in self.active_shares:
            del self.active_shares[file_id]
            return True
        return False
    
    def get_user_shares(self, user_id: int):
        user_shares = []
        for file_id, share_data in self.active_shares.items():
            if share_data['user_id'] == user_id:
                time_left = share_data['expiry'] - datetime.now()
                hours_left = int(time_left.total_seconds() / 3600)
                
                user_shares.append({
                    'file_id': file_id,
                    'filename': share_data['filename'],
                    'created': share_data['created'],
                    'expiry': share_data['expiry'],
                    'hours_left': hours_left,
                    'downloads': share_data['downloads'],
                    'token': share_data['token'],
                    'is_expired': datetime.now() > share_data['expiry']
                })
        
        return user_shares
    
    def cleanup_expired(self):
        expired_ids = []
        for file_id, share_data in self.active_shares.items():
            if datetime.now() > share_data['expiry']:
                expired_ids.append(file_id)
        
        for file_id in expired_ids:
            del self.active_shares[file_id]
        
        return len(expired_ids)

share_manager = FileShareManager()
