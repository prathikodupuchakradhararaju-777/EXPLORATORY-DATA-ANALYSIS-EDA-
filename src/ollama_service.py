import os
import streamlit as st
import pandas as pd
import ollama
import concurrent.futures
import socket
import time
from typing import Dict, Any, Tuple, Generator, List

# -----------------------------------------------------------------------------
# Connectivity Check & Singleton Ollama Client
# -----------------------------------------------------------------------------
@st.cache_resource
def get_ollama_client() -> ollama.Client:
    """
    Instantiates and caches a single Ollama client instance.
    """
    return ollama.Client()


def is_ollama_available(timeout: float = 0.1) -> bool:
    """
    Fast socket check to determine if Ollama daemon is running on localhost:11434.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex(('127.0.0.1', 11434))
        sock.close()
        return result == 0
    except Exception:
        return False


# -----------------------------------------------------------------------------
# KPI Aggregation
# -----------------------------------------------------------------------------
@st.cache_data
def compute_dataset_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates maintenance KPIs in a single pass to avoid repeated computations.
    """
    if df.empty:
        return {}

    total_machines = len(df)
    machine_failures = int(df["Machine failure"].sum())
    avg_air_temp = float(df["Air temperature [K]"].mean())
    avg_process_temp = float(df["Process temperature [K]"].mean())
    avg_rot_speed = float(df["Rotational speed [rpm]"].mean())
    avg_torque = float(df["Torque [Nm]"].mean())
    avg_tool_wear = float(df["Tool wear [min]"].mean())

    failure_cols = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']
    failure_dist = {}
    for col in failure_cols:
        if col in df.columns:
            failure_dist[col] = int(df[col].sum())

    return {
        "total_machines": total_machines,
        "machine_failures": machine_failures,
        "failure_rate_pct": round((machine_failures / total_machines) * 100, 2) if total_machines > 0 else 0,
        "avg_air_temp": round(avg_air_temp, 2),
        "avg_process_temp": round(avg_process_temp, 2),
        "avg_rot_speed": round(avg_rot_speed, 2),
        "avg_torque": round(avg_torque, 2),
        "avg_tool_wear": round(avg_tool_wear, 2),
        "failure_distribution": failure_dist
    }


# -----------------------------------------------------------------------------
# Fast Generation Options & Python Failure Flag Extraction
# -----------------------------------------------------------------------------
FAST_OLLAMA_OPTIONS = {
    "temperature": 0.2,
    "top_p": 0.9,
    "num_predict": 600,
    "num_ctx": 2048,
    "num_thread": max(1, os.cpu_count() or 4)
}


def extract_machine_failure_flags(machine_info: Dict[str, Any]) -> Tuple[List[str], str, str]:
    """
    Python logic to determine failure flags from machine telemetry:
    TWF = Tool Wear Failure
    HDF = Heat Dissipation Failure
    PWF = Power Failure
    OSF = Overstrain Failure
    RNF = Random Failure
    Returns: (list_of_active_failures, detected_issues_summary, calculated_priority)
    """
    twf = int(machine_info.get('twf', machine_info.get('TWF', 0)))
    hdf = int(machine_info.get('hdf', machine_info.get('HDF', 0)))
    pwf = int(machine_info.get('pwf', machine_info.get('PWF', 0)))
    osf = int(machine_info.get('osf', machine_info.get('OSF', 0)))
    rnf = int(machine_info.get('rnf', machine_info.get('RNF', 0)))

    failures_str = str(machine_info.get('failures', ''))
    if 'TWF' in failures_str: twf = 1
    if 'HDF' in failures_str: hdf = 1
    if 'PWF' in failures_str: pwf = 1
    if 'OSF' in failures_str: osf = 1
    if 'RNF' in failures_str: rnf = 1

    active_failures = []
    if twf == 1: active_failures.append("Tool Wear Failure (TWF)")
    if hdf == 1: active_failures.append("Heat Dissipation Failure (HDF)")
    if pwf == 1: active_failures.append("Power Failure (PWF)")
    if osf == 1: active_failures.append("Overstrain Failure (OSF)")
    if rnf == 1: active_failures.append("Random Failure (RNF)")

    if not active_failures:
        detected_issues = "No specific failure condition detected from the supplied sensor data."
        priority = "LOW"
    else:
        detected_issues = ", ".join(active_failures)
        if any("PWF" in f or "HDF" in f for f in active_failures) or len(active_failures) >= 2:
            priority = "CRITICAL"
        elif any("OSF" in f or "TWF" in f for f in active_failures):
            priority = "HIGH"
        else:
            priority = "MEDIUM"

    return active_failures, detected_issues, priority


