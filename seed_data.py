"""
seed_data.py

Seeds the database with 2 example SACCOs and 20 members (10 each),
plus savings accounts, loans, guarantors, collateral, and repayments
so the app has realistic data immediately after deployment.

Safe to re-run: checks for each SACCO by name first and skips if
already present, so running it twice won't duplicate data.

PostgreSQL version: uses %s placeholders via psycopg2.
"""
from datetime import datetime, timedelta
from database import init_db, get_db_connection
from modules import sacco_profile, customers, savings, loans, guarantors, collateral, collections


def backdate_loan(loan_id, months_ago):
    """Shifts disbursed_date and schedule due_dates into the past so
    some installments appear genuinely overdue in Analytics/Reports."""
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT disbursed_date FROM loans WHERE id = %s", (loan_id,))
    loan    = cur.fetchone()
    old_date= datetime.strptime(loan['disbursed_date'], '%Y-%m-%d')
    new_date= old_date - timedelta(days=months_ago * 30)
    cur.execute(
        "UPDATE loans SET disbursed_date = %s WHERE id = %s",
        (new_date.strftime('%Y-%m-%d'), loan_id)
    )
    cur.execute(
        "SELECT id, due_date FROM loan_schedule WHERE loan_id = %s", (loan_id,)
    )
    schedule = cur.fetchall()
    for s in schedule:
        old_due = datetime.strptime(s['due_date'], '%Y-%m-%d')
        new_due = old_due - timedelta(days=months_ago * 30)
        cur.execute(
            "UPDATE loan_schedule SET due_date = %s WHERE id = %s",
            (new_due.strftime('%Y-%m-%d'), s['id'])
        )
    conn.commit()
    cur.close()
    conn.close()


def seed_sacco(profile_data, members, loan_plan):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT id FROM sacco_profile WHERE sacco_name = %s",
        (profile_data['sacco_name'],)
    )
    existing = cur.fetchone()
    cur.close()
    conn.close()

    if existing:
        print(f"  Skipping '{profile_data['sacco_name']}' — already exists (id={existing['id']}).")
        return existing['id']

    sacco_id = sacco_profile.create_sacco(profile_data)
    print(f"  Created SACCO '{profile_data['sacco_name']}' (id={sacco_id})")

    customer_ids = []
    for m in members:
        customers.add_customer(
            m['name'], m['phone'], m['national_id'], sacco_id,
            m['member_type'], m['occupation'], None,
            m['gender'], m['dob'], m['pwd'], m['subsistence'],
            m['village'], m['parish']
        )
        cust = [c for c in customers.get_customers(sacco_id) if c['phone'] == m['phone']][0]
        customer_ids.append(cust['id'])

    name_to_id = {m['name']: cid for m, cid in zip(members, customer_ids)}
    for m, cid in zip(members, customer_ids):
        if m['member_type'] == 'Member':
            acc_id = savings.open_account(cid, sacco_id)
            savings.deposit(acc_id, m['deposit'], sacco_id, m['channel'])

    for plan in loan_plan:
        cid     = name_to_id[plan['name']]
        loan_id = loans.issue_loan(cid, plan['principal'], plan['rate'], plan['term'], sacco_id)
        if plan.get('guarantor'):
            g = plan['guarantor']
            guarantors.add_guarantor(loan_id, g['name'], g['phone'], g['nid'], g['relationship'])
        if plan.get('collateral'):
            c = plan['collateral']
            collateral.add_collateral(loan_id, c['description'], c['value'])
        if plan.get('backdate_months'):
            backdate_loan(loan_id, plan['backdate_months'])
        if plan.get('repay_full'):
            loan = loans.get_loan(loan_id)
            collections.record_repayment(
                loan_id, loan['total_due'], sacco_id,
                plan.get('repay_channel', 'MTN MoMo')
            )
        elif plan.get('repay_partial'):
            collections.record_repayment(
                loan_id, plan['repay_partial'], sacco_id,
                plan.get('repay_channel', 'Cash')
            )

    print(f"    -> {len(members)} members, {len(loan_plan)} loans seeded.")
    return sacco_id


