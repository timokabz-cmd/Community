import streamlit as st
from modules.database import get_db_connection

def verify_user(username, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                        (username, password)).fetchone()
    conn.close()
    return user

def check_password():
    """Returns True if the user is authenticated."""
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
