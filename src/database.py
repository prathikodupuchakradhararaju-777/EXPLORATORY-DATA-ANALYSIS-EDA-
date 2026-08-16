import sqlite3
import pandas as pd
import os
import hashlib
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "work_orders.db")


def get_db_connection() -> sqlite3.Connection:
    """
    Establishes a robust connection to the SQLite database.
    Ensures directory exists and configures thread safety for Streamlit.
    """
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Creates the 'work_orders' table if it does not already exist,
    applies indexes, performs schema migrations, and seeds sample data.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_order_id TEXT UNIQUE NOT NULL,
                    machine_id TEXT NOT NULL,
                    machine_type TEXT,
                    failure_prediction TEXT,
                    failure_type TEXT,
                    severity TEXT,
                    maintenance_action TEXT,
                    assigned_to TEXT,
                    status TEXT DEFAULT 'Pending',
                    priority TEXT,
                    created_at TEXT,
                    due_date TEXT,
                    completed_at TEXT,
                    ai_summary TEXT
                );
            """)
            
            # Migration check: ensure both failure_prediction and failure_type exist
            cursor.execute("PRAGMA table_info(work_orders)")
            columns = [row[1] for row in cursor.fetchall()]
            if "failure_prediction" not in columns:
                cursor.execute("ALTER TABLE work_orders ADD COLUMN failure_prediction TEXT;")
                cursor.execute("UPDATE work_orders SET failure_prediction = failure_type WHERE failure_prediction IS NULL;")
            if "failure_type" not in columns:
                cursor.execute("ALTER TABLE work_orders ADD COLUMN failure_type TEXT;")
                cursor.execute("UPDATE work_orders SET failure_type = failure_prediction WHERE failure_type IS NULL;")

            # Performance Optimization: Create DB Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_status ON work_orders(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_priority ON work_orders(priority);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_severity ON work_orders(severity);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_machine_type ON work_orders(machine_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_due_date ON work_orders(due_date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_created_at ON work_orders(created_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_machine_id ON work_orders(machine_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_assigned_to ON work_orders(assigned_to);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wo_lookup ON work_orders(status, priority, severity, machine_type);")

            conn.commit()
        init_users_db()
        init_preventive_db()
        seed_initial_data_if_empty()
    except Exception as e:
        print(f"Error initializing SQLite database: {e}")
        raise e


def seed_initial_data_if_empty() -> None:
    """
    Seeds initial realistic sample work orders if database is currently empty.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM work_orders")
            count = cursor.fetchone()[0]
            if count == 0:
                today_str = datetime.now().strftime("%Y-%m-%d")
                samples = [
                    {
                        "work_order_id": "WO-20260725-001",
                        "machine_id": "M14860",
                        "machine_type": "M",
                        "failure_prediction": "PWF",
                        "failure_type": "PWF",
                        "severity": "Critical",
                        "maintenance_action": "Emergency Power Supply Unit replacement",
                        "assigned_to": "Sarah Connor",
                        "status": "In Progress",
                        "priority": "High",
                        "created_at": "2026-07-24 09:15:00",
                        "due_date": today_str,
                        "completed_at": None,
                        "ai_summary": "High risk of power failure detected due to high voltage fluctuation."
                    },
                    {
                        "work_order_id": "WO-20260725-002",
                        "machine_id": "L47181",
                        "machine_type": "L",
                        "failure_prediction": "TWF",
                        "failure_type": "TWF",
                        "severity": "Medium",
                        "maintenance_action": "Tool replacement and alignment",
                        "assigned_to": "John Doe",
                        "status": "Completed",
                        "priority": "Medium",
                        "created_at": "2026-07-23 14:00:00",
                        "due_date": "2026-07-25",
                        "completed_at": "2026-07-23 18:30:00",
                        "ai_summary": "Tool wear exceeded safe operational threshold."
                    },
                    {
                        "work_order_id": "WO-20260725-003",
                        "machine_id": "H29415",
                        "machine_type": "H",
                        "failure_prediction": "HDF",
                        "failure_type": "HDF",
                        "severity": "Critical",
                        "maintenance_action": "Cooling fan inspection and thermal dissipation repair",
                        "assigned_to": "David Smith",
                        "status": "Pending",
                        "priority": "Critical",
                        "created_at": "2026-07-25 08:00:00",
                        "due_date": "2026-07-27",
                        "completed_at": None,
                        "ai_summary": "Heat dissipation failure risk identified during high thermal load."
                    },
                    {
                        "work_order_id": "WO-20260725-004",
                        "machine_id": "M15210",
                        "machine_type": "M",
                        "failure_prediction": "OSF",
                        "failure_type": "OSF",
                        "severity": "High",
                        "maintenance_action": "Mechanical strain torque adjustment & lubrication",
                        "assigned_to": "Michael Scott",
                        "status": "Completed",
                        "priority": "High",
                        "created_at": "2026-07-22 10:00:00",
                        "due_date": "2026-07-24",
                        "completed_at": "2026-07-22 15:45:00",
                        "ai_summary": "Mechanical overstrain limit reached during high RPM operations."
                    },
                    {
                        "work_order_id": "WO-20260725-005",
                        "machine_id": "L48320",
                        "machine_type": "L",
                        "failure_prediction": "RNF",
                        "failure_type": "RNF",
                        "severity": "Low",
                        "maintenance_action": "Routine diagnostic sensor check & calibration",
                        "assigned_to": "Unassigned",
                        "status": "Pending",
                        "priority": "Low",
                        "created_at": "2026-07-20 11:30:00",
                        "due_date": "2026-07-22",
                        "completed_at": None,
                        "ai_summary": "Random minor anomaly flagged in vibration sensors."
                    }
                ]
                for s in samples:
                    cursor.execute("""
                        INSERT INTO work_orders (
                            work_order_id, machine_id, machine_type, failure_prediction, failure_type,
                            severity, maintenance_action, assigned_to, status,
                            priority, created_at, due_date, completed_at, ai_summary
                        ) VALUES (
                            :work_order_id, :machine_id, :machine_type, :failure_prediction, :failure_type,
                            :severity, :maintenance_action, :assigned_to, :status,
                            :priority, :created_at, :due_date, :completed_at, :ai_summary
                        );
                    """, s)
                conn.commit()
    except Exception as e:
        print(f"Error seeding sample work orders: {e}")


