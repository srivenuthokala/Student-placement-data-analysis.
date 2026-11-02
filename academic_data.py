"""
Academic Data Layer for University Portal.
Provides schemas and records for Attendance, Marks, Timetables,
Assignments, Study Materials, and Announcements.
"""
import random
import sqlite3
from config import SQLITE_DB_PATH

SUBJECTS_BY_DEPARTMENT = {
    "Computer Science": ["Distributed Systems", "Machine Learning", "Cloud Architecture", "Compiler Design"],
    "Information Technology": ["Cloud Microservices", "Big Data Analytics", "Web Architecture", "Information Security"],
    "Electronics & Comm": ["VLSI Design", "Embedded Systems", "Digital Signal Processing", "Wireless Comm"],
    "Mechanical Engg": ["FEA Analysis", "Fluid Mechanics", "Automobile Engg", "Heat & Mass Transfer"],
    "Civil Engg": ["Structural Analysis", "Geotechnical Engg", "Hydraulics", "Transportation Engg"]
}


def init_academic_tables(conn):
    """Ensures academic schemas and tables exist in the database."""
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        total_classes INTEGER NOT NULL,
        attended_classes INTEGER NOT NULL,
        percentage REAL NOT NULL,
        FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS marks (
        mark_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        semester TEXT NOT NULL,
        subject TEXT NOT NULL,
        internal_marks REAL NOT NULL,
        external_marks REAL NOT NULL,
        total_marks REAL NOT NULL,
        grade TEXT NOT NULL,
        credits INTEGER NOT NULL,
        FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS assignments (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        department TEXT NOT NULL,
        title TEXT NOT NULL,
        subject TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Active',
        file_url TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS study_materials (
        material_id INTEGER PRIMARY KEY AUTOINCREMENT,
        department TEXT NOT NULL,
        subject TEXT NOT NULL,
        title TEXT NOT NULL,
        material_type TEXT NOT NULL,
        file_size TEXT NOT NULL,
        download_url TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS timetables (
        timetable_id INTEGER PRIMARY KEY AUTOINCREMENT,
        department TEXT NOT NULL,
        day_of_week TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        subject TEXT NOT NULL,
        room TEXT NOT NULL,
        faculty_name TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS announcements (
        announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        author TEXT NOT NULL,
        category TEXT NOT NULL,
        date_posted TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'Normal'
    );
    """)

    # Populate announcements
    cursor.execute("SELECT COUNT(*) FROM announcements")
    if cursor.fetchone()[0] == 0:
        announcements_data = [
            ("Campus Recruitment Drive: Google & Microsoft", "Upcoming technical interviews for eligible 2025 cohort students across all branches. Verify placement eligibility and profile on the portal.", "Prof. Sunita Rao (TPO)", "Placement", "2025-03-12", "Urgent"),
            ("Semester End University Examination Notification", "End semester theory and laboratory examinations commence on April 21. Minimum 75% attendance required for hall ticket generation.", "Dean of Academic Affairs", "Academic", "2025-03-10", "High"),
            ("Workshop: Scalable Cloud Architecture with Kubernetes", "Hands-on technical workshop organized by CSE & IT departments in Academic Seminar Hall B this Saturday.", "Dr. Rajesh Sharma (Faculty CSE)", "Workshop", "2025-03-08", "Normal"),
            ("Pre-Final & Final Year Research Internship Call", "Applications are invited for sponsored 6-month research internships in Embedded AI, Robotics, and Cloud Systems.", "Research & Innovation Cell", "Internship", "2025-03-05", "Normal"),
            ("Annual Sports & Cultural Festival 'AURA 2025'", "Registrations open for technical symposiums, hackathons, and sports events. Details available at the student activity center.", "Student Council", "Event", "2025-03-01", "Normal")
        ]
        cursor.executemany("INSERT INTO announcements (title, content, author, category, date_posted, priority) VALUES (?, ?, ?, ?, ?, ?)", announcements_data)

    # Populate assignments
    cursor.execute("SELECT COUNT(*) FROM assignments")
    if cursor.fetchone()[0] == 0:
        assignments_data = [
            ("Computer Science", "Distributed Consensus Algorithm Implementation", "Distributed Systems", "2025-03-25", "Active", "#"),
            ("Computer Science", "Deep Neural Network Model for Sentiment Classification", "Machine Learning", "2025-03-28", "Active", "#"),
            ("Information Technology", "Microservices Containerization & Gateway Project", "Cloud Microservices", "2025-03-24", "Active", "#"),
            ("Information Technology", "Network Intrusion Detection System Prototype", "Information Security", "2025-03-29", "Active", "#"),
            ("Electronics & Comm", "FPGA Digital Filter Simulation & Verilog Code", "VLSI Design", "2025-03-26", "Active", "#"),
            ("Electronics & Comm", "RTOS Task Scheduling on ARM Cortex-M4", "Embedded Systems", "2025-03-30", "Active", "#"),
            ("Mechanical Engg", "Finite Element Modeling of Gearbox Assembly", "FEA Analysis", "2025-03-27", "Active", "#"),
            ("Mechanical Engg", "Heat Exchanger Thermal Performance Analysis", "Heat & Mass Transfer", "2025-03-31", "Active", "#"),
            ("Civil Engg", "Seismic Response Analysis of Multi-Storey Frame", "Structural Analysis", "2025-03-29", "Active", "#"),
            ("Civil Engg", "Deep Foundation Soil Bearing Capacity Report", "Geotechnical Engg", "2025-04-02", "Active", "#")
        ]
        cursor.executemany("INSERT INTO assignments (department, title, subject, due_date, status, file_url) VALUES (?, ?, ?, ?, ?, ?)", assignments_data)

    # Populate study materials
    cursor.execute("SELECT COUNT(*) FROM study_materials")
    if cursor.fetchone()[0] == 0:
        materials_data = [
            ("Computer Science", "Distributed Systems Architecture & Paxos Notes", "Distributed Systems", "Lecture Notes PDF", "4.5 MB", "#"),
            ("Computer Science", "Advanced Machine Learning Algorithms Cheatsheet", "Machine Learning", "Reference PDF", "3.8 MB", "#"),
            ("Computer Science", "Compiler Lexical Analysis & Parsing Handbook", "Compiler Design", "Study Guide PDF", "2.9 MB", "#"),
            ("Information Technology", "Cloud Native Microservices Patterns & Best Practices", "Cloud Microservices", "Technical E-Book", "5.2 MB", "#"),
            ("Information Technology", "Big Data Analytics & MapReduce Practical Lab Manual", "Big Data Analytics", "Lab Manual PDF", "3.4 MB", "#"),
            ("Electronics & Comm", "VLSI Architecture & CMOS Design Lecture Series", "VLSI Design", "Handout PDF", "4.1 MB", "#"),
            ("Electronics & Comm", "Embedded C & Real-Time Operating Systems Guide", "Embedded Systems", "Code Reference PDF", "3.6 MB", "#"),
            ("Mechanical Engg", "Ansys FEA Simulation Practical Step-by-Step Manual", "FEA Analysis", "Guide PDF", "6.2 MB", "#"),
            ("Mechanical Engg", "Internal Combustion Engines & Automobile Systems", "Automobile Engg", "Lecture Notes PDF", "4.8 MB", "#"),
            ("Civil Engg", "IS 456 & IS 1893 Structural Design Manual", "Structural Analysis", "Code Manual PDF", "7.1 MB", "#"),
            ("Civil Engg", "Soil Mechanics & Foundation Engineering Handouts", "Geotechnical Engg", "Handbook PDF", "3.9 MB", "#")
        ]
        cursor.executemany("INSERT INTO study_materials (department, subject, title, material_type, file_size, download_url) VALUES (?, ?, ?, ?, ?, ?)", materials_data)

    # Populate timetables
    cursor.execute("SELECT COUNT(*) FROM timetables")
    if cursor.fetchone()[0] == 0:
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        timetable_entries = []
        for dept, subjs in SUBJECTS_BY_DEPARTMENT.items():
            for idx, day in enumerate(days):
                sub1 = subjs[idx % len(subjs)]
                sub2 = subjs[(idx + 1) % len(subjs)]
                sub3 = subjs[(idx + 2) % len(subjs)]
                timetable_entries.append((dept, day, "09:00 - 10:00 AM", sub1, f"Room {301 + (idx % 3)}", "Prof. Senior Faculty"))
                timetable_entries.append((dept, day, "10:15 - 11:15 AM", sub2, f"Room {301 + (idx % 3)}", "Prof. Associate Faculty"))
                timetable_entries.append((dept, day, "11:30 - 01:00 PM", f"{sub3} Practical Lab", f"{dept[:3].upper()} Lab 1", "Lab Instructors"))
                timetable_entries.append((dept, day, "02:00 - 03:30 PM", "Technical Seminar / Placement Prep", "Seminar Hall", "Department Team"))
        cursor.executemany("INSERT INTO timetables (department, day_of_week, time_slot, subject, room, faculty_name) VALUES (?, ?, ?, ?, ?, ?)", timetable_entries)

    # Populate attendance & marks for students
    cursor.execute("SELECT COUNT(*) FROM attendance")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT student_id, department, cgpa, is_eligible FROM students")
        students = cursor.fetchall()
        
        att_rows = []
        mark_rows = []
        random.seed(42)

        for s_id, dept, cgpa, elig in students:
            subjs = SUBJECTS_BY_DEPARTMENT.get(dept, SUBJECTS_BY_DEPARTMENT["Computer Science"])
            total_classes = 48
            for subj in subjs:
                if elig == 1:
                    pct = round(random.uniform(78.0, 96.5), 1)
                else:
                    pct = round(random.uniform(54.0, 72.5), 1)
                attended = int(round((pct / 100.0) * total_classes))
                att_rows.append((s_id, subj, total_classes, attended, pct))

                # Marks & Grades
                base = min(98, max(46, int(cgpa * 9.4 + random.uniform(-4, 4))))
                internal = round(min(30, max(14, base * 0.3)), 1)
                external = round(min(70, max(28, base * 0.7)), 1)
                tot = round(internal + external, 1)
                grade = "O" if tot >= 90 else "A+" if tot >= 80 else "A" if tot >= 70 else "B+" if tot >= 60 else "B" if tot >= 50 else "RA"
                mark_rows.append((s_id, "Semester 7", subj, internal, external, tot, grade, 4))

        cursor.executemany("INSERT INTO attendance (student_id, subject, total_classes, attended_classes, percentage) VALUES (?, ?, ?, ?, ?)", att_rows)
        cursor.executemany("INSERT INTO marks (student_id, semester, subject, internal_marks, external_marks, total_marks, grade, credits) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", mark_rows)

    conn.commit()


def get_student_academic_bundle(student_id: int, department: str):
    """Fetches full academic bundle for a student."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Attendance
    cursor.execute("SELECT subject, total_classes, attended_classes, percentage FROM attendance WHERE student_id = ?", (student_id,))
    attendance_records = [dict(r) for r in cursor.fetchall()]
    
    total_conducted = sum(r["total_classes"] for r in attendance_records) or 1
    total_attended = sum(r["attended_classes"] for r in attendance_records)
    overall_attendance = round((total_attended / total_conducted) * 100, 1) if attendance_records else 0.0

    # Marks
    cursor.execute("SELECT semester, subject, internal_marks, external_marks, total_marks, grade, credits FROM marks WHERE student_id = ? ORDER BY total_marks DESC", (student_id,))
    marks_records = [dict(r) for r in cursor.fetchall()]

    # Department Timetable
    cursor.execute("SELECT day_of_week, time_slot, subject, room, faculty_name FROM timetables WHERE department = ? ORDER BY day_of_week, time_slot", (department,))
    timetable_records = [dict(r) for r in cursor.fetchall()]

    # Department Assignments
    cursor.execute("SELECT assignment_id, title, subject, due_date, status, file_url FROM assignments WHERE department = ? ORDER BY due_date ASC", (department,))
    assignments_records = [dict(r) for r in cursor.fetchall()]

    # Department Study Materials
    cursor.execute("SELECT material_id, subject, title, material_type, file_size, download_url FROM study_materials WHERE department = ? ORDER BY title ASC", (department,))
    materials_records = [dict(r) for r in cursor.fetchall()]

    # Announcements
    cursor.execute("SELECT announcement_id, title, content, author, category, date_posted, priority FROM announcements ORDER BY date_posted DESC, priority DESC LIMIT 6")
    announcements_records = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "attendance": attendance_records,
        "overall_attendance": overall_attendance,
        "marks": marks_records,
        "timetable": timetable_records,
        "assignments": assignments_records,
        "materials": materials_records,
        "announcements": announcements_records
    }


def get_faculty_academic_bundle(department: str = None):
    """Fetches academic management metrics for faculty dashboard."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Low attendance count (<75%)
    cursor.execute("""
        SELECT s.student_id, s.roll_no, s.name, s.department, s.cgpa,
               ROUND(AVG(a.percentage), 1) as avg_attendance
        FROM students s
        JOIN attendance a ON s.student_id = a.student_id
        GROUP BY s.student_id
        HAVING avg_attendance < 75.0
        ORDER BY avg_attendance ASC
    """)
    low_attendance_students = [dict(r) for r in cursor.fetchall()]

    # Academic Grade Distribution
    cursor.execute("SELECT grade, COUNT(*) as count FROM marks GROUP BY grade")
    grade_distribution = {r["grade"]: r["count"] for r in cursor.fetchall()}

    # All Announcements
    cursor.execute("SELECT announcement_id, title, content, author, category, date_posted, priority FROM announcements ORDER BY date_posted DESC")
    announcements = [dict(r) for r in cursor.fetchall()]

    # Assignments
    cursor.execute("SELECT assignment_id, department, title, subject, due_date, status FROM assignments ORDER BY due_date ASC")
    assignments = [dict(r) for r in cursor.fetchall()]

    # Study Materials
    cursor.execute("SELECT material_id, department, subject, title, material_type, file_size FROM study_materials ORDER BY department, title ASC")
    materials = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "low_attendance_students": low_attendance_students,
        "grade_distribution": grade_distribution,
        "announcements": announcements,
        "assignments": assignments,
        "materials": materials
    }
