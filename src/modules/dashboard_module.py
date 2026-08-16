"""
Module 2: AI Predictive Maintenance Dashboard
A clean Executive Dashboard using Streamlit and Plotly for equipment telemetry analytics.
"""

import os
import sys
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Unified Dark Theme Styling Helper for Plotly Figures
DARK_LAYOUT = dict(
    paper_bgcolor="#1E293B",
    plot_bgcolor="#0F172A",
    font=dict(color="#F8FAFC", family="Inter, sans-serif", size=12),
    margin=dict(l=40, r=30, t=50, b=40),
    xaxis=dict(
        gridcolor="#334155",
        zerolinecolor="#334155",
        title_font=dict(size=12, color="#94A3B8"),
        tickfont=dict(size=11, color="#CBD5E1")
    ),
    yaxis=dict(
        gridcolor="#334155",
        zerolinecolor="#334155",
        title_font=dict(size=12, color="#94A3B8"),
        tickfont=dict(size=11, color="#CBD5E1")
    ),
    title=dict(
        font=dict(size=15, color="#F8FAFC", family="Poppins, sans-serif")
    )
)
COLOR_PALETTE = ['#2563EB', '#22C55E', '#F59E0B', '#EF4444', '#8B5CF6', '#38BDF8']

# Stable Plotly rendering configuration to prevent hover/resize modebar jitter
PLOTLY_CONFIG = {
    "displayModeBar": False,
    "responsive": True
}

# -------------------------------------------------------------
# 1. Cached Data Loader & Calculation Helpers
# -------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data(file_path: str = None) -> pd.DataFrame:
    """
    Loads the AI4I 2020 Predictive Maintenance dataset safely from disk.
    """
    if file_path and os.path.exists(file_path):
        return pd.read_csv(file_path)
    
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "ai4i2020.csv"),
        "data/ai4i2020.csv",
        "../data/ai4i2020.csv",
        "ai4i2020.csv"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return pd.read_csv(path)
            
    st.error("❌ Dataset file 'ai4i2020.csv' not found. Please verify data path.")
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def compute_kpi_values(df: pd.DataFrame):
    if df.empty:
        return {}
    total_machines = len(df)
    total_failures = int(df["Machine failure"].sum()) if "Machine failure" in df.columns else 0
    active_machines = total_machines - total_failures
    failure_pct = (total_failures / total_machines * 100) if total_machines > 0 else 0.0
    health_score = max(0.0, 100.0 - failure_pct)
    avg_rpm = float(df["Rotational speed [rpm]"].mean()) if "Rotational speed [rpm]" in df.columns else 0.0
    avg_tool_wear = float(df["Tool wear [min]"].mean()) if "Tool wear [min]" in df.columns else 0.0
    return {
        "total_machines": total_machines,
        "total_failures": total_failures,
        "active_machines": active_machines,
        "failure_pct": failure_pct,
        "health_score": health_score,
        "avg_rpm": avg_rpm,
        "avg_tool_wear": avg_tool_wear
    }

@st.cache_data(show_spinner=False)
def compute_dashboard_histogram_bins(df: pd.DataFrame, col: str, nbins: int = 30):
    clean_data = df[col].dropna()
    counts, bin_edges = np.histogram(clean_data, bins=nbins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    return pd.DataFrame({
        "Bin Center": bin_centers,
        "Count": counts
    })

@st.cache_data(show_spinner=False)
def get_dashboard_scatter_sample(df: pd.DataFrame, n: int = 2000, seed: int = 42):
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=seed)