def insert_work_order(data: Dict[str, Any]) -> bool:
    """
    Inserts a new work order record into the database.
    Prevents duplicate work_order_id and handles SQLite exceptions safely.
    """
    # Synchronize failure_prediction and failure_type
    f_pred = data.get("failure_prediction") or data.get("failure_type") or "None"
    data["failure_prediction"] = f_pred
    data["failure_type"] = f_pred

    query = """
        INSERT INTO work_orders (
            work_order_id, machine_id, machine_type, failure_prediction, failure_type,
            severity, maintenance_action, assigned_to, status,
            priority, created_at, due_date, completed_at, ai_summary
        ) VALUES (
            :work_order_id, :machine_id, :machine_type, :failure_prediction, :failure_type,
            :severity, :maintenance_action, :assigned_to, :status,
            :priority, :created_at, :due_date, :completed_at, :ai_summary
        );
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, data)
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        print(f"Work Order ID {data.get('work_order_id')} already exists.")
        return False
    except Exception as e:
        print(f"Error inserting work order: {e}")
        return False


def has_open_work_order(machine_id: str, failure_prediction: Optional[str] = None) -> bool:
    """
    Checks if an open work order ('Pending' or 'In Progress') already exists for the given machine_id.
    Prevents duplicate automatic creation.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if failure_prediction and failure_prediction != "None":
                cursor.execute("""
                    SELECT COUNT(*) FROM work_orders 
                    WHERE machine_id = ? 
                    AND status IN ('Pending', 'In Progress')
                    AND (failure_prediction = ? OR failure_type = ?)
                """, (machine_id, failure_prediction, failure_prediction))
            else:
                cursor.execute("""
                    SELECT COUNT(*) FROM work_orders 
                    WHERE machine_id = ? 
                    AND status IN ('Pending', 'In Progress')
                """, (machine_id,))
            count = cursor.fetchone()[0]
            return count > 0
    except Exception as e:
        print(f"Error checking open work order for {machine_id}: {e}")
        return False


