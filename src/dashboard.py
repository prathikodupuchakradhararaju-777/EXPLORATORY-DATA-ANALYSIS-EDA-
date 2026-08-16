import streamlit as st
import pandas as pd
import os
import sys

# Ensure src directory is in Python module search path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from database import init_db
from modules.eda_module import render_eda_page
from modules.dashboard_module import render_dashboard_page
from modules.machine_explorer_module import render_machine_explorer_page
from modules.work_orders_module import render_work_orders_page
from modules.preventive_module import render_preventive_module_page
from modules.auth_module import render_login_page, render_logout_sidebar

# -------------------------------------------------------------
# Page Configuration (Executed before DB init or UI calls)
# -------------------------------------------------------------
st.set_page_config(
    page_title="🤖 Agentic FacilityOps AI Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# Initialize SQLite Database & Schema (Cached once per process)
# -------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def initialize_database_once():
    init_db()

initialize_database_once()

# -------------------------------------------------------------
# Inject Enterprise Dark Theme & Global CSS
# -------------------------------------------------------------
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        /* Global Body & Theme Variables */
        :root {
            --bg-dark: #0F172A;
            --card-dark: #1E293B;
            --border-dark: #334155;
            --primary-blue: #2563EB;
            --accent-green: #22C55E;
            --accent-orange: #F59E0B;
            --accent-red: #EF4444;
            --accent-purple: #8B5CF6;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background-color: var(--bg-dark) !important;
            color: var(--text-main) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        /* Hide Streamlit default top header bar decoration */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
        }
        
        /* Sidebar dark styling */
        [data-testid="stSidebar"] {
            background-color: #0B1120 !important;
            border-right: 1px solid var(--border-dark) !important;
        }

        /* Custom Enterprise Top Header */
        .enterprise-header-container {
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            border: 1px solid var(--border-dark);
            border-radius: 16px;
            padding: 20px 24px;
            margin-bottom: 20px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .enterprise-title {
            font-family: 'Poppins', sans-serif;
            font-size: 26px;
            font-weight: 800;
            background: linear-gradient(135deg, #60A5FA 0%, #2563EB 50%, #8B5CF6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            letter-spacing: -0.5px;
        }
        .enterprise-subtitle {
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 4px;
            font-weight: 500;
        }

        /* Top Horizontal Nav Styling */
        div[data-testid="stHorizontalBlock"] .stRadio > div {
            display: flex;
            flex-direction: row;
            gap: 10px;
            background: #1E293B;
            padding: 8px;
            border-radius: 14px;
            border: 1px solid var(--border-dark);
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        }

        /* Segmented control button styling */
        div[data-baseweb="segmented-control"] {
            background-color: #1E293B !important;
            border: 1px solid var(--border-dark) !important;
            border-radius: 14px !important;
            padding: 6px !important;
            width: 100% !important;
        }

        div[data-baseweb="segmented-control"] button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            color: #94A3B8 !important;
            transition: all 0.25s ease !important;
            padding: 10px 16px !important;
        }

        div[data-baseweb="segmented-control"] button[aria-selected="true"] {
            background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
            color: #FFFFFF !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4) !important;
        }

        /* Enterprise KPI Cards */
        .kpi-card-box {
            background: linear-gradient(135deg, #1E293B 0%, #111827 100%);
            border-radius: 14px;
            padding: 16px 18px;
            border: 1px solid var(--border-dark);
            border-left: 5px solid var(--primary-blue);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
            margin-bottom: 14px;
            transition: transform 0.25s ease, box-shadow 0.25s ease;
        }
        .kpi-card-box:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(37, 99, 235, 0.25);
        }
        .kpi-card-total { border-left-color: #2563EB; }
        .kpi-card-active { border-left-color: #22C55E; }
        .kpi-card-pending { border-left-color: #F59E0B; }
        .kpi-card-in-progress { border-left-color: #38BDF8; }
        .kpi-card-completed { border-left-color: #22C55E; }
        .kpi-card-critical { border-left-color: #EF4444; }
        .kpi-card-severity { border-left-color: #F97316; }
        .kpi-card-due-today { border-left-color: #8B5CF6; }
        .kpi-card-overdue { border-left-color: #DC2626; }

        .kpi-val {
            font-size: 26px;
            font-weight: 800;
            margin-top: 6px;
            margin-bottom: 2px;
            color: #F8FAFC;
            letter-spacing: -0.5px;
        }
        .kpi-lbl {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: #94A3B8;
            font-weight: 700;
        }
        .kpi-trend {
            font-size: 11px;
            font-weight: 600;
            margin-top: 4px;
            color: #38BDF8;
        }

        /* Modern Badges */
        .badge-pending {
            background-color: rgba(245, 158, 11, 0.2);
            color: #FBBF24;
            border: 1px solid rgba(245, 158, 11, 0.4);
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 12px;
        }
        .badge-in-progress {
            background-color: rgba(56, 189, 248, 0.2);
            color: #38BDF8;
            border: 1px solid rgba(56, 189, 248, 0.4);
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 12px;
        }
        .badge-completed {
            background-color: rgba(34, 197, 94, 0.2);
            color: #4ADE80;
            border: 1px solid rgba(34, 197, 94, 0.4);
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 12px;
        }
        .badge-critical {
            background-color: rgba(239, 68, 68, 0.2);
            color: #FCA5A5;
            border: 1px solid rgba(239, 68, 68, 0.4);
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 12px;
        }
        .badge-cancelled {
            background-color: rgba(148, 163, 184, 0.2);
            color: #CBD5E1;
            border: 1px solid rgba(148, 163, 184, 0.4);
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 12px;
        }

        /* Buttons & Controls styling */
        .stButton > button {
            border-radius: 12px !important;
            font-weight: 600 !important;
            padding: 8px 18px !important;
            transition: all 0.25s ease !important;
            border: 1px solid var(--border-dark) !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
            color: #FFFFFF !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3) !important;
            border: none !important;
        }
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4) !important;
        }

        /* Data Editor & Tables */
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
            background-color: #1E293B !important;
            border: 1px solid var(--border-dark) !important;
            border-radius: 12px !important;
        }

        /* Footer styling */
        .enterprise-footer {
            margin-top: 50px;
            padding: 20px 0;
            border-top: 1px solid var(--border-dark);
            text-align: center;
            color: var(--text-muted);
            font-size: 13px;
        }
        .enterprise-footer strong {
            color: #F8FAFC;
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Load Telemetry Dataset
# -------------------------------------------------------------
DATA_PATH = os.path.join(BASE_DIR, "data", "ai4i2020.csv")

@st.cache_data
def load_data():
    if os.path.exists(DATA_PATH):
        return pd.read_csv(DATA_PATH)
    elif os.path.exists("data/ai4i2020.csv"):
        return pd.read_csv("data/ai4i2020.csv")
    else:
        return pd.read_csv("../data/ai4i2020.csv")

df = load_data()

# -------------------------------------------------------------
# User Authentication Check (Login Guard)
# -------------------------------------------------------------
if not st.session_state.get("authenticated", False):
    render_login_page()
    st.stop()

# -------------------------------------------------------------
# Enterprise Main Header Banner
# -------------------------------------------------------------
user = st.session_state.get("user_info", {})
user_name = user.get("full_name", "Administrator")
user_role = user.get("role", "Admin")

header_col1, header_col2 = st.columns([4, 1])

with header_col1:
    st.markdown("""
        <div class="enterprise-header-container">
            <div>
                <h1 class="enterprise-title">🤖 Agentic FacilityOps AI Platform</h1>
                <div class="enterprise-subtitle">AI-Powered Intelligent Facility Monitoring, Preventive Maintenance & Work Order Management</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

with header_col2:
    render_logout_sidebar()

# -------------------------------------------------------------
# Horizontal Top Navigation Bar
# -------------------------------------------------------------
st.markdown("##### 🧭 Navigation Hub")

nav_options = [
    "📊 EDA",
    "📈 Dashboard",
    "⚙️ Machine Explorer",
    "📋 Work Orders",
    "🛠️ Preventive Maintenance"
]

if "active_nav_tab" not in st.session_state:
    st.session_state["active_nav_tab"] = "📊 EDA"

# Backward compatibility if active tab was set to old name
if st.session_state.get("active_nav_tab") == "🤖 Predictive Maintenance":
    st.session_state["active_nav_tab"] = "🛠️ Preventive Maintenance"

selected_tab = st.segmented_control(
    "Select Navigation Module",
    options=nav_options,
    default=st.session_state["active_nav_tab"],
    key="top_nav_segmented_control",
    label_visibility="collapsed"
)

if selected_tab:
    st.session_state["active_nav_tab"] = selected_tab

active_tab = st.session_state.get("active_nav_tab", "📊 EDA")

st.divider()

# -------------------------------------------------------------
# Page Router
# -------------------------------------------------------------
if active_tab == "📊 EDA":
    render_eda_page(df)
elif active_tab == "📈 Dashboard":
    render_dashboard_page(df)
elif active_tab == "⚙️ Machine Explorer":
    render_machine_explorer_page(df)
elif active_tab == "📋 Work Orders":
    render_work_orders_page()
elif active_tab == "🛠️ Preventive Maintenance":
    render_preventive_module_page(df)

# -------------------------------------------------------------
# Enterprise Footer
# -------------------------------------------------------------
st.markdown("""
    <div class="enterprise-footer">
        <div><strong>© 2026 Agentic FacilityOps AI Platform</strong> | Autonomous Industrial Intelligence</div>
        <div style="margin-top: 6px; font-size: 12px; color: #64748B;">
            Powered by: <strong>Streamlit</strong> • <strong>Plotly Enterprise</strong> • <strong>Machine Learning</strong> • <strong>Ollama AI Agents</strong>
        </div>
    </div>
""", unsafe_allow_html=True)