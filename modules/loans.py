import streamlit as st
from services.loan_engine import calculate_interest, check_loan_eligibility
from database import get_db_connection

def render_loans():
    st.subheader("💰 Loan Management")
    # Simple UI for loan request
    amount = st.number_input("Loan Amount Requested", min_value=1000)
    savings = st.number_input("Current Savings Balance", min_value=0)
    
    if st.button("Check Eligibility"):
        if check_loan_eligibility(savings, amount):
            st.success("Eligible for loan!")
            interest = calculate_interest(amount, 10, 1) # 10% interest for 1 month
            st.write(f"Estimated Interest: UGX {interest:,.0f}")
        else:
            st.error("Ineligible: Amount exceeds 3x savings limit.")