def fetch_all_work_orders(
    status_filter: str = "All",
    priority_filter: str = "All",
    severity_filter: str = "All",
    type_filter: str = "All",
    search_query: str = "",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetches work orders from SQLite into a Pandas DataFrame based on filter criteria.
    Supports multi-column search, multi-filter combinations, and date range filters.
    """
    query = "SELECT * FROM work_orders WHERE 1=1"
    params = []

    if status_filter and status_filter != "All":
        if status_filter == "Open":
            query += " AND status IN ('Pending', 'In Progress')"
        else:
            query += " AND status = ?"
            params.append(status_filter)

    if priority_filter and priority_filter != "All":
        query += " AND priority = ?"
        params.append(priority_filter)

    if severity_filter and severity_filter != "All":
        query += " AND severity = ?"
        params.append(severity_filter)

    if type_filter and type_filter != "All":
        query += " AND machine_type = ?"
        params.append(type_filter)

    if start_date:
        query += " AND date(substr(created_at, 1, 10)) >= date(?)"
        params.append(start_date)

    if end_date:
        query += " AND date(substr(created_at, 1, 10)) <= date(?)"
        params.append(end_date)

    if search_query and search_query.strip():
        query += """ AND (
            work_order_id LIKE ? OR 
            machine_id LIKE ? OR 
            machine_type LIKE ? OR 
            failure_prediction LIKE ? OR 
            failure_type LIKE ? OR 
            maintenance_action LIKE ? OR 
            assigned_to LIKE ?
        )"""
        wildcard = f"%{search_query.strip()}%"
        params.extend([wildcard] * 7)

    query += " ORDER BY id DESC"

    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            # Ensure failure_prediction exists in dataframe
            if "failure_prediction" not in df.columns and "failure_type" in df.columns:
                df["failure_prediction"] = df["failure_type"]
            elif "failure_type" not in df.columns and "failure_prediction" in df.columns:
                df["failure_type"] = df["failure_prediction"]
            return df
    except Exception as e:
        print(f"Error fetching work orders: {e}")
        return pd.DataFrame()


def fetch_work_orders_paginated(
    status_filter: str = "All",
    priority_filter: str = "All",
    severity_filter: str = "All",
    type_filter: str = "All",
    search_query: str = "",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_column: str = "created_at",
    sort_order: str = "Descending",
    page: int = 1,
    page_size: int = 10
) -> Tuple[pd.DataFrame, int]:
    """
    Fetches a single page of work orders directly from SQLite using SQL filtering,
    SQL sorting, and SQL LIMIT/OFFSET pagination. Returns (df_page, total_count).
    """
    where_clauses = ["1=1"]
    params = []

    if status_filter and status_filter != "All":
        if status_filter == "Open":
            where_clauses.append("status IN ('Pending', 'In Progress')")
        else:
            where_clauses.append("status = ?")
            params.append(status_filter)

    if priority_filter and priority_filter != "All":
        where_clauses.append("priority = ?")
        params.append(priority_filter)

    if severity_filter and severity_filter != "All":
        where_clauses.append("severity = ?")
        params.append(severity_filter)

    if type_filter and type_filter != "All":
        where_clauses.append("machine_type = ?")
        params.append(type_filter)

    if start_date:
        where_clauses.append("date(substr(created_at, 1, 10)) >= date(?)")
        params.append(start_date)

    if end_date:
        where_clauses.append("date(substr(created_at, 1, 10)) <= date(?)")
        params.append(end_date)

    if search_query and search_query.strip():
        where_clauses.append("""(
            work_order_id LIKE ? OR 
            machine_id LIKE ? OR 
            machine_type LIKE ? OR 
            failure_prediction LIKE ? OR 
            failure_type LIKE ? OR 
            maintenance_action LIKE ? OR 
            assigned_to LIKE ?
        )""")
        wildcard = f"%{search_query.strip()}%"
        params.extend([wildcard] * 7)

    where_sql = " AND ".join(where_clauses)

    valid_cols = {
        "id": "id",
        "work_order_id": "work_order_id",
        "machine_id": "machine_id",
        "machine_type": "machine_type",
        "failure_prediction": "failure_prediction",
        "severity": "severity",
        "priority": "priority",
        "status": "status",
        "assigned_to": "assigned_to",
        "maintenance_action": "maintenance_action",
        "created_at": "created_at",
        "due_date": "due_date"
    }
    col_sql = valid_cols.get(sort_column, "created_at")
    dir_sql = "DESC" if sort_order in ["Descending", "DESC", "desc"] else "ASC"

    count_query = f"SELECT COUNT(*) FROM work_orders WHERE {where_sql}"

    offset = (max(1, page) - 1) * page_size
    data_query = f"SELECT * FROM work_orders WHERE {where_sql} ORDER BY {col_sql} {dir_sql} LIMIT ? OFFSET ?"
    data_params = list(params) + [page_size, offset]

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]

            df_page = pd.read_sql_query(data_query, conn, params=data_params)
            if "failure_prediction" not in df_page.columns and "failure_type" in df_page.columns:
                df_page["failure_prediction"] = df_page["failure_type"]
            elif "failure_type" not in df_page.columns and "failure_prediction" in df_page.columns:
                df_page["failure_type"] = df_page["failure_prediction"]

            return df_page, total_count
    except Exception as e:
        print(f"Error fetching paginated work orders: {e}")
        return pd.DataFrame(), 0


def fetch_work_order_ids(status_filter: str = "All") -> list:
    """
    Fetches lightweight list of Work Order IDs for dropdown selection without loading complete DataFrames.
    """
    query = "SELECT work_order_id FROM work_orders"
    params = []
    if status_filter and status_filter != "All":
        if status_filter == "Open":
            query += " WHERE status IN ('Pending', 'In Progress')"
        else:
            query += " WHERE status = ?"
            params.append(status_filter)
    query += " ORDER BY id DESC"
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [row["work_order_id"] for row in rows]
    except Exception as e:
        print(f"Error fetching work order IDs: {e}")
        return []


def update_work_order(
    work_order_id: str,
    assigned_to: str,
    status: str,
    priority: str,
    due_date: str,
    maintenance_action: Optional[str] = None
) -> bool:
    """
    Updates existing work order details. If status changes to 'Completed', automatically sets completed_at.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if status == "Completed":
        completed_at_clause = ", completed_at = CASE WHEN completed_at IS NULL THEN ? ELSE completed_at END"
    else:
        completed_at_clause = ", completed_at = NULL"

    if maintenance_action:
        query = f"""
            UPDATE work_orders
            SET assigned_to = ?,
                status = ?,
                priority = ?,
                due_date = ?,
                maintenance_action = ?
                {completed_at_clause}
            WHERE work_order_id = ?
        """
        params = [assigned_to, status, priority, due_date, maintenance_action]
    else:
        query = f"""
            UPDATE work_orders
            SET assigned_to = ?,
                status = ?,
                priority = ?,
                due_date = ?
                {completed_at_clause}
            WHERE work_order_id = ?
        """
        params = [assigned_to, status, priority, due_date]

    if status == "Completed":
        params.append(now_str)
    params.append(work_order_id)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating work order {work_order_id}: {e}")
        return False


def delete_work_order(work_order_id: str) -> bool:
    """
    Deletes a work order record from the SQLite database.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM work_orders WHERE work_order_id = ?", (work_order_id,))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting work order {work_order_id}: {e}")
        return False


def fetch_work_order_stats() -> Dict[str, Any]:
    """
    Calculates summary KPI statistics for Work Orders efficiently using a single aggregated SQL query.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN priority = 'Critical' THEN 1 ELSE 0 END) as critical_priority,
            SUM(CASE WHEN severity = 'High' OR severity = 'Critical' THEN 1 ELSE 0 END) as high_severity,
            SUM(CASE WHEN (priority = 'Critical' OR priority = 'High' OR severity = 'Critical') THEN 1 ELSE 0 END) as legacy_critical,
            SUM(CASE WHEN status != 'Completed' AND date(substr(due_date, 1, 10)) = date(?) THEN 1 ELSE 0 END) as due_today,
            SUM(CASE WHEN status != 'Completed' AND date(substr(due_date, 1, 10)) < date(?) THEN 1 ELSE 0 END) as overdue
        FROM work_orders
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (today_str, today_str))
            row = cursor.fetchone()
            
            total = row["total"] or 0
            pending = row["pending"] or 0
            in_progress = row["in_progress"] or 0
            open_count = pending + in_progress
            completed = row["completed"] or 0
            critical_priority = row["critical_priority"] or 0
            high_severity = row["high_severity"] or 0
            legacy_critical = row["legacy_critical"] or 0
            due_today = row["due_today"] or 0
            overdue = row["overdue"] or 0

            # Calculate average resolution time
            cursor.execute("SELECT created_at, completed_at FROM work_orders WHERE status = 'Completed' AND completed_at IS NOT NULL")
            completed_rows = cursor.fetchall()
            
            total_hours = 0.0
            resolved_count = 0
            for r in completed_rows:
                c_at = r["created_at"]
                comp_at = r["completed_at"]
                if c_at and comp_at:
                    try:
                        dt1 = datetime.strptime(c_at, "%Y-%m-%d %H:%M:%S")
                        dt2 = datetime.strptime(comp_at, "%Y-%m-%d %H:%M:%S")
                        diff_hours = (dt2 - dt1).total_seconds() / 3600.0
                        if diff_hours >= 0:
                            total_hours += diff_hours
                            resolved_count += 1
                    except Exception:
                        pass
            
            if resolved_count > 0:
                avg_hrs = total_hours / resolved_count
                avg_resolution_str = f"{avg_hrs:.1f} hrs" if avg_hrs < 24 else f"{avg_hrs / 24.0:.1f} days"
            else:
                avg_resolution_str = "N/A"

            return {
                "total": total,
                "open": open_count,
                "pending": pending,
                "in_progress": in_progress,
                "completed": completed,
                "critical": legacy_critical,
                "critical_priority": critical_priority,
                "high_severity": high_severity,
                "due_today": due_today,
                "overdue": overdue,
                "avg_resolution_time": avg_resolution_str
            }
    except Exception as e:
        print(f"Error calculating work order stats: {e}")
        return {
            "total": 0, "open": 0, "pending": 0, "in_progress": 0, "completed": 0,
            "critical": 0, "critical_priority": 0, "high_severity": 0, "due_today": 0,
            "overdue": 0, "avg_resolution_time": "N/A"
        }


