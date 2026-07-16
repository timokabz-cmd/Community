import hashlib
import hmac
import secrets
import streamlit as st
from database import get_db_connection

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, digest

def ensure_admin_account():
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM users WHERE username = ?", ('timo',)).fetchone()
    if existing is None:
        try:
            default_password = st.secrets.get("ADMIN_PASSWORD", "timo123")
        except Exception:
            default_password = "timo123"  # no secrets.toml configured at all — fall back quietly
        salt, pw_hash = hash_password(default_password)
        conn.execute(
            'INSERT INTO users (username, password_hash, salt, role, sacco_id) VALUES (?, ?, ?, ?, ?)',
            ('timo', pw_hash, salt, 'admin', None)  # role='admin' = super-admin, sees every SACCO
        )
        conn.commit()
    conn.close()

def verify_user(username, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user is None:
        return None
    _, digest = hash_password(password, user['salt'])
    return user if hmac.compare_digest(digest, user['password_hash']) else None

def update_password(username, new_password):
    conn = get_db_connection()
    salt, pw_hash = hash_password(new_password)
    conn.execute("UPDATE users SET password_hash = ?, salt = ? WHERE username = ?", (pw_hash, salt, username))
    conn.commit()
    conn.close()

def create_staff_user(username, password, sacco_id):
    """Creates a user scoped to one SACCO (role='staff'). No management UI built yet —
    this is here so the schema/auth layer is ready when that's needed."""
    conn = get_db_connection()
    existing = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        return False
    salt, pw_hash = hash_password(password)
    conn.execute(
        'INSERT INTO users (username, password_hash, salt, role, sacco_id) VALUES (?, ?, ?, ?, ?)',
        (username, pw_hash, salt, 'staff', sacco_id)
    )
    conn.commit()
    conn.close()
    return True
