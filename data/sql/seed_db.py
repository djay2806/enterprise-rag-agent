"""
Structured SQL database seeder.
Creates a SQLite database simulating enterprise HR + Sales data.
"""

import sqlite3
import os


DB_PATH = os.path.join(os.path.dirname(__file__), "enterprise.db")


def seed_database(db_path: str = DB_PATH) -> str:
    """Create and seed the SQLite database with enterprise data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # --- Employees Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            role TEXT NOT NULL,
            salary_usd INTEGER NOT NULL,
            hire_date TEXT NOT NULL,
            manager_id INTEGER,
            is_active INTEGER DEFAULT 1
        )
    """)

    employees = [
        (1,  "Priya Sharma",     "Engineering",  "Staff Engineer",        165000, "2019-03-15", None, 1),
        (2,  "Rahul Verma",      "Engineering",  "Senior SWE",            130000, "2020-07-01", 1,    1),
        (3,  "Ananya Rao",       "Engineering",  "SWE II",                105000, "2022-01-10", 1,    1),
        (4,  "Kiran Patel",      "AI Research",  "Research Scientist",    155000, "2021-04-22", None, 1),
        (5,  "Meera Nair",       "AI Research",  "ML Engineer",           125000, "2022-09-05", 4,    1),
        (6,  "Arjun Singh",      "Sales",        "VP of Sales",           175000, "2018-11-01", None, 1),
        (7,  "Deepa Krishnan",   "Sales",        "Account Executive",      85000, "2023-02-14", 6,    1),
        (8,  "Suresh Kumar",     "HR",           "HR Manager",             92000, "2020-05-30", None, 1),
        (9,  "Lakshmi Iyer",     "Finance",      "Finance Analyst",        88000, "2021-08-19", None, 1),
        (10, "Vijay Reddy",      "Engineering",  "DevOps Engineer",       115000, "2021-12-01", 1,    1),
    ]
    cursor.executemany("INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?,?,?,?)", employees)

    # --- Sales Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL,
            customer TEXT NOT NULL,
            deal_value_usd INTEGER NOT NULL,
            quarter TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)

    sales = [
        (1,  7, "DataCorp Ltd",     250000, "Q3-2024", "closed_won"),
        (2,  7, "RetailAI Inc",     180000, "Q3-2024", "closed_won"),
        (3,  7, "HealthTech LLC",    95000, "Q3-2024", "in_progress"),
        (4,  6, "MegaBank NA",      750000, "Q3-2024", "closed_won"),
        (5,  6, "InsureGiant Co",   420000, "Q2-2024", "closed_won"),
        (6,  7, "EduPlatform GmbH", 130000, "Q4-2024", "in_progress"),
        (7,  6, "AutoDrive Corp",   310000, "Q4-2024", "closed_won"),
        (8,  7, "CloudFirst Ltd",   200000, "Q4-2024", "closed_lost"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO sales VALUES (?,?,?,?,?,?)", sales)

    # --- Projects Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            lead_employee_id INTEGER,
            budget_usd INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    projects = [
        (1, "AI Platform v2.0",       "AI Research",  4,  500000, "2024-01-01", "active"),
        (2, "Customer RAG Bot",        "Engineering",  1,  200000, "2024-03-15", "active"),
        (3, "Sales Forecast ML Model", "AI Research",  5,   85000, "2024-06-01", "completed"),
        (4, "Cloud Migration GCP",     "Engineering",  10, 300000, "2024-02-01", "active"),
        (5, "HR Analytics Dashboard",  "HR",           8,   45000, "2024-07-01", "active"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO projects VALUES (?,?,?,?,?,?,?)", projects)

    conn.commit()
    conn.close()
    return db_path
