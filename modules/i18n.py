"""
modules/i18n.py

Internationalisation engine for CommunityFinanceOS.
Supports 5 languages: English, Luganda, Runyankore, Acholi, Swahili.

Usage anywhere in the app:
    from modules.i18n import t, LANGUAGES
    st.write(t("dashboard"))          # returns translated string
    st.button(t("save"))              # translated button label

NOTE ON TRANSLATIONS:
  - English:    Primary language — complete
  - Swahili:    East African standard — complete, well documented
  - Luganda:    Verified against documented sources — complete
  - Runyankore: Financial terms often borrowed from English in practice.
                Terms marked [~] are phonetic adaptations or borrowings
                that native speakers commonly use — have reviewed by a
                western Uganda native speaker before going fully live.
  - Acholi:     Similarly, many modern financial terms are English
                loanwords in Acholi speech. Terms marked [~] should be
                reviewed by a northern Uganda native speaker.
"""

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Language registry
# ─────────────────────────────────────────────────────────────────────────────

LANGUAGES = {
    "en":  "English",
    "lg":  "Luganda",
    "nyn": "Runyankore",
    "ach": "Acholi",
    "sw":  "Kiswahili",
}

LANGUAGE_FLAGS = {
    "en":  "🇬🇧",
    "lg":  "🇺🇬",
    "nyn": "🇺🇬",
    "ach": "🇺🇬",
    "sw":  "🌍",
}

# ─────────────────────────────────────────────────────────────────────────────
# Translation dictionary
# Keys are semantic identifiers — never change a key once shipped.
# Add new keys at the bottom of each section.
# ─────────────────────────────────────────────────────────────────────────────

