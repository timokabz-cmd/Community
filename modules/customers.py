import streamlit as st
from database import get_db_connection
from datetime import datetime

def render_customers():
    st.subheader("👥 Member Management")
    with st.form("new_member"):
        name = st.text_input("Full Name")
        phone = st.text_input("Phone Number")
        if st.form_submit_button("Register"):
            conn = get_db_connection()
            conn.execute("INSERT INTO members (name, phone, joined_date) VALUES (?,?,?)",
                         (name, phone, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            conn.close()
            st.success("Registered!")
