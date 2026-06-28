import streamlit as st
from services.loan_engine import calculate_interest, check_loan_eligibility
from database import get_db_connection

def render_loans():
    st.subheader("💰 Loan Management")
    
    # 1. Fetch members from database for the dropdown
    conn = get_db_connection()
    members = conn.execute("SELECT id, name FROM members").fetchall()
    conn.close()
    
    if not members:
        st.warning("No members found. Please register a member first.")
        return

    # 2. Create the selector
    member_options = {m['name']: m['id'] for m in members}
    selected_name = st.selectbox("Select Member", list(member_options.keys()))
    selected_member_id = member_options[selected_name]
    
    # 3. Loan Application Form
    amount = st.number_input("Loan Amount Requested", min_value=1000)
    savings = st.number_input("Current Savings Balance", min_value=0)
    
    if st.button("Check Eligibility"):
        if check_loan_eligibility(savings, amount):
            st.success(f"Member {selected_name} is eligible!")
            interest = calculate_interest(amount, 10, 1) 
            st.write(f"Estimated Interest: UGX {interest:,.0f}")
            
            # Optional: Save to database here in the future
        else:
            st.error(f"Ineligible: {selected_name} exceeds 3x savings limit.")
