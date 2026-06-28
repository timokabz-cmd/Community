import streamlit as st
import sqlite3
import hashlib
import hmac
import secrets

# --- 1. DATABASE & SECURITY LOGIC ---
def get_db_connection():
    conn = sqlite3.connect('finance.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, digest

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        salt TEXT,
        role TEXT
    )''')
    conn.commit()

    # Seed admin if empty
    existing = conn.execute('SELECT COUNT(*) AS c FROM users').fetchone()['c']
    if existing == 0:
        salt, pw_hash = hash_password('admin123')
        conn.execute(
            'INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)',
            ('admin', pw_hash, salt, 'admin')
        )
        conn.commit()
    conn.close()

def verify_user(username, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user is None: return None
    _, digest = hash_password(password, user['salt'])
    return user if hmac.compare_digest(digest, user['password_hash']) else None

# --- 2. APP SETUP & ROUTER ---
st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")
init_db()

# --- AUTH GATEKEEPER ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("🔒 Login")
    user_input = st.text_input("Username")
    pwd_input = st.text_input("Password", type="password")
    if st.button("Login"):
        user = verify_user(user_input, pwd_input)
        if user:
            st.session_state.authenticated = True
            st.session_state.user = user['username']
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()

# --- APP NAVIGATION ---
st.sidebar.title("🏛️ CommunityFinanceOS")
st.sidebar.write(f"Logged in: **{st.session_state.user}**")
choice = st.sidebar.selectbox("Workspace", ["Dashboard", "Customers", "Loans", "Collections", "Accounting", "Reporting"])

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

st.header(f"💼 {choice}")
st.info("Module active. Note: Persistence is ephemeral; transition to Supabase/Turso recommended for production.")
