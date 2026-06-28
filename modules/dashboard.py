import streamlit as st
from database import get_db_connection

def render_dashboard():
    st.subheader("🏢 Executive Management Overview")
    conn = get_db_connection()
    try:
        # Get count of members
        count = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        st.metric("Total Registered Members", count)
    except Exception as e:
        st.error(f"Data not available yet: {e}")
    finally:
        conn.close()
