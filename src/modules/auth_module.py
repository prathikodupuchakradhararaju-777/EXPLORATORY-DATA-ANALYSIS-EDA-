import streamlit as st
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from database import verify_user, create_user
except ImportError:
    from src.database import verify_user, create_user


def inject_auth_styles():
    """
    Inject custom CSS styles for the enterprise authentication interface.
    """
    st.markdown("""
        <style>
        .auth-container {
            max-width: 500px;
            margin: 40px auto;
            padding: 35px 30px;
            background: #1E293B;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
            border: 1px solid #334155;
            color: #F8FAFC;
        }
        .auth-header {
            text-align: center;
            margin-bottom: 25px;
        }
        .auth-title {
            font-size: 26px;
            font-weight: 800;
            background: linear-gradient(135deg, #38BDF8 0%, #2563EB 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 6px;
        }
        .auth-subtitle {
            font-size: 13px;
            color: #94A3B8;
            font-weight: 500;
        }
        .demo-badge-container {
            background-color: #0F172A;
            border-radius: 10px;
            padding: 12px 16px;
            margin-top: 15px;
            border-left: 4px solid #2563EB;
        }
        .demo-title {
            font-size: 12px;
            font-weight: 700;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .user-role-badge-admin {
            background-color: rgba(239, 68, 68, 0.2);
            color: #FCA5A5;
            border: 1px solid rgba(239, 68, 68, 0.4);
            padding: 3px 10px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 12px;
        }
        .user-role-badge-engineer {
            background-color: rgba(37, 99, 235, 0.2);
            color: #93C5FD;
            border: 1px solid rgba(37, 99, 235, 0.4);
            padding: 3px 10px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 12px;
        }
        .user-role-badge-operator {
            background-color: rgba(34, 197, 94, 0.2);
            color: #86EFAC;
            border: 1px solid rgba(34, 197, 94, 0.4);
            padding: 3px 10px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 12px;
        }
        </style>
    """, unsafe_allow_html=True)


def render_login_page():
    """
    Renders the centered Login & User Registration interface.
    """
    inject_auth_styles()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div class="auth-header">
                <div style="font-size: 52px; margin-bottom: 10px;">🤖</div>
                <div class="auth-title">Agentic FacilityOps AI Platform</div>
                <div class="auth-subtitle">AI-Powered Intelligent Facility Monitoring, Preventive Maintenance & Work Order Management</div>
            </div>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🔐 Sign In", "📝 Register User"])

        # -------------------------------------------------------------
        # TAB 1: LOGIN FORM
        # -------------------------------------------------------------
        with tab1:
            st.markdown("##### Sign In to Your Enterprise Account")
            
            login_username = st.text_input("Username", key="login_username_input", placeholder="Enter username (e.g., admin)")
            login_password = st.text_input("Password", type="password", key="login_password_input", placeholder="Enter password")
            
            col_submit, col_clear = st.columns([2, 1])
            with col_submit:
                if st.button("🔑 Log In", use_container_width=True, type="primary"):
                    if not login_username or not login_password:
                        st.error("Please provide both username and password.")
                    else:
                        user_info = verify_user(login_username, login_password)
                        if user_info:
                            st.session_state["authenticated"] = True
                            st.session_state["user_info"] = user_info
                            st.success(f"Welcome back, {user_info['full_name']}!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password. Please check your credentials.")

            # -------------------------------------------------------------
            # QUICK DEMO LOGIN BUTTONS
            # -------------------------------------------------------------
            st.markdown("---")
            st.markdown("""
                <div class="demo-title">⚡ Quick Demo Login (Click to Sign In Immediately):</div>
            """, unsafe_allow_html=True)

            d_col1, d_col2, d_col3 = st.columns(3)
            with d_col1:
                if st.button("🛡️ Admin", use_container_width=True, help="Login as System Administrator"):
                    user_info = verify_user("admin", "admin123")
                    if user_info:
                        st.session_state["authenticated"] = True
                        st.session_state["user_info"] = user_info
                        st.rerun()
            with d_col2:
                if st.button("🔧 Engineer", use_container_width=True, help="Login as Lead Maintenance Engineer"):
                    user_info = verify_user("engineer", "eng123")
                    if user_info:
                        st.session_state["authenticated"] = True
                        st.session_state["user_info"] = user_info
                        st.rerun()
            with d_col3:
                if st.button("👷 Operator", use_container_width=True, help="Login as Plant Operator"):
                    user_info = verify_user("operator", "op123")
                    if user_info:
                        st.session_state["authenticated"] = True
                        st.session_state["user_info"] = user_info
                        st.rerun()

            st.caption("ℹ️ Demo Credentials: **admin** / `admin123` | **engineer** / `eng123` | **operator** / `op123`")

        # -------------------------------------------------------------
        # TAB 2: SIGN UP / REGISTER FORM
        # -------------------------------------------------------------
        with tab2:
            st.markdown("##### Create a New Account")
            reg_username = st.text_input("Username", key="reg_username_input", placeholder="e.g. jdoe")
            reg_fullname = st.text_input("Full Name", key="reg_fullname_input", placeholder="e.g. John Doe")
            reg_password = st.text_input("Password", type="password", key="reg_password_input", placeholder="Minimum 4 characters")
            reg_role = st.selectbox("Role", ["Operator", "Engineer", "Admin"], key="reg_role_select")

            if st.button("✨ Create Account", use_container_width=True):
                res = create_user(reg_username, reg_password, reg_fullname, reg_role)
                if res["success"]:
                    st.success(res["message"])
                else:
                    st.error(res["message"])


def render_logout_sidebar():
    """
    Renders user details and the Logout button in the header/sidebar interface.
    """
    user = st.session_state.get("user_info", {})
    if not user:
        user = {"username": "User", "full_name": "Authenticated User", "role": "Operator"}

    role_class = "user-role-badge-operator"
    role_name = user.get("role", "Operator")
    if role_name == "Admin":
        role_class = "user-role-badge-admin"
    elif role_name == "Engineer":
        role_class = "user-role-badge-engineer"

    st.sidebar.markdown(f"""
        <div style="background-color: #1E293B; padding: 12px 14px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #334155;">
            <div style="font-size: 11px; text-transform: uppercase; color: #94A3B8; font-weight: 700; margin-bottom: 4px;">Logged in User</div>
            <div style="font-size: 15px; font-weight: 700; color: #F8FAFC;">👤 {user.get('full_name')}</div>
            <div style="margin-top: 6px; display: flex; align-items: center; justify-content: space-between;">
                <span style="font-size: 12px; color: #94A3B8;">@{user.get('username')}</span>
                <span class="{role_class}">{role_name}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Log Out", use_container_width=True, type="secondary"):
        st.session_state["authenticated"] = False
        st.session_state["user_info"] = None
        st.rerun()
