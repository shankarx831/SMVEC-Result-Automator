import psycopg2
import psycopg2.extras
import os
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load env variables if .env file exists
load_dotenv()

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("WARNING: DATABASE_URL environment variable is missing!")
        return None
        
    try:
        conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.DictCursor)
        return conn
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn: return
    
    try:
        with conn.cursor() as cursor:
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'user',
                    excel_count INTEGER DEFAULT 0,
                    word_count INTEGER DEFAULT 0
                )
            ''')
            
            # Create history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    filename VARCHAR(255) NOT NULL,
                    filepath VARCHAR(512) NOT NULL,
                    filesize INTEGER NOT NULL,
                    file_type VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create default admin if not exists
            admin_username = os.environ.get('DEFAULT_ADMIN_USER', 'admin').strip().lower()
            admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
            
            cursor.execute('SELECT * FROM users WHERE role = %s', ('admin',))
            if not cursor.fetchone():
                hashed_password = generate_password_hash(admin_password)
                cursor.execute(
                    'INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)',
                    (admin_username, hashed_password, 'admin')
                )
                print(f"Initialized Postgres database with default admin account ('{admin_username}' / '{admin_password}').")
        conn.commit()
    except Exception as e:
        print(f"Error initializing database schema: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_user(username, password, role='user'):
    username = username.strip().lower()
    hashed_password = generate_password_hash(password)
    conn = get_db_connection()
    if not conn: return False
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)',
                (username, hashed_password, role)
            )
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        conn.rollback()
        return False
    except Exception as e:
        print(f"Error creating user: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_user(username):
    username = username.strip().lower()
    conn = get_db_connection()
    if not conn: return None
    
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            return user
    finally:
        conn.close()

def get_all_users():
    conn = get_db_connection()
    if not conn: return []
    
    try:
        with conn.cursor() as cursor:
            # Query details including storage metrics
            cursor.execute('''
                SELECT u.id, u.username, u.role, u.excel_count, u.word_count, 
                       COALESCE(SUM(h.filesize), 0) as storage_used 
                FROM users u 
                LEFT JOIN history h ON u.id = h.user_id 
                GROUP BY u.id
                ORDER BY u.id ASC
            ''')
            return cursor.fetchall()
    finally:
        conn.close()

def delete_user(user_id):
    conn = get_db_connection()
    if not conn: return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
    finally:
        conn.close()

def update_password(user_id, new_password):
    hashed_password = generate_password_hash(new_password)
    conn = get_db_connection()
    if not conn: return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s', (hashed_password, user_id))
        conn.commit()
    finally:
        conn.close()

def increment_generation_count(username, excel_inc=0, word_inc=0):
    username = username.strip().lower()
    conn = get_db_connection()
    if not conn: return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                UPDATE users 
                SET excel_count = excel_count + %s, 
                    word_count = word_count + %s 
                WHERE username = %s
            ''', (excel_inc, word_inc, username))
        conn.commit()
    finally:
        conn.close()

def add_history_record(user_id, filename, filepath, filesize, file_type):
    conn = get_db_connection()
    if not conn: return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO history (user_id, filename, filepath, filesize, file_type)
                VALUES (%s, %s, %s, %s, %s)
            ''', (user_id, filename, filepath, filesize, file_type))
        conn.commit()
    finally:
        conn.close()

def get_user_history(user_id):
    conn = get_db_connection()
    if not conn: return []
    
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT filename, filesize, file_type, timestamp 
                FROM history 
                WHERE user_id = %s 
                ORDER BY timestamp DESC
            ''', (user_id,))
            history = cursor.fetchall()
            
            # Since psycopg2 returns datetime objects for TIMESTAMP columns, 
            # we need to convert them to strings to be compatible with our Jinja filter
            result = []
            for row in history:
                row_dict = dict(row)
                if row_dict['timestamp']:
                    row_dict['timestamp'] = row_dict['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                result.append(row_dict)
            return result
    finally:
        conn.close()

def enforce_user_quota(user_id):
    MAX_QUOTA = 50 * 1024 * 1024 # 50 Megabytes in bytes
    conn = get_db_connection()
    if not conn: return
    
    try:
        with conn.cursor() as cursor:
            # Calculate current size
            cursor.execute('SELECT SUM(filesize) as total_size FROM history WHERE user_id = %s', (user_id,))
            row = cursor.fetchone()
            total_size = row['total_size'] if row['total_size'] else 0
            
            if total_size > MAX_QUOTA:
                # Fetch files starting from the oldest
                cursor.execute('SELECT id, filepath, filesize, filename FROM history WHERE user_id = %s ORDER BY timestamp ASC', (user_id,))
                old_files = cursor.fetchall()
                
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
                    cursor.execute('DELETE FROM history WHERE id = %s', (f['id'],))
                    total_size -= f['filesize']
                
        conn.commit()
    except Exception as e:
        print(f"Error enforcing quota: {e}")
        conn.rollback()
    finally:
        conn.close()
