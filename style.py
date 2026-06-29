"""
style.py  —  SaccoOS Visual Layer
Drop this next to app.py and add two lines to app.py:

    from style import apply_styles
    apply_styles()          # call once, right after st.set_page_config()

Palette
-------
  Navy   #0B3D91  —  authority, trust
  Jade   #00A86B  —  prosperity, active
  Amber  #E8A020  —  at-risk loans
  Red    #D32F2F  —  overdue / critical
  Slate  #F0F4F8  —  app background
"""

import streamlit as st


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        /* ── Fonts ─────────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* ── App shell ──────────────────────────────────────────── */
        .stApp {
            background: #F0F4F8;
        }

        /* Hide default Streamlit chrome BUT keep the mobile header menu button */
        #MainMenu, footer { visibility: hidden; }
        [data-testid="stHeaderActionElements"] { visibility: hidden; }
        header { background: transparent !important; }

        /* ── Sidebar ────────────────────────────────────────────── */
        [data-testid="stSidebar"] {
            background: #0B3D91 !important;
            border-right: none !important;
        }
        [data-testid="stSidebar"] * {
            color: #D6E4FF !important;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #FFFFFF !important;
        }
        /* Sidebar nav radio pills */
        [data-testid="stSidebar"] .stRadio > div {
            gap: 4px;
        }
        [data-testid="stSidebar"] .stRadio label {
            background: rgba(255, 255, 255, 0.07);
            border-radius: 8px;
            padding: 10px 14px !important;
            transition: background 0.15s ease;
            cursor: pointer;
            font-weight: 500 !important;
        }
        [data-testid="stSidebar"] .stRadio label:hover {
            background: rgba(255, 255, 255, 0.15);
        }
        [data-testid="stSidebar"] .stSelectbox label {
            color: #93B4E0 !important;
            font-size: 11px !important;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }

        /* ── Typography ─────────────────────────────────────────── */
        h1 {
            color: #0B3D91 !important;
            font-size: 26px !important;
            font-weight: 700 !important;
            letter-spacing: -0.4px;
            line-height: 1.2;
        }
        h2 {
            color: #1A1A2E !important;
            font-size: 20px !important;
            font-weight: 600 !important;
        }
        h3 {
            color: #2C3E50 !important;
            font-size: 16px !important;
            font-weight: 600 !important;
        }

        /* ── KPI / Metric cards ─────────────────────────────────── */
        [data-testid="stMetric"] {
            background: #FFFFFF;
            border-radius: 12px;
            padding: 20px 22px !important;
            box-shadow: 0 2px 8px rgba(11, 61, 145, 0.08);
            border-left: 4px solid #00A86B;
        }
        [data-testid="stMetric"] label {
            font-size: 11px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.9px !important;
            color: #6B7A8D !important;
        }
        [data-testid="stMetricValue"] {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 26px !important;
            font-weight: 700 !important;
            color: #0B3D91 !important;
        }
        [data-testid="stMetricDelta"] {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
            font-weight: 500 !important;
        }

        /* ── Buttons ────────────────────────────────────────────── */
        .stButton > button {
            background: linear-gradient(135deg, #00A86B, #007A4D) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 22px !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            letter-spacing: 0.2px !important;
            transition: all 0.18s ease !important;
            box-shadow: 0 2px 8px rgba(0, 168, 107, 0.30) !important;
        }
        .stButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 14px rgba(0, 168, 107, 0.40) !important;
        }
        .stButton > button:active {
            transform: translateY(0) !important;
        }
        /* Secondary / outline variant */
        .stButton > button[kind="secondary"] {
            background: transparent !important;
            color: #0B3D91 !important;
            border: 2px solid #0B3D91 !important;
            box-shadow: none !important;
        }
        .stButton > button[kind="secondary"]:hover {
            background: #EEF3FB !important;
        }

        /* ── Form inputs ────────────────────────────────────────── */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stTextArea > div > div > textarea {
            border-radius: 8px !important;
            border: 1.5px solid #D0DCE8 !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 14px !important;
            transition: border-color 0.15s, box-shadow 0.15s !important;
        }
        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: #00A86B !important;
            box-shadow: 0 0 0 3px rgba(0, 168, 107, 0.12) !important;
        }
        .stSelectbox > div > div {
            border-radius: 8px !important;
            border: 1.5px solid #D0DCE8 !important;
        }
        .stSelectbox > div > div:focus-within {
            border-color: #00A86B !important;
            box-shadow: 0 0 0 3px rgba(0, 168, 107, 0.12) !important;
        }

        /* ── DataFrames / Tables ────────────────────────────────── */
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 2px 8px rgba(11, 61, 145, 0.08) !important;
        }

        /* ── Expanders ──────────────────────────────────────────── */
        [data-testid="stExpander"] {
            background: #FFFFFF;
            border-radius: 10px;
            border: 1.5px solid #E0E8F0 !important;
            box-shadow: 0 1px 4px rgba(11, 61, 145, 0.06);
        }

        /* ── Alert / toast messages ─────────────────────────────── */
        [data-testid="stAlert"] {
            border-radius: 10px !important;
        }

        /* ── Tabs ───────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            border-bottom: 2px solid #E0E8F0;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0 !important;
            padding: 8px 18px !important;
            font-weight: 500 !important;
        }
        .stTabs [aria-selected="true"] {
            color: #0B3D91 !important;
            font-weight: 700 !important;
            border-bottom: 3px solid #00A86B !important;
        }

        /* ── Divider ────────────────────────────────────────────── */
        hr {
            border: none;
            border-top: 1.5px solid #E0E8F0;
            margin: 24px 0;
        }

        /* ── Utility classes (use via st.markdown) ──────────────── */

        /* Status badges */
        .badge {
            display: inline-block;
            padding: 3px 11px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            font-family: 'Inter', sans-serif;
        }
        .badge-current  { background: #D1FAE5; color: #065F46; }
        .badge-atrisk   { background: #FEF3C7; color: #92400E; }
        .badge-overdue  { background: #FEE2E2; color: #991B1B; }
        .badge-settled  { background: #EDE9FE; color: #4C1D95; }

        /* White card surface */
        .sacco-card {
            background: #FFFFFF;
            border-radius: 14px;
            padding: 24px 28px;
            margin-bottom: 18px;
            box-shadow: 0 2px 10px rgba(11, 61, 145, 0.09);
            border-top: 3px solid #00A86B;
        }

        /* Red-accent card for critical alerts */
        .sacco-card-alert {
            background: #FFFFFF;
            border-radius: 14px;
            padding: 24px 28px;
            margin-bottom: 18px;
            box-shadow: 0 2px 10px rgba(211, 47, 47, 0.10);
            border-top: 3px solid #D32F2F;
        }

        /* Amber-accent card for at-risk items */
        .sacco-card-warn {
            background: #FFFFFF;
            border-radius: 14px;
            padding: 24px 28px;
            margin-bottom: 18px;
            box-shadow: 0 2px 10px rgba(232, 160, 32, 0.10);
            border-top: 3px solid #E8A020;
        }

        /* Monospace number spans */
        .mono {
            font-family: 'JetBrains Mono', monospace;
            font-size: 15px;
            font-weight: 500;
        }

        /* Page header bar */
        .page-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding-bottom: 18px;
            border-bottom: 2px solid #E0E8F0;
            margin-bottom: 28px;
        }
        .page-header h1 { margin: 0 !important; padding: 0 !important; }

        /* Section label */
        .section-label {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #6B7A8D;
            margin-bottom: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