def clean_ai_report(report_text: str, default_issues: str = "No specific failure condition detected from the supplied sensor data.") -> str:
    """
    Cleans invalid empty/placeholder values like None, null, N/A, Unknown, Unavailable
    and ensures meaningful context-specific text without breaking valid words.
    """
    if not report_text or not report_text.strip():
        return ""

    import re
    cleaned = report_text.strip()

    invalid_patterns = [
        (r'\b(None|none|null|NULL|N/A|n/a|Unknown|Unavailable)\b', 'Not Applicable'),
        (r'(?i)Detected Issues:\s*(None|none|null|N/A|n/a)', f'Detected Issues:\n{default_issues}'),
    ]

    for pattern, repl in invalid_patterns:
        cleaned = re.sub(pattern, repl, cleaned)

    return cleaned


# -----------------------------------------------------------------------------
# Built-in Rule-Based AI Engine (Offline Fallback)
# -----------------------------------------------------------------------------
def generate_rule_based_machine_analysis(machine_info: Dict[str, Any]) -> str:
    """
    Generates a structured, concise diagnostic report matching the required structure.
    Used as an intelligent fallback when Ollama service is unreachable or timing out.
    """
    product_id = str(machine_info.get('product_id', 'Not Applicable'))
    m_type = str(machine_info.get('type', 'Not Applicable'))
    air_temp = machine_info.get('air_temp', 'Not Applicable')
    process_temp = machine_info.get('process_temp', 'Not Applicable')
    rot_speed = machine_info.get('rot_speed', 'Not Applicable')
    torque = machine_info.get('torque', 'Not Applicable')
    tool_wear = machine_info.get('tool_wear', 'Not Applicable')

    active_failures, detected_issues, priority = extract_machine_failure_flags(machine_info)
    has_failure = len(active_failures) > 0

    if priority in ["CRITICAL", "HIGH"]:
        condition = f"Critical condition logged for machine {product_id} ({m_type}-Series). Parameter threshold breach detected."
    elif priority == "MEDIUM":
        condition = f"Warning condition logged for machine {product_id} ({m_type}-Series). Telemetry requires preventive monitoring."
    else:
        condition = f"Normal condition logged for machine {product_id} ({m_type}-Series). Equipment operating within standard margins."

    # Root Cause Analysis
    if "Tool Wear Failure (TWF)" in detected_issues or (isinstance(tool_wear, (int, float)) and tool_wear > 180):
        root_cause = f"High friction and abrasive tool wear accumulated over {tool_wear} minutes of continuous spindle operation."
    elif "Heat Dissipation Failure (HDF)" in detected_issues:
        root_cause = f"Thermal dissipation bottleneck between process temperature ({process_temp} K) and air temperature ({air_temp} K)."
    elif "Power Failure (PWF)" in detected_issues:
        root_cause = f"Drive motor power fluctuation or electrical torque imbalance ({torque} Nm at {rot_speed} RPM)."
    elif "Overstrain Failure (OSF)" in detected_issues:
        root_cause = f"Combined heavy mechanical torque load ({torque} Nm) and rotational speed causing structural load strain."
    elif "Random Failure (RNF)" in detected_issues:
        root_cause = "Transient electrical noise or micro-vibration spike triggering anomaly detection sensors."
    else:
        root_cause = "No physical degradation observed. Sensor telemetry exhibits stable operational equilibrium."

    # Recommended Actions
    if "Tool Wear Failure (TWF)" in detected_issues or (isinstance(tool_wear, (int, float)) and tool_wear > 180):
        rec1 = f"Inspect cutting tool insert condition for machine {product_id} and measure dimensional wear."
        rec2 = "Replace worn tool bit insert and perform spindle axis alignment."
        rec3 = "Calibrate tool offset parameters in CNC control interface."
    elif "Heat Dissipation Failure (HDF)" in detected_issues:
        rec1 = "Inspect cooling system fluid level and clean intake radiator filters."
        rec2 = "Flush thermal heat exchanger lines and verify coolant pump pressure."
        rec3 = "Monitor process temperature differential during high-rpm work cycles."
    elif "Power Failure (PWF)" in detected_issues:
        rec1 = "Inspect drive motor electrical wiring and verify grounding connections."
        rec2 = "Check power input supply voltage and calibrate drive controller torque limiters."
        rec3 = "Audit inverter fault history logs for over-current trip indicators."
    elif "Overstrain Failure (OSF)" in detected_issues:
        rec1 = "Inspect drive shaft assembly and spindle bearings for mechanical strain."
        rec2 = "Reduce operating load rate and adjust maximum torque limit parameters."
        rec3 = "Perform dynamic balance test on rotational drive assembly."
    else:
        rec1 = "Inspect tool edge wear and log current telemetry baselines."
        rec2 = "Check coolant reservoir level and clean air intake ventilation."
        rec3 = "Inspect motor electrical grounding and verify rotational speed stability."

    # Preventive Maintenance
    prev_maint = f"Perform routine preventive maintenance and sensor audit on machine {product_id} according to standard schedule."

    # Technician Note
    if priority in ["CRITICAL", "HIGH"]:
        tech_note = f"Perform lockout/tagout procedure before servicing machine {product_id}. Verify sensor calibration after maintenance."
    else:
        tech_note = f"Log telemetry readings during next routine shift check for machine {product_id}."

    # Final Assessment
    final_assess = f"Machine {product_id} maintenance review complete with priority {priority}. Execute recommendations per operating schedule."

    report = f"""MACHINE DIAGNOSTIC REPORT

Machine Condition:
{condition}

Detected Issues:
{detected_issues}

Root Cause Analysis:
{root_cause}

Maintenance Priority:
{priority}

Recommended Actions:
1. {rec1}
2. {rec2}
3. {rec3}

Preventive Maintenance:
{prev_maint}

Technician Note:
{tech_note}

Final Assessment:
{final_assess}"""

    return report


