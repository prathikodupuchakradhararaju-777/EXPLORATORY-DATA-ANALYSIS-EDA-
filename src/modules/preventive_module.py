import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional

try:
    from database import (
        fetch_all_preventive_schedules,
        insert_preventive_schedule,
        update_preventive_schedule,
        update_preventive_schedule_status,
        delete_preventive_schedule,
        has_open_work_order,
        insert_work_order
    )
    from work_orders import generate_work_order_id
    from ollama_service import generate_machine_analysis, is_ollama_available
except ImportError:
    from src.database import (
        fetch_all_preventive_schedules,
        insert_preventive_schedule,
        update_preventive_schedule,
        update_preventive_schedule_status,
        delete_preventive_schedule,
        has_open_work_order,
        insert_work_order
    )
    from src.work_orders import generate_work_order_id
    from src.ollama_service import generate_machine_analysis, is_ollama_available

# Color scheme & Plotly layout
DARK_LAYOUT = dict(
    paper_bgcolor="#1E293B",
    plot_bgcolor="#0F172A",
    font=dict(color="#F8FAFC", family="Inter, sans-serif"),
    xaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
    yaxis=dict(gridcolor="#334155", zerolinecolor="#334155")
)

# Stable Plotly rendering configuration to prevent hover/resize modebar jitter
PLOTLY_CONFIG = {
    "displayModeBar": False,
    "responsive": True
}

GREEN_PALETTE = ["#22C55E", "#10B981", "#34D399", "#059669", "#047857", "#A7F3D0"]

TECHNICIANS_LIST = ["Sarah Connor", "John Doe", "David Smith", "Michael Scott", "Emily Vance", "Alex Rivera"]
FREQUENCIES_LIST = ["Daily", "Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly"]
MAINTENANCE_TYPES_LIST = [
    "Bearing Inspection & Lubrication",
    "Tool Replacement & Calibration",
    "Coolant System & Thermal Service",
    "Electrical & Control Panel Check",
    "Vibration Sensor Diagnostics",
    "Hydraulic Fluid & Filter Replacement",
    "Annual Comprehensive Overhaul",
    "Routine Preventive Inspection"
]


