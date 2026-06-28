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
    if salt is None: salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, digest

def init_db():
    conn = get_db_connection()
    # Check if 'password_hash' column exists; if not, rebuild the table
    cursor = conn.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'password_hash' not in columns:
        conn.execute('DROP TABLE IF EXISTS users')
        conn.execute('''CREATE TABLE users (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            salt TEXT,
            role TEXT
        )''')
        salt, pw_hash = hash_password('admin123')
        conn.execute('INSERT INTO users VALUES (?, ?, ?, ?)', ('admin', pw_hash, salt, 'admin'))
        conn.commit()
    conn.close()

def verify_user(username, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user is None: return None
    _, digest = hash_password(password, user['salt'])
    return user if hmac.compare_digest(digest, user['password_hash']) else None

# --- 2. APP SETUP & AUTHENTICATION ---
st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")
init_db()

if 'authenticated' not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("🔒 Login Required")
    user_input = st.text_input("Username")
    pwd_input = st.text_input("Password", type="password")
    if st.button("Login"):
        user = verify_user(user_input, pwd_input)
        if user:
            st.session_state.authenticated = True
            st.session_state.user = user['username']
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.stop()

# --- 3. BUSINESS MODULES ---
def render_dashboard(): st.write("### Dashboard")
def render_customers(): st.write("### Customers")
def render_loans(): st.write("### Loans")
def render_collections(): st.write("### Collections")
def render_accounting(): st.write("### Accounting")
def render_reporting(): st.write("### Reporting")

# --- 4. NAVIGATION & ROUTER ---
st.sidebar.title("🏛️ CommunityFinanceOS")
st.sidebar.write(f"Logged in as: **{st.session_state.user}**")
menu = ["Dashboard", "Customers", "Loans", "Collections", "Accounting", "Reporting"]
choice = st.sidebar.selectbox("Select Workspace", menu)

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

st.header(f"💼 {choice}")
if choice == "Dashboard": render_dashboard()
elif choice == "Customers": render_customers()
elif choice == "Loans": render_loans()
elif choice == "Collections": render_collections()
elif choice == "Accounting": render_accounting()
elif choice == "Reporting": render_reporting()