def generate_rule_based_executive_report(kpis: Dict[str, Any]) -> str:
    """
    Generates a dataset-wide executive maintenance report using rule-based summary logic.
    """
    if not kpis:
        return "No dataset KPIs provided for analysis."

    total_m = kpis.get("total_machines", 0)
    failures = kpis.get("machine_failures", 0)
    rate = kpis.get("failure_rate_pct", 0)
    avg_air = kpis.get("avg_air_temp", 0)
    avg_proc = kpis.get("avg_process_temp", 0)
    avg_rpm = kpis.get("avg_rot_speed", 0)
    avg_torq = kpis.get("avg_torque", 0)
    avg_wear = kpis.get("avg_tool_wear", 0)
    dist = kpis.get("failure_distribution", {})

    dist_items = [f"**{k}**: {v}" for k, v in dist.items() if v > 0]
    dist_str = ", ".join(dist_items) if dist_items else "No specific failure modes recorded"

    lines = []
    lines.append("### Executive Fleet Maintenance Report")
    lines.append(f"*{'Ollama Local LLM' if is_ollama_available() else 'Built-in Dataset Analytics Engine'}*\n")
    lines.append(f"- **Executive Health Summary**: Fleet monitoring covers **{total_m:,}** equipment units. Total logged machine failures: **{failures:,}** (**{rate}%** overall failure rate).")
    lines.append(f"- **Telemetry Baselines**: Fleet average ambient air temp is **{avg_air} K** with process temp at **{avg_proc} K** (mean ΔT = **{round(avg_proc - avg_air, 2)} K**). Mean operating speed is **{avg_rpm} RPM**, average torque is **{avg_torq} Nm**, and mean tool wear is **{avg_wear} min**.")
    lines.append(f"- **Failure Mode Distribution**: {dist_str}.")
    lines.append("- **Strategic Recommendations**:")
    lines.append("  1. **Tool Wear Management**: Prioritize tool replacement for machines exceeding 180 minutes wear to prevent TWF spikes.")
    lines.append("  2. **Thermal Dissipation Audit**: Ensure cooling systems maintain ΔT > 8.6 K under heavy rotational speeds.")
    lines.append("  3. **Load Optimization**: Balance machine work assignments to minimize overstrain (OSF) and power surges (PWF).")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Complete Response Interfaces (Non-Streaming & Backend First)
# -----------------------------------------------------------------------------
def stream_machine_analysis(machine_info: Dict[str, Any], model_name: str = "llama3.2") -> Generator[str, None, None]:
    """
    Returns the complete machine analysis report at once after backend generation finishes.
    """
    _, report_text = generate_machine_analysis(machine_info, model_name=model_name)
    yield report_text


def _execute_ollama_chat(client: ollama.Client, model: str, prompt: str, options: dict) -> str:
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options=options,
        keep_alive="1h"
    )
    return response["message"]["content"]


