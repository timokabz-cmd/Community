import streamlit as st
import sqlite3

# --- 1. DATABASE SETUP ---
def get_db_connection():
    conn = sqlite3.connect('finance.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, role TEXT)')
    conn.commit()
    conn.close()

# --- 2. AUTHENTICATION LOGIC ---
def verify_user(username, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                        (username, password)).fetchone()
    conn.close()
    return user

def check_password():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.role = None
        st.session_state.user = None

    if not st.session_state.authenticated:
        st.subheader("🔒 Login Required")
        user_input = st.text_input("Username")
        pwd_input = st.text_input("Password", type="password")
        if st.button("Login"):
            user = verify_user(user_input, pwd_input)
            if user:
                st.session_state.authenticated = True
                st.session_state.role = user['role']
                st.session_state.user = user['username']
                st.rerun()
            else:
                st.error("Invalid username or password")
        return False
    return True

# --- 3. BUSINESS MODULES (Your content here) ---
def render_dashboard(): st.write("### Dashboard")
def render_customers(): st.write("### Customers")
def render_loans(): st.write("### Loans")
def render_collections(): st.write("### Collections")
def render_accounting(): st.write("### Accounting")
def render_reporting(): st.write("### Reporting")

# --- 4. APP ROUTER ---
st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")
init_db()

if not check_password():
    st.stop()

st.sidebar.title("🏛️ CommunityFinanceOS")
menu = ["Dashboard", "Customers", "Loans", "Collections", "Accounting", "Reporting"]
choice = st.sidebar.selectbox("Select Workspace", menu)

if choice == "Dashboard": render_dashboard()
elif choice == "Customers": render_customers()
elif choice == "Loans": render_loans()
elif choice == "Collections": render_collections()
elif choice == "Accounting": render_accounting()
elif choice == "Reporting": render_reporting()