# -------------------------------------------------------------
# 2. Interactive Sidebar Filters
# -------------------------------------------------------------
def create_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates an interactive sidebar with filters for Machine Type, Machine Failure,
    and telemetry metric ranges (Air Temp, Process Temp, RPM, Torque, Tool Wear).
    Returns the dynamically filtered DataFrame.
    """
    st.sidebar.markdown("## 🎛️ Dataset Filters")
    st.sidebar.markdown("---")

    if df.empty:
        return df

    # Reset Filters Button
    if st.sidebar.button("🔄 Reset All Filters", use_container_width=True, key="dash_reset_filters_btn"):
        st.rerun()

    st.sidebar.markdown("### Equipment & Failure Filters")

    # 1. Machine Type Filter (L, M, H)
    type_options = list(df["Type"].unique()) if "Type" in df.columns else ["L", "M", "H"]
    selected_types = st.sidebar.multiselect(
        "Machine Type (L, M, H)",
        options=type_options,
        default=type_options,
        key="dash_type_multiselect",
        help="L: Low quality, M: Medium quality, H: High quality"
    )

    # 2. Machine Failure Filter (Yes/No)
    failure_options = ["All", "No Failure", "Failure"]
    selected_failure_choice = st.sidebar.selectbox(
        "Machine Failure",
        options=failure_options,
        index=0,
        key="dash_failure_selectbox",
        help="Filter fleet by machinery failure status."
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Telemetry Metric Ranges")

    # 3. Air Temperature Range Slider
    if "Air temperature [K]" in df.columns:
        min_air = float(df["Air temperature [K]"].min())
        max_air = float(df["Air temperature [K]"].max())
        air_range = st.sidebar.slider(
            "Air Temperature Range (K)",
            min_value=min_air,
            max_value=max_air,
            value=(min_air, max_air),
            step=0.1,
            key="dash_air_temp_slider"
        )
    else:
        air_range = None

    # 4. Process Temperature Range Slider
    if "Process temperature [K]" in df.columns:
        min_proc = float(df["Process temperature [K]"].min())
        max_proc = float(df["Process temperature [K]"].max())
        proc_range = st.sidebar.slider(
            "Process Temperature Range (K)",
            min_value=min_proc,
            max_value=max_proc,
            value=(min_proc, max_proc),
            step=0.1,
            key="dash_proc_temp_slider"
        )
    else:
        proc_range = None

    # 5. Rotational Speed (RPM) Range Slider
    if "Rotational speed [rpm]" in df.columns:
        min_rpm = int(df["Rotational speed [rpm]"].min())
        max_rpm = int(df["Rotational speed [rpm]"].max())
        rpm_range = st.sidebar.slider(
            "Rotational Speed Range (RPM)",
            min_value=min_rpm,
            max_value=max_rpm,
            value=(min_rpm, max_rpm),
            step=10,
            key="dash_rpm_slider"
        )
    else:
        rpm_range = None

    # 6. Torque Range Slider
    if "Torque [Nm]" in df.columns:
        min_trq = float(df["Torque [Nm]"].min())
        max_trq = float(df["Torque [Nm]"].max())
        trq_range = st.sidebar.slider(
            "Torque Range (Nm)",
            min_value=min_trq,
            max_value=max_trq,
            value=(min_trq, max_trq),
            step=0.5,
            key="dash_trq_slider"
        )
    else:
        trq_range = None

    # 7. Tool Wear Range Slider
    if "Tool wear [min]" in df.columns:
        min_wear = int(df["Tool wear [min]"].min())
        max_wear = int(df["Tool wear [min]"].max())
        wear_range = st.sidebar.slider(
            "Tool Wear Range (min)",
            min_value=min_wear,
            max_value=max_wear,
            value=(min_wear, max_wear),
            step=5,
            key="dash_wear_slider"
        )
    else:
        wear_range = None

    # Apply filters
    filtered_df = df.copy()

    if selected_types and "Type" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Type"].isin(selected_types)]

    if selected_failure_choice == "No Failure" and "Machine failure" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Machine failure"] == 0]
    elif selected_failure_choice == "Failure" and "Machine failure" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Machine failure"] == 1]

    if air_range and "Air temperature [K]" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["Air temperature [K]"] >= air_range[0]) &
            (filtered_df["Air temperature [K]"] <= air_range[1])
        ]

    if proc_range and "Process temperature [K]" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["Process temperature [K]"] >= proc_range[0]) &
            (filtered_df["Process temperature [K]"] <= proc_range[1])
        ]

    if rpm_range and "Rotational speed [rpm]" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["Rotational speed [rpm]"] >= rpm_range[0]) &
            (filtered_df["Rotational speed [rpm]"] <= rpm_range[1])
        ]

    if trq_range and "Torque [Nm]" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["Torque [Nm]"] >= trq_range[0]) &
            (filtered_df["Torque [Nm]"] <= trq_range[1])
        ]

    if wear_range and "Tool wear [min]" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["Tool wear [min]"] >= wear_range[0]) &
            (filtered_df["Tool wear [min]"] <= wear_range[1])
        ]

    return filtered_df


# -------------------------------------------------------------
# 3. Enterprise Modern KPI Cards Display
# -------------------------------------------------------------
def display_kpis(df: pd.DataFrame):
    """
    Displays enterprise KPI cards:
    - Total Assets
    - Active Machines
    - Critical Alerts
    - Predicted Failures
    - Average RPM
    - Average Tool Wear
    - System Health Score
    Includes icons, rounded dark glass containers, trend lines, and hover animations.
    """
    st.markdown("### 📊 FacilityOps Key Performance Indicators (KPIs)")

    if df.empty:
        st.warning("⚠️ No data available to compute KPIs.")
        return

    # Compute key values via cached helper
    kpi_dict = compute_kpi_values(df)
    total_machines = kpi_dict.get("total_machines", 0)
    active_machines = kpi_dict.get("active_machines", 0)
    total_failures = kpi_dict.get("total_failures", 0)
    failure_pct = kpi_dict.get("failure_pct", 0.0)
    health_score = kpi_dict.get("health_score", 100.0)
    avg_rpm = kpi_dict.get("avg_rpm", 0.0)
    avg_tool_wear = kpi_dict.get("avg_tool_wear", 0.0)

    kpis = [
        {
            "title": "Total Assets",
            "value": f"{total_machines:,}",
            "sub": "Active Equipment Units",
            "icon": "🏭",
            "border_class": "kpi-card-total",
            "trend": "↑ 100% Monitored"
        },
        {
            "title": "Active Machines",
            "value": f"{active_machines:,}",
            "sub": "Optimal Operational State",
            "icon": "🟢",
            "border_class": "kpi-card-active",
            "trend": f"↑ {health_score:.1f}% Nominal"
        },
        {
            "title": "Critical Alerts",
            "value": f"{total_failures:,}",
            "sub": "Attention Required",
            "icon": "🚨",
            "border_class": "kpi-card-critical",
            "trend": f"↓ {failure_pct:.2f}% Fleet Rate"
        },
        {
            "title": "Predicted Failures",
            "value": f"{total_failures:,}",
            "sub": "AI Diagnostic Flag",
            "icon": "⚡",
            "border_class": "kpi-card-severity",
            "trend": "↑ High Risk Flagged"
        },
        {
            "title": "Average RPM",
            "value": f"{avg_rpm:,.1f}",
            "sub": "Fleet Speed Baseline",
            "icon": "🔄",
            "border_class": "kpi-card-in-progress",
            "trend": "Nominal 1,538 RPM"
        },
        {
            "title": "Average Tool Wear",
            "value": f"{avg_tool_wear:.1f} min",
            "sub": "Mean Cutting Wear",
            "icon": "🛠️",
            "border_class": "kpi-card-pending",
            "trend": "Limit: 200 min"
        },
        {
            "title": "System Health Score",
            "value": f"{health_score:.1f}%",
            "sub": "Overall Plant Reliability",
            "icon": "🛡️",
            "border_class": "kpi-card-completed",
            "trend": "⭐ Enterprise Grade"
        }
    ]

    r1_cols = st.columns(4)
    for idx in range(4):
        kpi = kpis[idx]
        r1_cols[idx].markdown(f"""
            <div class="kpi-card-box {kpi['border_class']}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="kpi-lbl">{kpi['title']}</span>
                    <span style="font-size: 22px;">{kpi['icon']}</span>
                </div>
                <div class="kpi-val">{kpi['value']}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                    <span style="font-size: 11px; color: #94A3B8;">{kpi['sub']}</span>
                    <span class="kpi-trend">{kpi['trend']}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    r2_cols = st.columns(3)
    for idx in range(4, 7):
        kpi = kpis[idx]
        r2_cols[idx - 4].markdown(f"""
            <div class="kpi-card-box {kpi['border_class']}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="kpi-lbl">{kpi['title']}</span>
                    <span style="font-size: 22px;">{kpi['icon']}</span>
                </div>
                <div class="kpi-val">{kpi['value']}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                    <span style="font-size: 11px; color: #94A3B8;">{kpi['sub']}</span>
                    <span class="kpi-trend">{kpi['trend']}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)


# -------------------------------------------------------------
# 4. Machine Failure Distribution Section
# -------------------------------------------------------------
def machine_failure_section(df: pd.DataFrame):
    """
    Displays Pie, Donut, and Bar charts for Failure vs No Failure in Dark Theme.
    """
    st.markdown("---")
    st.markdown("### ⚠️ Machine Failure & Health Distribution")

    if df.empty or "Machine failure" not in df.columns:
        st.warning("No failure data available.")
        return

    fail_counts = df["Machine failure"].value_counts().reset_index()
    fail_counts.columns = ["Status_Code", "Count"]
    fail_counts["Status"] = fail_counts["Status_Code"].map({0: "No Failure", 1: "Failure"})
    total = len(df)
    fail_counts["Percentage"] = (fail_counts["Count"] / total * 100).round(2)

    col1, col2, col3 = st.columns(3)

    with col1:
        fig_pie = px.pie(
            fail_counts,
            names="Status",
            values="Count",
            title="Pie Chart: Failure Overview",
            color="Status",
            color_discrete_map={"No Failure": "#22C55E", "Failure": "#EF4444"},
            hover_data=["Percentage"]
        )
        fig_pie.update_traces(textinfo="label+percent+value", pull=[0, 0.08])
        fig_pie.update_layout(template="plotly_dark", legend_title="Failure Status", height=380, **DARK_LAYOUT)
        st.plotly_chart(fig_pie, use_container_width=True, config=PLOTLY_CONFIG)

    with col2:
        fig_donut = px.pie(
            fail_counts,
            names="Status",
            values="Count",
            title="Donut Chart: Health Ratio",
            color="Status",
            color_discrete_map={"No Failure": "#22C55E", "Failure": "#EF4444"},
            hole=0.45,
            hover_data=["Percentage"]
        )
        fig_donut.update_traces(textinfo="label+percent")
        fig_donut.update_layout(template="plotly_dark", legend_title="Failure Status", height=380, **DARK_LAYOUT)
        st.plotly_chart(fig_donut, use_container_width=True, config=PLOTLY_CONFIG)

    with col3:
        fig_bar = px.bar(
            fail_counts,
            x="Status",
            y="Count",
            text="Count",
            color="Status",
            color_discrete_map={"No Failure": "#22C55E", "Failure": "#EF4444"},
            title="Bar Chart: Volume Comparison",
            hover_data=["Percentage"]
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(
            template="plotly_dark",
            xaxis_title="Machine Failure Status",
            yaxis_title="Count of Machines",
            showlegend=False,
            height=380,
            **DARK_LAYOUT
        )
        st.plotly_chart(fig_bar, use_container_width=True, config=PLOTLY_CONFIG)


# -------------------------------------------------------------
# 5. Machine Type Distribution Section
# -------------------------------------------------------------
def machine_type_section(df: pd.DataFrame):
    """
    Displays counts of Low (L), Medium (M), and High (H) machines.
    """
    st.markdown("---")
    st.markdown("### 🏭 Machine Type Distribution")

    if df.empty or "Type" not in df.columns:
        st.warning("No machine type data available.")
        return

    type_counts = df["Type"].value_counts().reset_index()
    type_counts.columns = ["Type Code", "Count"]
    type_labels = {"L": "Low (L)", "M": "Medium (M)", "H": "High (H)"}
    type_counts["Machine Type"] = type_counts["Type Code"].map(lambda x: type_labels.get(x, x))
    total = len(df)
    type_counts["Percentage"] = (type_counts["Count"] / total * 100).round(2)

    col1, col2 = st.columns(2)

    with col1:
        fig_pie = px.pie(
            type_counts,
            names="Machine Type",
            values="Count",
            title="Pie Chart: Machine Type Breakdown",
            color="Machine Type",
            color_discrete_sequence=["#2563EB", "#8B5CF6", "#F59E0B"],
            hover_data=["Percentage"]
        )
        fig_pie.update_traces(textinfo="label+percent+value")
        fig_pie.update_layout(template="plotly_dark", legend_title="Machine Type", height=380, **DARK_LAYOUT)
        st.plotly_chart(fig_pie, use_container_width=True, config=PLOTLY_CONFIG)

    with col2:
        fig_bar = px.bar(
            type_counts,
            x="Machine Type",
            y="Count",
            text="Count",
            color="Machine Type",
            color_discrete_sequence=["#2563EB", "#8B5CF6", "#F59E0B"],
            title="Bar Chart: Low, Medium, High Fleet Count",
            hover_data=["Percentage"]
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(
            template="plotly_dark",
            xaxis_title="Machine Type",
            yaxis_title="Count of Equipment Units",
            showlegend=False,
            height=380,
            **DARK_LAYOUT
        )
        st.plotly_chart(fig_bar, use_container_width=True, config=PLOTLY_CONFIG)


# -------------------------------------------------------------
# 6. Core Thermal & Dynamic Telemetry Section
# -------------------------------------------------------------
def create_charts(df: pd.DataFrame):
    """
    Renders core interactive Plotly visualizations in Dark Theme:
    - Pre-aggregated Histogram of Air Temperature
    - Pre-aggregated Histogram of Process Temperature
    - Deterministic Scatter Plot: RPM vs Torque
    - Box Plot: Tool Wear vs Machine Type
    """
    st.markdown("---")
    st.markdown("### 🌡️ Temperature, Torque & Tool Wear Analytics")

    if df.empty:
        st.warning("No data available for telemetry charts.")
        return

    col1, col2 = st.columns(2)

    with col1:
        if "Air temperature [K]" in df.columns:
            binned_air = compute_dashboard_histogram_bins(df, "Air temperature [K]", nbins=30)
            fig_air = px.bar(
                binned_air,
                x="Bin Center",
                y="Count",
                title="🌡️ Air Temperature Distribution",
                color_discrete_sequence=["#2563EB"]
            )
            fig_air.update_layout(
                template="plotly_dark",
                xaxis_title="Air Temperature [K]",
                yaxis_title="Count of Machines",
                bargap=0.05,
                height=380,
                **DARK_LAYOUT
            )
            st.plotly_chart(fig_air, use_container_width=True, config=PLOTLY_CONFIG)

    with col2:
        if "Process temperature [K]" in df.columns:
            binned_proc = compute_dashboard_histogram_bins(df, "Process temperature [K]", nbins=30)
            fig_proc = px.bar(
                binned_proc,
                x="Bin Center",
                y="Count",
                title="🔥 Process Temperature Distribution",
                color_discrete_sequence=["#8B5CF6"]
            )
            fig_proc.update_layout(
                template="plotly_dark",
                xaxis_title="Process Temperature [K]",
                yaxis_title="Count of Machines",
                bargap=0.05,
                height=380,
                **DARK_LAYOUT
            )
            st.plotly_chart(fig_proc, use_container_width=True, config=PLOTLY_CONFIG)

    col3, col4 = st.columns(2)

    with col3:
        if "Rotational speed [rpm]" in df.columns and "Torque [Nm]" in df.columns and "Machine failure" in df.columns:
            scatter_df = get_dashboard_scatter_sample(df, n=2000, seed=42).copy()
            scatter_df["Failure Status"] = scatter_df["Machine failure"].map({0: "No Failure", 1: "Failure"})
            fig_rpm_trq = px.scatter(
                scatter_df,
                x="Rotational speed [rpm]",
                y="Torque [Nm]",
                color="Failure Status",
                color_discrete_map={"No Failure": "#22C55E", "Failure": "#EF4444"},
                title="⚡ Scatter Plot: RPM vs Torque (Color by Failure)",
                hover_data=["Type", "Tool wear [min]"],
                opacity=0.75
            )
            fig_rpm_trq.update_layout(
                template="plotly_dark",
                xaxis_title="Rotational Speed (RPM)",
                yaxis_title="Torque (Nm)",
                legend_title="Machine Failure",
                height=380,
                **DARK_LAYOUT
            )
            st.plotly_chart(fig_rpm_trq, use_container_width=True, config=PLOTLY_CONFIG)

    with col4:
        if "Tool wear [min]" in df.columns and "Type" in df.columns:
            fig_box_wear = px.box(
                df,
                x="Type",
                y="Tool wear [min]",
                color="Type",
                color_discrete_sequence=["#2563EB", "#8B5CF6", "#F59E0B"],
                title="🛠️ Box Plot: Tool Wear vs Machine Type",
                points=False
            )
            fig_box_wear.update_layout(
                template="plotly_dark",
                xaxis_title="Machine Type (L, M, H)",
                yaxis_title="Tool Wear [min]",
                height=380,
                **DARK_LAYOUT
            )
            st.plotly_chart(fig_box_wear, use_container_width=True, config=PLOTLY_CONFIG)


# -------------------------------------------------------------
# 7. RPM and Tool Wear Analysis Section
# -------------------------------------------------------------
def rpm_analysis(df: pd.DataFrame):
    """
    Creates an analysis section for RPM and Tool Wear.
    """
    st.markdown("---")
    st.markdown("### ⚙️ Speed & Tool Wear Operational Envelope")

    if df.empty:
        st.warning("No data available for RPM and Tool Wear Analysis.")
        return

    analysis_df = df.copy()
    if "Machine failure" in analysis_df.columns:
        analysis_df["Failure Status"] = analysis_df["Machine failure"].map({0: "No Failure", 1: "Failure"})

    col1, col2 = st.columns(2)

    with col1:
        if "Rotational speed [rpm]" in analysis_df.columns:
            binned_rpm = compute_dashboard_histogram_bins(analysis_df, "Rotational speed [rpm]", nbins=35)
            fig_rpm = px.bar(
                binned_rpm,
                x="Bin Center",
                y="Count",
                title="🔄 RPM Distribution Histogram",
                color_discrete_sequence=["#2563EB"]
            )
            fig_rpm.update_layout(
                template="plotly_dark",
                xaxis_title="Rotational Speed (RPM)",
                yaxis_title="Count",
                bargap=0.05,
                height=380,
                **DARK_LAYOUT
            )
            st.plotly_chart(fig_rpm, use_container_width=True, config=PLOTLY_CONFIG)

    with col2:
        if "Tool wear [min]" in analysis_df.columns:
            binned_wear = compute_dashboard_histogram_bins(analysis_df, "Tool wear [min]", nbins=35)
            fig_wear = px.bar(
                binned_wear,
                x="Bin Center",
                y="Count",
                title="🛠️ Tool Wear Distribution Histogram",
                color_discrete_sequence=["#F59E0B"]
            )
            fig_wear.update_layout(
                template="plotly_dark",
                xaxis_title="Tool Wear (min)",
                yaxis_title="Count",
                bargap=0.05,
                height=380,
                **DARK_LAYOUT
            )
            st.plotly_chart(fig_wear, use_container_width=True, config=PLOTLY_CONFIG)

    col3, col4 = st.columns(2)

    with col3:
        if "Rotational speed [rpm]" in analysis_df.columns and "Tool wear [min]" in analysis_df.columns:
            scatter_rpm = get_dashboard_scatter_sample(analysis_df, n=2000, seed=42)
            fig_rpm_wear = px.scatter(
                scatter_rpm,
                x="Rotational speed [rpm]",
                y="Tool wear [min]",
                color="Failure Status" if "Failure Status" in scatter_rpm.columns else None,
                color_discrete_map={"No Failure": "#22C55E", "Failure": "#EF4444"},
                title="📍 RPM vs Tool Wear Scatter Plot",
                opacity=0.65
            )
            fig_rpm_wear.update_layout(
                template="plotly_dark",
                xaxis_title="Rotational Speed (RPM)",
                yaxis_title="Tool Wear (min)",
                height=380,
                **DARK_LAYOUT
            )
            st.plotly_chart(fig_rpm_wear, use_container_width=True, config=PLOTLY_CONFIG)

    with col4:
        if "Torque [Nm]" in analysis_df.columns and "Tool wear [min]" in analysis_df.columns:
            scatter_trq = get_dashboard_scatter_sample(analysis_df, n=2000, seed=42)
            fig_trq_wear = px.scatter(
                scatter_trq,
                x="Torque [Nm]",
                y="Tool wear [min]",
                color="Failure Status" if "Failure Status" in scatter_trq.columns else None,
                color_discrete_map={"No Failure": "#22C55E", "Failure": "#EF4444"},
                title="⚡ Torque vs Tool Wear Scatter Plot",
                opacity=0.65
            )
            fig_trq_wear.update_layout(
                template="plotly_dark",
                xaxis_title="Torque (Nm)",
                yaxis_title="Tool Wear (min)",
                height=380,
                **DARK_LAYOUT
            )
            st.plotly_chart(fig_trq_wear, use_container_width=True, config=PLOTLY_CONFIG)


# -------------------------------------------------------------
# 8. Main Render Function
# -------------------------------------------------------------
def render_dashboard_page(df: pd.DataFrame = None):
    """
    Main renderer for Module 2: AI Predictive Maintenance Dashboard.
    """
    st.title("📈 Module 2: AI Executive Dashboard")
    st.caption("Real-time telemetry KPIs, fleet distribution models, interactive risk charts, and downloadable datasets.")

    with st.spinner("Rendering Dashboard Metrics..."):
        if df is None or df.empty:
            df = load_data()

        if df.empty:
            st.error("❌ Unable to load telemetry dataset for Dashboard.")
            return

        filtered_df = create_sidebar(df)

    col_hdr1, col_hdr2 = st.columns([3, 1])
    with col_hdr1:
        st.success(f"Displaying **{len(filtered_df):,}** filtered records out of **{len(df):,}** total machinery rows.")
    with col_hdr2:
        csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Filtered CSV",
            data=csv_bytes,
            file_name="filtered_preventive_maintenance_data.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
            key="dash_export_csv_btn"
        )

    # 1. KPI Cards
    display_kpis(filtered_df)

    # 2. Machine Failure Distribution Section
    machine_failure_section(filtered_df)

    # 3. Machine Type Distribution Section
    machine_type_section(filtered_df)

    # 4. Interactive Plotly Charts Section (Thermal, Torque & Tool Wear Analytics)
    create_charts(filtered_df)

    # 5. RPM and Tool Wear Analysis Section
    rpm_analysis(filtered_df)

