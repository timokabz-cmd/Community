# modules/dashboard.py
import streamlit as st
from database.connection import get_db_connection

def render():
    st.write("#### 🏛️ Dashboard")
    conn = get_db_connection()
    # Your logic for stats and metrics goes here
    st.info("Dashboard loaded from modules folder.")
    conn.close()

