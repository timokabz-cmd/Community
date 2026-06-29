""" One-click demo data loader for CommunityFinanceOS. Triggered from the "Demo Data" section in the Administration tab. Populates 20 realistic Ugandan member/outsider profiles — with savings, loans at different repayment stages (on-track, overdue, fully closed), guarantors, and collateral — so the Dashboard, Analytics, Reports, and AI Insights tabs all have real data to demonstrate. All names, phone numbers, and IDs below are fictional, for demo purposes only. """
from datetime import date, timedelta
from modules.customers import add_customer, get_customers
from modules.savings import open_account, deposit
from modules.loans import issue_loan
from modules.collections import record_repayment
from modules.guarantors import add_guarantor
from modules.collateral import add_collateral

PROFILES = [
    {"name": "Grace Nansubuga", "phone": "0772100001", "nin": "CM85021501AB", "type": "Member",
     "occupation": "Trader / Shop Owner", "savings": 350000,
     "loan": {"principal": 500000, "rate": 12, "term": 4, "disbursed_days_ago": 95},
     "repayments": [{"amount": 150000, "days_ago": 40, "method": "MTN MoMo"}]},

    {"name": "Peter Okello", "phone": "0701100002", "nin": "CM90031202CD", "type": "Outsider",
     "occupation": "Boda Boda Rider", "savings": None,
     "loan": {"principal": 300000, "rate": 15, "term": 3, "disbursed_days_ago": 10},
     "repayments": []},

    {"name": "Sarah Atim", "phone": "0752100003", "nin": "CM88041503EF", "type": "Member",
     "occupation": "Farmer", "savings": 120000,
     "loan": {"principal": 250000, "rate": 10, "term": 3, "disbursed_days_ago": 200},
     "repayments": [
         {"amount": 91667, "days_ago": 160, "method": "Airtel Money"},
         {"amount": 91667, "days_ago": 130, "method": "Airtel Money"},
         {"amount": 91666, "days_ago": 100, "method": "Airtel Money"},
     ]},

    {"name": "James Mukasa", "phone": "0782100004", "nin": "CM79051204GH", "type": "Member",
     "occupation": "Teacher", "savings": 600000, "loan": None, "repayments": []},

    {"name": "Ritah Nakimuli", "phone": "0712100005", "nin": "CM93061505IJ", "type": "Member",
     "occupation": "Market Vendor", "savings": 80000,
     "loan": {"principal": 150000, "rate": 10, "term": 2, "disbursed_days_ago": 5},
     "repayments": []},

    {"name": "David Ssempa", "phone": "0742100006", "nin": "CM86071306KL", "type": "Outsider",
     "occupation": "Artisan / Craftsman", "savings": None,
     "loan": {"principal": 400000, "rate": 18, "term": 4, "disbursed_days_ago": 130},
     "repayments": [{"amount": 100000, "days_ago": 60, "method": "Cash"}]},

    {"name": "Esther Auma", "phone": "0772100007", "nin": "CM91081507MN", "type": "Member",
     "occupation": "Civil Servant", "savings": 900000, "loan": None, "repayments": []},

    {"name": "Moses Kato", "phone": "0702100008", "nin": "CM84091308OP", "type": "Member",
     "occupation": "Trader / Shop Owner", "savings": 250000,
     "loan": {"principal": 600000, "rate": 12, "term": 5, "disbursed_days_ago": 45},
     "repayments": [{"amount": 134400, "days_ago": 15, "method": "MTN MoMo"}]},

    {"name": "Joyce Namatovu", "phone": "0752100009", "nin": "CM89101509QR", "type": "Member",
     "occupation": "Salaried Employee", "savings": 450000, "loan": None, "repayments": []},

    {"name": "Robert Tumwine", "phone": "0782100010", "nin": "CM82111310ST", "type": "Outsider",
     "occupation": "Transporter", "savings": None,
     "loan": {"principal": 800000, "rate": 20, "term": 6, "disbursed_days_ago": 200},
     "repayments": [
         {"amount": 160000, "days_ago": 170, "method": "Airtel Money"},
         {"amount": 160000, "days_ago": 140, "method": "Airtel Money"},
         {"amount": 160000, "days_ago": 110, "method": "Airtel Money"},
         {"amount": 160000, "days_ago": 80, "method": "Airtel Money"},
     ]},

    {"name": "Patricia Akello", "phone": "0712100011", "nin": "CM94121511UV", "type": "Member",
     "occupation": "Farmer", "savings": 60000,
     "loan": {"principal": 180000, "rate": 10, "term": 3, "disbursed_days_ago": 70},
     "repayments": []},

    {"name": "Samuel Wasswa", "phone": "0742100012", "nin": "CM87011312WX", "type": "Member",
     "occupation": "Boda Boda Rider", "savings": 40000,
     "loan": {"principal": 200000, "rate": 15, "term": 2, "disbursed_days_ago": 100},
     "repayments": [
         {"amount": 115000, "days_ago": 70, "method": "MTN MoMo"},
         {"amount": 115000, "days_ago": 40, "method": "MTN MoMo"},
     ]},

    {"name": "Florence Adongo", "phone": "0772100013", "nin": "CM90021513YZ", "type": "Member",
     "occupation": "Market Vendor", "savings": 95000, "loan": None, "repayments": []},

    {"name": "Charles Kirabo", "phone": "0702100014", "nin": "CM83031314AA", "type": "Outsider",
     "occupation": "Trader / Shop Owner", "savings": None,
     "loan": {"principal": 1000000, "rate": 15, "term": 6, "disbursed_days_ago": 20},
     "repayments": []},

    {"name": "Agnes Nyirahabimana", "phone": "0752100015", "nin": "CM92041515BB", "type": "Member",
     "occupation": "Teacher", "savings": 700000,
     "loan": {"principal": 300000, "rate": 10, "term": 3, "disbursed_days_ago": 15},
     "repayments": []},

    {"name": "Emmanuel Byaruhanga", "phone": "0782100016", "nin": "CM85051316CC", "type": "Member",
     "occupation": "Civil Servant", "savings": 500000, "loan": None, "repayments": []},

    {"name": "Stella Among", "phone": "0712100017", "nin": "CM91061517DD", "type": "Member",
     "occupation": "Salaried Employee", "savings": 320000,
     "loan": {"principal": 450000, "rate": 12, "term": 4, "disbursed_days_ago": 35},
     "repayments": [{"amount": 126000, "days_ago": 5, "method": "MTN MoMo"}]},

    {"name": "Francis Lubega", "phone": "0742100018", "nin": "CM88071318EE", "type": "Outsider",
     "occupation": "Artisan / Craftsman", "savings": None,
     "loan": {"principal": 250000, "rate": 18, "term": 3, "disbursed_days_ago": 50},
     "repayments": []},

    {"name": "Brenda Kemigisha", "phone": "0772100019", "nin": "CM93081519FF", "type": "Member",
     "occupation": "Farmer", "savings": 150000, "loan": None, "repayments": []},

    {"name": "Vincent Opio", "phone": "0702100020", "nin": "CM86091320GG", "type": "Member",
     "occupation": "Trader / Shop Owner", "savings": 280000,
     "loan": {"principal": 700000, "rate": 12, "term": 5, "disbursed_days_ago": 8},
     "repayments": []},
]


