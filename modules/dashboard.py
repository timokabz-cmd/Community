import streamlit as st
from database import get_db_connection

def render_dashboard():
    st.subheader("🏢 Executive Management Overview")
    conn = get_db_connection()
    # Replace these queries with the ones that worked for you before
    try:
        # Example: showing total members
        total_members = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        st.metric("Total Registered Members", total_members)
    except Exception as e:
        st.error(f"Error loading data: {e}")
    conn.close()
