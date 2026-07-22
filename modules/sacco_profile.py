import streamlit as st
from database import get_db_connection
from modules.customers import get_customers

EMYOOGA_CATEGORIES = [
    "Boda Boda", "Market Vendors", "Tailors", "Salon Operators", "Carpenters",
    "Restaurant Owners", "Journalists", "Mechanics", "Farmers", "Fishermen",
    "Youth", "Women", "PWDs", "Elected Leaders", "Private Teachers",
    "Drivers", "Traditional Healers", "Artisans / Craftsmen", "Other"
]

def get_all_saccos():
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM sacco_profile ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_profile(sacco_id):
    if sacco_id is None:
        return None
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM sacco_profile WHERE id = %s", (sacco_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def create_sacco(data):
    conn = get_db_connection()
    cur  = conn.cursor()
    columns      = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    cur.execute(
        f"INSERT INTO sacco_profile ({columns}) VALUES ({placeholders}) RETURNING id",
        list(data.values())
    )
    new_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()
    return new_id

def update_sacco(sacco_id, data):
    conn = get_db_connection()
    cur  = conn.cursor()
    set_clause = ", ".join(f"{key} = %s" for key in data.keys())
    cur.execute(
        f"UPDATE sacco_profile SET {set_clause} WHERE id = %s",
        list(data.values()) + [sacco_id]
    )
    conn.commit()
    cur.close()
    conn.close()

def save_profile(sacco_id, data):
    """Upserts a SACCO profile. Creates if sacco_id is None, updates otherwise."""
    if sacco_id is None:
        return create_sacco(data)
    update_sacco(sacco_id, data)
    return sacco_id

