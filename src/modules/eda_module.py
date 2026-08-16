import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Unified Dark Theme Styling Helper for Plotly Figures
DARK_LAYOUT = dict(
    paper_bgcolor="#1E293B",
    plot_bgcolor="#0F172A",
    font=dict(color="#F8FAFC", family="Inter, sans-serif"),
    xaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
    yaxis=dict(gridcolor="#334155", zerolinecolor="#334155")
)
COLOR_PALETTE = ['#2563EB', '#22C55E', '#F59E0B', '#EF4444', '#8B5CF6', '#38BDF8']

# Stable Plotly rendering configuration to prevent hover/resize modebar jitter
PLOTLY_CONFIG = {
    "displayModeBar": False,
    "responsive": True
}

# -------------------------------------------------------------
# Cached EDA Helper Calculations
# -------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_eda_overview_metrics(df: pd.DataFrame):
    total_rows = df.shape[0]
    total_cols = df.shape[1]
    missing_vals = int(df.isnull().sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    return total_rows, total_cols, missing_vals, duplicate_rows

@st.cache_data(show_spinner=False)
def get_schema_and_null_summaries(df: pd.DataFrame):
    dtype_df = pd.DataFrame({
        "Column Name": df.columns,
        "Data Type": [str(dtype) for dtype in df.dtypes],
        "Non-Null Count": df.notnull().sum().values
    })
    null_df = pd.DataFrame({
        "Column Name": df.columns,
        "Missing Count": df.isnull().sum().values,
        "Missing Percentage (%)": (df.isnull().sum().values / len(df) * 100).round(2)
    })
    return dtype_df, null_df

@st.cache_data(show_spinner=False)
def get_statistical_summary(df: pd.DataFrame):
    return df.describe().T

@st.cache_data(show_spinner=False)
def get_correlation_matrix(df: pd.DataFrame):
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    if "UDI" in numeric_cols:
        numeric_cols.remove("UDI")  # Exclude non-telemetry ID column
    return df[numeric_cols].corr()

@st.cache_data(show_spinner=False)
def get_deterministic_sample(df: pd.DataFrame, n: int = 10, seed: int = 42):
    return df.sample(n=min(n, len(df)), random_state=seed)

@st.cache_data(show_spinner=False)
def compute_histogram_bins(df: pd.DataFrame, col: str, nbins: int = 30):
    clean_data = df[col].dropna()
    counts, bin_edges = np.histogram(clean_data, bins=nbins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    return pd.DataFrame({
        "Bin Center": bin_centers,
        "Count": counts
    })

@st.cache_data(show_spinner=False)
def get_scatter_sample(df: pd.DataFrame, n: int = 2000, seed: int = 42):
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=seed)

@st.cache_data(show_spinner=False)
def get_eda_analytical_insights(df: pd.DataFrame):
    avg_air = float(df["Air temperature [K]"].mean()) if "Air temperature [K]" in df.columns else 0.0
    avg_proc = float(df["Process temperature [K]"].mean()) if "Process temperature [K]" in df.columns else 0.0
    avg_delta = avg_proc - avg_air
    max_wear = float(df["Tool wear [min]"].max()) if "Tool wear [min]" in df.columns else 0.0
    total_len = len(df)
    return avg_air, avg_proc, avg_delta, max_wear, total_len

def render_eda_page(df: pd.DataFrame):
    """
    Module 1: Exploratory Data Analysis (EDA)
    Exploratory data analysis, dataset inspection, statistical summaries,
    correlation matrix, histograms, box plots, scatter plots, and outlier analysis.
    """
    # Anti-jitter layout stabilization CSS
    st.markdown("""
        <style>
            div[data-testid="stPlotlyChart"] {
                overflow: hidden !important;
                border-radius: 8px;
            }
            div[data-testid="stDataFrame"] {
                overflow: hidden !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("📈 Module 1: Exploratory Data Analysis (EDA)")
    st.caption("Deep-dive exploratory analysis, statistical distributions, correlation, and feature relationships.")

    if df.empty:
        st.error("No telemetry data available for Exploratory Data Analysis.")
        return

    # -------------------------------------------------------------
    # 1. Dataset Overview & Structural Properties
    # -------------------------------------------------------------
    st.header("1. Dataset Overview & Metadata")
    
    total_rows, total_cols, missing_vals, duplicate_rows = get_eda_overview_metrics(df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Records (Rows)", f"{total_rows:,}")
    col2.metric("Total Features (Columns)", f"{total_cols}")
    col3.metric("Missing Values Count", f"{missing_vals}")
    col4.metric("Duplicate Rows", f"{duplicate_rows}")

    st.subheader("Data Preview")
    view_option = st.radio(
        "Preview Rows",
        ["First 10 Rows (Head)", "Last 10 Rows (Tail)", "Random Sample (10 Rows)"],
        horizontal=True,
        key="eda_preview_option"
    )
    if view_option == "First 10 Rows (Head)":
        st.dataframe(df.head(10), use_container_width=True, hide_index=True, height=380)
    elif view_option == "Last 10 Rows (Tail)":
        st.dataframe(df.tail(10), use_container_width=True, hide_index=True, height=380)
    else:
        st.dataframe(get_deterministic_sample(df, 10), use_container_width=True, hide_index=True, height=380)

    st.divider()

    # -------------------------------------------------------------
    # 2. Data Types & Missing Value Analysis
    # -------------------------------------------------------------
    st.header("2. Schema Data Types & Missing Values")
    col_dt1, col_dt2 = st.columns(2)

    dtype_df, null_df = get_schema_and_null_summaries(df)

    with col_dt1:
        st.subheader("Column Data Types")
        st.dataframe(dtype_df, use_container_width=True, hide_index=True, height=350)

    with col_dt2:
        st.subheader("Missing Value Summary")
        st.dataframe(null_df, use_container_width=True, hide_index=True, height=350)

    st.divider()

    # -------------------------------------------------------------
    # 3. Statistical Summary
    # -------------------------------------------------------------
    st.header("3. Descriptive Statistical Summary")
    st.write("Summary statistics for all numerical features in the telemetry dataset:")
    st.dataframe(get_statistical_summary(df), use_container_width=True, height=350)

    st.divider()

    # -------------------------------------------------------------
    # 4. Correlation Matrix & Heatmap
    # -------------------------------------------------------------
    st.header("4. Correlation Analysis & Heatmap")
    st.write("Examines pairwise linear correlations across numerical telemetry features.")

    corr_matrix = get_correlation_matrix(df)

    c_col1, c_col2 = st.columns([1, 2])
    with c_col1:
        st.subheader("Correlation Table")
        st.dataframe(corr_matrix.round(3), use_container_width=True, height=450)

    with c_col2:
        fig_corr = px.imshow(
            corr_matrix,
            text_auto=".2f",
            aspect="auto",
            title="Interactive Telemetry Correlation Heatmap",
            color_continuous_scale="Blues"
        )
        fig_corr.update_layout(
            height=450,
            autosize=True,
            margin=dict(l=20, r=20, t=50, b=20),
            template="plotly_dark",
            **DARK_LAYOUT
        )
        st.plotly_chart(fig_corr, use_container_width=True, config=PLOTLY_CONFIG)

    st.divider()

    # -------------------------------------------------------------
    # 5. Distributions & Histograms
    # -------------------------------------------------------------
    st.header("5. Feature Distribution Histograms")
    st.write("Distribution analysis for continuous sensor measurements:")

    sensor_cols = ["Air temperature [K]", "Process temperature [K]", "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]
    available_sensors = [c for c in sensor_cols if c in df.columns]

    nbins = st.slider("Select Histogram Bins", min_value=10, max_value=100, value=30, step=5, key="eda_hist_bins")

    hist_cols = st.columns(2)
    for i, col in enumerate(available_sensors):
        binned_df = compute_histogram_bins(df, col, nbins=nbins)
        fig_hist = px.bar(
            binned_df,
            x="Bin Center",
            y="Count",
            title=f"{col} Distribution",
            color_discrete_sequence=['#2563EB']
        )
        fig_hist.update_layout(
            height=350,
            autosize=True,
            margin=dict(l=20, r=20, t=50, b=20),
            template="plotly_dark",
            xaxis_title=col,
            yaxis_title="Count",
            bargap=0.05,
            **DARK_LAYOUT
        )
        with hist_cols[i % 2]:
            st.plotly_chart(fig_hist, use_container_width=True, config=PLOTLY_CONFIG)

    st.divider()

    # -------------------------------------------------------------
    # 6. Box Plots & Outlier Detection
    # -------------------------------------------------------------
    st.header("6. Outlier Detection & Box Plots")
    st.write("Box plot analysis showing median, quartiles, and statistical outliers across machine types.")

    selected_box_col = st.selectbox(
        "Select Telemetry Feature for Box Plot Analysis",
        options=available_sensors,
        index=0,
        key="eda_box_feature"
    )

    box_col1, box_col2 = st.columns(2)

    with box_col1:
        fig_box_type = px.box(
            df,
            x="Type",
            y=selected_box_col,
            color="Type",
            title=f"{selected_box_col} by Machine Type (L/M/H)",
            points=False,
            color_discrete_sequence=COLOR_PALETTE
        )
        fig_box_type.update_layout(
            height=400,
            autosize=True,
            margin=dict(l=20, r=20, t=50, b=20),
            template="plotly_dark",
            **DARK_LAYOUT
        )
        st.plotly_chart(fig_box_type, use_container_width=True, config=PLOTLY_CONFIG)

    with box_col2:
        if "Machine failure" in df.columns:
            fig_box_fail = px.box(
                df,
                x="Machine failure",
                y=selected_box_col,
                color="Machine failure",
                title=f"{selected_box_col} grouped by Failure Flag (0 = Normal, 1 = Failed)",
                points=False,
                color_discrete_sequence=['#22C55E', '#EF4444']
            )
            fig_box_fail.update_layout(
                height=400,
                autosize=True,
                margin=dict(l=20, r=20, t=50, b=20),
                template="plotly_dark",
                **DARK_LAYOUT
            )
            st.plotly_chart(fig_box_fail, use_container_width=True, config=PLOTLY_CONFIG)

    # -------------------------------------------------------------
    # 7. Scatter Plots & Feature Relationships
    # -------------------------------------------------------------
    st.divider()
    st.header("7. Feature Relationships & Scatter Plots")
    st.write("Explore multi-variable relationships and clusters across telemetry metrics.")

    sc_col1, sc_col2 = st.columns(2)
    with sc_col1:
        x_axis = st.selectbox("X-Axis Feature", options=available_sensors, index=2, key="eda_scatter_x")  # RPM
    with sc_col2:
        y_axis = st.selectbox("Y-Axis Feature", options=available_sensors, index=3, key="eda_scatter_y")  # Torque

    color_by = st.selectbox("Color By", options=["Machine failure", "Type", "TWF", "HDF", "PWF", "OSF", "RNF"], index=0, key="eda_scatter_color")

    scatter_df = get_scatter_sample(df, n=2000, seed=42)
    fig_scatter = px.scatter(
        scatter_df,
        x=x_axis,
        y=y_axis,
        color=color_by,
        title=f"{x_axis} vs {y_axis} (Colored by {color_by})",
        hover_data=["Product ID", "Type", "Machine failure"],
        opacity=0.7,
        color_discrete_sequence=COLOR_PALETTE
    )
    fig_scatter.update_layout(
        height=500,
        autosize=True,
        margin=dict(l=20, r=20, t=50, b=20),
        template="plotly_dark",
        **DARK_LAYOUT
    )
    st.plotly_chart(fig_scatter, use_container_width=True, config=PLOTLY_CONFIG)

    # -------------------------------------------------------------
    # 8. EDA Data Insights & Summary
    # -------------------------------------------------------------
    st.divider()
    st.header("8. Exploratory Data Insights Summary")

    avg_air, avg_proc, avg_delta, max_wear, total_len = get_eda_analytical_insights(df)
    missing_val_msg = "zero missing values" if missing_vals == 0 else f"{missing_vals:,} missing values"

    st.info(f"""
    💡 **Key Analytical Findings**:
    - **Thermal Behavior**: Average ambient temperature is **{avg_air:.2f} K** while process temperature averages **{avg_proc:.2f} K** (mean thermal delta = **{avg_delta:.2f} K**).
    - **Rotational Speed & Torque**: Inverse relationship observed between rotational speed (RPM) and torque (Nm), consistent with constant power operational envelopes.
    - **Tool Wear Accumulation**: Maximum tool wear recorded in dataset reaches **{max_wear} min**, with critical failure probability escalating beyond 180-200 minutes of continuous wear.
    - **Data Integrity**: Total dataset size is **{total_len:,} rows** with {missing_val_msg} across telemetry fields.
    """)