def run_seed():
    init_db()
    print("Seeding demo data...")

    # ── SACCO A ──────────────────────────────────────────────────────────────
    sacco_a_profile = {
        'sacco_name': 'Namuwongo United SACCO',
        'parish': 'Namuwongo', 'sub_county': 'Nakawa Division',
        'constituency': 'Nakawa', 'district': 'Kampala',
        'date_of_formation': '2023-06-01',
        'ursb_registration_number': 'URSB/SACCO/2023/04567',
        'permanent_registration_status': 'Yes',
        'bank_name': 'Centenary Bank', 'bank_account_number': '3100123456',
        'total_registered_members': 10, 'number_of_enterprise_groups': 3,
        'emyooga_category': 'Market Vendors',
        'apex_sacco_name': 'Nakawa Constituency SACCO',
        'parish_associations': 'Namuwongo Traders Association\nLuzira Roadside Vendors Association',
        'number_of_parish_associations': 2,
        'date_of_last_agm': '2026-02-14', 'date_of_last_audit': '2025-12-10',
        'auditor_name': 'Highgate Audit & Tax Advisors', 'audit_report_filed': 'Yes',
        'annual_subscription_paid': 'Yes',
        'share_capital_per_member': 100000.0, 'membership_joining_fee': 50000.0,
    }
    sacco_a_members = [
        {'name': 'Nakimuli Sarah',  'phone': '0772100001', 'national_id': 'CM91234501', 'gender': 'Female', 'dob': '1988-04-12', 'pwd': 'No',  'subsistence': 'No',  'village': 'Bukasa',  'parish': 'Namuwongo', 'member_type': 'Member',  'occupation': 'Trader / Shop Owner',  'deposit': 150000, 'channel': 'MTN MoMo'},
        {'name': 'Okello Patrick',  'phone': '0772100002', 'national_id': 'CM91234502', 'gender': 'Male',   'dob': '1979-09-23', 'pwd': 'No',  'subsistence': 'Yes', 'village': 'Bukasa',  'parish': 'Namuwongo', 'member_type': 'Member',  'occupation': 'Farmer',               'deposit':  80000, 'channel': 'Cash'},
        {'name': 'Nansubuga Joan',  'phone': '0772100003', 'national_id': 'CM91234503', 'gender': 'Female', 'dob': '2002-03-15', 'pwd': 'No',  'subsistence': 'Yes', 'village': 'Kasubi',  'parish': 'Lubaga',    'member_type': 'Member',  'occupation': 'Market Vendor',        'deposit':  60000, 'channel': 'Airtel Money'},
        {'name': 'Ssempala Moses',  'phone': '0772100004', 'national_id': 'CM91234504', 'gender': 'Male',   'dob': '1995-11-02', 'pwd': 'No',  'subsistence': 'No',  'village': 'Bukasa',  'parish': 'Namuwongo', 'member_type': 'Member',  'occupation': 'Boda Boda Rider',      'deposit':  40000, 'channel': 'MTN MoMo'},
        {'name': 'Atim Grace',      'phone': '0772100005', 'national_id': 'CM91234505', 'gender': 'Female', 'dob': '1992-06-30', 'pwd': 'No',  'subsistence': 'No',  'village': 'Luzira',  'parish': 'Namuwongo', 'member_type': 'Outsider', 'occupation': 'Artisan / Craftsman',  'deposit':      0, 'channel': 'Cash'},
        {'name': 'Kato Henry',      'phone': '0772100006', 'national_id': 'CM91234506', 'gender': 'Male',   'dob': '1965-01-20', 'pwd': 'Yes', 'subsistence': 'No',  'village': 'Bukasa',  'parish': 'Lubaga',    'member_type': 'Member',  'occupation': 'Civil Servant',        'deposit': 200000, 'channel': 'Bank Transfer'},
        {'name': 'Namutebi Irene',  'phone': '0772100007', 'national_id': 'CM91234507', 'gender': 'Female', 'dob': '1985-08-08', 'pwd': 'No',  'subsistence': 'No',  'village': 'Kibuye',  'parish': 'Namuwongo', 'member_type': 'Member',  'occupation': 'Salaried Employee',    'deposit': 120000, 'channel': 'MTN MoMo'},
        {'name': 'Wasswa Charles',  'phone': '0772100008', 'national_id': 'CM91234508', 'gender': 'Male',   'dob': '2000-02-18', 'pwd': 'No',  'subsistence': 'No',  'village': 'Bukasa',  'parish': 'Namuwongo', 'member_type': 'Member',  'occupation': 'Transporter',          'deposit':  30000, 'channel': 'Airtel Money'},
        {'name': 'Achen Brenda',    'phone': '0772100009', 'national_id': 'CM91234509', 'gender': 'Female', 'dob': '1998-12-05', 'pwd': 'No',  'subsistence': 'Yes', 'village': 'Luzira',  'parish': 'Namuwongo', 'member_type': 'Outsider', 'occupation': 'Market Vendor',        'deposit':      0, 'channel': 'Cash'},
        {'name': 'Mugisha Robert',  'phone': '0772100010', 'national_id': 'CM91234510', 'gender': 'Male',   'dob': '1972-07-14', 'pwd': 'No',  'subsistence': 'No',  'village': 'Bukasa',  'parish': 'Lubaga',    'member_type': 'Member',  'occupation': 'Trader / Shop Owner',  'deposit': 175000, 'channel': 'Bank Transfer'},
    ]
    sacco_a_loans = [
        {'name': 'Nakimuli Sarah', 'principal': 500000, 'rate': 10, 'term': 4,
         'guarantor': {'name': 'Nakimuli Peter', 'phone': '0772199001', 'nid': 'CM80011001', 'relationship': 'Husband'},
         'repay_partial': 150000, 'repay_channel': 'MTN MoMo'},
        {'name': 'Okello Patrick',  'principal': 300000, 'rate': 8,  'term': 3,
         'collateral': {'description': 'Cattle (2 heads)', 'value': 1200000}},
        {'name': 'Ssempala Moses',  'principal': 400000, 'rate': 10, 'term': 3,
         'backdate_months': 4},
        {'name': 'Namutebi Irene',  'principal': 250000, 'rate': 9,  'term': 2,
         'repay_full': True, 'repay_channel': 'Bank Transfer'},
        {'name': 'Mugisha Robert',  'principal': 600000, 'rate': 10, 'term': 6,
         'guarantor': {'name': 'Mugisha Florence', 'phone': '0772199002', 'nid': 'CM80011002', 'relationship': 'Wife'},
         'collateral': {'description': 'Shop fittings & stock, Namuwongo market', 'value': 2000000}},
    ]
    seed_sacco(sacco_a_profile, sacco_a_members, sacco_a_loans)

    # ── SACCO B ──────────────────────────────────────────────────────────────
    sacco_b_profile = {
        'sacco_name': 'Bwaise Traders SACCO',
        'parish': 'Bwaise III', 'sub_county': 'Kawempe Division',
        'constituency': 'Kawempe North', 'district': 'Kampala',
        'date_of_formation': '2022-11-15',
        'ursb_registration_number': 'URSB/SACCO/2022/03210',
        'permanent_registration_status': 'No',
        'bank_name': 'Stanbic Bank', 'bank_account_number': '9030456789',
        'total_registered_members': 10, 'number_of_enterprise_groups': 2,
        'emyooga_category': 'Boda Boda',
        'apex_sacco_name': 'Kawempe North Constituency SACCO',
        'parish_associations': 'Bwaise Boda Riders Association\nKazo Roundabout Vendors Association',
        'number_of_parish_associations': 2,
        'date_of_last_agm': '2025-12-20', 'date_of_last_audit': '',
        'auditor_name': '', 'audit_report_filed': 'No',
        'annual_subscription_paid': 'Yes',
        'share_capital_per_member': 100000.0, 'membership_joining_fee': 50000.0,
    }
    sacco_b_members = [
        {'name': 'Kirabo Esther',    'phone': '0701200001', 'national_id': 'CM92234501', 'gender': 'Female', 'dob': '1991-05-09', 'pwd': 'No',  'subsistence': 'No',  'village': 'Bwaise III', 'parish': 'Kawempe', 'member_type': 'Member',  'occupation': 'Market Vendor',       'deposit':  90000, 'channel': 'Airtel Money'},
        {'name': 'Ssebunya Tonny',   'phone': '0701200002', 'national_id': 'CM92234502', 'gender': 'Male',   'dob': '1987-10-01', 'pwd': 'No',  'subsistence': 'No',  'village': 'Kazo',       'parish': 'Bwaise',  'member_type': 'Member',  'occupation': 'Boda Boda Rider',     'deposit':  50000, 'channel': 'MTN MoMo'},
        {'name': 'Nakitto Florence', 'phone': '0701200003', 'national_id': 'CM92234503', 'gender': 'Female', 'dob': '1980-02-27', 'pwd': 'No',  'subsistence': 'Yes', 'village': 'Bwaise II',  'parish': 'Kawempe', 'member_type': 'Member',  'occupation': 'Trader / Shop Owner', 'deposit': 130000, 'channel': 'Cash'},
        {'name': 'Lubega David',     'phone': '0701200004', 'national_id': 'CM92234504', 'gender': 'Male',   'dob': '1996-09-19', 'pwd': 'No',  'subsistence': 'No',  'village': 'Kazo',       'parish': 'Bwaise',  'member_type': 'Member',  'occupation': 'Boda Boda Rider',     'deposit':  35000, 'channel': 'MTN MoMo'},
        {'name': 'Namusoke Betty',   'phone': '0701200005', 'national_id': 'CM92234505', 'gender': 'Female', 'dob': '2003-01-11', 'pwd': 'No',  'subsistence': 'Yes', 'village': 'Bwaise III', 'parish': 'Kawempe', 'member_type': 'Member',  'occupation': 'Artisan / Craftsman', 'deposit':  25000, 'channel': 'Airtel Money'},
        {'name': 'Kasozi Ronald',    'phone': '0701200006', 'national_id': 'CM92234506', 'gender': 'Male',   'dob': '1969-12-24', 'pwd': 'Yes', 'subsistence': 'No',  'village': 'Bwaise I',   'parish': 'Kawempe', 'member_type': 'Outsider', 'occupation': 'Other',               'deposit':      0, 'channel': 'Cash'},
        {'name': 'Tumusiime Agnes',  'phone': '0701200007', 'national_id': 'CM92234507', 'gender': 'Female', 'dob': '1994-07-07', 'pwd': 'No',  'subsistence': 'No',  'village': 'Kazo',       'parish': 'Bwaise',  'member_type': 'Member',  'occupation': 'Market Vendor',       'deposit':  70000, 'channel': 'MTN MoMo'},
        {'name': 'Byaruhanga Allan', 'phone': '0701200008', 'national_id': 'CM92234508', 'gender': 'Male',   'dob': '1983-04-04', 'pwd': 'No',  'subsistence': 'No',  'village': 'Bwaise II',  'parish': 'Kawempe', 'member_type': 'Member',  'occupation': 'Transporter',         'deposit': 100000, 'channel': 'Bank Transfer'},
        {'name': 'Nabirye Sandra',   'phone': '0701200009', 'national_id': 'CM92234509', 'gender': 'Female', 'dob': '1999-11-29', 'pwd': 'No',  'subsistence': 'No',  'village': 'Bwaise III', 'parish': 'Kawempe', 'member_type': 'Outsider', 'occupation': 'Other',               'deposit':      0, 'channel': 'Cash'},
        {'name': 'Mukasa Isaac',     'phone': '0701200010', 'national_id': 'CM92234510', 'gender': 'Male',   'dob': '1975-03-03', 'pwd': 'No',  'subsistence': 'No',  'village': 'Bwaise I',   'parish': 'Kawempe', 'member_type': 'Member',  'occupation': 'Teacher',             'deposit': 140000, 'channel': 'MTN MoMo'},
    ]
    sacco_b_loans = [
        {'name': 'Ssebunya Tonny',   'principal': 350000, 'rate': 9,  'term': 3,
         'collateral': {'description': 'Motorcycle, Reg #UAX 245K', 'value': 4500000}},
        {'name': 'Nakitto Florence', 'principal': 450000, 'rate': 10, 'term': 4,
         'guarantor': {'name': 'Nakitto James', 'phone': '0701299001', 'nid': 'CM81011003', 'relationship': 'Brother'},
         'repay_partial': 100000, 'repay_channel': 'Cash'},
        {'name': 'Lubega David',     'principal': 280000, 'rate': 9,  'term': 3,
         'backdate_months': 5},
        {'name': 'Byaruhanga Allan', 'principal': 300000, 'rate': 8,  'term': 2,
         'repay_full': True, 'repay_channel': 'Bank Transfer'},
    ]
    seed_sacco(sacco_b_profile, sacco_b_members, sacco_b_loans)

    print("\nDone. Login: timo / timo123 (or ADMIN_PASSWORD secret).")


if __name__ == "__main__":
    run_seed()
