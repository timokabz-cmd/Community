import streamlit as st
from datetime import datetime
from database import get_db_connection

OCCUPATIONS = [
    "Trader / Shop Owner", "Farmer", "Boda Boda Rider", "Teacher", "Civil Servant",
    "Artisan / Craftsman", "Market Vendor", "Salaried Employee", "Transporter",
    "Student", "Other"
]

def add_customer(name, phone, national_id, member_type='Member', occupation=None):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO customers (name, phone, national_id, created_at, member_type, occupation) VALUES (?,?,?,?,?,?)",
        (name, phone, national_id, datetime.now().strftime('%Y-%m-%d'), member_type, occupation)
    )
    conn.commit()
    conn.close()

def get_customers():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    conn.close()
    return rows

def render():
    st.write("#### Add New Customer")
    with st.form("add_customer_form", clear_on_submit=True):
        name = st.text_input("Full name")
        phone = st.text_input("Phone number (e.g. 0772xxxxxx)")
        national_id = st.text_input("National ID (optional)")
        member_type = st.radio(
            "Relationship to the SACCO", ["Member", "Outsider"], horizontal=True,
            help="Members can save AND borrow. Outsiders are loan-only clients with no savings account."
        )
        occupation = st.selectbox("Occupation / Category", OCCUPATIONS)
        submitted = st.form_submit_button("Add Customer")
        if submitted:
            if name and phone:
                add_customer(name, phone, national_id, member_type, occupation)
                st.success(f"Customer '{name}' added as a {member_type}.")
            else:
                st.error("Name and phone number are required.")

    st.write("#### All Customers")
    customers = get_customers()
    if customers:
        st.dataframe(
            [{"ID": c['id'], "Name": c['name'], "Phone": c['phone'], "Type": c['member_type'],
              "Occupation": c['occupation'], "National ID": c['national_id'], "Joined": c['created_at']} for c in customers],
            use_container_width=True
        )
    else:
        st.info("No customers yet.")
