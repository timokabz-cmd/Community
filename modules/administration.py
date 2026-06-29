import streamlit as st
from database import get_db_connection
from auth import hash_password
from modules.customers import get_customers

def add_user(username, password, role='staff'):
    salt, pw_hash = hash_password(password)
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (username, pw_hash, salt, role))
    conn.commit()
    conn.close()
    return True

def get_users():
    conn = get_db_connection()
    rows = conn.execute("SELECT username, role FROM users").fetchall()
    conn.close()
    return rows

def get_customer_profile(customer_id):
    conn = get_db_connection()
    customer = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
    loans = conn.execute("SELECT * FROM loans WHERE customer_id=?", (customer_id,)).fetchall()
    savings = conn.execute("SELECT * FROM savings_accounts WHERE customer_id=?", (customer_id,)).fetchone()
    guarantors_given = conn.execute(
        """SELECT guarantors.*, loans.id as loan_ref FROM guarantors JOIN loans ON guarantors.loan_id = loans.id WHERE loans.customer_id = ?""",
        (customer_id,)
    ).fetchall()
    conn.close()
    return customer, loans, savings, guarantors_given

def render():
    st.write("#### 🌱 Demo Data")
    st.caption(
        "Loads 20 sample profiles — Members and Outsiders — with savings, loans at different "
        "repayment stages (on-track, overdue, fully closed), guarantors, and collateral. "
        "Safe to click more than once — it skips any profile already loaded."
    )
    if st.button("Load 20 Demo Profiles"):
        from seed_data import seed_demo_data
        created, skipped = seed_demo_data()
        if created:
            st.success(f"Loaded {created} new demo profile(s).")
        if skipped:
            st.info(f"Skipped {skipped} profile(s) already present.")
        if not created and not skipped:
            st.warning("Nothing to load.")

    st.write("---")
    st.write("#### 👥 Manage Staff & Admin Users")
    with st.form("add_user_form", clear_on_submit=True):
        new_username = st.text_input("New username")
        new_password = st.text_input("New password", type="password")
        role = st.selectbox("Role", ["staff", "admin"])
        submitted = st.form_submit_button("Create User")
        if submitted:
            if new_username and new_password:
                created = add_user(new_username, new_password, role)
                if created:
                    st.success(f"User '{new_username}' created with role '{role}'.")
                else:
                    st.error("That username already exists.")
            else:
                st.error("Username and password are required.")

    users = get_users()
    if users:
        st.dataframe([{"Username": u['username'], "Role": u['role']} for u in users], use_container_width=True)

    st.write("---")
    st.write("#### 🔍 Customer 360 View")
    customers = get_customers()
    if not customers:
        st.info("No customers yet.")
        return

    customer_map = {f"{c['name']} ({c['phone']})": c['id'] for c in customers}
    choice = st.selectbox("Select customer", list(customer_map.keys()))
    customer, loans, savings, guarantors_given = get_customer_profile(customer_map[choice])

    st.write(f"**{customer['name']}** — {customer['member_type']} | {customer['occupation'] or 'No occupation set'}")
    st.write(f"📞 {customer['phone']} | 🆔 {customer['national_id'] or 'N/A'} | Joined {customer['created_at']}")

    if savings:
        st.write(f"💰 **Savings Balance:** UGX {savings['balance']:,.0f}")
    else:
        st.write("💰 No savings account (Outsider, or member who hasn't opened one yet)")

    if loans:
        st.write("**Loan History:**")
        st.dataframe(
            [{"Loan ID": l['id'], "Principal": l['principal'], "Balance": l['balance'], "Status": l['status'],
              "Disbursed": l['disbursed_date']} for l in loans],
            use_container_width=True
        )
    else:
        st.info("No loans on record for this customer.")

    if guarantors_given:
        st.write("**Guarantors Backing This Customer's Loans:**")
        st.dataframe(
            [{"Loan ID": g['loan_ref'], "Guarantor": g['name'], "Phone": g['phone']} for g in guarantors_given],
            use_container_width=True
        )