# -------------------------------------------------------------
# User Management & Authentication Database Functions
# -------------------------------------------------------------
def hash_password(password: str) -> str:
    """
    Hashes a plain text password using SHA-256 with a salt.
    """
    salt = "ai_predictive_maint_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()


def init_users_db() -> None:
    """
    Creates the 'users' table if it does not already exist.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT DEFAULT 'Operator',
                    created_at TEXT
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
            conn.commit()
        seed_default_users()
    except Exception as e:
        print(f"Error initializing users database table: {e}")


def seed_default_users() -> None:
    """
    Seeds default admin, engineer, and operator accounts if the users table is empty.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            if count == 0:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                default_accounts = [
                    {
                        "username": "admin",
                        "password_hash": hash_password("admin123"),
                        "full_name": "System Administrator",
                        "role": "Admin",
                        "created_at": now_str
                    },
                    {
                        "username": "engineer",
                        "password_hash": hash_password("eng123"),
                        "full_name": "Lead Maintenance Engineer",
                        "role": "Engineer",
                        "created_at": now_str
                    },
                    {
                        "username": "operator",
                        "password_hash": hash_password("op123"),
                        "full_name": "Plant Equipment Operator",
                        "role": "Operator",
                        "created_at": now_str
                    }
                ]
                for user in default_accounts:
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, full_name, role, created_at)
                        VALUES (:username, :password_hash, :full_name, :role, :created_at)
                    """, user)
                conn.commit()
    except Exception as e:
        print(f"Error seeding default users: {e}")


def create_user(username: str, password: str, full_name: str, role: str = "Operator") -> Dict[str, Any]:
    """
    Registers a new user in the database. Returns status dict.
    """
    username = username.strip().lower()
    full_name = full_name.strip()
    
    if not username or not password or not full_name:
        return {"success": False, "message": "All fields (username, password, full name) are required."}
    
    if len(password) < 4:
        return {"success": False, "message": "Password must be at least 4 characters long."}

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hashed_pwd = hash_password(password)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (username, hashed_pwd, full_name, role, now_str))
            conn.commit()
            return {"success": True, "message": "Account registered successfully! You can now log in."}
    except sqlite3.IntegrityError:
        return {"success": False, "message": f"Username '{username}' is already taken. Please choose another."}
    except Exception as e:
        return {"success": False, "message": f"Database error creating user: {str(e)}"}


def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Verifies user credentials. Returns user info dict if valid, else None.
    """
    username = username.strip().lower()
    hashed_pwd = hash_password(password)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, full_name, role, created_at
                FROM users
                WHERE username = ? AND password_hash = ?
            """, (username, hashed_pwd))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "full_name": row["full_name"],
                    "role": row["role"],
                    "created_at": row["created_at"]
                }
    except Exception as e:
        print(f"Error verifying user credentials: {e}")
    return None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Fetches user information by username.
    """
    username = username.strip().lower()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, full_name, role, created_at
                FROM users
                WHERE username = ?
            """, (username,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "full_name": row["full_name"],
                    "role": row["role"],
                    "created_at": row["created_at"]
                }
    except Exception as e:
        print(f"Error fetching user: {e}")
    return None


# -------------------------------------------------------------
# Work Orders Pruning / Cleanup Function
# -------------------------------------------------------------
def clean_work_orders_table(keep_count: int = 10) -> int:
    """
    Prunes the 'work_orders' table to retain only the latest `keep_count` records
    ordered by id DESC. Permanently deletes all older test work orders.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM work_orders;")
            total_count = cursor.fetchone()[0]
            if total_count > keep_count:
                cursor.execute("""
                    DELETE FROM work_orders 
                    WHERE id NOT IN (
                        SELECT id FROM work_orders ORDER BY id DESC LIMIT ?
                    );
                """, (keep_count,))
                conn.commit()
                deleted_count = total_count - keep_count
                print(f"Cleaned work_orders database: Purged {deleted_count} old test records, retained latest {keep_count}.")
                return deleted_count
            return 0
    except Exception as e:
        print(f"Error cleaning work_orders table: {e}")
        return 0


