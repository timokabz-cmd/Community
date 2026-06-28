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

    # Make sure there is always an admin account to log in with.
    # This runs every time the app starts, so it survives Streamlit
    # Cloud wiping the database on reboot/redeploy.
    existing = conn.execute(
        "SELECT * FROM users WHERE username = ?", ('admin',)
    ).fetchone()
    if existing is None:
        default_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
        salt, pw_hash = hash_password(default_password)
        conn.execute(
            'INSERT INTO users VALUES (?, ?, ?, ?)',
            ('admin', pw_hash, salt, 'admin')
        )
        conn.commit()
    conn.close()

def verify_user(username, password):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if user is None:
        return None
    _, digest = hash_password(password, user['salt'])
    return user if hmac.compare_digest(digest, user['password_hash']) else None

def update_password(username, new_password):
    conn = get_db_connection()
    salt, pw_hash = hash_password(new_password)
    conn.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
        (pw_hash, salt, username)
    )
    conn.commit()
    conn.close()

# --- 2. APP SETUP & AUTHENTICATION ---
st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")
init_db()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

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
    st.caption("Default login: admin / admin123 — change it after your first login.")
    st.stop()

# --- 3. BUSINESS MODULES ---
def render_dashboard(): st.write("### Dashboard")
def render_customers(): st.write("### Customers")
def render_loans(): st.write("### Loans")
def render_collections(): st.write("### Collections")
def render_accounting(): st.write("### Accounting")
def render_reporting(): st.write("### Reporting")

def render_account_settings():
    st.write("### Change Password")
    new_pwd = st.text_input("New password", type="password")
    confirm_pwd = st.text_input("Confirm new password", type="password")
    if st.button("Update password"):
        if not new_pwd:
            st.error("Password cannot be empty.")
        elif new_pwd != confirm_pwd:
            st.error("Passwords don't match.")
        else:
            update_password(st.session_state.user, new_pwd)
            st.success("Password updated. Use it next time you log in.")

# --- 4. NAVIGATION & ROUTER ---
st.sidebar.title("🏛️ CommunityFinanceOS")
st.sidebar.write(f"Logged in as: **{st.session_state.user}**")
menu = ["Dashboard", "Customers", "Loans", "Collections", "Accounting", "Reporting", "Account Settings"]
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
elif choice == "Account Settings": render_account_settings()
