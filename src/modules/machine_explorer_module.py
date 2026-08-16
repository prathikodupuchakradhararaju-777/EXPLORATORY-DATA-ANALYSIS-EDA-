import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

try:
    from ollama_service import generate_machine_analysis, is_ollama_available
    from database import has_open_work_order
    from work_orders import create_ai_work_order
    from pdf_generator import create_machine_pdf
except ImportError:
    from src.ollama_service import generate_machine_analysis, is_ollama_available
    from src.database import has_open_work_order
    from src.work_orders import create_ai_work_order
    from src.pdf_generator import create_machine_pdf


# -------------------------------------------------------------
# Cached Lookup Helpers
# -------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_unique_product_ids(df: pd.DataFrame):
    if df is not None and "Product ID" in df.columns:
        return list(df["Product ID"].unique())
    return []

@st.cache_data(show_spinner=False)
def get_filtered_product_ids(df: pd.DataFrame, machine_type: str):
    if df is not None and "Type" in df.columns and "Product ID" in df.columns:
        if machine_type != "All":
            return list(df[df["Type"] == machine_type]["Product ID"].unique())
        return list(df["Product ID"].unique())
    return []

@st.cache_data(show_spinner=False)
def get_roster_preview(df: pd.DataFrame, n: int = 20):
    cols = ['Product ID', 'Type', 'Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]', 'Machine failure']
    available_cols = [c for c in cols if c in df.columns]
    return df[available_cols].head(n)


