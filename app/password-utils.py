# app/auth_utils.py
import os
import json
import hashlib
import secrets
import filelock
from datetime import datetime

USERS_FILE = 'users.json'

def generate_salt():
    """Generate a random salt for password hashing"""
    return secrets.token_hex(16)

def hash_password(password, salt=None):
    """Hash a password with a salt using SHA-256"""
    if salt is None:
        salt = generate_salt()
    
    # Combine password and salt, then hash
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return password_hash, salt

def verify_password(stored_hash, stored_salt, provided_password):
    """Verify a password against a stored hash and salt"""
    calculated_hash, _ = hash_password(provided_password, stored_salt)
    return secrets.compare_digest(calculated_hash, stored_hash)

def migrate_users_to_hashed_passwords():
    """Migrate existing plaintext passwords to hashed passwords"""
    if not os.path.exists(USERS_FILE):
        print(f"Error: {USERS_FILE} does not exist.")
        return False
    
    lock = filelock.FileLock(f"{USERS_FILE}.lock")
    with lock:
        try:
            with open(USERS_FILE, 'r') as f:
                try:
                    users = json.load(f)
                except json.JSONDecodeError:
                    users = []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading {USERS_FILE}: {e}")
            return False
        
        for user in users:
            if 'password_hash' not in user:  # Not yet migrated
                password = user.pop('password', None)  # Remove plaintext password
                if password:
                    password_hash, salt = hash_password(password)
                    user['password_hash'] = password_hash
            temp_file = f"{USERS_FILE}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(users, f, indent=2)
            os.replace(temp_file, USERS_FILE)
        try:
            with open(USERS_FILE, 'w') as f:
                json.dump(users, f, indent=2)
                return True
        except Exception as e:
            print(f"Error migrating passwords: {e}")
            return False
def create_user(username, email, password, role='user'):
    """Create a new user with a hashed password"""
    password_hash, salt = hash_password(password)
    
    new_user = {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "salt": salt,
        "role": role,
        "active": True,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    lock = filelock.FileLock(f"{USERS_FILE}.lock")
    with lock:
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, 'r') as f:
                    users = json.load(f)
            else:
                users = []
            
            # Check if username or email already exists
            for user in users:
                if user.get('username') == username:
                    return False, "Username already exists"
                if user.get('email') == email:
                    return False, "Email already exists"
            
            users.append(new_user)
            
            with open(USERS_FILE, 'w') as f:
                json.dump(users, f, indent=2)
            
            return True, "User created successfully"
        except Exception as e:
            return False, f"Error creating user: {e}"

def validate_user(username, password):
    """Validate user credentials using secure password verification"""
    users = get_users()
    for user in users:
        if user.get('username') == username:
            # Check if we're using the new hash system
            if 'password_hash' in user and 'salt' in user:
                # Verify using the hash system
                if verify_password(user['password_hash'], user['salt'], password):
                    return user.get('active', True)
            # Legacy plain text password (fallback during migration)
            elif 'password' in user and user.get('password') == password:
                return user.get('active', True)
    return False

def get_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading {USERS_FILE}: {e}")
            return []
    else:
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)
    return []
def get_user_by_username(username):
    """Get a user record by username"""
    users = get_users()
    for user in users:
        if user.get('username') == username:
            return user
    return None

def is_admin(username):
    """Check if a user has admin privileges"""
    user = get_user_by_username(username)
    return user is not None and user.get('role') == 'admin'
