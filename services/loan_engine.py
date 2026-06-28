# services/loan_engine.py
def calculate_interest(principal, rate, duration):
    # This is where your professional logic will eventually live
    return principal * (rate / 100) * duration

def check_loan_eligibility(member_savings, requested_amount):
    # Business rule: Can only borrow 3x savings
    if requested_amount <= (member_savings * 3):
        return True
    return False
