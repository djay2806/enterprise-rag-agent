"""
SQL Agent Storage Layer.
Provides natural-language-to-SQL execution over SQLite enterprise database.
"""

import sqlite3
import os
import sys
import re
from typing import Any, Dict, List

# Default DB path relative to project root
DEFAULT_DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sql", "enterprise.db")


class SQLEngine:
    """
    Wraps SQLite with schema introspection and safe query execution.
    """

    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = db_path
        self._ensure_seeded()

    def _ensure_seeded(self):
        if not os.path.exists(self.db_path):
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
            from data.sql.seed_db import seed_database
            seed_database(self.db_path)

    def get_schema(self) -> str:
        """Return the full DDL schema for all tables (injected into LLM prompt)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        schema_parts = []
        for table in tables:
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE name=?", (table,))
            ddl = cursor.fetchone()[0]
            schema_parts.append(ddl)
        conn.close()
        return "\n\n".join(schema_parts)

    def execute_query(self, sql: str) -> Dict[str, Any]:
        """
        Safely execute a SELECT query and return structured results.
        Rejects any mutating SQL (INSERT, UPDATE, DROP, etc.).
        """
        # Safety guard: only allow SELECT statements
        clean_sql = sql.strip().upper()
        if not clean_sql.startswith("SELECT"):
            return {
                "success": False,
                "error": "Only SELECT queries are permitted.",
                "rows": [],
                "columns": [],
            }

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            conn.close()
            return {
                "success": True,
                "columns": columns,
                "rows": [dict(row) for row in rows],
                "row_count": len(rows),
            }
        except sqlite3.Error as e:
            return {
                "success": False,
                "error": str(e),
                "rows": [],
                "columns": [],
            }

    def extract_sql_from_response(self, llm_response: str) -> str:
        """Extract the first SQL block from an LLM-generated response."""
        # Try fenced code block first
        match = re.search(r"```(?:sql)?\s*(SELECT.*?)```", llm_response, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback: find first SELECT ... ; pattern
        match = re.search(r"(SELECT.*?;)", llm_response, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
