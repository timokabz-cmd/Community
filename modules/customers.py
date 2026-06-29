import streamlit as st
from datetime import datetime
from database import get_db_connection

OCCUPATIONS = [
    "Trader / Shop Owner", "Farmer", "Boda Boda Rider", "Teacher", "Civil Servant",
    "Artisan / Craftsman", "Market Vendor", "Salaried Employee", "Transporter",
    "Student", "Other"
]

def add_customer(name, phone, national_id, member_type='Member', occupation=None, location=None, photo=None):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO customers (name, phone, national_id, created_at, member_type, occupation, location, photo) VALUES (?,?,?,?,?,?,?,?)",
        (name, phone, national_id, datetime.now().strftime('%Y-%m-%d'), member_type, occupation, location, photo)
    )
    conn.commit()
    conn.close()

def get_customers():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    conn.close()
    return rows

def get_customer(customer_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    conn.close()
    return row

def render():
    st.write("#### Add New Customer")
    with st.form("add_customer_form", clear_on_submit=True):
        name = st.text_input("Full name")
        phone = st.text_input("Phone number (e.g. 0772xxxxxx)")
        national_id = st.text_input("National ID (optional)")
        location = st.text_input("Location (e.g. village/parish, Namuwongo)")
        member_type = st.radio(
            "Relationship to the SACCO", ["Member", "Outsider"], horizontal=True,
            help="Members can save AND borrow. Outsiders are loan-only clients with no savings account."
        )
        occupation = st.selectbox("Occupation / Category", OCCUPATIONS)
        photo_file = st.file_uploader("Passport photo (optional)", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Add Customer")
        if submitted:
            if name and phone:
                photo_bytes = photo_file.getvalue() if photo_file else None
                add_customer(name, phone, national_id, member_type, occupation, location, photo_bytes)
                st.success(f"Customer '{name}' added as a {member_type}.")
            else:
                st.error("Name and phone number are required.")

    st.write("#### All Customers")
    customers = get_customers()
    if not customers:
        st.info("No customers yet.")
        return

    st.dataframe(
        [{"ID": c['id'], "Name": c['name'], "Phone": c['phone'], "Type": c['member_type'],
          "Occupation": c['occupation'], "Location": c['location'] or '—',
          "National ID": c['national_id'], "Photo": "Yes" if c['photo'] else "No",
          "Joined": c['created_at']} for c in customers],
        use_container_width=True
    )

    st.write("#### View Customer Profile")
    customer_map = {f"{c['name']} ({c['phone']})": c['id'] for c in customers}
    choice = st.selectbox("Select a customer to view", list(customer_map.keys()))
    customer = get_customer(customer_map[choice])
    col1, col2 = st.columns([1, 3])
    with col1:
        if customer['photo']:
            st.image(customer['photo'], width=120, caption="Passport photo")
        else:
            st.caption("No passport photo on file.")
    with col2:
        st.write(f"**{customer['name']}** — {customer['member_type']}")
        st.write(f"📞 {customer['phone']} | 🆔 {customer['national_id'] or 'N/A'}")
        st.write(f"📍 {customer['location'] or 'Location not set'}")
        st.write(f"Occupation: {customer['occupation'] or '—'} | Joined: {customer['created_at']}")
