import streamlit as st
import pandas as pd
import io
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from database import (
        fetch_all_work_orders,
        fetch_work_orders_paginated,
        fetch_work_order_ids,
        fetch_work_order_stats,
        insert_work_order,
        update_work_order,
        delete_work_order,
        get_db_connection
    )
    from work_orders import (
        generate_work_order_id,
        create_workorder_pdf
    )
except ImportError:
    from src.database import (
        fetch_all_work_orders,
        fetch_work_orders_paginated,
        fetch_work_order_ids,
        fetch_work_order_stats,
        insert_work_order,
        update_work_order,
        delete_work_order,
        get_db_connection
    )
    from src.work_orders import (
        generate_work_order_id,
        create_workorder_pdf
    )

# -------------------------------------------------------------
# On-Demand Export Helpers (Deferred execution)
# -------------------------------------------------------------
def generate_wo_excel_bytes(df: pd.DataFrame) -> bytes:
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='WorkOrders')
    return excel_buffer.getvalue()

def generate_wo_pdf_bytes(df: pd.DataFrame) -> bytes:
    return create_workorder_pdf(
        df=df,
        company_name="Agentic FacilityOps AI Platform",
        generated_by="Admin"
    )

def render_work_orders_page():
    """
    Module 4: Work Orders Management
    High-performance database-first SQLite work order lifecycle management,
    SQL-level pagination/filtering/search, KPI metrics, on-demand exports,
    and verified transaction save confirmations.
    """
    st.title("📋 Module 4: Autonomous Work Order Management")
    st.caption("SQLite work order lifecycle management, maintenance tracking, and PDF dispatch reporting.")

    # -------------------------------------------------------------
    # 0. Render Persisted Database Operation Flash Messages
    # -------------------------------------------------------------
    if "wo_flash_msg" in st.session_state:
        msg_type, msg_text = st.session_state["wo_flash_msg"]
        if msg_type == "success":
            st.success(msg_text)
        elif msg_type == "warning":
            st.warning(msg_text)
        elif msg_type == "error":
            st.error(msg_text)
        elif msg_type == "info":
            st.info(msg_text)
        del st.session_state["wo_flash_msg"]

    # -------------------------------------------------------------
    # 1. Work Order KPI Metrics Overview (Single aggregated SQL query)
    # -------------------------------------------------------------
    stats = fetch_work_order_stats()

    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5, kpi_col6, kpi_col7, kpi_col8 = st.columns(8)

    with kpi_col1:
        st.markdown(f"""
        <div class="kpi-card-box kpi-card-total">
            <div class="kpi-lbl">Total</div>
            <div class="kpi-val">{stats.get("total", 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col2:
        st.markdown(f"""
        <div class="kpi-card-box kpi-card-pending">
            <div class="kpi-lbl">Pending</div>
            <div class="kpi-val">{stats.get("pending", 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col3:
        st.markdown(f"""
        <div class="kpi-card-box kpi-card-in-progress">
            <div class="kpi-lbl">In Progress</div>
            <div class="kpi-val">{stats.get("in_progress", 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col4:
        st.markdown(f"""
        <div class="kpi-card-box kpi-card-completed">
            <div class="kpi-lbl">Completed</div>
            <div class="kpi-val">{stats.get("completed", 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col5:
        st.markdown(f"""
        <div class="kpi-card-box kpi-card-critical">
            <div class="kpi-lbl">Critical Prio</div>
            <div class="kpi-val">{stats.get("critical_priority", 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col6:
        st.markdown(f"""
        <div class="kpi-card-box kpi-card-severity">
            <div class="kpi-lbl">High Severity</div>
            <div class="kpi-val">{stats.get("high_severity", 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col7:
        st.markdown(f"""
        <div class="kpi-card-box kpi-card-due-today">
            <div class="kpi-lbl">Due Today</div>
            <div class="kpi-val">{stats.get("due_today", 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col8:
        st.markdown(f"""
        <div class="kpi-card-box kpi-card-overdue">
            <div class="kpi-lbl">Overdue</div>
            <div class="kpi-val">{stats.get("overdue", 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # -------------------------------------------------------------
    # 2. Sidebar Filters & SQL Search
    # -------------------------------------------------------------
    st.sidebar.header("📋 Work Order Filters")
    filter_status = st.sidebar.selectbox("Status Filter", ["All", "Open", "Pending", "In Progress", "Completed", "Cancelled"], key="wo_filter_status_selectbox")
    filter_priority = st.sidebar.selectbox("Priority Filter", ["All", "Low", "Medium", "High", "Critical"], key="wo_filter_priority_selectbox")
    filter_severity = st.sidebar.selectbox("Severity Filter", ["All", "Low", "Medium", "High", "Critical"], key="wo_filter_severity_selectbox")
    filter_machine_type = st.sidebar.selectbox("Machine Type Filter", ["All", "L", "M", "H"], key="wo_filter_machine_type_selectbox")

    use_date_range = st.sidebar.checkbox("Enable Date Range Filter", value=False, key="wo_use_date_range_checkbox")
    start_date_val = None
    end_date_val = None
    if use_date_range:
        d_col1, d_col2 = st.sidebar.columns(2)
        start_date_input = d_col1.date_input("Start Date", value=datetime.now().date() - pd.Timedelta(days=30), key="wo_start_date_input")
        end_date_input = d_col2.date_input("End Date", value=datetime.now().date() + pd.Timedelta(days=7), key="wo_end_date_input")
        start_date_val = start_date_input.strftime("%Y-%m-%d")
        end_date_val = end_date_input.strftime("%Y-%m-%d")

    st.subheader("🔍 Instant Work Order Search")
    search_query = st.text_input(
        "Search Work Orders",
        placeholder="Type Work Order ID, Machine ID, Type, Failure Prediction, or Assigned Technician...",
        key="instant_wo_search_mod"
    )

    # -------------------------------------------------------------
    # 3. Interactive SQL Paginated & Sorted Table
    # -------------------------------------------------------------
    st.subheader("📋 Work Orders Table & Data View")

    pg_col1, pg_col2, pg_col3 = st.columns([2, 2, 2])
    with pg_col1:
        rows_per_page = st.selectbox("Rows per Page", [5, 10, 20, 50, 100], index=1, key="wo_rows_per_page_mod")

    sort_options = {
        "Created Date": "created_at",
        "Work Order ID": "work_order_id",
        "Machine ID": "machine_id",
        "Machine Type": "machine_type",
        "Severity": "severity",
        "Priority": "priority",
        "Status": "status",
        "Assigned Technician": "assigned_to",
        "Due Date": "due_date"
    }

    with pg_col3:
        sort_label = st.selectbox("Sort By Column", options=list(sort_options.keys()), index=0, key="wo_sort_column_selectbox")
        sort_column = sort_options[sort_label]
        sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True, key="wo_sort_order_mod")

    # Fetch page selector input (1-based index)
    page_param = st.session_state.get("wo_current_page_val", 1)

    # Query only the requested page of records via SQL LIMIT/OFFSET
    display_df, total_records = fetch_work_orders_paginated(
        status_filter=filter_status,
        priority_filter=filter_priority,
        severity_filter=filter_severity,
        type_filter=filter_machine_type,
        search_query=search_query,
        start_date=start_date_val,
        end_date=end_date_val,
        sort_column=sort_column,
        sort_order=sort_order,
        page=page_param,
        page_size=rows_per_page
    )

    max_page = max(1, (total_records + rows_per_page - 1) // rows_per_page)
    effective_page = min(max(1, page_param), max_page)

    # If effective_page changed due to filtering, re-query page if needed
    if effective_page != page_param:
        display_df, total_records = fetch_work_orders_paginated(
            status_filter=filter_status,
            priority_filter=filter_priority,
            severity_filter=filter_severity,
            type_filter=filter_machine_type,
            search_query=search_query,
            start_date=start_date_val,
            end_date=end_date_val,
            sort_column=sort_column,
            sort_order=sort_order,
            page=effective_page,
            page_size=rows_per_page
        )

    with pg_col2:
        current_page = st.number_input("Page Selector", min_value=1, max_value=max_page, value=effective_page, step=1, key="wo_page_num_mod")
        st.session_state["wo_current_page_val"] = current_page
        st.caption(f"Showing page {current_page} of {max_page} ({total_records} matching records in database)")

    if not display_df.empty:
        all_columns = list(display_df.columns)
        default_cols = [c for c in [
            'work_order_id', 'machine_id', 'machine_type', 'failure_prediction',
            'severity', 'priority', 'status', 'assigned_to', 'maintenance_action',
            'created_at', 'due_date'
        ] if c in all_columns]

        selected_columns = st.multiselect(
            "📌 Column Selection",
            options=all_columns,
            default=default_cols,
            key="wo_selected_columns_multiselect"
        )

        if selected_columns:
            st.dataframe(
                display_df[selected_columns],
                column_config={
                    "work_order_id": st.column_config.TextColumn("Work Order ID", width="medium"),
                    "machine_id": st.column_config.TextColumn("Machine ID", width="small"),
                    "machine_type": st.column_config.TextColumn("Type", width="small"),
                    "failure_prediction": st.column_config.TextColumn("Failure Mode", width="medium"),
                    "severity": st.column_config.TextColumn("Severity", width="small"),
                    "priority": st.column_config.TextColumn("Priority", width="small"),
                    "status": st.column_config.TextColumn("Status", width="medium"),
                    "assigned_to": st.column_config.TextColumn("Technician", width="medium"),
                    "maintenance_action": st.column_config.TextColumn("Maintenance Action", width="large"),
                    "created_at": st.column_config.TextColumn("Created At", width="medium"),
                    "due_date": st.column_config.TextColumn("Due Date", width="medium")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("Please select at least one column to display.")
    else:
        st.info("No work orders found matching the filter criteria.")

    st.write("")

    # -------------------------------------------------------------
    # 4. On-Demand Data Export Controls (Generated ONLY on user click)
    # -------------------------------------------------------------
    with st.expander("📥 Export Options (CSV / Excel / PDF Report)", expanded=False):
        st.caption("Generate reports on-demand for the current filter criteria.")
        exp_col1, exp_col2, exp_col3 = st.columns(3)

        with exp_col1:
            if st.button("📄 Prepare CSV Export", key="btn_prep_csv", use_container_width=True):
                export_df = fetch_all_work_orders(
                    status_filter=filter_status,
                    priority_filter=filter_priority,
                    severity_filter=filter_severity,
                    type_filter=filter_machine_type,
                    search_query=search_query,
                    start_date=start_date_val,
                    end_date=end_date_val
                )
                st.session_state["exp_csv_bytes"] = export_df.to_csv(index=False).encode('utf-8')
            
            if "exp_csv_bytes" in st.session_state:
                st.download_button(
                    label="📥 Download CSV File",
                    data=st.session_state["exp_csv_bytes"],
                    file_name=f"work_orders_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    type="primary",
                    key="wo_export_csv_download"
                )

        with exp_col2:
            if st.button("📊 Prepare Excel Export", key="btn_prep_excel", use_container_width=True):
                export_df = fetch_all_work_orders(
                    status_filter=filter_status,
                    priority_filter=filter_priority,
                    severity_filter=filter_severity,
                    type_filter=filter_machine_type,
                    search_query=search_query,
                    start_date=start_date_val,
                    end_date=end_date_val
                )
                st.session_state["exp_excel_bytes"] = generate_wo_excel_bytes(export_df)

            if "exp_excel_bytes" in st.session_state:
                st.download_button(
                    label="📊 Download Excel File",
                    data=st.session_state["exp_excel_bytes"],
                    file_name=f"work_orders_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary",
                    key="wo_export_excel_download"
                )

        with exp_col3:
            if st.button("📄 Prepare PDF Report", key="btn_prep_pdf", use_container_width=True):
                export_df = fetch_all_work_orders(
                    status_filter=filter_status,
                    priority_filter=filter_priority,
                    severity_filter=filter_severity,
                    type_filter=filter_machine_type,
                    search_query=search_query,
                    start_date=start_date_val,
                    end_date=end_date_val
                )
                st.session_state["exp_pdf_bytes"] = generate_wo_pdf_bytes(export_df)

            if "exp_pdf_bytes" in st.session_state:
                st.download_button(
                    label="📄 Download PDF Report",
                    data=st.session_state["exp_pdf_bytes"],
                    file_name=f"work_order_report_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="wo_download_pdf_report_download"
                )

    st.divider()

    # -------------------------------------------------------------
    # 5. Work Order CRUD Operations (Create / Update / Delete)
    # -------------------------------------------------------------
    tab_create, tab_update, tab_delete = st.tabs([
        "➕ Create Work Order", "✏️ Update Work Order", "🗑️ Delete Work Order"
    ])

    with tab_create:
        st.subheader("➕ Create Manual Work Order")
        with st.form("create_wo_form_mod"):
            col_m1, col_m2, col_m3 = st.columns(3)
            m_id = col_m1.text_input("Machine ID", value="M14860")
            m_type = col_m2.selectbox("Machine Type", ["L", "M", "H"])
            f_pred = col_m3.selectbox("Failure Mode Flag", ["TWF", "HDF", "PWF", "OSF", "RNF", "None"])

            col_m4, col_m5, col_m6 = st.columns(3)
            sev = col_m4.selectbox("Severity", ["Low", "Medium", "High", "Critical"])
            prio = col_m5.selectbox("Priority", ["Low", "Medium", "High", "Critical"])
            tech = col_m6.selectbox("Assign Technician", ["John Doe", "David Smith", "Sarah Connor", "Michael Scott", "Unassigned"])

            m_action = st.text_input("Maintenance Action", value="Preventive Maintenance & Inspection")
            due_input = st.date_input("Due Date", value=datetime.now().date() + pd.Timedelta(days=3))
            summary_input = st.text_area("AI Summary / Maintenance Notes", value="Manual work order creation.")

            submit_create = st.form_submit_button("💾 Save Work Order to SQLite", type="primary")

            if submit_create:
                wo_id = generate_work_order_id()
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                due_str = due_input.strftime("%Y-%m-%d")

                data = {
                    "work_order_id": wo_id,
                    "machine_id": m_id,
                    "machine_type": m_type,
                    "failure_prediction": f_pred,
                    "failure_type": f_pred,
                    "severity": sev,
                    "maintenance_action": m_action,
                    "assigned_to": tech,
                    "status": "Pending",
                    "priority": prio,
                    "created_at": now_str,
                    "due_date": due_str,
                    "completed_at": None,
                    "ai_summary": summary_input
                }

                if insert_work_order(data):
                    st.session_state["wo_flash_msg"] = (
                        "success",
                        f"✅ Work Order {wo_id} saved successfully to SQLite."
                    )
                else:
                    st.session_state["wo_flash_msg"] = (
                        "error",
                        f"❌ Failed to save Work Order {wo_id} to SQLite. Please check the database/error details."
                    )
                st.rerun()

    with tab_update:
        st.subheader("✏️ Update Work Order Details")
        wo_ids = fetch_work_order_ids()
        if wo_ids:
            selected_wo_id = st.selectbox("Select Work Order to Edit", options=wo_ids, key="edit_wo_select_mod")

            if selected_wo_id:
                # Query single row from SQLite
                row_edit = None
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT * FROM work_orders WHERE work_order_id = ?", (selected_wo_id,))
                        r = cursor.fetchone()
                        if r:
                            row_edit = dict(r)
                except Exception as e:
                    print(f"Error fetching record to edit: {e}")

                if row_edit:
                    with st.form("update_wo_form_mod"):
                        u_col1, u_col2, u_col3 = st.columns(3)
                        tech_list = ["John Doe", "David Smith", "Sarah Connor", "Michael Scott", "Unassigned"]
                        tech_idx = tech_list.index(row_edit['assigned_to']) if row_edit['assigned_to'] in tech_list else 4
                        edit_tech = u_col1.selectbox("Assigned Technician", tech_list, index=tech_idx)

                        status_list = ["Pending", "In Progress", "Completed", "Cancelled"]
                        status_idx = status_list.index(row_edit['status']) if row_edit['status'] in status_list else 0
                        edit_status = u_col2.selectbox("Status", status_list, index=status_idx)

                        prio_list = ["Low", "Medium", "High", "Critical"]
                        prio_idx = prio_list.index(row_edit['priority']) if row_edit['priority'] in prio_list else 0
                        edit_prio = u_col3.selectbox("Priority Level", prio_list, index=prio_idx)

                        edit_action = st.text_input("Maintenance Action", value=row_edit['maintenance_action'] or "")

                        curr_due = datetime.now().date()
                        if row_edit['due_date'] and str(row_edit['due_date']) != "None":
                            try:
                                curr_due = datetime.strptime(str(row_edit['due_date']), "%Y-%m-%d").date()
                            except Exception:
                                pass

                        edit_due_date = st.date_input("Modify Due Date", value=curr_due)

                        submit_update = st.form_submit_button("✏️ Save Changes to SQLite", type="primary")

                        if submit_update:
                            due_str = edit_due_date.strftime("%Y-%m-%d")
                            if update_work_order(selected_wo_id, edit_tech, edit_status, edit_prio, due_str, edit_action):
                                st.session_state["wo_flash_msg"] = (
                                    "success",
                                    f"✅ Work Order {selected_wo_id} updated successfully in SQLite."
                                )
                            else:
                                if selected_wo_id not in fetch_work_order_ids():
                                    st.session_state["wo_flash_msg"] = (
                                        "warning",
                                        f"⚠️ Work Order {selected_wo_id} was not found."
                                    )
                                else:
                                    st.session_state["wo_flash_msg"] = (
                                        "error",
                                        f"❌ Work Order {selected_wo_id} could not be updated in SQLite."
                                    )
                            st.rerun()
                else:
                    st.warning(f"⚠️ Work Order {selected_wo_id} was not found.")
        else:
            st.info("No work orders available to update.")

    with tab_delete:
        st.subheader("🗑️ Permanent Work Order Deletion")
        del_ids = fetch_work_order_ids()
        if del_ids:
            del_wo_id = st.selectbox("Select Work Order to Delete", options=del_ids, key="del_wo_select_mod")
            
            del_row = None
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM work_orders WHERE work_order_id = ?", (del_wo_id,))
                    r = cursor.fetchone()
                    if r:
                        del_row = dict(r)
            except Exception as e:
                print(f"Error fetching record to delete: {e}")

            if del_row:
                st.warning(f"""
                ⚠️ **Work Order Summary for Deletion:**
                - **Work Order ID:** `{del_row['work_order_id']}`
                - **Machine ID:** `{del_row['machine_id']}` ({del_row.get('machine_type', 'N/A')})
                - **Failure Mode:** `{del_row.get('failure_prediction', 'N/A')}`
                - **Status:** `{del_row['status']}`
                - **Assigned Technician:** `{del_row['assigned_to']}`
                """)

                confirm_check = st.checkbox(f"I confirm that I want to permanently delete Work Order {del_wo_id} from SQLite.", key="del_confirm_check_mod")

                if st.button("🗑️ Permanently Delete Work Order", type="primary", key="wo_delete_submit_btn"):
                    if confirm_check:
                        if delete_work_order(del_wo_id):
                            st.session_state["wo_flash_msg"] = (
                                "success",
                                f"✅ Work Order {del_wo_id} deleted successfully from SQLite."
                            )
                        else:
                            if del_wo_id not in fetch_work_order_ids():
                                st.session_state["wo_flash_msg"] = (
                                    "warning",
                                    f"⚠️ Work Order {del_wo_id} was not found."
                                )
                            else:
                                st.session_state["wo_flash_msg"] = (
                                    "error",
                                    f"❌ Failed to delete Work Order {del_wo_id} from SQLite."
                                )
                        st.rerun()
                    else:
                        st.error("⚠️ Please check the confirmation checkbox above before deleting.")
            else:
                st.warning(f"⚠️ Work Order {del_wo_id} was not found.")
        else:
            st.info("No work orders available to delete.")