# -------------------------------------------------------------
# Preventive Maintenance Database Functions
# -------------------------------------------------------------
def init_preventive_db() -> None:
    """
    Creates the 'preventive_maintenance' table if it does not already exist,
    applies indexes, and seeds initial realistic sample data.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preventive_maintenance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_id TEXT UNIQUE NOT NULL,
                    machine_id TEXT NOT NULL,
                    machine_name TEXT,
                    maintenance_type TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    technician TEXT NOT NULL,
                    start_date TEXT,
                    next_due_date TEXT,
                    last_service_date TEXT,
                    priority TEXT DEFAULT 'Medium',
                    status TEXT DEFAULT 'Scheduled',
                    estimated_duration TEXT DEFAULT '2 hours',
                    created_date TEXT,
                    notes TEXT
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pm_status ON preventive_maintenance(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pm_frequency ON preventive_maintenance(frequency);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pm_machine_id ON preventive_maintenance(machine_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pm_technician ON preventive_maintenance(technician);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pm_due_date ON preventive_maintenance(next_due_date);")
            conn.commit()
        seed_preventive_schedules_if_empty()
    except Exception as e:
        print(f"Error initializing preventive_maintenance database table: {e}")


def seed_preventive_schedules_if_empty() -> None:
    """
    Seeds initial realistic preventive maintenance schedules if database table is empty.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM preventive_maintenance;")
            count = cursor.fetchone()[0]
            if count == 0:
                today = date.today()
                today_str = today.strftime("%Y-%m-%d")
                
                samples = [
                    {
                        "schedule_id": "PM-202608-001",
                        "machine_id": "M14860",
                        "machine_name": "CNC Milling Center M1",
                        "maintenance_type": "Bearing Inspection & Lubrication",
                        "frequency": "Weekly",
                        "technician": "Sarah Connor",
                        "start_date": "2026-08-01",
                        "next_due_date": today_str,
                        "last_service_date": "2026-07-25",
                        "priority": "High",
                        "status": "Scheduled",
                        "estimated_duration": "2.0 hours",
                        "created_date": "2026-08-01",
                        "notes": "Inspect drive spindle bearings and refill synthetic grease."
                    },
                    {
                        "schedule_id": "PM-202608-002",
                        "machine_id": "L47181",
                        "machine_name": "High-Precision Lathe L4",
                        "maintenance_type": "Tool Replacement & Calibration",
                        "frequency": "Daily",
                        "technician": "John Doe",
                        "start_date": "2026-08-02",
                        "next_due_date": today_str,
                        "last_service_date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
                        "priority": "Medium",
                        "status": "In Progress",
                        "estimated_duration": "1.5 hours",
                        "created_date": "2026-08-02",
                        "notes": "Routine check of tool wear index and alignment calibration."
                    },
                    {
                        "schedule_id": "PM-202608-003",
                        "machine_id": "H29415",
                        "machine_name": "Heavy Duty Press H2",
                        "maintenance_type": "Coolant System & Thermal Service",
                        "frequency": "Monthly",
                        "technician": "David Smith",
                        "start_date": "2026-07-10",
                        "next_due_date": (today - timedelta(days=2)).strftime("%Y-%m-%d"),
                        "last_service_date": "2026-07-10",
                        "priority": "Critical",
                        "status": "Overdue",
                        "estimated_duration": "3.0 hours",
                        "created_date": "2026-07-10",
                        "notes": "Flush cooling circuit, clean heat exchanger filters."
                    },
                    {
                        "schedule_id": "PM-202608-004",
                        "machine_id": "M15210",
                        "machine_name": "Automated Machining Cell M2",
                        "maintenance_type": "Electrical & Control Panel Check",
                        "frequency": "Quarterly",
                        "technician": "Michael Scott",
                        "start_date": "2026-06-01",
                        "next_due_date": (today + timedelta(days=15)).strftime("%Y-%m-%d"),
                        "last_service_date": "2026-05-15",
                        "priority": "Low",
                        "status": "Scheduled",
                        "estimated_duration": "4.0 hours",
                        "created_date": "2026-06-01",
                        "notes": "Inspect main breaker, measure input voltage harmonics."
                    },
                    {
                        "schedule_id": "PM-202608-005",
                        "machine_id": "L48320",
                        "machine_name": "Precision Cutting Unit L5",
                        "maintenance_type": "Vibration Sensor Diagnostics",
                        "frequency": "Weekly",
                        "technician": "Sarah Connor",
                        "start_date": "2026-08-04",
                        "next_due_date": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
                        "last_service_date": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
                        "priority": "Medium",
                        "status": "Completed",
                        "estimated_duration": "1.0 hour",
                        "created_date": "2026-08-04",
                        "notes": "Completed weekly accelerometer sensor drift test."
                    },
                    {
                        "schedule_id": "PM-202608-006",
                        "machine_id": "H29800",
                        "machine_name": "Hydraulic Stamping Station H3",
                        "maintenance_type": "Hydraulic Fluid & Filter Replacement",
                        "frequency": "Half-Yearly",
                        "technician": "Emily Vance",
                        "start_date": "2026-04-01",
                        "next_due_date": (today + timedelta(days=45)).strftime("%Y-%m-%d"),
                        "last_service_date": "2026-02-10",
                        "priority": "High",
                        "status": "Scheduled",
                        "estimated_duration": "5.0 hours",
                        "created_date": "2026-04-01",
                        "notes": "Full hydraulic oil flush and high-pressure filter element replacement."
                    },
                    {
                        "schedule_id": "PM-202608-007",
                        "machine_id": "M16000",
                        "machine_name": "5-Axis CNC Router M4",
                        "maintenance_type": "Annual Comprehensive Overhaul",
                        "frequency": "Yearly",
                        "technician": "David Smith",
                        "start_date": "2026-01-15",
                        "next_due_date": (today + timedelta(days=120)).strftime("%Y-%m-%d"),
                        "last_service_date": "2025-08-20",
                        "priority": "Medium",
                        "status": "Scheduled",
                        "estimated_duration": "8.0 hours",
                        "created_date": "2026-01-15",
                        "notes": "Complete mechanical alignment check, spindle overhaul, and laser calibration."
                    }
                ]
                
                for s in samples:
                    cursor.execute("""
                        INSERT INTO preventive_maintenance (
                            schedule_id, machine_id, machine_name, maintenance_type,
                            frequency, technician, start_date, next_due_date,
                            last_service_date, priority, status, estimated_duration,
                            created_date, notes
                        ) VALUES (
                            :schedule_id, :machine_id, :machine_name, :maintenance_type,
                            :frequency, :technician, :start_date, :next_due_date,
                            :last_service_date, :priority, :status, :estimated_duration,
                            :created_date, :notes
                        );
                    """, s)
                conn.commit()
    except Exception as e:
        print(f"Error seeding preventive maintenance data: {e}")


