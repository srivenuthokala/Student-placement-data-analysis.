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
            ("username", "TEXT"),
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

        # Create companies directory table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            company_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            industry TEXT DEFAULT 'Technology & Software',
            tier TEXT DEFAULT 'Tier 1',
            website TEXT,
            contact_email TEXT,
            location TEXT DEFAULT 'Pan India',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Create placement drives table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS placement_drives (
            drive_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            role TEXT NOT NULL,
            package_lpa REAL NOT NULL,
            drive_date TEXT NOT NULL,
            min_cgpa REAL DEFAULT 6.0,
            eligible_departments TEXT DEFAULT 'All Departments',
            max_backlogs INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Upcoming',
            registered_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Create applications & interviews table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            application_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            roll_no TEXT NOT NULL,
            student_name TEXT NOT NULL,
            department TEXT NOT NULL,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            applied_date TEXT NOT NULL,
            current_round TEXT DEFAULT 'Aptitude Test',
            status TEXT DEFAULT 'Applied',
            package_lpa REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Create system_settings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            setting_key TEXT PRIMARY KEY,
            setting_val TEXT NOT NULL
        );
        """)

        # Seed initial companies if empty
        cursor.execute("SELECT COUNT(*) FROM companies")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("""
                INSERT INTO companies (name, industry, tier, website, contact_email, location)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                ("Google", "Cloud & AI Systems", "Tier 1 (Super Dream)", "https://careers.google.com", "campus-in@google.com", "Bangalore / Hyderabad"),
                ("Microsoft", "Enterprise Software & Cloud", "Tier 1 (Super Dream)", "https://careers.microsoft.com", "india-recruiting@microsoft.com", "Hyderabad / Noida"),
                ("Amazon", "E-Commerce & AWS Cloud", "Tier 1 (Super Dream)", "https://amazon.jobs", "aws-campus@amazon.com", "Bangalore / Chennai"),
                ("Cisco Systems", "Networking & Cyber Security", "Tier 1 (Super Dream)", "https://cisco.com/careers", "cisco-hire@cisco.com", "Bangalore"),
                ("Oracle", "Database & Enterprise Cloud", "Tier 2 (Dream)", "https://oracle.com/careers", "campus-relations@oracle.com", "Bangalore / Pune"),
                ("Infosys", "Consulting & IT Services", "Tier 2 (Dream)", "https://infosys.com/careers", "campusconnect@infosys.com", "Bangalore / Pune / Mysore"),
                ("Tata Consultancy Services", "Global IT Infrastructure", "Tier 2 (Dream)", "https://tcs.com/careers", "campus-in@tcs.com", "Mumbai / Chennai / Hyderabad"),
                ("Wipro", "Digital Transformation", "Tier 3 (Regular)", "https://wipro.com/careers", "freshers@wipro.com", "Bangalore / Kolkata"),
                ("Accenture", "Technology & Strategy", "Tier 2 (Dream)", "https://accenture.com/careers", "india.campus@accenture.com", "Gurgaon / Bangalore"),
                ("Cognizant", "Interactive & IT Operations", "Tier 3 (Regular)", "https://cognizant.com/careers", "campus-india@cognizant.com", "Chennai / Coimbatore")
            ])

        # Seed initial placement drives if empty
        cursor.execute("SELECT COUNT(*) FROM placement_drives")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("""
                INSERT INTO placement_drives (company_name, role, package_lpa, drive_date, min_cgpa, eligible_departments, max_backlogs, status, registered_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                ("Google", "Software Development Engineer", 18.5, "2025-03-15", 7.5, "Computer Science, Information Technology, Electronics & Comm", 0, "Active", 48),
                ("Microsoft", "Cloud Solutions Engineer", 16.0, "2025-03-22", 7.0, "Computer Science, Information Technology, Electronics & Comm", 0, "Active", 52),
                ("Amazon", "SDE - Operations Tech", 14.0, "2025-03-29", 7.0, "All Departments", 0, "Upcoming", 65),
                ("Oracle", "Systems Applications Engineer", 11.5, "2025-04-05", 6.5, "Computer Science, Information Technology", 0, "Upcoming", 42),
                ("Infosys", "Specialist Programmer", 9.5, "2025-04-12", 6.5, "All Departments", 0, "Upcoming", 88),
                ("Tata Consultancy Services", "Digital Innovator", 7.5, "2025-04-20", 6.0, "All Departments", 0, "Upcoming", 120),
                ("Accenture", "Advanced App Engineering Analyst", 6.5, "2025-02-18", 6.0, "All Departments", 0, "Completed", 110)
            ])

        # Seed initial applications if empty
        cursor.execute("SELECT COUNT(*) FROM applications")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO applications (student_id, roll_no, student_name, department, company, role, applied_date, current_round, status, package_lpa)
                SELECT s.student_id, s.roll_no, s.name, s.department, 'Google', 'Software Development Engineer', '2025-02-20', 'Technical Round 2', 'In Progress', 18.5
                FROM students s WHERE s.cgpa >= 8.5 AND s.is_eligible = 1 LIMIT 5
            """)
            cursor.execute("""
                INSERT INTO applications (student_id, roll_no, student_name, department, company, role, applied_date, current_round, status, package_lpa)
                SELECT s.student_id, s.roll_no, s.name, s.department, 'Microsoft', 'Cloud Solutions Engineer', '2025-02-22', 'Technical Round 1', 'In Progress', 16.0
                FROM students s WHERE s.cgpa >= 7.8 AND s.cgpa < 8.5 AND s.is_eligible = 1 LIMIT 6
            """)
            cursor.execute("""
                INSERT INTO applications (student_id, roll_no, student_name, department, company, role, applied_date, current_round, status, package_lpa)
                SELECT s.student_id, s.roll_no, s.name, s.department, 'Amazon', 'SDE - Operations Tech', '2025-02-25', 'Aptitude Test', 'Shortlisted', 14.0
                FROM students s WHERE s.cgpa >= 7.0 AND s.is_eligible = 1 LIMIT 8
            """)

        # Seed default system settings
        default_settings = [
            ("min_cgpa_cutoff", "6.0"),
            ("max_backlogs_allowed", "0"),
            ("dream_package_threshold", "10.0"),
            ("currency_unit", "LPA"),
            ("target_graduation_year", "2025"),
            ("policy_one_dream_offer", "Enabled"),
            ("institution_name", "EduPlace University Placement Cell"),
            ("contact_email", "tpo@eduplace.ac.in")
        ]
        for key, val in default_settings:
            cursor.execute("INSERT OR IGNORE INTO system_settings (setting_key, setting_val) VALUES (?, ?)", (key, val))

        # Seed initial faculty accounts if table is empty
        cursor.execute("SELECT COUNT(*) FROM faculty")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("""
                INSERT INTO faculty (faculty_code, username, name, department, email, password_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                ("FAC001", "faculty", "Dr. Rajesh Sharma", "Computer Science", "faculty@eduplace.ac.in", generate_password_hash("faculty123")),
                ("FAC002", "placement_officer", "Prof. Sunita Rao", "Training & Placement Cell", "tpo@eduplace.ac.in", generate_password_hash("faculty123")),
            ])
        else:
            # Ensure faculty account password is updated to requested faculty123
            cursor.execute("""
                UPDATE faculty
                SET password_hash = ?
                WHERE LOWER(username) = 'faculty'
            """, (generate_password_hash("faculty123"),))

        # Ensure all students have password_hash set to student123
        cursor.execute("""
            UPDATE students
            SET password_hash = ?
        """, (generate_password_hash("student123"),))

        # Ensure student with username = 'student' exists (map to primary student or COM2025001)
        cursor.execute("""
            UPDATE students
            SET username = 'student'
            WHERE roll_no = 'COM2025001' OR student_id = (SELECT MIN(student_id) FROM students)
        """)

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
                    ("FAC001", "faculty", "Dr. Rajesh Sharma", "Computer Science", "faculty@eduplace.ac.in", generate_password_hash("faculty123")),
                    ("FAC002", "placement_officer", "Prof. Sunita Rao", "Training & Placement Cell", "tpo@eduplace.ac.in", generate_password_hash("faculty123")),
                ])
            else:
                cursor.execute("""
                    UPDATE faculty
                    SET password_hash = %s
                    WHERE LOWER(username) = 'faculty'
                """, (generate_password_hash("faculty123"),))

            cursor.execute("""
                UPDATE students
                SET password_hash = %s
            """, (generate_password_hash("student123"),))

            cursor.execute("""
                UPDATE students
                SET username = 'student'
                WHERE roll_no = 'COM2025001' OR student_id = (SELECT MIN(student_id) FROM (SELECT student_id FROM students) as s)
            """)
        except Exception as e:
            print(f"Error seeding faculty: {e}")

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

