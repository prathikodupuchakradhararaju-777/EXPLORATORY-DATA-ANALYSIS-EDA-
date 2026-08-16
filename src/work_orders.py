import random
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple

try:
    from database import insert_work_order, fetch_all_work_orders, has_open_work_order
    from pdf_generator import create_workorder_pdf
except ImportError:
    from src.database import insert_work_order, fetch_all_work_orders, has_open_work_order
    from src.pdf_generator import create_workorder_pdf


def generate_work_order_id() -> str:
    """
    Generates a unique Work Order ID adhering strictly to the WO-YYYYMMDD-001 format.
    Queries SQLite directly for today's records to determine the next sequential number.
    """
    date_str = datetime.now().strftime("%Y%m%d")
    prefix = f"WO-{date_str}-"
    
    try:
        from database import get_db_connection
    except ImportError:
        from src.database import get_db_connection

    max_seq = 0
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT work_order_id FROM work_orders WHERE work_order_id LIKE ? ORDER BY work_order_id DESC",
                (f"{prefix}%",)
            )
            rows = cursor.fetchall()
            for r in rows:
                parts = str(r["work_order_id"]).split('-')
                if len(parts) == 3 and parts[2].isdigit():
                    max_seq = max(max_seq, int(parts[2]))
                    break
    except Exception as e:
        print(f"Error generating work order id: {e}")

    next_seq = max_seq + 1
    return f"{prefix}{next_seq:03d}"


def assess_severity_and_priority(failures_str: str, has_failure: bool) -> Tuple[str, str, str]:
    """
    Determines severity, priority, and default maintenance action based on detected machine failure modes.
    """
    if not has_failure or failures_str == "None" or not failures_str.strip():
        return "Low", "Low", "Routine Preventive Inspection"

    failures = [f.strip() for f in failures_str.split(",")]

    if "PWF" in failures or "HDF" in failures:
        return "Critical", "Critical", "Emergency Electrical & Thermal Dissipation Repair"
    elif "OSF" in failures:
        return "High", "High", "Mechanical Overstrain & Torque Adjustment"
    elif "TWF" in failures:
        return "Medium", "Medium", "Tool Replacement & Alignment"
    elif "RNF" in failures:
        return "Low", "Medium", "Diagnostic Sensor Calibration"
    else:
        return "Medium", "Medium", "General Preventive Maintenance"


