import streamlit as st
from services.loan_engine import calculate_interest, check_loan_eligibility
from database import get_db_connection

def render_loans():
    st.subheader("💰 Loan Management")
    
    conn = get_db_connection()
    members = conn.execute("SELECT id, name FROM members").fetchall()
    conn.close()
    
    if not members:
        st.warning("No members found. Please register a member first.")
        return

    member_options = {m['name']: m['id'] for m in members}
    selected_name = st.selectbox("Select Member", list(member_options.keys()))
    selected_member_id = member_options[selected_name]
    
    amount = st.number_input("Loan Amount Requested", min_value=1000)
    
    if st.button("Submit Loan Application"):
        # Save to database
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO loans (member_id, amount, status) VALUES (?, ?, ?)",
            (selected_member_id, amount, 'Pending')
        )
        conn.commit()
        conn.close()
        st.success(f"Loan application for {selected_name} submitted successfully!")
