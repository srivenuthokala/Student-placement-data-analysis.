"""
Database abstraction layer for SQLite and MySQL.
Provides unified connection handling, table initialization, and query execution.
"""
import sqlite3
import pandas as pd
from config import DB_ENGINE, SQLITE_DB_PATH, MYSQL_CONFIG


def get_connection():
    """Returns a connection to either SQLite or MySQL based on config."""
    if DB_ENGINE.lower() == "mysql":
        try:
            import mysql.connector
            return mysql.connector.connect(**MYSQL_CONFIG)
        except Exception as e:
            print(f"[ERROR] Could not connect to MySQL: {e}")
            print("[INFO] Falling back to SQLite database...")
            return sqlite3.connect(SQLITE_DB_PATH)
    else:
        return sqlite3.connect(SQLITE_DB_PATH)


def init_database():
    """Initializes tables in the active database engine."""
    conn = get_connection()
    cursor = conn.cursor()

    if isinstance(conn, sqlite3.Connection):
        # SQLite dialect
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            graduation_year INTEGER NOT NULL,
            cgpa REAL NOT NULL,
            is_eligible INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS skills (
            skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS student_skills (
            student_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            PRIMARY KEY (student_id, skill_id),
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS placements (
            placement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            package REAL NOT NULL,
            placement_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Placed',
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
        );
        """)
    else:
        # MySQL dialect
        with open("schema.sql", "r") as f:
            sql_script = f.read()
        for statement in sql_script.split(";"):
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                except Exception as e:
                    print(f"Error executing statement: {e}")

    conn.commit()
    conn.close()
    print(f"[OK] Database initialized successfully using '{conn.__class__.__module__}' engine.")


def fetch_dataframe(query: str, params=None) -> pd.DataFrame:
    """Executes a SELECT query and returns the results as a Pandas DataFrame."""
    conn = get_connection()
    try:
        if params:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()


def execute_non_query(query: str, params=None):
    """Executes an INSERT, UPDATE, or DELETE query."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()
