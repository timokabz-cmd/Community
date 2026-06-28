import streamlit as st
import sqlite3

# --- 1. DATABASE SETUP ---
def get_db_connection():
    conn = sqlite3.connect('finance.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Ensure your schema is created here
    conn.execute('CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, role TEXT)')
    # Add other tables as needed
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

# --- 3. BUSINESS MODULES ---
def render_dashboard():
    st.write("### Executive Dashboard")
    st.info("Overview of loan performance and active collections.")

def render_customers():
    st.write("### Customer Management")
    st.write("Register and verify new loan applicants.")

def render_loans():
    st.write("### Loan Portfolio")
    st.write("Track active loans, interest, and repayment schedules.")

def render_collections():
    st.write("### Collections Pipeline")
    st.write("Manage daily recovery tasks and mobile money webhooks.")

def render_accounting():
    st.write("### Double-Entry Ledger")
    st.write("Review all transactions and balance the books.")

def render_reporting():
    st.write("### Financial Reporting")
    st.write("Generate regulatory and internal performance reports.")

# --- 4. APP ROUTER ---
st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")
init_db()

if not check_password():
    st.stop()

st.sidebar.title("🏛️ CommunityFinanceOS")
st.sidebar.write(f"Logged in as: **{st.session_state.user}**")

menu = ["Dashboard", "Customers", "Loans", "Collections", "Accounting", "Reporting"]
choice = st.sidebar.selectbox("Select Workspace", menu)

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()

st.header(f"💼 {choice}")

if choice == "Dashboard": render_dashboard()
elif choice == "Customers": render_customers()
elif choice == "Loans": render_loans()
elif choice == "Collections": render_collections()
elif choice == "Accounting": render_accounting()
elif choice == "Reporting": render_reporting()
