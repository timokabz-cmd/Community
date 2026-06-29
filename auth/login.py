import streamlit as st
import sqlite3
import hashlib
import hmac
import secrets

def hash_password(password, salt=None):
    if salt is None: salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, digest

def verify_user(username, password):
    from database.connection import get_db_connection
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user is None: return None
    _, digest = hash_password(password, user['salt'])
    return user if hmac.compare_digest(digest, user['password_hash']) else None

def check_session():
    return st.session_state.get('authenticated', False)

