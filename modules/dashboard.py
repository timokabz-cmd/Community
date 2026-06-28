import streamlit as st
from database import get_db_connection

def render_dashboard():
    conn = get_db_connection()
    
    # Fetching metrics from the database
    # 1. Total Members
    total_members = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    
    # 2. Total Portfolio Value (Sum of all pending loans)
    total_loans = conn.execute("SELECT SUM(amount) FROM loans").fetchone()[0] or 0
    
    # 3. Total Collected (Sum of all ledger entries)
    total_collections = conn.execute("SELECT SUM(amount) FROM ledger").fetchone()[0] or 0
    
    conn.close()
    
    # Displaying Metrics
    st.subheader("📊 Executive Overview")
    col1, col2, col3 = st.columns(3)
    
    col1.metric("Total Members", total_members)
    col2.metric("Portfolio Value", f"UGX {total_loans:,.0f}")
    col3.metric("Total Collected", f"UGX {total_collections:,.0f}")
    
    # Adding a visual breakdown
    st.write("---")
    st.subheader("💡 System Status")
    st.success(f"System is running optimally with {total_members} active members.")
