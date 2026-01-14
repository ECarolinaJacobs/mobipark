import sqlite3
import bcrypt
from utils.storage_utils import DB_PATH


def start():
    # Connect to the configured database file
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print(f"Database connection succeeded: {DB_PATH}")

    # Check if is_hashed column exists
    cursor.execute("PRAGMA table_info(users)")
    columns_info = cursor.fetchall()
    columns = [column[1] for column in columns_info]

    print(f"Existing columns: {columns}")

    # Add column only if it doesn't exist
    if 'is_hashed' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN is_hashed INTEGER DEFAULT 0')
        conn.commit()
        print("Added is_hashed column")
    else:
        print("is_hashed column already exists")

    # Fetch only users with unhashed passwords
    cursor.execute('SELECT id, password FROM users WHERE is_hashed = 0 OR is_hashed IS NULL')
    users = cursor.fetchall()

    # Rehash each password
    for user_id, password in users:
        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')

    # Update the user's password with the hashed version and mark as hashed
        cursor.execute('UPDATE users SET password = ?, is_hashed = 1 WHERE id = ?', (hashed_password, user_id))

    # Commit all changes
    conn.commit()

    print(f"Rehashed passwords for {len(users)} users")

    # Close connection
    conn.close()

