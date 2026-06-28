import streamlit as st
from database import get_db_connection
from datetime import datetime

def render_customers():
    st.subheader("👥 Member Management")
    # Registration Form
    with st.form("new_member"):
        name = st.text_input("Full Name")
        phone = st.text_input("Phone Number")
        nid = st.text_input("National ID")
        savings = st.number_input("Opening Savings", min_value=0)
        if st.form_submit_button("Register Member"):
            conn = get_db_connection()
            try:
                conn.execute("INSERT INTO members (name, phone, national_id, savings_balance, joined_date) VALUES (?,?,?,?,?)",
                             (name, phone, nid, savings, datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success("Member registered!")
            except:
                st.error("Phone number already exists.")
            conn.close()