def insert_preventive_schedule(schedule_data: Dict[str, Any]) -> bool:
    """
    Inserts a new preventive maintenance schedule record into SQLite database.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO preventive_maintenance (
                    schedule_id, machine_id, machine_name, maintenance_type,
                    frequency, technician, start_date, next_due_date,
                    last_service_date, priority, status, estimated_duration,
                    created_date, notes
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                );
            """, (
                schedule_data.get("schedule_id"),
                schedule_data.get("machine_id"),
                schedule_data.get("machine_name", schedule_data.get("machine_id")),
                schedule_data.get("maintenance_type"),
                schedule_data.get("frequency"),
                schedule_data.get("technician"),
                schedule_data.get("start_date"),
                schedule_data.get("next_due_date"),
                schedule_data.get("last_service_date", schedule_data.get("start_date")),
                schedule_data.get("priority", "Medium"),
                schedule_data.get("status", "Scheduled"),
                schedule_data.get("estimated_duration", "2 hours"),
                schedule_data.get("created_date", date.today().strftime("%Y-%m-%d")),
                schedule_data.get("notes", "")
            ))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error inserting preventive maintenance schedule: {e}")
        return False


def fetch_all_preventive_schedules() -> pd.DataFrame:
    """
    Fetches all preventive maintenance schedules from SQLite database.
    """
    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM preventive_maintenance ORDER BY id DESC;", conn)
            return df
    except Exception as e:
        print(f"Error fetching preventive maintenance schedules: {e}")
        return pd.DataFrame()


