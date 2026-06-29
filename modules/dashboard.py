# modules/dashboard.py
import streamlit as st
from database.connection import get_db_connection

def render():
    st.write("### 🏛️ Dashboard")
    conn = get_db_connection()
    # Add your query logic here later
    st.info("Dashboard module is now connected!")
    conn.close()