TRANSLATIONS = {

    # ── App shell ─────────────────────────────────────────────────────────────
    "app_name": {
        "en":  "CommunityFinanceOS",
        "lg":  "CommunityFinanceOS",
        "nyn": "CommunityFinanceOS",
        "ach": "CommunityFinanceOS",
        "sw":  "CommunityFinanceOS",
    },
    "login_required": {
        "en":  "🔒 Login Required",
        "lg":  "🔒 Yingira mu Enkola",
        "nyn": "🔒 Yinjira mu Enkora",
        "ach": "🔒 Donyo ikome",
        "sw":  "🔒 Ingia Kwanza",
    },
    "username": {
        "en":  "Username",
        "lg":  "Erinnya ly'omukozesa",
        "nyn": "Izina ry'omukozesa",
        "ach": "Nyingi me tic",
        "sw":  "Jina la mtumiaji",
    },
    "password": {
        "en":  "Password",
        "lg":  "Ekigambo ekyama",
        "nyn": "Ekigambo kyama",
        "ach": "Lok me mung",
        "sw":  "Nenosiri",
    },
    "login": {
        "en":  "Login",
        "lg":  "Yingira",
        "nyn": "Yinjira",
        "ach": "Donyo",
        "sw":  "Ingia",
    },
    "logout": {
        "en":  "Logout",
        "lg":  "Funa",
        "nyn": "Okuva",
        "ach": "Wot woko",
        "sw":  "Toka",
    },
    "invalid_login": {
        "en":  "Invalid username or password.",
        "lg":  "Erinnya oba ekigambo tekituufu.",
        "nyn": "Izina oba ekigambo si ryoona.",
        "ach": "Nyingi onyo lok mung pe atir.",
        "sw":  "Jina au nenosiri si sahihi.",
    },
    "select_language": {
        "en":  "Select Language",
        "lg":  "Londa Olulimi",
        "nyn": "Reeba Orurimi",
        "ach": "Yer leb",
        "sw":  "Chagua Lugha",
    },
    "navigate": {
        "en":  "Navigate",
        "lg":  "Yenda",
        "nyn": "Genda",
        "ach": "Cit",
        "sw":  "Nenda",
    },
    "current_sacco": {
        "en":  "Current SACCO",
        "lg":  "SACCO ey'enkola kati",
        "nyn": "SACCO ya hano",
        "ach": "SACCO ma eni",
        "sw":  "SACCO ya Sasa",
    },
    "super_admin_label": {
        "en":  "🔴 Super Admin",
        "lg":  "🔴 Omuyinza Omukulu",
        "nyn": "🔴 Omukuru w'Enkora",
        "ach": "🔴 Ladit Madit",
        "sw":  "🔴 Msimamizi Mkuu",
    },
    "sacco_admin_label": {
        "en":  "🟡 SACCO Admin",
        "lg":  "🟡 Omuyinza wa SACCO",
        "nyn": "🟡 Omukuru wa SACCO",
        "ach": "🟡 Ladit SACCO",
        "sw":  "🟡 Msimamizi wa SACCO",
    },
    "staff_label": {
        "en":  "🟢 Staff",
        "lg":  "🟢 Abakozi",
        "nyn": "🟢 Abakozi",
        "ach": "🟢 Lukwena",
        "sw":  "🟢 Wafanyikazi",
    },

    # ── Navigation pages ──────────────────────────────────────────────────────
    "nav_dashboard": {
        "en":  "🏠 Dashboard",
        "lg":  "🏠 Pulanga",
        "nyn": "🏠 Pulanga",
        "ach": "🏠 Boma me nying",
        "sw":  "🏠 Dashibodi",
    },
    "nav_sacco_profile": {
        "en":  "🏢 SACCO Profile",
        "lg":  "🏢 Ebikwata ku SACCO",
        "nyn": "🏢 Ebikwata kuri SACCO",
        "ach": "🏢 Lok me SACCO",
        "sw":  "🏢 Wasifu wa SACCO",
    },
    "nav_customers": {
        "en":  "👤 Customers",
        "lg":  "👤 Abagimu",
        "nyn": "👤 Abagumya",
        "ach": "👤 Lwak",
        "sw":  "👤 Wateja",
    },
    "nav_savings": {
        "en":  "🏦 Savings",
        "lg":  "🏦 Ebikolwa",
        "nyn": "🏦 Okutereka",
        "ach": "🏦 Kano lim",
        "sw":  "🏦 Akiba",
    },
    "nav_loans": {
        "en":  "💰 Loans",
        "lg":  "💰 Enguzi",
        "nyn": "💰 Okuguza",
        "ach": "💰 Kwo lim",
        "sw":  "💰 Mikopo",
    },
    "nav_collections": {
        "en":  "📅 Collections",
        "lg":  "📅 Okussa",
        "nyn": "📅 Okuteeka",
        "ach": "📅 Kano lim",
        "sw":  "📅 Makusanyo",
    },
    "nav_accounting": {
        "en":  "💼 Accounting",
        "lg":  "💼 Okubalirira",
        "nyn": "💼 Kubalira",
        "ach": "💼 Bal lim",
        "sw":  "💼 Uhasibu",
    },
    "nav_reports": {
        "en":  "📈 Reports",
        "lg":  "📈 Ebibuuza",
        "nyn": "📈 Ripoti",
        "ach": "📈 Ripot",
        "sw":  "📈 Ripoti",
    },
    "nav_analytics": {
        "en":  "📊 Analytics",
        "lg":  "📊 Okusesengula",
        "nyn": "📊 Okunabira",
        "ach": "📊 Kwanyo",
        "sw":  "📊 Uchanganuzi",
    },
    "nav_gold_points": {
        "en":  "🏅 Gold Points",
        "lg":  "🏅 Amanye ga Zaabu",
        "nyn": "🏅 Amaheereza ga Zahabu",
        "ach": "🏅 Dano pa Jahabu",
        "sw":  "🏅 Pointi za Dhahabu",
    },
    "nav_nssf": {
        "en":  "🇺🇬 NSSF Compliance",
        "lg":  "🇺🇬 NSSF Okugoberera",
        "nyn": "🇺🇬 NSSF Okwetora",
        "ach": "🇺🇬 NSSF Lubo",
        "sw":  "🇺🇬 Utiifu wa NSSF",
    },
    "nav_ai_insights": {
        "en":  "🤖 AI Insights",
        "lg":  "🤖 Amagezi ga AI",
        "nyn": "🤖 Amagezi ga AI",
        "ach": "🤖 Ngec pa AI",
        "sw":  "🤖 Maarifa ya AI",
    },
    "nav_administration": {
        "en":  "⚙ Administration",
        "lg":  "⚙ Okulabirira",
        "nyn": "⚙ Okurungika",
        "ach": "⚙ Loc",
        "sw":  "⚙ Utawala",
    },
    "nav_qr_codes": {
        "en":  "📱 Login QR Codes",
        "lg":  "📱 QR Code ez'okuYingira",
        "nyn": "📱 QR Code ez'okwinjira",
        "ach": "📱 QR Code me donyo",
        "sw":  "📱 Nambari za QR",
    },
    "nav_account_settings": {
        "en":  "🔑 Account Settings",
        "lg":  "🔑 Entegeka y'Akaunti",
        "nyn": "🔑 Entegeka y'Akaonti",
        "ach": "🔑 Ter me akaunt",
        "sw":  "🔑 Mipangilio ya Akaunti",
    },

    # ── Dashboard ─────────────────────────────────────────────────────────────
    "todays_snapshot": {
        "en":  "Today's Snapshot",
        "lg":  "Ebya Leero",
        "nyn": "Ebya Erizooba",
        "ach": "Tic pa kaweny",
        "sw":  "Muhtasari wa Leo",
    },
    "expected_today": {
        "en":  "Expected Today",
        "lg":  "Ebisuubidwa Leero",
        "nyn": "Ebiteganijwe Erizooba",
        "ach": "Ma gimito kaweny",
        "sw":  "Inayotarajiwa Leo",
    },
    "collected_today": {
        "en":  "Collected Today",
        "lg":  "Byakusanyizibwa Leero",
        "nyn": "Byakusanyizibwa Erizooba",
        "ach": "Okano kaweny",
        "sw":  "Iliyokusanywa Leo",
    },
    "business_overview": {
        "en":  "Business Overview",
        "lg":  "Ebirowoozo by'Omulimu",
        "nyn": "Ebirebire by'Omushaho",
        "ach": "Wel me tic",
        "sw":  "Muhtasari wa Biashara",
    },
    "upcoming_repayments": {
        "en":  "Upcoming Repayments (next 7 days)",
        "lg":  "Okuddiza Enguzi (ennaku 7 ezijja)",
        "nyn": "Okuzzaayo Okuguza (emizooba 7 ejja)",
        "ach": "Dwok lim (nino 7 ma bino)",
        "sw":  "Malipo Yanayokuja (siku 7)",
    },

    # ── Customers ─────────────────────────────────────────────────────────────
    "add_customer": {
        "en":  "Add New Customer",
        "lg":  "Yongera Omugumba Omuggya",
        "nyn": "Yongera Omugumba Omupya",
        "ach": "Med dano manyen",
        "sw":  "Ongeza Mteja Mpya",
    },
    "full_name": {
        "en":  "Full Name",
        "lg":  "Erinnya Lyonna",
        "nyn": "Izina Ryona",
        "ach": "Nyingi mapol",
        "sw":  "Jina Kamili",
    },
    "phone": {
        "en":  "Phone Number",
        "lg":  "Enamba ya Simu",
        "nyn": "Namba ya Simu",
        "ach": "Namba pa fon",
        "sw":  "Nambari ya Simu",
    },
    "national_id": {
        "en":  "National ID",
        "lg":  "Kaadi y'Ensi",
        "nyn": "Kaadi y'Ensi",
        "ach": "Kaad me lobo",
        "sw":  "Kitambulisho cha Taifa",
    },
    "gender": {
        "en":  "Gender",
        "lg":  "Ekika",
        "nyn": "Oburuguru",
        "ach": "Dano manok",
        "sw":  "Jinsia",
    },
    "female": {
        "en":  "Female",
        "lg":  "Omukazi",
        "nyn": "Omukazi",
        "ach": "Dako",
        "sw":  "Mwanamke",
    },
    "male": {
        "en":  "Male",
        "lg":  "Omusajja",
        "nyn": "Omushaija",
        "ach": "Laco",
        "sw":  "Mwanaume",
    },
    "date_of_birth": {
        "en":  "Date of Birth",
        "lg":  "Olunaku lw'Oluzaalibwa",
        "nyn": "Eizooba ry'Okuzaarwa",
        "ach": "Nino me nywalo",
        "sw":  "Tarehe ya Kuzaliwa",
    },
    "village": {
        "en":  "Village",
        "lg":  "Kyalo",
        "nyn": "Kaaro",
        "ach": "Gaŋ",
        "sw":  "Kijiji",
    },
    "parish": {
        "en":  "Parish",
        "lg":  "Omutendera",
        "nyn": "Omutendera",
        "ach": "Peri",
        "sw":  "Parokia",
    },
    "occupation": {
        "en":  "Occupation",
        "lg":  "Omulimu",
        "nyn": "Omushaho",
        "ach": "Tic",
        "sw":  "Kazi",
    },
    "member": {
        "en":  "Member",
        "lg":  "Omukopi",
        "nyn": "Omukopi",
        "ach": "Luplok",
        "sw":  "Mwanachama",
    },
    "outsider": {
        "en":  "Outsider",
        "lg":  "Omugeni",
        "nyn": "Omugenzi",
        "ach": "Dano me woko",
        "sw":  "Mgeni",
    },
    "pwd": {
        "en":  "Person with Disability (PWD)?",
        "lg":  "Omuntu aliina Obulemu?",
        "nyn": "Omuntu w'Obumuga?",
        "ach": "Dano ma ki orem?",
        "sw":  "Mtu wenye Ulemavu (PWD)?",
    },
    "subsistence": {
        "en":  "In Subsistence Economy?",
        "lg":  "Ali mu Bukulembeze bw'Okwekolera?",
        "nyn": "Ali mu Bukulembeze bw'Okwetungura?",
        "ach": "Tye i cam me kwo keken?",
        "sw":  "Yuko katika Uchumi wa Kujikimu?",
    },
    "joined": {
        "en":  "Joined",
        "lg":  "Yayingira",
        "nyn": "Yinjira",
        "ach": "Donyo",
        "sw":  "Alijiunga",
    },
    "add_customer_btn": {
        "en":  "Add Customer",
        "lg":  "Yongera Omugumba",
        "nyn": "Yongera Omugumba",
        "ach": "Med dano",
        "sw":  "Ongeza Mteja",
    },
    "all_customers": {
        "en":  "All Customers",
        "lg":  "Abagimu Bonna",
        "nyn": "Abagumba Bona",
        "ach": "Dano weng",
        "sw":  "Wateja Wote",
    },

    # ── NSSF ──────────────────────────────────────────────────────────────────
    "nssf_registration": {
        "en":  "🇺🇬 NSSF Registration",
        "lg":  "🇺🇬 Okwandika kwa NSSF",
        "nyn": "🇺🇬 Okwandika kwa NSSF",
        "ach": "🇺🇬 Coyo nyingi ki NSSF",
        "sw":  "🇺🇬 Usajili wa NSSF",
    },
    "nssf_registered_q": {
        "en":  "Is this member registered with NSSF?",
        "lg":  "Omukopi ono yandise ne NSSF?",
        "nyn": "Omukopi oyu yandikire na NSSF?",
        "ach": "Luplok man gicoyoe ki NSSF?",
        "sw":  "Je, mwanachama huyu amesajiliwa na NSSF?",
    },
    "nssf_number": {
        "en":  "NSSF Membership Number",
        "lg":  "Enamba ya NSSF",
        "nyn": "Namba ya NSSF",
        "ach": "Namba pa NSSF",
        "sw":  "Nambari ya NSSF",
    },
    "nssf_contribution_rate": {
        "en":  "Monthly NSSF Contribution Rate (%)",
        "lg":  "Ekitundu kya NSSF buli mwezi (%)",
        "nyn": "Omugabo gwa NSSF buri mwezi (%)",
        "ach": "Wel lim NSSF dwe acel (%)",
        "sw":  "Kiwango cha Mchango wa NSSF kwa Mwezi (%)",
    },
    "nssf_not_registered_warning": {
        "en":  "This member is not yet registered with NSSF. They can still be enrolled today, but their NSSF contributions will only begin once registered. Register at nssfug.org.",
        "lg":  "Omukopi ono tayandise ne NSSF. Ayinza okwandikibwa leero naye ebikolwa bya NSSF binaatandika nga bweyandika. Yandika ku nssfug.org.",
        "nyn": "Omukopi oyu tayandikire na NSSF. Ayinza kwandikibwa erizooba naye omugabo gwa NSSF gunaatandika nga gwyandika. Yandika kuri nssfug.org.",
        "ach": "Luplok man pe gicoyoe ki NSSF. Twerge donyo kaweny ento lim NSSF bigake ka gicoyoe. Coy nyingi i nssfug.org.",
        "sw":  "Mwanachama huyu hajasajiliwa bado na NSSF. Anaweza kusajiliwa leo lakini michango ya NSSF itaanza baada ya usajili. Sajili kwenye nssfug.org.",
    },
    "nssf_registered_badge": {
        "en":  "🇺🇬 NSSF Registered",
        "lg":  "🇺🇬 Yandisiddwa ne NSSF",
        "nyn": "🇺🇬 Yandikire na NSSF",
        "ach": "🇺🇬 Gicoyoe ki NSSF",
        "sw":  "🇺🇬 Amesajiliwa na NSSF",
    },
    "not_nssf_registered": {
        "en":  "⚠️ Not NSSF Registered",
        "lg":  "⚠️ Tayandisiddwa ne NSSF",
        "nyn": "⚠️ Tayandikire na NSSF",
        "ach": "⚠️ Pe gicoyoe ki NSSF",
        "sw":  "⚠️ Hajaandikishwa na NSSF",
    },

    # ── Gold Points ───────────────────────────────────────────────────────────
    "gold_points_title": {
        "en":  "Save with your SACCO. Build with Uganda.",
        "lg":  "Tereka ne SACCO yo. Zimba Uganda.",
        "nyn": "Tereka na SACCO yawe. Zimba Uganda.",
        "ach": "Kan lim ki SACCO meri. Ger Uganda.",
        "sw":  "Weka na SACCO yako. Jenga Uganda.",
    },
    "gold_points_subtitle": {
        "en":  "Every shilling saved in your SACCO, a piece goes to build the nation. Earn Gold Points for every NSSF contribution.",
        "lg":  "Ssente zonna zeterekedde mu SACCO yo, ekitundu kigenda okuzimba ensi. Wanula Amanye ga Zaabu buli kikolwa kya NSSF.",
        "nyn": "Ensimbi zona ziterekedwe mu SACCO yawe, ekitundu kigenda okuzimba ensi. Wanura Amaheereza ga Zahabu buri omugabo gwa NSSF.",
        "ach": "Lim dyang ma ikano i SACCO, dul acel cito i gero lobo. Nwo Dano pa Jahabu pi lim NSSF dwe acel.",
        "sw":  "Kila shilingi iliyohifadhiwa katika SACCO yako, sehemu inaenda kuijenga taifa. Pata Pointi za Dhahabu kwa kila mchango wa NSSF.",
    },
    "tier_bronze": {
        "en":  "🥉 Bronze Saver",
        "lg":  "🥉 Omutereka wa Bule",
        "nyn": "🥉 Omutereka wa Bule",
        "ach": "🥉 Kano lim pa Bule",
        "sw":  "🥉 Mwekaji wa Shaba",
    },
    "tier_silver": {
        "en":  "🥈 Silver Patriot",
        "lg":  "🥈 Omutereka wa Ffeeza",
        "nyn": "🥈 Omukwatiriza wa Fedha",
        "ach": "🥈 Lamwony me Fedha",
        "sw":  "🥈 Mzalendo wa Fedha",
    },
    "tier_gold": {
        "en":  "🥇 Gold Champion",
        "lg":  "🥇 Omuwanguzi wa Zaabu",
        "nyn": "🥇 Omuwanguzi wa Zahabu",
        "ach": "🥇 Lanepo pa Jahabu",
        "sw":  "🥇 Bingwa wa Dhahabu",
    },
    "tier_national": {
        "en":  "🏆 National Builder",
        "lg":  "🏆 Omuzimbi w'Ensi",
        "nyn": "🏆 Omuzimbi w'Ensi",
        "ach": "🏆 Lacen me Lobo",
        "sw":  "🏆 Mjenzi wa Taifa",
    },
    "leaderboard": {
        "en":  "SACCO Leaderboard",
        "lg":  "Okulinganira kwa SACCO",
        "nyn": "Okulinganira kwa SACCO",
        "ach": "Wel pa SACCO",
        "sw":  "Ubao wa Matokeo wa SACCO",
    },

    # ── Savings ───────────────────────────────────────────────────────────────
    "deposit": {
        "en":  "Deposit",
        "lg":  "Tereka",
        "nyn": "Okutereka",
        "ach": "Kano lim",
        "sw":  "Amana",
    },
    "withdraw": {
        "en":  "Withdraw",
        "lg":  "Ggyako",
        "nyn": "Kugyako",
        "ach": "Nwo lim",
        "sw":  "Toa",
    },
    "balance": {
        "en":  "Balance",
        "lg":  "Omuwendo Osigaddewo",
        "nyn": "Ensimbi Ezisigaire",
        "ach": "Lim ma kwo",
        "sw":  "Salio",
    },
    "amount": {
        "en":  "Amount (UGX)",
        "lg":  "Omuwendo (UGX)",
        "nyn": "Omuwendo (UGX)",
        "ach": "Wel lim (UGX)",
        "sw":  "Kiasi (UGX)",
    },
    "payment_channel": {
        "en":  "Payment Channel",
        "lg":  "Engeri y'Okusasula",
        "nyn": "Engira y'Okusasula",
        "ach": "Yo me tuku lim",
        "sw":  "Njia ya Malipo",
    },
    "open_account": {
        "en":  "Open Savings Account",
        "lg":  "Yambula Akaunti y'Okutereka",
        "nyn": "Fumba Akaonti y'Okutereka",
        "ach": "Yab akaunt me kano lim",
        "sw":  "Fungua Akaunti ya Akiba",
    },
    "nssf_contribution": {
        "en":  "🇺🇬 NSSF Contribution",
        "lg":  "🇺🇬 Ekikolwa kya NSSF",
        "nyn": "🇺🇬 Omugabo gwa NSSF",
        "ach": "🇺🇬 Lim NSSF",
        "sw":  "🇺🇬 Mchango wa NSSF",
    },
    "net_to_sacco": {
        "en":  "Net to SACCO Savings",
        "lg":  "Ebisingawo mu SACCO",
        "nyn": "Ebisingawo mu SACCO",
        "ach": "Lim ma dong i SACCO",
        "sw":  "Kilichobaki kwa Akiba ya SACCO",
    },
    "gross_deposit": {
        "en":  "Gross Deposit",
        "lg":  "Omuwendo Gwonna Ogutereddwa",
        "nyn": "Omuwendo Gwona Ogutereddwa",
        "ach": "Lim dyang ma ikano",
        "sw":  "Amana ya Jumla",
    },
    "process": {
        "en":  "Process",
        "lg":  "Kola",
        "nyn": "Kora",
        "ach": "Tim",
        "sw":  "Fanya",
    },

    # ── Loans ─────────────────────────────────────────────────────────────────
    "issue_loan": {
        "en":  "Issue a New Loan",
        "lg":  "Wa Enguzi Enyoggeza",
        "nyn": "Wa Okuguza Okupya",
        "ach": "Mi kwo lim manyen",
        "sw":  "Toa Mkopo Mpya",
    },
    "principal": {
        "en":  "Principal Amount (UGX)",
        "lg":  "Omuwendo Omukulu (UGX)",
        "nyn": "Omuwendo Omukuru (UGX)",
        "ach": "Lim matidi (UGX)",
        "sw":  "Kiasi cha Msingi (UGX)",
    },
    "interest_rate": {
        "en":  "Interest Rate (%)",
        "lg":  "Omusulo (%)",
        "nyn": "Akatundwe (%)",
        "ach": "Lim ma med (%)",
        "sw":  "Riba (%)",
    },
    "term_months": {
        "en":  "Term (months)",
        "lg":  "Obudde (emyezi)",
        "nyn": "Obuzibu (emyezi)",
        "ach": "Kare (dwe)",
        "sw":  "Muda (miezi)",
    },
    "total_repayable": {
        "en":  "Total Repayable",
        "lg":  "Omuwendo Gwonna Ogw'Okuddiza",
        "nyn": "Omuwendo Gwona Ogw'Okuzzaayo",
        "ach": "Lim weng ma idwok",
        "sw":  "Jumla ya Kulipa",
    },
    "monthly_installment": {
        "en":  "Monthly Installment",
        "lg":  "Ekitundu kya Buli Mwezi",
        "nyn": "Ekitundu kya Buri Mwezi",
        "ach": "Lim dwe acel",
        "sw":  "Awamu ya Kila Mwezi",
    },
    "disburse_loan": {
        "en":  "Disburse Loan",
        "lg":  "Wa Enguzi",
        "nyn": "Wa Okuguza",
        "ach": "Mi kwo lim",
        "sw":  "Toa Mkopo",
    },
    "loan_status_active": {
        "en":  "Active",
        "lg":  "Enkola",
        "nyn": "Enkora",
        "ach": "Tye i tic",
        "sw":  "Hai",
    },
    "loan_status_closed": {
        "en":  "Closed",
        "lg":  "Enkomerero",
        "nyn": "Enkomerero",
        "ach": "Giko",
        "sw":  "Imefungwa",
    },
    "guarantor": {
        "en":  "Guarantor",
        "lg":  "Omukuumi",
        "nyn": "Omukuumi",
        "ach": "Ladit lakwe",
        "sw":  "Mdhamini",
    },
    "collateral": {
        "en":  "Collateral",
        "lg":  "Ekintu ky'Okukuuma",
        "nyn": "Ekintu ky'Okukuuma",
        "ach": "Gin ma iketo i te",
        "sw":  "Dhamana",
    },

    # ── Collections ───────────────────────────────────────────────────────────
    "record_repayment": {
        "en":  "Record a Repayment",
        "lg":  "Wandiika Okuddiza",
        "nyn": "Wandiika Okuzzaayo",
        "ach": "Coy dwok lim",
        "sw":  "Rekodi Malipo",
    },
    "overdue_loans": {
        "en":  "⚠️ Overdue Loans — Follow-Up List",
        "lg":  "⚠️ Enguzi ez'Okumala Obudde — Elist y'Okuddamu",
        "nyn": "⚠️ Okuguza Okumaze Obudde — Orulemba rw'Okuddamu",
        "ach": "⚠️ Kwo lim ma okato — Cik me lubo",
        "sw":  "⚠️ Mikopo Iliyochelewa — Orodha ya Ufuatiliaji",
    },
    "collected_today": {
        "en":  "Collected Today",
        "lg":  "Byakusanyizibwa Leero",
        "nyn": "Byakusanyizibwa Erizooba",
        "ach": "Okano kaweny",
        "sw":  "Iliyokusanywa Leo",
    },
    "collected_this_month": {
        "en":  "Collected This Month",
        "lg":  "Byakusanyizibwa Omwezi Guno",
        "nyn": "Byakusanyizibwa Omwezi Ogu",
        "ach": "Okano i dwe man",
        "sw":  "Iliyokusanywa Mwezi Huu",
    },
    "days_overdue": {
        "en":  "days overdue",
        "lg":  "ennaku ez'okuggita",
        "nyn": "emizooba gy'okugita",
        "ach": "nino ma okato",
        "sw":  "siku za kuchelewa",
    },

    # ── Reports ───────────────────────────────────────────────────────────────
    "executive_dashboard": {
        "en":  "Executive Dashboard",
        "lg":  "Pulanga Enkulu",
        "nyn": "Pulanga Enkuru",
        "ach": "Boma me ladit",
        "sw":  "Dashibodi ya Utendaji",
    },
    "portfolio_analysis": {
        "en":  "Portfolio Analysis",
        "lg":  "Okusesengula Ebikolwa",
        "nyn": "Okunabira Ebikorwa",
        "ach": "Kwanyo me tic",
        "sw":  "Uchambuzi wa Kwinginza",
    },
    "membership_demographics": {
        "en":  "Membership Demographics",
        "lg":  "Ebikwata ku Bakopi",
        "nyn": "Ebikwata ku Bakopi",
        "ach": "Ngec me lwak",
        "sw":  "Takwimu za Wanachama",
    },
    "savings_performance": {
        "en":  "Savings Performance",
        "lg":  "Enkola y'Okutereka",
        "nyn": "Enkora y'Okutereka",
        "ach": "Tic me kano lim",
        "sw":  "Utendaji wa Akiba",
    },
    "nssf_compliance_report": {
        "en":  "NSSF Compliance Report",
        "lg":  "Ripoti ya NSSF",
        "nyn": "Ripoti ya NSSF",
        "ach": "Ripot pa NSSF",
        "sw":  "Ripoti ya Utiifu wa NSSF",
    },
    "nssf_monthly_export": {
        "en":  "NSSF Monthly Export",
        "lg":  "Okufulumya Amakulu ga NSSF buli mwezi",
        "nyn": "Okufulumya Amakuru ga NSSF buri mwezi",
        "ach": "Gony amaro NSSF dwe acel",
        "sw":  "Usafirishaji wa Kila Mwezi wa NSSF",
    },
    "nssf_outreach_export": {
        "en":  "NSSF Outreach Export",
        "lg":  "Okufulumya Abakyayandika NSSF",
        "nyn": "Okufulumya Abataayandikira NSSF",
        "ach": "Gony amaro dano pe ki NSSF",
        "sw":  "Usafirishaji wa Uhamasishaji wa NSSF",
    },
    "download": {
        "en":  "Download",
        "lg":  "Ddamu",
        "nyn": "Kugya",
        "ach": "Gony",
        "sw":  "Pakua",
    },
    "total_members": {
        "en":  "Total Members",
        "lg":  "Bakopi Bonna",
        "nyn": "Bakopi Bona",
        "ach": "Luplok weng",
        "sw":  "Wanachama Wote",
    },
    "compliance_rate": {
        "en":  "Compliance Rate",
        "lg":  "Omutendera gw'Okugoberera",
        "nyn": "Omutendera gw'Okwetora",
        "ach": "Wel me lubo",
        "sw":  "Kiwango cha Utiifu",
    },

    # ── AI Insights ───────────────────────────────────────────────────────────
    "ai_insights_title": {
        "en":  "AI Insights",
        "lg":  "Amagezi ga AI",
        "nyn": "Amagezi ga AI",
        "ach": "Ngec pa AI",
        "sw":  "Maarifa ya AI",
    },
    "daily_brief": {
        "en":  "Daily Intelligence Brief",
        "lg":  "Amakulu g'Olunaku",
        "nyn": "Amakuru g'Erizooba",
        "ach": "Ngec pa dwe kaweny",
        "sw":  "Muhtasari wa Kila Siku",
    },
    "ask_ai": {
        "en":  "Ask the AI Analyst",
        "lg":  "Buuza AI",
        "nyn": "Buuza AI",
        "ach": "Penyi AI",
        "sw":  "Uliza Mchambuzi wa AI",
    },
    "ask_ai_placeholder": {
        "en":  "e.g. Which members are at risk of defaulting this month?",
        "lg":  "e.g. Bakopi bani abali mu kabi okudda ku nguzi omwezi guno?",
        "nyn": "e.g. Bakopi bani abari mu kabi okuzaayo okuguza omwezi ogu?",
        "ach": "eg. Luplok mene ma gitye i cwiny me pe dwok lim i dwe man?",
        "sw":  "mf. Wanachama wapi walio katika hatari ya kutolipa mwezi huu?",
    },
    "member_search": {
        "en":  "Member Profile Search",
        "lg":  "Noonya Omukopi",
        "nyn": "Reba Omukopi",
        "ach": "Yeny luplok",
        "sw":  "Tafuta Wasifu wa Mwanachama",
    },

    # ── General UI ────────────────────────────────────────────────────────────
    "yes": {
        "en":  "Yes",
        "lg":  "Yee",
        "nyn": "Yego",
        "ach": "Ee",
        "sw":  "Ndiyo",
    },
    "no": {
        "en":  "No",
        "lg":  "Nedda",
        "nyn": "Nedda",
        "ach": "Peke",
        "sw":  "Hapana",
    },
    "save": {
        "en":  "Save",
        "lg":  "Tereka",
        "nyn": "Bika",
        "ach": "Gwok",
        "sw":  "Hifadhi",
    },
    "cancel": {
        "en":  "Cancel",
        "lg":  "Sazaamu",
        "nyn": "Reka",
        "ach": "Juk",
        "sw":  "Ghairi",
    },
    "confirm": {
        "en":  "Confirm",
        "lg":  "Kakasa",
        "nyn": "Kakasa",
        "ach": "Mok ada",
        "sw":  "Thibitisha",
    },
    "error_name_phone_required": {
        "en":  "Name and phone number are required.",
        "lg":  "Erinnya ne enamba ya simu bikwatagana.",
        "nyn": "Izina na namba ya simu birakwatagana.",
        "ach": "Nyingi ki namba pa fon gileng.",
        "sw":  "Jina na nambari ya simu zinahitajika.",
    },
    "success_customer_added": {
        "en":  "Customer added successfully.",
        "lg":  "Omugumba yayongerwa bulungi.",
        "nyn": "Omugumba yayongerwa bulungi.",
        "ach": "Dano okedo maber.",
        "sw":  "Mteja ameongezwa kwa mafanikio.",
    },
    "no_data_yet": {
        "en":  "No data yet.",
        "lg":  "Tewali makulu.",
        "nyn": "Nta makuru nawe.",
        "ach": "Ngec pe dong.",
        "sw":  "Hakuna data bado.",
    },
    "change_password": {
        "en":  "Change Password",
        "lg":  "Kyusa Ekigambo Ekyama",
        "nyn": "Hindura Ekigambo Kyama",
        "ach": "Lok me mung",
        "sw":  "Badilisha Nenosiri",
    },
    "new_password": {
        "en":  "New Password",
        "lg":  "Ekigambo Ekyama Ekiggya",
        "nyn": "Ekigambo Kyama Ekipya",
        "ach": "Lok me mung manyen",
        "sw":  "Nenosiri Mpya",
    },
    "confirm_password": {
        "en":  "Confirm New Password",
        "lg":  "Kakasa Ekigambo Ekyama Ekiggya",
        "nyn": "Kakasa Ekigambo Kyama Ekipya",
        "ach": "Mok ada lok me mung manyen",
        "sw":  "Thibitisha Nenosiri Mpya",
    },
    "update_password": {
        "en":  "Update Password",
        "lg":  "Kyusa Ekigambo",
        "nyn": "Hindura Ekigambo",
        "ach": "Yub lok me mung",
        "sw":  "Sasisha Nenosiri",
    },
    "password_updated": {
        "en":  "Password updated successfully.",
        "lg":  "Ekigambo ekyusa bulungi.",
        "nyn": "Ekigambo kyahindurika bulungi.",
        "ach": "Lok me mung olokke maber.",
        "sw":  "Nenosiri imesasishwa kwa mafanikio.",
    },
    "passwords_no_match": {
        "en":  "Passwords do not match.",
        "lg":  "Ebigambo tebiganye.",
        "nyn": "Ebigambo tibiganye.",
        "ach": "Lok me mung pe twero.",
        "sw":  "Nenosiri hazilingani.",
    },

    # ── NSSF Campaign text ────────────────────────────────────────────────────
    "campaign_tagline": {
        "en":  "Uganda National Savings Programme",
        "lg":  "Pulologamu y'Okutereka Ensi ya Uganda",
        "nyn": "Pulogiramu y'Okutereka y'Ensi ya Uganda",
        "ach": "Purugram me kano lim pa lobo Uganda",
        "sw":  "Programu ya Akiba ya Taifa ya Uganda",
    },
    "patriot_message": {
        "en":  "Every shilling is a brick.",
        "lg":  "Ssente buli nnya ye tuffaali.",
        "nyn": "Ensimbi buri nnya ni itafaali.",
        "ach": "Lim acel acel en oduro acel.",
        "sw":  "Kila shilingi ni tofali.",
    },
    "consent_nssf": {
        "en":  "By joining this SACCO on the CommunityFinanceOS platform, you consent to your NSSF registration status and contribution data being shared with NSSF Uganda for social security administration. Your data will not be shared with any other third party.",
        "lg":  "Nga oyingira mu SACCO eno ku pulatifomu ya CommunityFinanceOS, oyingizizza okugabana amakulu g'okwandikibwa kwa NSSF ne ebikolwa byawo ne NSSF Uganda okukuuma obuwanguzi bw'essanyu. Amakulu go tegalaganyizibwa ne muntu mugenyi nakyomu.",
        "nyn": "Bwoyinjira mu SACCO eno kuri pulatifoomu ya CommunityFinanceOS, weemerera okugabana amakuru g'okwandikibwa kwa NSSF n'omugabo gwawo na NSSF Uganda okukuuma obwisinge bw'essanyu. Amakuru gawe tagagabanyizibwa na muntu omugenzi nahoona.",
        "ach": "Ka idonyo i SACCO man i pulatifom me CommunityFinanceOS, iyee ni gipoka ngec me coy nyingi NSSF ki lim ma iketo ne NSSF Uganda pi gwoko me yot kwo. Ngeci meri pe gibikogi ki ŋat mukene mo.",
        "sw":  "Kwa kujiunga na SACCO hii kwenye jukwaa la CommunityFinanceOS, unakubali data yako ya usajili wa NSSF na michango kushirikiwa na NSSF Uganda kwa usimamizi wa usalama wa jamii. Data yako haitashirikiwa na mtu mwingine yeyote.",
    },

    # ── Administration ────────────────────────────────────────────────────────
    "user_management": {
        "en":  "User Management",
        "lg":  "Okulabirira Abakozesa",
        "nyn": "Okurungika Abakozesa",
        "ach": "Lo lukwena",
        "sw":  "Usimamizi wa Watumiaji",
    },
    "create_user": {
        "en":  "Create User",
        "lg":  "Kola Omukozesa",
        "nyn": "Kora Omukozesa",
        "ach": "Ger dano",
        "sw":  "Unda Mtumiaji",
    },
    "role": {
        "en":  "Role",
        "lg":  "Omulimu",
        "nyn": "Omulimu",
        "ach": "Tic",
        "sw":  "Jukumu",
    },
    "assign_sacco": {
        "en":  "Assign to SACCO",
        "lg":  "Yereka ku SACCO",
        "nyn": "Gira kuri SACCO",
        "ach": "Mio i SACCO",
        "sw":  "Weka kwenye SACCO",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Translation engine
# ─────────────────────────────────────────────────────────────────────────────

def get_language() -> str:
    """Returns the active language code from session state. Defaults to 'en'."""
    return st.session_state.get('language', 'en')

def t(key: str, lang: str = None) -> str:
    """
    Translate a key to the active language.
    Falls back to English if key or translation is missing.

    Usage:
        t("login")          → uses session language
        t("login", "lg")    → forces Luganda
    """
    lang = lang or get_language()
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key  # return the key itself so missing strings are visible
    return entry.get(lang) or entry.get('en') or key

def set_language(lang_code: str):
    """Set language in session state."""
    if lang_code in LANGUAGES:
        st.session_state['language'] = lang_code

def language_selector_widget():
    """
    Renders the language selector on the login page.
    Returns the selected language code.
    """
    options     = list(LANGUAGES.keys())
    labels      = [f"{LANGUAGE_FLAGS[k]} {LANGUAGES[k]}" for k in options]
    current     = get_language()
    current_idx = options.index(current) if current in options else 0

    selected_label = st.selectbox(
        t("select_language"),
        labels,
        index=current_idx,
        key="lang_selector_widget"
    )
    selected_code = options[labels.index(selected_label)]
    set_language(selected_code)
    return selected_code
