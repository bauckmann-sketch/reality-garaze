"""Main Streamlit application entry point."""

import streamlit as st
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

st.set_page_config(
    page_title="Realitní Tracker | Sreality",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Block search engine indexing
st.markdown('<meta name="robots" content="noindex, nofollow">', unsafe_allow_html=True)

# Custom CSS — GarageLedger premium light theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@200;400;600;800;900&family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: #f7f9ff;
    }

    /* Sidebar — clean light panel */
    [data-testid="stSidebar"] {
        background: #edf4ff;
        border-right: 1px solid #d8eaff;
    }
    [data-testid="stSidebar"] * {
        color: #001d32 !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: #43474d !important;
        font-weight: 500;
        font-family: 'Manrope', sans-serif;
        padding: 0.5rem 0.75rem;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: #d8eaff;
        color: #00152a !important;
    }
    [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
        font-family: 'Manrope', sans-serif;
        font-weight: 600;
    }

    /* Cards */
    .metric-card {
        background: #ffffff;
        padding: 1.5rem 1.8rem;
        border-radius: 16px;
        border: 1px solid #e3efff;
        box-shadow: 0 1px 3px rgba(0, 21, 42, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, #85f8c4, #006c4a);
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0, 21, 42, 0.08);
    }

    /* Tables */
    .stDataFrame {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid #e3efff;
    }

    /* Headers — Manrope */
    h1, h2, h3 {
        font-family: 'Manrope', sans-serif !important;
        font-weight: 800 !important;
        color: #00152a !important;
        letter-spacing: -0.02em !important;
    }
    h1 {
        font-size: 2.2rem !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #edf4ff;
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-family: 'Manrope', sans-serif;
        font-weight: 600;
        color: #43474d;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: #d8eaff;
        color: #00152a;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: #ffffff !important;
        color: #00152a !important;
        box-shadow: 0 1px 3px rgba(0, 21, 42, 0.08);
    }

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        font-family: 'Manrope', sans-serif;
        letter-spacing: -0.01em;
        transition: all 0.2s ease;
        border: 1px solid #e3efff;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(0, 21, 42, 0.1);
    }
    .stButton > button[kind="primary"] {
        background: #00152a !important;
        color: #ffffff !important;
        border-color: #00152a !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #102a43 !important;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Status badges */
    .badge-active {
        background: rgba(0, 108, 74, 0.1);
        color: #006c4a;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
    }
    .badge-inactive {
        background: rgba(186, 26, 26, 0.1);
        color: #ba1a1a;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
    }
    .badge-price-down {
        background: rgba(0, 108, 74, 0.1);
        color: #006c4a;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-price-up {
        background: rgba(186, 26, 26, 0.1);
        color: #ba1a1a;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* Selectbox and inputs */
    .stSelectbox [data-baseweb="select"] {
        border-radius: 10px;
        border-color: #d8eaff;
    }
    .stTextInput input {
        border-radius: 10px;
        border-color: #d8eaff;
    }

    /* Slider */
    .stSlider [data-baseweb="slider"] [role="slider"] {
        background: #00152a;
    }

    /* Expander */
    .streamlit-expanderHeader {
        font-family: 'Manrope', sans-serif;
        font-weight: 600;
        color: #00152a;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #edf4ff;
    }
    ::-webkit-scrollbar-thumb {
        background: #c3c6ce;
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #74777e;
    }

    /* Info/Warning/Error boxes */
    .stAlert {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
from src.dashboard.components.filters import sidebar_info
sidebar_info()

# Navigation
page = st.sidebar.radio(
    "Navigace",
    options=[
        "📋 Přehled inzerátů",
        "📈 Cenové grafy",
        "⚙️ Nastavení",
    ],
    label_visibility="collapsed",
)

# Page routing
if page == "📋 Přehled inzerátů":
    from src.dashboard.views.page_prehled import render
    render()
elif page == "📈 Cenové grafy":
    from src.dashboard.views.page_ceny import render
    render()
elif page == "⚙️ Nastavení":
    from src.dashboard.views.page_nastaveni import render
    render()