def render_preventive_module_page(df: pd.DataFrame):
    """
    Module 4: Preventive Maintenance Management System
    Features:
    - Performance KPI Metrics Cards
    - 1. Create Maintenance Schedule
    - 2. View Existing Schedules & Calendar Timeline
    - 3. Update Maintenance Schedule
    - 4. Delete Maintenance Schedule
    - AI Preventive Recommendations & Reports
    - Plotly Interactive Analytics
    """
    st.markdown("""
        <style>
            .pm-header-box {
                background: linear-gradient(135deg, #1E293B 0%, #064E3B 100%);
                border: 1px solid #10B981;
                border-radius: 16px;
                padding: 20px 24px;
                margin-bottom: 20px;
                box-shadow: 0 8px 24px rgba(16, 185, 129, 0.2);
            }
            .pm-header-title {
                font-family: 'Poppins', sans-serif;
                font-size: 26px;
                font-weight: 800;
                color: #4ADE80;
                margin: 0;
            }
            .pm-header-subtitle {
                color: #9CA3AF;
                font-size: 13px;
                margin-top: 4px;
            }
            .pm-kpi-card {
                background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
                border-radius: 14px;
                padding: 16px 18px;
                border: 1px solid #334155;
                border-left: 5px solid #22C55E;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
                margin-bottom: 14px;
            }
            .pm-kpi-card-overdue { border-left-color: #EF4444; }
            .pm-kpi-card-completed { border-left-color: #10B981; }
            .pm-kpi-card-pending { border-left-color: #F59E0B; }
            .pm-kpi-card-rate { border-left-color: #3B82F6; }
            .pm-kpi-val {
                font-size: 26px;
                font-weight: 800;
                color: #F8FAFC;
                margin-top: 4px;
            }
            .pm-kpi-lbl {
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.8px;
                color: #94A3B8;
                font-weight: 700;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="pm-header-box">
            <h1 class="pm-header-title">🛠️ Module 4: Preventive Maintenance Management System</h1>
            <div class="pm-header-subtitle">
                Scheduled asset care, technician calendar, schedule creation/updating/deletion, and SQLite database persistence.
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Fetch Preventive Maintenance Schedules from SQLite
    pm_df = fetch_all_preventive_schedules()

    if pm_df.empty:
        st.info("No preventive maintenance schedules found in database. Initializing sample schedule database...")
        st.rerun()

    # Dynamic status update helper for overdue items (Optimized for once-per-session execution)
    if "pm_overdue_synced" not in st.session_state:
        today_str = date.today().strftime("%Y-%m-%d")
        for idx, row in pm_df.iterrows():
            if row['status'] not in ['Completed', 'Overdue'] and str(row['next_due_date']) < today_str:
                update_preventive_schedule_status(row['schedule_id'], 'Overdue')
        st.session_state["pm_overdue_synced"] = True
        pm_df = fetch_all_preventive_schedules()

    # -------------------------------------------------------------
    # PREVENTIVE MAINTENANCE DASHBOARD (KPI CARDS)
    # -------------------------------------------------------------
    st.subheader("📊 Preventive Maintenance Performance Metrics")

    total_schedules = len(pm_df)
    completed_count = len(pm_df[pm_df['status'] == 'Completed'])
    pending_count = len(pm_df[pm_df['status'].isin(['Scheduled', 'In Progress', 'Pending'])])
    overdue_count = len(pm_df[pm_df['status'] == 'Overdue'])
    completion_rate = round((completed_count / total_schedules * 100), 1) if total_schedules > 0 else 0.0

    # Calculate average interval (in days) between service frequencies
    freq_days_map = {"Daily": 1, "Weekly": 7, "Monthly": 30, "Quarterly": 90, "Half-Yearly": 180, "Yearly": 365}
    avg_interval = round(pm_df['frequency'].map(freq_days_map).mean(), 1) if not pm_df.empty else 7.0

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

    kpi1.markdown(f"""
        <div class="pm-kpi-card">
            <div class="pm-kpi-lbl">📋 Total Scheduled</div>
            <div class="pm-kpi-val">{total_schedules}</div>
        </div>
    """, unsafe_allow_html=True)

    kpi2.markdown(f"""
        <div class="pm-kpi-card pm-kpi-card-completed">
            <div class="pm-kpi-lbl">✅ Completed</div>
            <div class="pm-kpi-val">{completed_count}</div>
        </div>
    """, unsafe_allow_html=True)

    kpi3.markdown(f"""
        <div class="pm-kpi-card pm-kpi-card-pending">
            <div class="pm-kpi-lbl">⏳ Pending / In Prog</div>
            <div class="pm-kpi-val">{pending_count}</div>
        </div>
    """, unsafe_allow_html=True)

    kpi4.markdown(f"""
        <div class="pm-kpi-card pm-kpi-card-overdue">
            <div class="pm-kpi-lbl">⚠️ Overdue</div>
            <div class="pm-kpi-val">{overdue_count}</div>
        </div>
    """, unsafe_allow_html=True)

    kpi5.markdown(f"""
        <div class="pm-kpi-card pm-kpi-card-rate">
            <div class="pm-kpi-lbl">📈 Completion Rate</div>
            <div class="pm-kpi-val">{completion_rate}%</div>
        </div>
    """, unsafe_allow_html=True)

    kpi6.markdown(f"""
        <div class="pm-kpi-card">
            <div class="pm-kpi-lbl">⏱️ Avg Interval</div>
            <div class="pm-kpi-val">{avg_interval} <span style="font-size:12px;color:#94A3B8;">Days</span></div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Available machine IDs list for dropdowns
    available_machine_ids = df['Product ID'].unique().tolist() if df is not None and not df.empty and 'Product ID' in df.columns else ["M14860", "L47181", "H29415", "M15210", "L48320"]

    # -------------------------------------------------------------
    # MODULE SUB-TABS NAVIGATION (EXPECTED MODULE FLOW)
    # -------------------------------------------------------------
    tab_create, tab_directory, tab_update, tab_delete, tab_ai, tab_charts = st.tabs([
        "➕ Create Schedule",
        "📋 View Existing Schedules",
        "✏️ Update Schedule",
        "🗑️ Delete Schedule",
        "🤖 AI Recommendations",
        "📈 Analytics"
    ])

    # -------------------------------------------------------------
    # 1. CREATE MAINTENANCE SCHEDULE
    # -------------------------------------------------------------
    with tab_create:
        st.subheader("➕ Create New Maintenance Schedule")
        st.write("Configure automated routine servicing schedules for facility machinery.")

        with st.form("create_preventive_schedule_form"):
            s_col1, s_col2 = st.columns(2)

            with s_col1:
                sch_machine_id = st.selectbox("Machine ID", options=available_machine_ids, index=0)
                sch_machine_name = st.text_input("Machine Name / Description", value=f"Industrial Machine {sch_machine_id}")
                sch_type = st.selectbox("Maintenance Type", options=MAINTENANCE_TYPES_LIST, index=0)
                sch_freq = st.selectbox("Maintenance Frequency", options=FREQUENCIES_LIST, index=1)
                sch_priority = st.selectbox("Priority Level", options=["Critical", "High", "Medium", "Low"], index=2)

            with s_col2:
                sch_tech = st.selectbox("Assigned Technician", options=TECHNICIANS_LIST, index=0)
                sch_start_date = st.date_input("Start Date", value=date.today())

                default_delta = {"Daily": 1, "Weekly": 7, "Monthly": 30, "Quarterly": 90, "Half-Yearly": 180, "Yearly": 365}.get(sch_freq, 7)
                sch_due_date = st.date_input("Next Due Date", value=date.today() + timedelta(days=default_delta))

                sch_duration = st.selectbox("Estimated Duration", options=["0.5 hours", "1.0 hour", "2.0 hours", "3.0 hours", "4.0 hours", "8.0 hours"], index=2)
                sch_status = st.selectbox("Initial Status", options=["Scheduled", "In Progress", "Completed"], index=0)

            sch_notes = st.text_area("Maintenance Scope & Remarks", value="Inspect key mechanical components, measure operating vibration, and verify thermal limits.")

            submit_sch_btn = st.form_submit_button("✅ Create Preventive Maintenance Schedule", type="primary", use_container_width=True)

            if submit_sch_btn:
                if not sch_machine_id or not sch_type:
                    st.error("⚠️ Machine ID and Maintenance Type are required fields.")
                elif sch_due_date < sch_start_date:
                    st.error("⚠️ Next Due Date cannot be before Start Date.")
                else:
                    schedule_id = f"PM-{datetime.now().strftime('%Y%m')}-{len(pm_df)+1:03d}"
                    new_sch_data = {
                        "schedule_id": schedule_id,
                        "machine_id": sch_machine_id,
                        "machine_name": sch_machine_name,
                        "maintenance_type": sch_type,
                        "frequency": sch_freq,
                        "technician": sch_tech,
                        "start_date": sch_start_date.strftime("%Y-%m-%d"),
                        "next_due_date": sch_due_date.strftime("%Y-%m-%d"),
                        "last_service_date": sch_start_date.strftime("%Y-%m-%d"),
                        "priority": sch_priority,
                        "status": sch_status,
                        "estimated_duration": sch_duration,
                        "created_date": date.today().strftime("%Y-%m-%d"),
                        "notes": sch_notes
                    }

                    if insert_preventive_schedule(new_sch_data):
                        st.success(f"🎉 Preventive Maintenance Schedule **{schedule_id}** successfully created and saved to SQLite database!")
                        st.rerun()
                    else:
                        st.error("Failed to insert schedule record into SQLite database.")

    # -------------------------------------------------------------
    # 2. VIEW EXISTING SCHEDULES & CALENDAR
    # -------------------------------------------------------------
    with tab_directory:
        st.subheader("📋 View Existing Maintenance Schedules")
        st.write("Browse, search, and manage existing maintenance schedules stored in the database.")

        # Filters
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            freq_filter = st.selectbox("Filter by Frequency", options=["All"] + FREQUENCIES_LIST, index=0, key="pm_freq_filter_selectbox")
        with f_col2:
            status_filter = st.selectbox("Filter by Status", options=["All", "Scheduled", "In Progress", "Overdue", "Completed"], index=0, key="pm_status_filter_selectbox")
        with f_col3:
            tech_filter = st.selectbox("Filter by Technician", options=["All"] + TECHNICIANS_LIST, index=0, key="pm_tech_filter_selectbox")
        with f_col4:
            search_query = st.text_input("Search Machine / ID", value="", placeholder="e.g. M14860", key="pm_search_query_textinput")

        # Apply filters
        filtered_df = pm_df.copy()
        if freq_filter != "All":
            filtered_df = filtered_df[filtered_df['frequency'] == freq_filter]
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['status'] == status_filter]
        if tech_filter != "All":
            filtered_df = filtered_df[filtered_df['technician'] == tech_filter]
        if search_query.strip():
            sq = search_query.strip().lower()
            filtered_df = filtered_df[
                filtered_df['machine_id'].astype(str).str.lower().str.contains(sq) |
                filtered_df['machine_name'].astype(str).str.lower().str.contains(sq) |
                filtered_df['maintenance_type'].astype(str).str.lower().str.contains(sq)
            ]

        # Render Main Data Table
        st.dataframe(
            filtered_df[[
                'schedule_id', 'machine_id', 'machine_name', 'maintenance_type',
                'frequency', 'technician', 'last_service_date', 'next_due_date',
                'priority', 'status'
            ]],
            column_config={
                "schedule_id": st.column_config.TextColumn("Schedule ID", width="small"),
                "machine_id": st.column_config.TextColumn("Machine ID", width="small"),
                "machine_name": st.column_config.TextColumn("Machine Name", width="medium"),
                "maintenance_type": st.column_config.TextColumn("Maintenance Type", width="medium"),
                "frequency": st.column_config.TextColumn("Frequency", width="small"),
                "technician": st.column_config.TextColumn("Technician", width="small"),
                "last_service_date": st.column_config.DateColumn("Last Serviced", width="small"),
                "next_due_date": st.column_config.DateColumn("Next Due Date", width="small"),
                "priority": st.column_config.TextColumn("Priority", width="small"),
                "status": st.column_config.TextColumn("Status", width="small"),
            },
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # Work Order Generation & Quick Actions
        st.subheader("⚡ Quick Actions & Work Order Integration")
        sel_schedule_id = st.selectbox(
            "Select Schedule for Quick Actions",
            options=filtered_df['schedule_id'].tolist() if not filtered_df.empty else [],
            key="pm_sel_schedule_id_view"
        )

        if sel_schedule_id:
            row_data = pm_df[pm_df['schedule_id'] == sel_schedule_id].iloc[0]
            act_col1, act_col2, act_col3 = st.columns(3)

            with act_col1:
                st.markdown(f"**Target Machine**: `{row_data['machine_id']}` ({row_data['machine_name']})")
                st.markdown(f"**Type**: `{row_data['maintenance_type']}` | **Tech**: `{row_data['technician']}`")

            with act_col2:
                new_st = st.selectbox("Update Schedule Status", options=["Scheduled", "In Progress", "Completed", "Overdue"], index=["Scheduled", "In Progress", "Completed", "Overdue"].index(row_data['status']) if row_data['status'] in ["Scheduled", "In Progress", "Completed", "Overdue"] else 0, key="update_st_select_dir")
                if st.button("💾 Update Status in SQLite", use_container_width=True, key="save_st_dir_btn"):
                    if update_preventive_schedule_status(sel_schedule_id, new_st):
                        st.success(f"Status for {sel_schedule_id} updated to **{new_st}**!")
                        st.rerun()

            with act_col3:
                if st.button("⚡ Generate Work Order from Schedule", type="primary", use_container_width=True, key="gen_wo_from_pm_btn"):
                    m_id = str(row_data['machine_id'])
                    wo_id = generate_work_order_id()
                    now_dt = datetime.now()

                    wo_data = {
                        "work_order_id": wo_id,
                        "machine_id": m_id,
                        "machine_type": m_id[0] if len(m_id) > 0 and m_id[0].isalpha() else "M",
                        "failure_prediction": "Preventive Service",
                        "failure_type": row_data['maintenance_type'],
                        "severity": row_data['priority'],
                        "maintenance_action": f"Scheduled Preventive Maintenance: {row_data['maintenance_type']} ({row_data['frequency']})",
                        "assigned_to": row_data['technician'],
                        "status": "Pending",
                        "priority": row_data['priority'],
                        "created_at": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "due_date": row_data['next_due_date'],
                        "completed_at": None,
                        "ai_summary": f"Preventive Maintenance Work Order generated for {row_data['machine_name']} ({m_id}). Task: {row_data['maintenance_type']}. Notes: {row_data['notes']}"
                    }

                    if insert_work_order(wo_data):
                        st.success(f"✅ Work Order **{wo_id}** created successfully in SQLite database!")
                    else:
                        st.error("Failed to insert generated Work Order into SQLite database.")

    # -------------------------------------------------------------
    # 3. UPDATE MAINTENANCE SCHEDULE
    # -------------------------------------------------------------
    with tab_update:
        st.subheader("✏️ Update Maintenance Schedule")
        st.write("Select an existing maintenance schedule to edit its parameters and save changes to SQLite.")

        if pm_df.empty:
            st.warning("No schedules available to update.")
        else:
            up_schedule_id = st.selectbox(
                "Select Maintenance Schedule ID to Edit",
                options=pm_df['schedule_id'].tolist(),
                key="update_schedule_id_selector"
            )

            if up_schedule_id:
                up_row = pm_df[pm_df['schedule_id'] == up_schedule_id].iloc[0]

                # Parse existing next_due_date safely
                try:
                    curr_due_date = datetime.strptime(str(up_row['next_due_date']), "%Y-%m-%d").date()
                except Exception:
                    curr_due_date = date.today()

                with st.form(f"edit_schedule_form_{up_schedule_id}"):
                    u_col1, u_col2 = st.columns(2)

                    with u_col1:
                        # 1. Machine ID
                        curr_m_id = str(up_row['machine_id'])
                        m_id_idx = available_machine_ids.index(curr_m_id) if curr_m_id in available_machine_ids else 0
                        up_machine_id = st.selectbox("Machine ID", options=available_machine_ids, index=m_id_idx)

                        # 2. Machine Name / Type
                        up_machine_name = st.text_input("Machine Name / Details", value=str(up_row.get('machine_name', curr_m_id)))

                        # 3. Maintenance Type
                        curr_m_type = str(up_row['maintenance_type'])
                        m_type_idx = MAINTENANCE_TYPES_LIST.index(curr_m_type) if curr_m_type in MAINTENANCE_TYPES_LIST else 0
                        up_maintenance_type = st.selectbox("Maintenance Type", options=MAINTENANCE_TYPES_LIST, index=m_type_idx)

                        # Frequency
                        curr_freq = str(up_row.get('frequency', 'Weekly'))
                        freq_idx = FREQUENCIES_LIST.index(curr_freq) if curr_freq in FREQUENCIES_LIST else 1
                        up_frequency = st.selectbox("Frequency", options=FREQUENCIES_LIST, index=freq_idx)

                    with u_col2:
                        # 4. Maintenance Date (Next Due Date)
                        up_next_due_date = st.date_input("Maintenance Date (Next Due Date)", value=curr_due_date)

                        # 5. Priority
                        curr_prio = str(up_row.get('priority', 'Medium'))
                        prio_opts = ["Critical", "High", "Medium", "Low"]
                        prio_idx = prio_opts.index(curr_prio) if curr_prio in prio_opts else 2
                        up_priority = st.selectbox("Priority Level", options=prio_opts, index=prio_idx)

                        # 6. Assigned Technician
                        curr_tech = str(up_row.get('technician', 'Sarah Connor'))
                        tech_idx = TECHNICIANS_LIST.index(curr_tech) if curr_tech in TECHNICIANS_LIST else 0
                        up_technician = st.selectbox("Assigned Technician", options=TECHNICIANS_LIST, index=tech_idx)

                        # Status
                        curr_stat = str(up_row.get('status', 'Scheduled'))
                        stat_opts = ["Scheduled", "In Progress", "Completed", "Overdue"]
                        stat_idx = stat_opts.index(curr_stat) if curr_stat in stat_opts else 0
                        up_status = st.selectbox("Schedule Status", options=stat_opts, index=stat_idx)

                    # 7. Remarks / Notes
                    up_notes = st.text_area("Remarks / Maintenance Scope Notes", value=str(up_row.get('notes', '')))

                    save_update_btn = st.form_submit_button("💾 Save Schedule Updates to SQLite", type="primary", use_container_width=True)

                    if save_update_btn:
                        if not str(up_machine_id).strip():
                            st.error("⚠️ Machine ID cannot be empty.")
                        elif not str(up_maintenance_type).strip():
                            st.error("⚠️ Maintenance Type cannot be empty.")
                        else:
                            update_payload = {
                                "machine_id": up_machine_id,
                                "machine_name": up_machine_name,
                                "maintenance_type": up_maintenance_type,
                                "frequency": up_frequency,
                                "technician": up_technician,
                                "next_due_date": up_next_due_date.strftime("%Y-%m-%d"),
                                "priority": up_priority,
                                "status": up_status,
                                "notes": up_notes
                            }

                            if update_preventive_schedule(up_schedule_id, update_payload):
                                st.success(f"✅ Maintenance Schedule **{up_schedule_id}** updated successfully in SQLite database!")
                                st.rerun()
                            else:
                                st.error(f"Failed to update schedule {up_schedule_id} in SQLite database.")

    # -------------------------------------------------------------
    # 4. DELETE MAINTENANCE SCHEDULE
    # -------------------------------------------------------------
    with tab_delete:
        st.subheader("🗑️ Delete Maintenance Schedule")
        st.write("Select a maintenance schedule record to permanently remove from SQLite database.")

        if pm_df.empty:
            st.warning("No schedules available to delete.")
        else:
            del_schedule_id = st.selectbox(
                "Select Schedule ID to Delete",
                options=pm_df['schedule_id'].tolist(),
                key="delete_schedule_id_selector"
            )

            if del_schedule_id:
                del_row = pm_df[pm_df['schedule_id'] == del_schedule_id].iloc[0]

                st.markdown(f"""
                    <div style="background-color: #1E293B; padding: 18px 22px; border-radius: 12px; border: 1px solid #EF4444; margin-bottom: 20px;">
                        <div style="font-size: 16px; font-weight: 700; color: #FCA5A5; margin-bottom: 8px;">
                            ⚠️ Are you sure you want to delete this maintenance schedule?
                        </div>
                        <div style="font-size: 13px; color: #CBD5E1; line-height: 1.6;">
                            • <b>Schedule ID:</b> <code>{del_schedule_id}</code><br/>
                            • <b>Target Machine:</b> <code>{del_row['machine_id']}</code> ({del_row['machine_name']})<br/>
                            • <b>Maintenance Task:</b> {del_row['maintenance_type']} ({del_row['frequency']})<br/>
                            • <b>Assigned Technician:</b> {del_row['technician']}<br/>
                            • <b>Next Due Date:</b> {del_row['next_due_date']}<br/>
                            • <b>Current Status:</b> {del_row['status']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                d_btn_col1, d_btn_col2 = st.columns(2)
                with d_btn_col1:
                    if st.button("🗑️ Yes, Delete Schedule", type="primary", use_container_width=True, key="confirm_del_btn"):
                        if delete_preventive_schedule(del_schedule_id):
                            st.success(f"✅ Maintenance Schedule **{del_schedule_id}** deleted successfully from SQLite database!")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete schedule {del_schedule_id} from SQLite database.")

                with d_btn_col2:
                    if st.button("❌ Cancel", use_container_width=True, key="cancel_del_btn"):
                        st.info("Schedule deletion cancelled.")

    # -------------------------------------------------------------
    # AI PREVENTIVE RECOMMENDATIONS
    # -------------------------------------------------------------
    with tab_ai:
        st.subheader("🤖 AI Preventive Maintenance Recommendations")
        st.write("Automated AI recommendations based on equipment telemetry and service history.")

        ai_rec_col1, ai_rec_col2 = st.columns([1, 1])

        with ai_rec_col1:
            st.markdown("#### 💡 System Recommendations")
            st.markdown("""
                - 🔧 **Spindle & Bearing**: *Service drive bearing within the next 7 days to prevent micro-vibration wear.*
                - 💧 **Lubrication**: *Replace synthetic gear lubricant this week for high-load CNC machines.*
                - 📊 **Vibration Monitoring**: *Inspect vibration amplitude levels on Lathe L4 during peak RPM operations.*
                - ❄️ **Cooling Circuit**: *Check thermal cooling pressure & flush heat exchanger filters.*
                - 🛠️ **Tool Wear**: *Perform preventive replacement of worn cutting tools exceeding 180 operating minutes.*
                - 🔍 **General Audit**: *Conduct quarterly preventive sensor calibration across all heavy-duty presses.*
            """)

        with ai_rec_col2:
            st.markdown("#### 📄 Generate AI Preventive Maintenance Report")
            rep_machine_id = st.selectbox(
                "Select Machine for AI Report",
                options=pm_df['machine_id'].unique().tolist() if not pm_df.empty else ["M14860"],
                key="pm_ai_report_machine_selectbox"
            )

            if st.button("🤖 Generate AI Preventive Report", type="primary", use_container_width=True, key="pm_generate_ai_report_btn"):
                with st.spinner("Generating Complete AI Maintenance Report... Please wait."):
                    selected_pm = pm_df[pm_df['machine_id'] == rep_machine_id]

                    mock_telemetry = {
                        "product_id": rep_machine_id,
                        "type": rep_machine_id[0] if len(rep_machine_id) > 0 and rep_machine_id[0].isalpha() else "M",
                        "air_temp": 298.2,
                        "process_temp": 308.7,
                        "rot_speed": 1500,
                        "torque": 42.0,
                        "tool_wear": 140,
                        "failures": "Preventive Care Scheduled"
                    }

                    _, ai_report_text = generate_machine_analysis(mock_telemetry)

                    st.markdown("### 📋 AI Preventive Maintenance Report Summary")
                    st.markdown(ai_report_text)
                    st.download_button(
                        label="📥 Download Complete AI Report (.txt)",
                        data=ai_report_text,
                        file_name=f"Preventive_Maintenance_Report_{rep_machine_id}.txt",
                        mime="text/plain",
                        key="pm_download_ai_report_btn"
                    )

    # -------------------------------------------------------------
    # PLOTLY CHARTS
    # -------------------------------------------------------------
    with tab_charts:
        st.subheader("📈 Interactive Preventive Maintenance Analytics")

        ch_col1, ch_col2 = st.columns(2)

        with ch_col1:
            freq_counts = pm_df['frequency'].value_counts().reset_index()
            freq_counts.columns = ['Frequency', 'Count']
            fig_freq = px.bar(
                freq_counts,
                x='Frequency',
                y='Count',
                title='Maintenance Frequency Distribution',
                color='Frequency',
                color_discrete_sequence=GREEN_PALETTE,
                text='Count'
            )
            fig_freq.update_layout(height=360, template="plotly_dark", **DARK_LAYOUT)
            st.plotly_chart(fig_freq, use_container_width=True, config=PLOTLY_CONFIG)

        with ch_col2:
            status_counts = pm_df['status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            fig_status = px.pie(
                status_counts,
                names='Status',
                values='Count',
                title='Preventive Maintenance Status Distribution',
                color='Status',
                color_discrete_map={
                    'Completed': '#22C55E',
                    'In Progress': '#3B82F6',
                    'Scheduled': '#F59E0B',
                    'Overdue': '#EF4444'
                },
                hole=0.4
            )
            fig_status.update_layout(height=360, template="plotly_dark", **DARK_LAYOUT)
            st.plotly_chart(fig_status, use_container_width=True, config=PLOTLY_CONFIG)

        ch_col3, ch_col4 = st.columns(2)

        with ch_col3:
            tech_counts = pm_df['technician'].value_counts().reset_index()
            tech_counts.columns = ['Technician', 'Assigned Tasks']
            fig_tech = px.bar(
                tech_counts,
                x='Assigned Tasks',
                y='Technician',
                orientation='h',
                title='Technician Workload Distribution',
                color='Assigned Tasks',
                color_continuous_scale=["#059669", "#34D399", "#A7F3D0"]
            )
            fig_tech.update_layout(height=360, template="plotly_dark", **DARK_LAYOUT)
            st.plotly_chart(fig_tech, use_container_width=True, config=PLOTLY_CONFIG)

        with ch_col4:
            sc_data = pd.DataFrame({
                "Category": ["Scheduled / Active", "Completed"],
                "Count": [pending_count + overdue_count, completed_count]
            })
            fig_sc = px.bar(
                sc_data,
                x="Category",
                y="Count",
                title="Scheduled vs. Completed Maintenance",
                color="Category",
                color_discrete_map={"Scheduled / Active": "#F59E0B", "Completed": "#22C55E"},
                text="Count"
            )
            fig_sc.update_layout(height=360, template="plotly_dark", **DARK_LAYOUT)
            st.plotly_chart(fig_sc, use_container_width=True, config=PLOTLY_CONFIG)