@st.cache_data
def generate_maintenance_report(kpis: Dict[str, Any], model_name: str = "llama3.2", timeout: int = 30) -> Tuple[bool, str]:
    """
    Generates dataset-wide executive maintenance report.
    Tries Ollama first, falls back gracefully to built-in engine if unavailable.
    """
    if not kpis:
        return False, "No dataset KPIs provided for analysis."

    if is_ollama_available(timeout=0.1):
        prompt = f"""You are an AI Equipment Fleet Reliability Engineer. Summarize this equipment dataset maintenance status:
- Total Machines: {kpis['total_machines']}
- Machine Failures: {kpis['machine_failures']} ({kpis['failure_rate_pct']}%)
- Avg Air Temp: {kpis['avg_air_temp']} K
- Avg Process Temp: {kpis['avg_process_temp']} K
- Avg Rotational Speed: {kpis['avg_rot_speed']} RPM
- Avg Torque: {kpis['avg_torque']} Nm
- Avg Tool Wear: {kpis['avg_tool_wear']} min
- Failure Distribution: {kpis['failure_distribution']}

Provide a crisp Executive Maintenance Report (250-300 words). Cover key operational risks, sensor norms, and strategic priority action items."""
        client = get_ollama_client()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(_execute_ollama_chat, client, model_name, prompt, FAST_OLLAMA_OPTIONS)
            report_text = future.result(timeout=timeout)
            executor.shutdown(wait=False)
            return True, clean_ai_report(report_text)
        except Exception:
            executor.shutdown(wait=False)
            pass  # Fall back to built-in generator

    return True, generate_rule_based_executive_report(kpis)


def generate_machine_analysis(machine_info: Dict[str, Any], model_name: str = "llama3.2", timeout: int = 30) -> Tuple[bool, str]:
    """
    Generates complete machine-specific report using Python failure evaluation and Ollama fast execution.
    Failsafe fallback to built-in rule engine if Ollama is unreachable, times out, or returns empty text.
    """
    p_id = str(machine_info.get('product_id', 'Not Applicable'))
    m_type = str(machine_info.get('type', 'Not Applicable'))
    air_t = machine_info.get('air_temp', 'Not Applicable')
    proc_t = machine_info.get('process_temp', 'Not Applicable')
    rot_s = machine_info.get('rot_speed', 'Not Applicable')
    torq = machine_info.get('torque', 'Not Applicable')
    wear = machine_info.get('tool_wear', 'Not Applicable')

    # Python failure flag evaluation
    active_failures, detected_issues, priority = extract_machine_failure_flags(machine_info)

    if is_ollama_available(timeout=0.1):
        prompt = f"""You are an expert AI industrial reliability engineer. Generate a fast, concise machine maintenance report for equipment {p_id}.

SUPPLIED MACHINE TELEMETRY DATA:
- Machine ID: {p_id}
- Machine Type: {m_type}
- Air Temperature: {air_t} K
- Process Temperature: {proc_t} K
- Rotational Speed: {rot_s} RPM
- Torque: {torq} Nm
- Tool Wear: {wear} min
- Python Detected Issues: {detected_issues}
- Calculated Priority: {priority}

STRICT INSTRUCTIONS:
1. Return EXACTLY the Markdown structure below with no extra headings or markdown preamble.
2. Every section must contain meaningful, actionable technical information based on the actual sensor values provided.
3. NEVER output words like "None", "null", "N/A", "Unknown", or "Unavailable".
4. Recommended Actions must be specific actionable maintenance steps.

STRICT STRUCTURE TO RETURN:

MACHINE DIAGNOSTIC REPORT

Machine Condition:
[Short 1-2 sentence assessment of machine condition]

Detected Issues:
{detected_issues}

Root Cause Analysis:
[Concise root cause explanation based on telemetry]

Maintenance Priority:
{priority}

Recommended Actions:
1. [Actionable step 1]
2. [Actionable step 2]
3. [Actionable step 3]

Preventive Maintenance:
[Practical preventive maintenance recommendation]

Technician Note:
[Short practical instruction for service technician]

Final Assessment:
[One concise concluding sentence]
"""

        client = get_ollama_client()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        try:
            future = executor.submit(_execute_ollama_chat, client, model_name, prompt, FAST_OLLAMA_OPTIONS)
            analysis_text = future.result(timeout=timeout)
            executor.shutdown(wait=False)
            if analysis_text and len(analysis_text.strip()) > 50:
                cleaned_report = clean_ai_report(analysis_text, detected_issues)
                return True, cleaned_report
        except Exception:
            executor.shutdown(wait=False)
            pass

    # Seamless rule-based fallback if Ollama is unavailable or timed out
    fallback_report = generate_rule_based_machine_analysis(machine_info)
    return True, clean_ai_report(fallback_report, detected_issues)



