import hashlib
import hmac
import secrets
import streamlit as st
from database import get_db_connection

ROLE_SUPER_ADMIN = 'super_admin'
ROLE_SACCO_ADMIN = 'sacco_admin'
ROLE_STAFF       = 'staff'

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, digest

def ensure_admin_account():
    conn = get_db_connection()
    cur  = conn.cursor()

    # Migrate legacy 'admin' role values
    cur.execute(
        "UPDATE users SET role = %s WHERE username = %s AND role = 'admin'",
        (ROLE_SUPER_ADMIN, 'timo')
    )
    cur.execute(
        "UPDATE users SET role = %s WHERE username != 'timo' AND role = 'admin'",
        (ROLE_SACCO_ADMIN,)
    )
    conn.commit()

    cur.execute("SELECT * FROM users WHERE username = %s", ('timo',))
    existing = cur.fetchone()
    if existing is None:
        try:
            default_password = st.secrets.get("ADMIN_PASSWORD", "timo123")
        except Exception:
            default_password = "timo123"
        salt, pw_hash = hash_password(default_password)
        cur.execute(
            "INSERT INTO users (username, password_hash, salt, role, sacco_id) VALUES (%s,%s,%s,%s,%s)",
            ('timo', pw_hash, salt, ROLE_SUPER_ADMIN, None)
        )
        conn.commit()

    cur.close()
    conn.close()

def verify_user(username, password):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user is None:
        return None
    _, digest = hash_password(password, user['salt'])
    return user if hmac.compare_digest(digest, user['password_hash']) else None

def update_password(username, new_password):
    conn = get_db_connection()
    cur  = conn.cursor()
    salt, pw_hash = hash_password(new_password)
    cur.execute(
        "UPDATE users SET password_hash = %s, salt = %s WHERE username = %s",
        (pw_hash, salt, username)
    )
    conn.commit()
    cur.close()
    conn.close()

def create_user(username, password, role, sacco_id=None):
    if role not in (ROLE_SUPER_ADMIN, ROLE_SACCO_ADMIN, ROLE_STAFF):
        return False
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return False
    salt, pw_hash = hash_password(password)
    cur.execute(
        "INSERT INTO users (username, password_hash, salt, role, sacco_id) VALUES (%s,%s,%s,%s,%s)",
        (username, pw_hash, salt, role, sacco_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return True

def delete_user(username):
    if username == 'timo':
        return False
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM users WHERE username = %s", (username,))
    conn.commit()
    cur.close()
    conn.close()
    return True

def get_all_users():
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT u.username, u.role, u.sacco_id, s.sacco_name
        FROM users u
        LEFT JOIN sacco_profile s ON u.sacco_id = s.id
        ORDER BY u.role, u.username
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows
