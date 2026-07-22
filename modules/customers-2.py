import streamlit as st
from datetime import datetime, date
from database import get_db_connection
from modules.nssf_engine import award_points, get_points_balance, get_tier

OCCUPATIONS = [
    "Trader / Shop Owner", "Farmer", "Boda Boda Rider", "Teacher", "Civil Servant",
    "Artisan / Craftsman", "Market Vendor", "Salaried Employee", "Transporter",
    "Student", "Other"
]

def calculate_age(dob_str):
    if not dob_str:
        return None
    try:
        dob   = datetime.strptime(dob_str, '%Y-%m-%d').date()
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except ValueError:
        return None

def add_customer(name, phone, national_id, sacco_id, member_type='Member', occupation=None,
                 photo=None, gender=None, date_of_birth=None, pwd_status='No',
                 subsistence_status=None, village=None, parish=None,
                 nssf_registered=0, nssf_number=None, nssf_contribution_rate=5.0):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO customers
            (name, phone, national_id, created_at, member_type, occupation, photo,
             gender, date_of_birth, pwd_status, subsistence_status, village, parish,
             sacco_id, nssf_registered, nssf_number, nssf_contribution_rate)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (name, phone, national_id, datetime.now().strftime('%Y-%m-%d'), member_type,
          occupation, photo, gender, date_of_birth, pwd_status, subsistence_status,
          village, parish, sacco_id, nssf_registered, nssf_number, nssf_contribution_rate))
    customer_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()
    if nssf_registered == 1:
        award_points(customer_id, sacco_id, "nssf_enrolled")
    return customer_id

def get_customers(sacco_id):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE sacco_id = %s ORDER BY id DESC", (sacco_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_customer(customer_id):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    st.write("#### Add New Customer")
    with st.form("add_customer_form", clear_on_submit=True):
        name         = st.text_input("Full name")
        phone        = st.text_input("Phone number (e.g. 0772xxxxxx)")
        national_id  = st.text_input("National ID (optional)")
        gender       = st.selectbox("Gender", ["Female", "Male"])
        dob          = st.date_input("Date of birth", value=None,
                                     min_value=date(1920,1,1), max_value=date.today())
        col1, col2   = st.columns(2)
        with col1: village = st.text_input("Village")
        with col2: parish  = st.text_input("Parish")
        member_type  = st.radio("Relationship to the SACCO", ["Member", "Outsider"], horizontal=True)
        occupation   = st.selectbox("Occupation / Category", OCCUPATIONS)
        occupation_other = st.text_input("If 'Other', specify here")
        subsistence_status = st.radio("In the subsistence economy?", ["No", "Yes"], horizontal=True)
        pwd_status   = st.radio("Person with a disability (PWD)?", ["No", "Yes"], horizontal=True)
        photo_file   = st.file_uploader("Passport photo (optional)", type=["jpg","jpeg","png"])

        st.divider()
        st.markdown("##### 🇺🇬 NSSF Registration")
        st.caption("Uganda National Social Security Fund — required for all SACCO members.")
        nssf_status = st.radio("Is this member registered with NSSF?", ["Yes","No"], horizontal=True)
        nssf_number = None
        nssf_contribution_rate = 5.0
        if nssf_status == "Yes":
            nssf_number = st.text_input("NSSF Membership Number", placeholder="e.g. 1000123456")
            nssf_contribution_rate = st.slider("Monthly NSSF contribution rate (%)",
                                               min_value=1, max_value=20, value=5)
        else:
            st.warning(
                "⚠️ This member is not yet registered with NSSF. "
                "Register at **[nssfug.org](https://www.nssfug.org)** — update their NSSF number later from their profile."
            )

        submitted = st.form_submit_button("Add Customer")
        if submitted:
            if name and phone:
                photo_bytes = photo_file.getvalue() if photo_file else None
                dob_str     = dob.strftime('%Y-%m-%d') if dob else None
                final_occ   = occupation_other.strip() if occupation == "Other" and occupation_other.strip() else occupation
                nssf_flag   = 1 if nssf_status == "Yes" else 0
                add_customer(
                    name, phone, national_id, sacco_id, member_type, final_occ, photo_bytes,
                    gender, dob_str, pwd_status, subsistence_status, village, parish,
                    nssf_registered=nssf_flag, nssf_number=nssf_number,
                    nssf_contribution_rate=float(nssf_contribution_rate)
                )
                if nssf_flag == 1:
                    st.success(f"✅ '{name}' enrolled. NSSF registered — 50 Gold Points awarded! 🥉")
                else:
                    st.success(f"✅ '{name}' enrolled. Remind them to register with NSSF to start earning Gold Points.")
            else:
                st.error("Name and phone number are required.")

    st.write("#### All Customers")
    customers = get_customers(sacco_id)
    if not customers:
        st.info("No customers yet for this SACCO.")
        return

    st.dataframe(
        [{"ID": c['id'], "Name": c['name'], "Phone": c['phone'], "Type": c['member_type'],
          "Gender": c['gender'] or '—', "Age": calculate_age(c['date_of_birth']) or '—',
          "PWD": c['pwd_status'] or 'No', "Subsistence": c['subsistence_status'] or '—',
          "Occupation": c['occupation'], "Village": c['village'] or '—',
          "Parish": c['parish'] or '—', "National ID": c['national_id'],
          "NSSF": "✅ Registered" if c['nssf_registered'] else "⚠️ Not Registered",
          "Photo": "Yes" if c['photo'] else "No", "Joined": c['created_at']}
         for c in customers],
        use_container_width=True
    )

    st.write("#### View Customer Profile")
    customer_map = {f"{c['name']} ({c['phone']})": c['id'] for c in customers}
    choice       = st.selectbox("Select a customer to view", list(customer_map.keys()))
    customer     = get_customer(customer_map[choice])

    col1, col2 = st.columns([1, 3])
    with col1:
        if customer['photo']:
            st.image(bytes(customer['photo']), width=120, caption="Passport photo")
        else:
            st.caption("No passport photo on file.")
    with col2:
        st.write(f"**{customer['name']}** — {customer['member_type']}")
        st.write(f"📞 {customer['phone']} | 🆔 {customer['national_id'] or 'N/A'}")
        age = calculate_age(customer['date_of_birth'])
        st.write(f"Gender: {customer['gender'] or '—'} | Age: {age or '—'} | PWD: {customer['pwd_status'] or 'No'}")
        st.write(f"📍 {customer['village'] or '—'}, {customer['parish'] or '—'}")
        st.write(f"Occupation: {customer['occupation'] or '—'} | Subsistence: {customer['subsistence_status'] or '—'}")
        st.write(f"Joined: {customer['created_at']}")
        st.divider()
        nssf_col, pts_col = st.columns(2)
        with nssf_col:
            if customer['nssf_registered']:
                st.success("🇺🇬 NSSF Registered")
                st.caption(f"Number: {customer['nssf_number'] or 'Not captured'}")
                st.caption(f"Rate: {customer['nssf_contribution_rate'] or 5.0}% per deposit")
            else:
                st.error("⚠️ Not NSSF Registered")
                st.caption("Register at [nssfug.org](https://www.nssfug.org)")
        with pts_col:
            points = get_points_balance(customer['id'])
            tier   = get_tier(points)
            st.info(f"{tier}")
            st.caption(f"**{points:,} Gold Points**")