def update_preventive_schedule_status(schedule_id: str, new_status: str, last_service_date: Optional[str] = None) -> bool:
    """
    Updates status and service date of a preventive maintenance schedule in SQLite.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if new_status == "Completed" and not last_service_date:
                last_service_date = date.today().strftime("%Y-%m-%d")
            
            if last_service_date:
                cursor.execute("""
                    UPDATE preventive_maintenance
                    SET status = ?, last_service_date = ?
                    WHERE schedule_id = ?;
                """, (new_status, last_service_date, schedule_id))
            else:
                cursor.execute("""
                    UPDATE preventive_maintenance
                    SET status = ?
                    WHERE schedule_id = ?;
                """, (new_status, schedule_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error updating preventive maintenance status: {e}")
        return False


def delete_preventive_schedule(schedule_id: str) -> bool:
    """
    Deletes a preventive maintenance schedule record by schedule_id.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM preventive_maintenance WHERE schedule_id = ?;", (schedule_id,))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error deleting preventive schedule: {e}")
        return False


def update_preventive_schedule(schedule_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Updates all editable fields of an existing preventive maintenance schedule in SQLite database.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE preventive_maintenance
                SET machine_id = ?,
                    machine_name = ?,
                    maintenance_type = ?,
                    frequency = ?,
                    technician = ?,
                    next_due_date = ?,
                    priority = ?,
                    status = ?,
                    notes = ?
                WHERE schedule_id = ?;
            """, (
                update_data.get("machine_id"),
                update_data.get("machine_name", update_data.get("machine_id")),
                update_data.get("maintenance_type"),
                update_data.get("frequency", "Weekly"),
                update_data.get("technician"),
                update_data.get("next_due_date"),
                update_data.get("priority", "Medium"),
                update_data.get("status", "Scheduled"),
                update_data.get("notes", ""),
                schedule_id
            ))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating preventive maintenance schedule {schedule_id}: {e}")
        return False


