"""
Configuration Module for P2P File Sharing System
Loads configuration from environment variables with fallback to defaults

Network Configuration Notes:
- SERVER_HOST: Use '0.0.0.0' to accept connections from any network interface (LAN/WAN)
              Use '127.0.0.1' for localhost only (same machine)
- For LAN access, set SERVER_HOST=0.0.0.0 and clients connect using the host's IP address
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from parent directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Server Configuration
# Default to 0.0.0.0 for network-wide access, can override in .env
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', 9000))

# Client Configuration
CLIENT_PORT_MIN = int(os.getenv('CLIENT_PORT_MIN', 6000))
CLIENT_PORT_MAX = int(os.getenv('CLIENT_PORT_MAX', 7000))
CLIENT_REPO_BASE = os.getenv('CLIENT_REPO_BASE', './repos')
CLIENT_HEARTBEAT_INTERVAL = int(os.getenv('CLIENT_HEARTBEAT_INTERVAL', 60))
CLIENT_CLEANUP_INTERVAL = int(os.getenv('CLIENT_CLEANUP_INTERVAL', 30))
CLIENT_INACTIVE_TIMEOUT = int(os.getenv('CLIENT_INACTIVE_TIMEOUT', 1200))

# API Server Configuration
ADMIN_API_HOST = os.getenv('ADMIN_API_HOST', '0.0.0.0')
ADMIN_API_PORT = int(os.getenv('ADMIN_API_PORT', 5500))
CLIENT_API_HOST = os.getenv('CLIENT_API_HOST', '0.0.0.0')
CLIENT_API_PORT = int(os.getenv('CLIENT_API_PORT', 5501))

# Admin Authentication
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# Security
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 3600))

# Database
USER_DB_PATH = os.getenv('USER_DB_PATH', './data/users.json')

# Create necessary directories
os.makedirs(os.path.dirname(USER_DB_PATH) if os.path.dirname(USER_DB_PATH) else './data', exist_ok=True)
os.makedirs(CLIENT_REPO_BASE, exist_ok=True)

def get_config():
    """Return configuration as dictionary"""
    return {
        'server': {
            'host': SERVER_HOST,
            'port': SERVER_PORT
        },
        'client': {
            'port_min': CLIENT_PORT_MIN,
            'port_max': CLIENT_PORT_MAX,
            'repo_base': CLIENT_REPO_BASE,
            'heartbeat_interval': CLIENT_HEARTBEAT_INTERVAL,
            'cleanup_interval': CLIENT_CLEANUP_INTERVAL,
            'inactive_timeout': CLIENT_INACTIVE_TIMEOUT
        },
        'api': {
            'admin_host': ADMIN_API_HOST,
            'admin_port': ADMIN_API_PORT,
            'client_host': CLIENT_API_HOST,
            'client_port': CLIENT_API_PORT
        },
        'admin': {
            'username': ADMIN_USERNAME,
            'password': ADMIN_PASSWORD
        },
        'security': {
            'jwt_secret': JWT_SECRET_KEY,
            'session_timeout': SESSION_TIMEOUT
        },
        'database': {
            'user_db_path': USER_DB_PATH
        }
    }

if __name__ == '__main__':
    # Test configuration loading
    config = get_config()
    print("Configuration loaded successfully:")
    import json
    print(json.dumps(config, indent=2))
