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

# Custom CSS for premium dark theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid #E0E0E0;
    }
    [data-testid="stSidebar"] * {
        color: #1A1A2E !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: #333 !important;
        font-weight: 500;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: #F0F2F6;
        border-radius: 8px;
    }

    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #1A1D23, #22252D);
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        border: 1px solid #2A2D35;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(108, 99, 255, 0.15);
    }

    /* Tables */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }

    /* Headers */
    h1, h2, h3 {
        font-weight: 600 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(108, 99, 255, 0.3);
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Status badges */
    .badge-active {
        background: rgba(67, 233, 123, 0.15);
        color: #43E97B;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .badge-inactive {
        background: rgba(255, 101, 132, 0.15);
        color: #FF6584;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .badge-price-down {
        background: rgba(67, 233, 123, 0.15);
        color: #43E97B;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
    }
    .badge-price-up {
        background: rgba(255, 101, 132, 0.15);
        color: #FF6584;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
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
