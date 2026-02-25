"""
Database tool builder.

Given a DB connection string, exposes two Claude tools:
  - list_tables   : returns available table names + schema
  - query_database: executes a read-only SELECT and returns rows as JSON

Claude decides when to call these tools. We run the actual SQL, send
results back, and Claude formats the final answer.
"""

import json
from typing import Any
from sqlalchemy import create_engine, text, inspect


# ── Tool definitions (sent to Anthropic) ────────────────────────────────────

def build_db_tools(allowed_tables: list[str]) -> list[dict]:
    """
    Return the Anthropic tool definitions for this DB resource.
    `allowed_tables` restricts which tables Claude may mention (for safety).
    """
    table_hint = (
        f"Allowed tables: {', '.join(allowed_tables)}. "
        if allowed_tables else
        "All tables in the database are accessible. "
    )

    return [
        {
            "name": "list_tables",
            "description": (
                "List all available database tables and their column schemas. "
                "Call this first if you need to understand the database structure before querying."
            ),
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "query_database",
            "description": (
                "Execute a SQL SELECT query against the database and return the results. "
                + table_hint
                + "Only SELECT statements are allowed. Never use INSERT, UPDATE, DELETE, DROP."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "A valid SQL SELECT statement to execute.",
                    }
                },
                "required": ["sql"],
            },
        },
    ]


# ── Tool execution ───────────────────────────────────────────────────────────

def _get_schema(db_url: str, allowed_tables: list[str]) -> str:
    """Return table names and columns as a formatted string."""
    engine = create_engine(db_url)
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()
    tables = [t for t in all_tables if not allowed_tables or t in allowed_tables]

    lines = []
    for table in tables:
        columns = inspector.get_columns(table)
        col_defs = ", ".join(f"{c['name']} ({c['type']})" for c in columns)
        lines.append(f"  {table}: {col_defs}")

    engine.dispose()
    return "Tables:\n" + "\n".join(lines) if lines else "No accessible tables found."


def _run_query(db_url: str, sql: str, allowed_tables: list[str]) -> str:
    """Execute a SELECT query and return JSON rows. Rejects non-SELECT statements."""
    normalized = sql.strip().upper()
    if not normalized.startswith("SELECT"):
        return json.dumps({"error": "Only SELECT statements are allowed."})

    # Naive guard: block mutation keywords anywhere in the statement
    blocked = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "REPLACE"}
    words = set(normalized.split())
    blocked_found = words & blocked
    if blocked_found:
        return json.dumps({"error": f"Blocked keyword(s): {', '.join(blocked_found)}"})

    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            engine.dispose()
            return json.dumps({"columns": columns, "rows": rows, "count": len(rows)}, default=str)
    except Exception as e:
        engine.dispose()
        return json.dumps({"error": str(e)})


def execute_db_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    db_url: str,
    allowed_tables: list[str],
) -> str:
    """Dispatch a tool call and return the result string."""
    if tool_name == "list_tables":
        return _get_schema(db_url, allowed_tables)
    elif tool_name == "query_database":
        sql = tool_input.get("sql", "")
        return _run_query(db_url, sql, allowed_tables)
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
