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


from werkzeug.security import generate_password_hash


def init_database():
    """Initializes tables in the active database engine and ensures auth schemas exist."""
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
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS faculty (
            faculty_id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_code TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
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

        # Migration: ensure student fields exist on students table if created previously without them
        cursor.execute("PRAGMA table_info(students)")
        existing_cols = [c[1] for c in cursor.fetchall()]

        new_columns = [
            ("password_hash", "TEXT"),
            ("admission_type", "TEXT DEFAULT 'Regular'"),
            ("year_of_study", "TEXT DEFAULT '4th Year'"),
            ("section", "TEXT DEFAULT 'A'"),
            ("email", "TEXT"),
            ("mobile", "TEXT"),
            ("dob", "TEXT"),
            ("gender", "TEXT DEFAULT 'Male'"),
            ("backlogs", "INTEGER DEFAULT 0"),
            ("academic_year", "TEXT DEFAULT '2024-2025'"),
            ("placement_eligibility", "TEXT DEFAULT 'Eligible'"),
            ("placement_status", "TEXT DEFAULT 'Unplaced'"),
            ("diploma_qualification", "TEXT"),
            ("diploma_percentage", "REAL"),
            ("diploma_college", "TEXT"),
            ("admission_year", "INTEGER DEFAULT 2021")
        ]

        for col_name, col_type in new_columns:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE students ADD COLUMN {col_name} {col_type}")
                except Exception as ex:
                    print(f"[INFO] Column {col_name} migration note: {ex}")

        # Create placement_audit_logs table to preserve history on student updates/deletions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS placement_audit_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            student_id INTEGER,
            roll_no TEXT,
            details TEXT NOT NULL,
            performed_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Seed initial faculty accounts if table is empty
        cursor.execute("SELECT COUNT(*) FROM faculty")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("""
                INSERT INTO faculty (faculty_code, username, name, department, email, password_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                ("FAC001", "faculty", "Dr. Rajesh Sharma", "Computer Science", "faculty@eduplace.ac.in", generate_password_hash("Faculty@123")),
                ("FAC002", "placement_officer", "Prof. Sunita Rao", "Training & Placement Cell", "tpo@eduplace.ac.in", generate_password_hash("Faculty@123")),
            ])

        # Ensure existing students have valid hashed passwords (Student@123)
        cursor.execute("""
            UPDATE students
            SET password_hash = ?
            WHERE password_hash IS NULL OR password_hash = ''
        """, (generate_password_hash("Student@123"),))

        # Backfill default values for existing students if empty
        cursor.execute("""
            UPDATE students
            SET email = LOWER(roll_no) || '@eduplace.ac.in'
            WHERE email IS NULL OR email = ''
        """)
        cursor.execute("""
            UPDATE students
            SET mobile = '98765' || SUBSTR('00000' || student_id, -5)
            WHERE mobile IS NULL OR mobile = ''
        """)
        cursor.execute("""
            UPDATE students
            SET dob = '2003-05-15'
            WHERE dob IS NULL OR dob = ''
        """)
        cursor.execute("""
            UPDATE students
            SET year_of_study = '4th Year'
            WHERE year_of_study IS NULL OR year_of_study = ''
        """)
        cursor.execute("""
            UPDATE students
            SET section = CASE (student_id % 3) WHEN 0 THEN 'A' WHEN 1 THEN 'B' ELSE 'C' END
            WHERE section IS NULL OR section = ''
        """)
        cursor.execute("""
            UPDATE students
            SET gender = CASE (student_id % 2) WHEN 0 THEN 'Male' ELSE 'Female' END
            WHERE gender IS NULL OR gender = ''
        """)
        cursor.execute("""
            UPDATE students
            SET academic_year = '2024-2025'
            WHERE academic_year IS NULL OR academic_year = ''
        """)
        cursor.execute("""
            UPDATE students
            SET backlogs = CASE WHEN is_eligible = 1 THEN 0 ELSE 2 END
            WHERE backlogs IS NULL
        """)
        cursor.execute("""
            UPDATE students
            SET placement_eligibility = CASE WHEN is_eligible = 1 THEN 'Eligible' ELSE 'Not Eligible' END
            WHERE placement_eligibility IS NULL OR placement_eligibility = ''
        """)
        cursor.execute("""
            UPDATE students
            SET placement_status = CASE 
                WHEN (SELECT COUNT(*) FROM placements p WHERE p.student_id = students.student_id) > 0 THEN 'Placed'
                ELSE 'Unplaced'
            END
            WHERE placement_status IS NULL OR placement_status = ''
        """)
        cursor.execute("""
            UPDATE students
            SET admission_type = 'Regular', admission_year = 2021
            WHERE admission_type IS NULL OR admission_type = ''
        """)

        # Seed representative lateral-entry students among existing cohort (direct 2nd year entry)
        cursor.execute("""
            UPDATE students
            SET admission_type = 'Lateral Entry',
                admission_year = 2022,
                year_of_study = '4th Year',
                diploma_qualification = 'Diploma in ' || department,
                diploma_percentage = ROUND(80.5 + (student_id % 15) * 0.9, 2),
                diploma_college = 'State Government Polytechnic Institute'
            WHERE (student_id % 8 = 0)
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

        # Seed faculty for MySQL if empty
        try:
            cursor.execute("SELECT COUNT(*) FROM faculty")
            if cursor.fetchone()[0] == 0:
                cursor.executemany("""
                    INSERT INTO faculty (faculty_code, username, name, department, email, password_hash)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [
                    ("FAC001", "faculty", "Dr. Rajesh Sharma", "Computer Science", "faculty@eduplace.ac.in", generate_password_hash("Faculty@123")),
                    ("FAC002", "placement_officer", "Prof. Sunita Rao", "Training & Placement Cell", "tpo@eduplace.ac.in", generate_password_hash("Faculty@123")),
                ])
                cursor.execute("""
                    UPDATE students
                    SET password_hash = %s
                    WHERE password_hash IS NULL OR password_hash = ''
                """, (generate_password_hash("Student@123"),))
        except Exception as e:
            print(f"Error seeding faculty: {e}")

    # Initialize academic tables (attendance, marks, assignments, study materials, announcements)
    try:
        from academic_data import init_academic_tables
        init_academic_tables(conn)
    except Exception as e:
        print(f"[WARNING] Could not initialize academic tables: {e}")

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


def log_audit_event(action: str, student_id: int, roll_no: str, details: str, performed_by: str):
    """Logs administrative and student placement mutations into placement_audit_logs."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO placement_audit_logs (action, student_id, roll_no, details, performed_by)
            VALUES (?, ?, ?, ?, ?)
        """, (action, student_id, roll_no, str(details), performed_by))
        conn.commit()
    except Exception as e:
        print(f"[WARN] Failed to write audit log: {e}")
    finally:
        cursor.close()
        conn.close()