def render_machine_explorer_page(df: pd.DataFrame):
    """
    Module 3: Machine Explorer
    Individual machine lookup, sensor gauges, failure diagnostics,
    AI machine analysis, and automated work order generation.
    Optimized for high-performance PDF & AI report generation.
    """
    st.title("⚙️ Module 3: Machine Explorer & Live Sensor Telemetry")
    st.caption("Inspect individual machine health, monitor live sensor parameters, and run AI machine diagnostics.")

    if df is None or df.empty:
        st.error("⚠️ Machine data is unavailable or empty.")
        return

    # Machine Search & Selection
    product_ids = get_unique_product_ids(df)

    col_search1, col_search2 = st.columns([2, 1])
    with col_search1:
        selected_product_id = st.selectbox(
            "Search or Select Machine Product ID",
            options=[""] + product_ids,
            index=0,
            key="mach_exp_product_id_selectbox",
            help="Select a machine Product ID to view real-time telemetry metrics."
        )

    with col_search2:
        filter_type = st.selectbox(
            "Quick Filter by Type",
            ["All", "L", "M", "H"],
            key="mach_exp_type_filter_selectbox"
        )

    if filter_type != "All":
        filtered_ids = get_filtered_product_ids(df, filter_type)
        if selected_product_id and selected_product_id not in filtered_ids:
            selected_product_id = ""
        product_ids = filtered_ids

    if not selected_product_id:
        st.info("💡 **Select a Product ID above** to inspect individual equipment metrics and run AI diagnostics.")

        st.subheader("Equipment Roster Overview")
        st.dataframe(
            get_roster_preview(df, 20),
            use_container_width=True,
            hide_index=True
        )
        return

    # Single Dataframe Filter Pass
    machine_records = df[df['Product ID'] == selected_product_id]
    if machine_records.empty:
        st.error(f"⚠️ No records found for Product ID: {selected_product_id}")
        return

    machine = machine_records.iloc[0]

    # Health status check
    is_failure = machine.get('Machine failure', 0) == 1
    health_status = "CRITICAL / FAILURE PREDICTED" if is_failure else "OPERATIONAL / HEALTHY"
    health_color = "#EF4444" if is_failure else "#22C55E"

    st.markdown(f"""
        <div style="background-color: #1E293B; padding: 16px 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 20px; border-left: 6px solid {health_color};">
            <div style="font-size: 12px; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Equipment Health Status</div>
            <div style="font-size: 22px; font-weight: 800; color: {health_color}; margin-top: 2px;">
                {health_status}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 1. Machine Identification & Specifications
    st.subheader("1. Equipment Specification & Details")
    info_col1, info_col2, info_col3, info_col4 = st.columns(4)
    info_col1.write(f"**Product ID:** `{machine.get('Product ID', 'N/A')}`")
    info_col2.write(f"**Equipment Class:** `{machine.get('Type', 'N/A')}`")
    info_col3.write(f"**UDI Sequence:** `{machine.get('UDI', 'N/A')}`")
    info_col4.write(f"**Failure Flag:** `{machine.get('Machine failure', 0)}`")

    st.divider()

    # 2. Real-Time Telemetry Sensors
    st.subheader("2. Live Sensor Telemetry Gauges")
    s_col1, s_col2, s_col3, s_col4, s_col5 = st.columns(5)
    s_col1.metric("Air Temperature", f"{machine.get('Air temperature [K]', 0)} K")
    s_col2.metric("Process Temperature", f"{machine.get('Process temperature [K]', 0)} K")
    s_col3.metric("Rotational Speed", f"{machine.get('Rotational speed [rpm]', 0)} RPM")
    s_col4.metric("Torque", f"{machine.get('Torque [Nm]', 0)} Nm")
    s_col5.metric("Tool Wear", f"{machine.get('Tool wear [min]', 0)} min")

    st.divider()

    # 3. Detected Failure Modes
    st.subheader("3. Sensor Failure Mode Flags")
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
    f_col1.write(f"**Tool Wear (TWF):** `{machine.get('TWF', 0)}`")
    f_col2.write(f"**Heat Dissipation (HDF):** `{machine.get('HDF', 0)}`")
    f_col3.write(f"**Power Failure (PWF):** `{machine.get('PWF', 0)}`")
    f_col4.write(f"**Overstrain (OSF):** `{machine.get('OSF', 0)}`")
    f_col5.write(f"**Random Failure (RNF):** `{machine.get('RNF', 0)}`")

    fails = [f for f in ['TWF', 'HDF', 'PWF', 'OSF', 'RNF'] if machine.get(f, 0) == 1] or ['None']
    failures_str = ', '.join(fails)

    p_id_str = str(machine.get('Product ID', 'N/A'))

    machine_info = {
        "product_id": p_id_str,
        "type": str(machine.get('Type', 'N/A')),
        "air_temp": machine.get('Air temperature [K]', 0),
        "process_temp": machine.get('Process temperature [K]', 0),
        "rot_speed": machine.get('Rotational speed [rpm]', 0),
        "torque": machine.get('Torque [Nm]', 0),
        "tool_wear": machine.get('Tool wear [min]', 0),
        "failures": failures_str
    }

    if is_failure:
        auto_check_key = f"auto_wo_checked_{p_id_str}_{failures_str}"
        if auto_check_key not in st.session_state:
            st.session_state[auto_check_key] = has_open_work_order(p_id_str, failures_str)

        if not st.session_state[auto_check_key]:
            ai_text_summary = f"Automated AI Preventive Maintenance Alert: Machine {p_id_str} flagged with failure modes ({failures_str})."
            auto_created, auto_wo_id = create_ai_work_order(
                machine_info=machine_info,
                ai_summary=ai_text_summary,
                assigned_to="Unassigned",
                prevent_duplicates=True
            )
            if auto_created:
                st.session_state[auto_check_key] = True
                st.error(f"🚨 **AUTOMATIC WORK ORDER CREATED**: Work Order **{auto_wo_id}** auto-generated in SQLite for Machine **{p_id_str}** due to predicted failure ({failures_str}).")
        else:
            st.warning(f"⚠️ Active Work Order already exists in SQLite database for Machine **{p_id_str}**.")

    st.divider()

    # 4. AI Machine Assistant & Work Order Creation
    st.subheader("4. 🤖 AI Machine Diagnostics & Automated Report Generation")
    if is_ollama_available():
        st.caption("🟢 Connected to Ollama Local LLM Engine")
    else:
        st.caption("⚡ Operating via Built-in Preventive Analytics Engine (Ollama server offline)")

    col_ai1, col_ai2 = st.columns([1, 1])
    with col_ai1:
        run_ai = st.button("🤖 Generate AI & PDF Report", type="primary", use_container_width=True, key="mach_exp_generate_report_btn")
    with col_ai2:
        create_wo = st.button("📝 Create Work Order from AI Report", use_container_width=True, key="mach_exp_create_wo_btn")

    report_container = st.container()

    p_id_key = str(machine.get('Product ID'))

    if run_ai:
        with st.status("⚡ Generating Complete Machine Maintenance Report...", expanded=True) as status:
            status.write("⏳ Extracting telemetry sensor metrics...")
            
            status.write("🤖 Generating AI Machine Maintenance Report...")
            try:
                # Execute AI report generation (Ollama fast call with fallback)
                _, report_text = generate_machine_analysis(machine_info)
            except Exception as ex:
                st.warning(f"⚠️ AI report generation encountered an issue: {ex}. Using built-in diagnostic summary.")
                from ollama_service import generate_rule_based_machine_analysis
                report_text = generate_rule_based_machine_analysis(machine_info)

            status.write("📋 Preparing report display...")
            st.session_state[f"last_analysis_{p_id_key}"] = report_text

            status.write("📄 Generating PDF Report...")
            try:
                pdf_bytes = create_machine_pdf(machine_info, report_text)
                st.session_state[f"pdf_bytes_{p_id_key}"] = pdf_bytes
            except Exception as pdf_err:
                st.error(f"⚠️ PDF Generation Error: {pdf_err}")
                st.session_state[f"pdf_bytes_{p_id_key}"] = None

            status.write("✅ Report generated successfully!")
            status.update(label="🎉 Maintenance Report Ready!", state="complete", expanded=False)

    # Render Report & Download Options
    if f"last_analysis_{p_id_key}" in st.session_state:
        saved_report = st.session_state[f"last_analysis_{p_id_key}"]
        pdf_bytes = st.session_state.get(f"pdf_bytes_{p_id_key}")

        with report_container:
            st.markdown(saved_report)
            st.markdown("---")
            
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                if pdf_bytes:
                    st.download_button(
                        label="📄 Download PDF Report (.pdf)",
                        data=pdf_bytes,
                        file_name=f"AI_Maintenance_Report_{p_id_key}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                        key="mach_exp_download_pdf_btn"
                    )
                else:
                    st.warning("PDF report rendering unavailable.")

            with d_col2:
                st.download_button(
                    label="📥 Download Text Report (.txt)",
                    data=saved_report,
                    file_name=f"AI_Maintenance_Report_{p_id_key}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="mach_exp_download_txt_btn"
                )

    if create_wo:
        ai_text = st.session_state.get(f"last_analysis_{p_id_key}", "")
        if not ai_text:
            with st.spinner("Generating AI Analysis for Work Order..."):
                try:
                    _, ai_text = generate_machine_analysis(machine_info)
                    st.session_state[f"last_analysis_{p_id_key}"] = ai_text
                except Exception:
                    from ollama_service import generate_rule_based_machine_analysis
                    ai_text = generate_rule_based_machine_analysis(machine_info)
                    st.session_state[f"last_analysis_{p_id_key}"] = ai_text

        from work_orders import extract_fields_from_ai_report
        parsed_fields = extract_fields_from_ai_report(ai_text, machine_info)

        success, wo_id = create_ai_work_order(machine_info, ai_text, prevent_duplicates=False)
        if success:
            st.success(
                f"✅ **Work Order {wo_id} Created Successfully in SQLite!**\n\n"
                f"- **Target Machine**: `{parsed_fields['machine_id']}`\n"
                f"- **Extracted Priority**: `{parsed_fields['priority']}`\n"
                f"- **Maintenance Action**: `{parsed_fields['maintenance_type']}`\n"
                f"- **Technician Recommended**: `{parsed_fields['technician_recommendation']}`\n"
                f"- **Target Due Date**: `{parsed_fields['due_date']}`"
            )
        else:
            st.error("Failed to create Work Order in SQLite database.")