def extract_fields_from_ai_report(ai_report_text: str, machine_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Automatically parses Machine ID, Priority Level, Maintenance Type,
    Technician Recommendation, and Due Date directly from an AI Maintenance Report.
    """
    fallback_m_id = str(machine_info.get("product_id", "N/A"))
    
    # 1. Machine ID
    m_id_match = re.search(r"(?:-\s*\*\*Machine ID\*\*|machine\s+ID):\s*`?([A-Za-z0-9_-]+)`?", ai_report_text, re.IGNORECASE)
    machine_id = m_id_match.group(1).strip() if m_id_match else fallback_m_id

    # 2. Priority Level (CRITICAL, HIGH, MEDIUM, LOW)
    priority = "Low"
    prio_match = re.search(r"(?:### Priority Level|Maintenance Priority:?)\s*\n*\*?\*?`?(CRITICAL|HIGH|MEDIUM|LOW)`?\*?\*?", ai_report_text, re.IGNORECASE)
    if prio_match:
        prio_str = prio_match.group(1).upper()
        if prio_str == "CRITICAL":
            priority = "Critical"
        elif prio_str == "HIGH":
            priority = "High"
        elif prio_str == "MEDIUM":
            priority = "Medium"
        elif prio_str == "LOW":
            priority = "Low"
    else:
        if "CRITICAL" in ai_report_text.upper():
            priority = "Critical"
        elif "HIGH" in ai_report_text.upper():
            priority = "High"
        elif "MEDIUM" in ai_report_text.upper():
            priority = "Medium"

    # 3. Maintenance Type / Action
    maint_type = "AI Preventive Maintenance Service"
    rec_action_match = re.search(r"Recommended Actions:\s*\n+1\.\s*([^\n]+)", ai_report_text, re.IGNORECASE)
    action_match = re.search(r"-\s*\*\*Immediate Action\*\*:\s*([^\n]+)", ai_report_text)

    if rec_action_match:
        maint_type = rec_action_match.group(1).strip().replace("`", "")
    elif action_match:
        maint_type = action_match.group(1).strip().replace("`", "")
    elif "TWF" in ai_report_text or "Tool Change" in ai_report_text or "cutting tool" in ai_report_text.lower() or "tool wear" in ai_report_text.lower():
        maint_type = "Tool Replacement & Spindle Calibration"
    elif "HDF" in ai_report_text or "Coolant" in ai_report_text or "Heat Exchanger" in ai_report_text:
        maint_type = "Coolant System & Thermal Service"
    elif "PWF" in ai_report_text or "Power" in ai_report_text or "Torque" in ai_report_text:
        maint_type = "Electrical Drive & Torque Calibration"
    elif "OSF" in ai_report_text or "Overstrain" in ai_report_text:
        maint_type = "Mechanical Overstrain & Load Service"
    elif "RNF" in ai_report_text or "Sensor" in ai_report_text:
        maint_type = "Vibration Sensor Diagnostics & Audit"

    # 4. Technician Recommendation
    if priority == "Critical":
        tech_rec = "Emergency Field Reliability Engineer (Sarah Connor)"
    elif priority == "High":
        tech_rec = "Lead Maintenance Technician (John Doe)"
    elif priority == "Medium":
        tech_rec = "Systems Diagnostic Engineer (David Smith)"
    else:
        tech_rec = "Shift Preventive Inspector (Alex Rivera)"

    # 5. Due Date
    due_date_match = re.search(r"-\s*\*\*Next Inspection Date\*\*:\s*`?(\d{4}-\d{2}-\d{2})`?", ai_report_text)
    if due_date_match:
        due_date = due_date_match.group(1).strip()
    else:
        days_ahead = 1 if priority == "Critical" else (3 if priority == "High" else 7)
        due_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    return {
        "machine_id": machine_id,
        "priority": priority,
        "maintenance_type": maint_type,
        "technician_recommendation": tech_rec,
        "due_date": due_date
    }



def create_ai_work_order(machine_info: Dict[str, Any], ai_summary: str, assigned_to: str = "Unassigned", prevent_duplicates: bool = True) -> Tuple[bool, str]:
    """
    Automatically populates and persists a new Work Order into SQLite when AI predicts failure.
    Extracts Machine ID, Priority, Maintenance Type, Technician Recommendation, and Due Date automatically.
    """
    extracted = extract_fields_from_ai_report(ai_summary, machine_info)
    machine_id = extracted["machine_id"]
    failures_str = str(machine_info.get("failures", "None"))

    if prevent_duplicates and has_open_work_order(machine_id, failures_str):
        return False, f"An active open Work Order already exists for Machine {machine_id}."

    work_order_id = generate_work_order_id()
    now_dt = datetime.now()
    created_at = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    assigned = assigned_to if assigned_to != "Unassigned" else extracted["technician_recommendation"]

    work_order_data = {
        "work_order_id": work_order_id,
        "machine_id": machine_id,
        "machine_type": str(machine_info.get("type", "N/A")),
        "failure_prediction": failures_str,
        "failure_type": failures_str,
        "severity": extracted["priority"],
        "maintenance_action": extracted["maintenance_type"],
        "assigned_to": assigned,
        "status": "Pending",
        "priority": extracted["priority"],
        "created_at": created_at,
        "due_date": extracted["due_date"],
        "completed_at": None,
        "ai_summary": ai_summary
    }

    success = insert_work_order(work_order_data)
    if success:
        return True, work_order_id
    else:
        return False, "Failed to persist Work Order to database."


# Predefined status workflow rules
WORKFLOW_TRANSITIONS = {
    "Pending": ["Pending", "In Progress", "Cancelled"],
    "In Progress": ["In Progress", "Completed", "Pending", "Cancelled"],
    "Completed": ["Completed", "In Progress"],
    "Cancelled": ["Cancelled", "Pending"]
}


def get_allowed_next_statuses(current_status: str) -> list:
    """
    Returns the list of valid next status options based on the predefined workflow.
    """
    return WORKFLOW_TRANSITIONS.get(current_status, ["Pending", "In Progress", "Completed", "Cancelled"])