def seed_demo_data():
    """Idempotent: re-running this skips any profile whose phone number is already in the database, so it's safe to click more than once."""
    existing_phones = {c['phone'] for c in get_customers()}
    created, skipped = 0, 0

    for profile in PROFILES:
        if profile["phone"] in existing_phones:
            skipped += 1
            continue

        add_customer(profile["name"], profile["phone"], profile["nin"], profile["type"], profile["occupation"])
        customer = next(c for c in get_customers() if c['phone'] == profile["phone"])
        created += 1

        if profile["savings"] is not None and profile["type"] == "Member":
            acc_id = open_account(customer['id'])
            deposit(acc_id, profile["savings"])

        if profile["loan"]:
            loan = profile["loan"]
            disbursed_date = date.today() - timedelta(days=loan["disbursed_days_ago"])
            loan_id = issue_loan(customer['id'], loan["principal"], loan["rate"], loan["term"], disbursed_date)

            for rp in profile["repayments"]:
                txn_date = date.today() - timedelta(days=rp["days_ago"])
                record_repayment(loan_id, rp["amount"], rp["method"], txn_date=txn_date)

            # Larger loans and outsider loans get a guarantor/collateral on file, for realism
            if loan["principal"] >= 400000:
                first_name = profile["name"].split()[0]
                add_guarantor(loan_id, f"{first_name}'s Guarantor", "0770000000", "N/A", "Relative")
            if profile["type"] == "Outsider":
                add_collateral(loan_id, "Motorcycle / asset held as security", round(loan["principal"] * 1.2))

    return created, skipped