def render():
    from auth import ROLE_SUPER_ADMIN
    role             = st.session_state.get('user_role')
    current_sacco_id = st.session_state.get('current_sacco_id')

    st.write("#### 🏢 SACCO Profile")
    st.caption(
        "Organisation-level identity, Emyooga classification, and governance details — "
        "captured once per SACCO, used across PDM/Emyooga/funder reporting."
    )

    if role == ROLE_SUPER_ADMIN:
        saccos = get_all_saccos()
        with st.expander("➕ Create New SACCO"):
            new_name = st.text_input("New SACCO name", key="new_sacco_name_input")
            if st.button("Create SACCO"):
                if new_name:
                    new_id = create_sacco({'sacco_name': new_name})
                    st.success(f"Created '{new_name}'. Use the sidebar to switch to it.")
                    st.session_state.current_sacco_id = new_id
                    st.rerun()
                else:
                    st.error("SACCO name is required.")
        saccos = get_all_saccos()
        if not saccos:
            st.info("No SACCOs yet — create one above to get started.")
            return
        sacco_map   = {(s['sacco_name'] or f"SACCO #{s['id']}"): s['id'] for s in saccos}
        labels      = list(sacco_map.keys())
        default_lbl = next((lbl for lbl, sid in sacco_map.items() if sid == current_sacco_id), labels[0])
        choice      = st.selectbox("Editing profile for:", labels, index=labels.index(default_lbl))
        editing_sacco_id = sacco_map[choice]
    else:
        editing_sacco_id = current_sacco_id
        if editing_sacco_id is None:
            st.warning("Your account isn't assigned to a SACCO yet. Contact your administrator.")
            return

    profile          = get_profile(editing_sacco_id)
    p                = dict(profile) if profile else {}
    live_member_count= len(get_customers(editing_sacco_id))

    with st.expander("SACCO Identity & Registration", expanded=True):
        sacco_name  = st.text_input("SACCO name", value=p.get('sacco_name') or '')
        col1, col2, col3 = st.columns(3)
        with col1: parish      = st.text_input("Parish (HQ)",    value=p.get('parish') or '')
        with col2: sub_county  = st.text_input("Sub-county",     value=p.get('sub_county') or '')
        with col3: district    = st.text_input("District",       value=p.get('district') or '')
        date_of_formation = st.text_input(
            "Date of formation (YYYY-MM-DD)", value=p.get('date_of_formation') or '',
            help="Partial or approximate dates accepted."
        )
        ursb_registration_number = st.text_input(
            "URSB registration number", value=p.get('ursb_registration_number') or '',
            help="PDM cooperative number and Emyooga provisional number refer to the same underlying ID."
        )
        permanent_registration_status = st.radio(
            "Permanent registration granted?", ["No", "Yes"], horizontal=True,
            index=["No", "Yes"].index(p.get('permanent_registration_status') or 'No')
        )
        col4, col5 = st.columns(2)
        with col4: bank_name           = st.text_input("Bank name",           value=p.get('bank_name') or '')
        with col5: bank_account_number = st.text_input("Bank account number", value=p.get('bank_account_number') or '')
        total_registered_members = st.number_input(
            "Total registered members", min_value=0, step=1,
            value=int(p.get('total_registered_members') or live_member_count)
        )
        st.caption(f"System currently has {live_member_count} customer record(s) for this SACCO.")
        number_of_enterprise_groups = st.number_input(
            "Number of enterprise groups", min_value=0, step=1,
            value=int(p.get('number_of_enterprise_groups') or 0)
        )

    with st.expander("Emyooga Classification"):
        emyooga_category = st.selectbox(
            "Emyooga category", EMYOOGA_CATEGORIES,
            index=EMYOOGA_CATEGORIES.index(p['emyooga_category'])
            if p.get('emyooga_category') in EMYOOGA_CATEGORIES else 0
        )
        apex_sacco_name    = st.text_input("Constituency SACCO name (Apex)", value=p.get('apex_sacco_name') or '')
        constituency       = st.text_input("Constituency", value=p.get('constituency') or '')
        parish_associations= st.text_area(
            "Parish association name(s) — one per line", value=p.get('parish_associations') or ''
        )
        association_lines  = [l for l in parish_associations.splitlines() if l.strip()]
        number_of_parish_associations = st.number_input(
            "Number of parish associations", min_value=0, step=1,
            value=int(p.get('number_of_parish_associations') or len(association_lines))
        )

    with st.expander("Governance & Compliance"):
        col6, col7 = st.columns(2)
        with col6: date_of_last_agm   = st.text_input("Date of last AGM (YYYY-MM-DD)",   value=p.get('date_of_last_agm') or '')
        with col7: date_of_last_audit = st.text_input("Date of last audit (YYYY-MM-DD)", value=p.get('date_of_last_audit') or '')
        auditor_name = st.text_input("Auditor / audit firm", value=p.get('auditor_name') or '')
        audit_report_filed = st.radio(
            "Audit report filed?", ["No", "Yes"], horizontal=True,
            index=["No", "Yes"].index(p.get('audit_report_filed') or 'No')
        )
        annual_subscription_paid = st.radio(
            "Annual subscription paid?", ["No", "Yes"], horizontal=True,
            index=["No", "Yes"].index(p.get('annual_subscription_paid') or 'No')
        )
        col8, col9 = st.columns(2)
        with col8:
            share_capital_per_member = st.number_input(
                "Share capital per member (UGX)", min_value=0.0, step=10000.0,
                value=float(p.get('share_capital_per_member') or 100000.0)
            )
        with col9:
            membership_joining_fee = st.number_input(
                "Membership joining fee (UGX)", min_value=0.0, step=5000.0,
                value=float(p.get('membership_joining_fee') or 50000.0)
            )

    if st.button("Save SACCO Profile"):
        save_profile(editing_sacco_id, {
            'sacco_name': sacco_name, 'parish': parish, 'sub_county': sub_county,
            'constituency': constituency, 'district': district,
            'date_of_formation': date_of_formation,
            'ursb_registration_number': ursb_registration_number,
            'permanent_registration_status': permanent_registration_status,
            'bank_account_number': bank_account_number, 'bank_name': bank_name,
            'total_registered_members': total_registered_members,
            'number_of_enterprise_groups': number_of_enterprise_groups,
            'emyooga_category': emyooga_category, 'apex_sacco_name': apex_sacco_name,
            'parish_associations': parish_associations,
            'number_of_parish_associations': number_of_parish_associations,
            'date_of_last_agm': date_of_last_agm, 'date_of_last_audit': date_of_last_audit,
            'auditor_name': auditor_name, 'audit_report_filed': audit_report_filed,
            'annual_subscription_paid': annual_subscription_paid,
            'share_capital_per_member': share_capital_per_member,
            'membership_joining_fee': membership_joining_fee,
        })
        st.success("SACCO profile saved.")
