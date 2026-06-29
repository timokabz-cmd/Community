# auth/login.py
import streamlit as st
import hashlib
import hmac
from database.connection import get_db_connection

def hash_password(password, salt=None):
    import secrets
    if salt is None: salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, digest

def verify_user(username, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user is None: return None
    _, digest = hash_password(password, user['salt'])
    return user if hmac.compare_digest(digest, user['password_hash']) else None

def check_session():
    return st.session_state.get('authenticated', False)
