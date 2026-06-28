import streamlit as st
from database import get_db_connection

def render_customers():
    st.subheader("👤 New Member Registration")
    
    with st.form("member_form"):
        full_name = st.text_input("Full Name")
        phone_number = st.text_input("Phone Number")
        submit = st.form_submit_button("Register Member")
        
        if submit:
            if full_name and phone_number:
                conn = get_db_connection()
                try:
                    conn.execute(
                        "INSERT INTO members (name, phone) VALUES (?, ?)", 
                        (full_name, phone_number)
                    )
                    conn.commit()
                    st.success(f"Successfully registered {full_name}!")
                except Exception as e:
                    st.error(f"Error saving to database: {e}")
                finally:
                    conn.close()
            else:
                st.warning("Please fill in all fields.")

    # Show list of existing members
    st.write("---")
    st.subheader("📋 Registered Members")
    conn = get_db_connection()
    members = conn.execute("SELECT * FROM members").fetchall()
    conn.close()
    
    if members:
        st.table(members)
    else:
        st.write("No members registered yet.")
