"""
User Database Manager
Handles user authentication and data persistence
"""

import json
import os
import hashlib
import hmac
from datetime import datetime
import threading

class UserDB:
    def __init__(self, db_path='./data/users.json'):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create database file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else './data', exist_ok=True)
        if not os.path.exists(self.db_path):
            self._save_db({'users': {}})
    
    def _load_db(self):
        """Load database from file"""
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except:
            return {'users': {}}
    
    def _save_db(self, data):
        """Save database to file"""
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username, password, display_name=None):
        """
        Register a new user
        Returns: (success: bool, message: str, user_data: dict or None)
        """
        with self.lock:
            db = self._load_db()
            
            # Check if username already exists
            if username in db['users']:
                return False, 'Username already exists', None
            
            # Create user record
            user_data = {
                'username': username,
                'password_hash': self._hash_password(password),
                'display_name': display_name or username,
                'created_at': datetime.now().isoformat(),
                'last_login': None,
                'files': [],  # List of files owned by this user
                'settings': {
                    'auto_publish': False,
                    'default_repo': f'repo_{username}'
                }
            }
            
            db['users'][username] = user_data
            self._save_db(db)
            
            # Return user data without password hash
            safe_user = {k: v for k, v in user_data.items() if k != 'password_hash'}
            return True, 'User registered successfully', safe_user
    
    def authenticate_user(self, username, password):
        """
        Authenticate user credentials
        Returns: (success: bool, message: str, user_data: dict or None)
        """
        with self.lock:
            db = self._load_db()
            
            if username not in db['users']:
                return False, 'Invalid username or password', None
            
            user = db['users'][username]
            password_hash = self._hash_password(password)
            
            if user['password_hash'] != password_hash:
                return False, 'Invalid username or password', None
            
            # Update last login
            user['last_login'] = datetime.now().isoformat()
            self._save_db(db)
            
            # Return user data without password hash
            safe_user = {k: v for k, v in user.items() if k != 'password_hash'}
            return True, 'Authentication successful', safe_user
    
    def get_user(self, username):
        """Get user data by username"""
        with self.lock:
            db = self._load_db()
            if username in db['users']:
                user = db['users'][username].copy()
                user.pop('password_hash', None)
                return user
            return None
    
    def update_user(self, username, **kwargs):
        """Update user data"""
        with self.lock:
            db = self._load_db()
            
            if username not in db['users']:
                return False, 'User not found'
            
            # Update allowed fields
            allowed_fields = ['display_name', 'files', 'settings']
            for field in allowed_fields:
                if field in kwargs:
                    db['users'][username][field] = kwargs[field]
            
            self._save_db(db)
            return True, 'User updated successfully'
    
    def add_user_file(self, username, file_info):
        """Add a file to user's file list"""
        with self.lock:
            db = self._load_db()
            
            if username not in db['users']:
                return False, 'User not found'
            
            # Add file if not already in list
            files = db['users'][username]['files']
            existing = next((f for f in files if f['name'] == file_info['name']), None)
            
            if existing:
                # Update existing file info
                existing.update(file_info)
            else:
                # Add new file
                files.append(file_info)
            
            self._save_db(db)
            return True, 'File added successfully'
    
    def remove_user_file(self, username, filename):
        """Remove a file from user's file list"""
        with self.lock:
            db = self._load_db()
            
            if username not in db['users']:
                return False, 'User not found'
            
            files = db['users'][username]['files']
            db['users'][username]['files'] = [f for f in files if f['name'] != filename]
            
            self._save_db(db)
            return True, 'File removed successfully'
    
    def get_all_users(self):
        """Get all users (without password hashes)"""
        with self.lock:
            db = self._load_db()
            users = {}
            for username, user_data in db['users'].items():
                safe_user = {k: v for k, v in user_data.items() if k != 'password_hash'}
                users[username] = safe_user
            return users

# Utility function to find available port
def find_available_port(port_min=6000, port_max=7000):
    """Find an available port in the specified range"""
    import socket
    for port in range(port_min, port_max + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', port))
            sock.close()
            return port
        except OSError:
            continue
    return None

if __name__ == '__main__':
    # Test the user database
    db = UserDB('./data/users.json')
    
    # Test registration
    success, msg, user = db.register_user('testuser', 'password123', 'Test User')
    print(f"Register: {msg}")
    print(f"User data: {user}")
    
    # Test authentication
    success, msg, user = db.authenticate_user('testuser', 'password123')
    print(f"Auth: {msg}")
    print(f"User data: {user}")
    
    # Test wrong password
    success, msg, user = db.authenticate_user('testuser', 'wrongpassword')
    print(f"Wrong auth: {msg}")
