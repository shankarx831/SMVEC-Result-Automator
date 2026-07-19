import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load env variables if .env file exists
load_dotenv()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            excel_count INTEGER DEFAULT 0,
            word_count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()

    # Create history table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            filesize INTEGER NOT NULL,
            file_type TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    conn.commit()

    # Migration: Add excel_count and word_count if they do not exist
    try:
        conn.execute('ALTER TABLE users ADD COLUMN excel_count INTEGER DEFAULT 0')
        conn.commit()
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute('ALTER TABLE users ADD COLUMN word_count INTEGER DEFAULT 0')
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # Create default admin if not exists
    admin_username = os.environ.get('DEFAULT_ADMIN_USER', 'admin').strip().lower()
    admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')

    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE role = ?', ('admin',))
    if not cursor.fetchone():
        hashed_password = generate_password_hash(admin_password)
        conn.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            (admin_username, hashed_password, 'admin')
        )
        conn.commit()
        print(f"Initialized database with default admin account ('{admin_username}' / '{admin_password}').")
    conn.close()

def create_user(username, password, role='user'):
    username = username.strip().lower()
    hashed_password = generate_password_hash(password)
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            (username, hashed_password, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(username):
    username = username.strip().lower()
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def get_all_users():
    conn = get_db_connection()
    # Query details including storage metrics
    users = conn.execute('''
        SELECT u.id, u.username, u.role, u.excel_count, u.word_count, 
               COALESCE(SUM(h.filesize), 0) as storage_used 
        FROM users u 
        LEFT JOIN history h ON u.id = h.user_id 
        GROUP BY u.id
    ''').fetchall()
    conn.close()
    return users

def delete_user(user_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def increment_generation_count(username, excel_inc=0, word_inc=0):
    username = username.strip().lower()
    conn = get_db_connection()
    conn.execute('''
        UPDATE users 
        SET excel_count = excel_count + ?, 
            word_count = word_count + ? 
        WHERE username = ?
    ''', (excel_inc, word_inc, username))
    conn.commit()
    conn.close()

def add_history_record(user_id, filename, filepath, filesize, file_type):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO history (user_id, filename, filepath, filesize, file_type)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, filename, filepath, filesize, file_type))
    conn.commit()
    conn.close()

def get_user_history(user_id):
    conn = get_db_connection()
    history = conn.execute('''
        SELECT filename, filesize, file_type, timestamp 
        FROM history 
        WHERE user_id = ? 
        ORDER BY timestamp DESC
    ''', (user_id,)).fetchall()
    conn.close()
    return history

def enforce_user_quota(user_id):
    MAX_QUOTA = 50 * 1024 * 1024 # 50 Megabytes in bytes
    conn = get_db_connection()
    
    # Calculate current size
    row = conn.execute('SELECT SUM(filesize) as total_size FROM history WHERE user_id = ?', (user_id,)).fetchone()
    total_size = row['total_size'] or 0
    
    if total_size > MAX_QUOTA:
        # Fetch files starting from the oldest
        old_files = conn.execute('SELECT id, filepath, filesize, filename FROM history WHERE user_id = ? ORDER BY timestamp ASC', (user_id,)).fetchall()
        for f in old_files:
            if total_size <= MAX_QUOTA:
                break
            
            # Delete physical file
            path = f['filepath']
            if os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"Quota Enforcement: Deleted local file {f['filename']}")
                except Exception as e:
                    print(f"Failed to delete file {path} during quota check: {e}")
            
            # Delete record
            conn.execute('DELETE FROM history WHERE id = ?', (f['id'],))
            conn.commit()
            total_size -= f['filesize']
            
    conn.close()
