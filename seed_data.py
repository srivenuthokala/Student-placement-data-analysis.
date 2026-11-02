"""
Seed script to populate database with realistic, fictional student placement data.
Generates:
- 200 Students across all 5 departments with Regular and Lateral Entry admissions
- Full profile details (contact, DOB, gender, year of study, section, academic year)
- Lateral entry polytechnic diploma credentials
- Skills catalog and student skill mappings
- Placement offers from 16 verified corporate company partners
- Course attendance and semester marks for all 200 students
"""
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from database import init_database, get_connection, log_audit_event
from academic_data import SUBJECTS_BY_DEPARTMENT

DEPARTMENTS = [
    "Computer Science",
    "Information Technology",
    "Electronics & Comm",
    "Mechanical Engg",
    "Civil Engg"
]

SKILLS_POOL = [
    "Python", "SQL", "Java", "C++", "Data Structures",
    "Machine Learning", "React", "Node.js", "AWS", "Docker",
    "Embedded Systems", "AutoCAD", "MATLAB", "Spring Boot",
    "Data Analytics", "Kubernetes", "IoT", "Cybersecurity"
]

COMPANY_PARTNERS = [
    {
        "company": "Google",
        "tier": "Super Dream",
        "category": "Tier 1 Product",
        "icon": "fa-brands fa-google",
        "role": "Associate Software Engineer",
        "salary_range": (24.0, 34.0),
        "depts": ["Computer Science", "Information Technology", "Electronics & Comm"]
    },
    {
        "company": "Microsoft",
        "tier": "Super Dream",
        "category": "Cloud & OS",
        "icon": "fa-brands fa-microsoft",
        "role": "Software Engineer",
        "salary_range": (20.0, 30.0),
        "depts": ["Computer Science", "Information Technology", "Electronics & Comm"]
    },
    {
        "company": "Amazon",
        "tier": "Super Dream",
        "category": "E-Commerce & Cloud",
        "icon": "fa-brands fa-amazon",
        "role": "SDE-1 (Cloud Services)",
        "salary_range": (16.0, 26.0),
        "depts": ["Computer Science", "Information Technology"]
    },
    {
        "company": "Qualcomm",
        "tier": "Super Dream",
        "category": "Semiconductors",
        "icon": "fa-solid fa-microchip",
        "role": "Embedded Software Engineer",
        "salary_range": (14.0, 22.0),
        "depts": ["Electronics & Comm", "Computer Science"]
    },
    {
        "company": "Adobe",
        "tier": "Super Dream",
        "category": "Creative & Cloud Tech",
        "icon": "fa-solid fa-shapes",
        "role": "Member of Technical Staff",
        "salary_range": (16.0, 24.0),
        "depts": ["Computer Science", "Information Technology"]
    },
    {
        "company": "Cisco Systems",
        "tier": "Dream",
        "category": "Networking & Security",
        "icon": "fa-solid fa-network-wired",
        "role": "Network Security Engineer",
        "salary_range": (12.0, 18.0),
        "depts": ["Computer Science", "Information Technology", "Electronics & Comm"]
    },
    {
        "company": "Samsung R&D",
        "tier": "Dream",
        "category": "Consumer Electronics",
        "icon": "fa-solid fa-mobile-screen",
        "role": "R&D Software Engineer",
        "salary_range": (11.0, 17.5),
        "depts": ["Computer Science", "Electronics & Comm"]
    },
    {
        "company": "Oracle",
        "tier": "Dream",
        "category": "Enterprise Database",
        "icon": "fa-solid fa-database",
        "role": "Applications Developer",
        "salary_range": (10.5, 16.0),
        "depts": ["Computer Science", "Information Technology"]
    },
    {
        "company": "Deloitte",
        "tier": "Dream",
        "category": "Tech Consulting",
        "icon": "fa-solid fa-chart-line",
        "role": "Technology Analyst",
        "salary_range": (7.5, 11.5),
        "depts": ["Computer Science", "Information Technology", "Electronics & Comm", "Mechanical Engg", "Civil Engg"]
    },
    {
        "company": "Texas Instruments",
        "tier": "Dream",
        "category": "Hardware & Embedded",
        "icon": "fa-solid fa-bolt",
        "role": "Analog & Digital Design Engineer",
        "salary_range": (12.5, 19.0),
        "depts": ["Electronics & Comm"]
    },
    {
        "company": "Tata Motors",
        "tier": "Core Engineering",
        "category": "Automotive & EV",
        "icon": "fa-solid fa-car-side",
        "role": "Graduate Engineer Trainee (R&D)",
        "salary_range": (6.0, 9.5),
        "depts": ["Mechanical Engg", "Electronics & Comm"]
    },
    {
        "company": "L&T (Larsen & Toubro)",
        "tier": "Core Engineering",
        "category": "Infrastructure & EPC",
        "icon": "fa-solid fa-building",
        "role": "Graduate Engineer Trainee (Design)",
        "salary_range": (5.5, 8.5),
        "depts": ["Civil Engg", "Mechanical Engg"]
    },
    {
        "company": "Bosch",
        "tier": "Core Engineering",
        "category": "Industrial IoT & Auto",
        "icon": "fa-solid fa-gears",
        "role": "Embedded Automotive Specialist",
        "salary_range": (6.5, 10.5),
        "depts": ["Mechanical Engg", "Electronics & Comm"]
    },
    {
        "company": "TCS",
        "tier": "IT Solutions",
        "category": "Enterprise Services",
        "icon": "fa-solid fa-laptop-code",
        "role": "Digital Specialist Engineer",
        "salary_range": (4.0, 8.5),
        "depts": ["Computer Science", "Information Technology", "Electronics & Comm", "Mechanical Engg", "Civil Engg"]
    },
    {
        "company": "Infosys",
        "tier": "IT Solutions",
        "category": "Global IT Services",
        "icon": "fa-solid fa-code-branch",
        "role": "Specialist Programmer",
        "salary_range": (4.5, 9.0),
        "depts": ["Computer Science", "Information Technology", "Electronics & Comm", "Mechanical Engg", "Civil Engg"]
    },
    {
        "company": "Cognizant",
        "tier": "IT Solutions",
        "category": "Digital Engineering",
        "icon": "fa-solid fa-cubes",
        "role": "GenC Next Developer",
        "salary_range": (4.5, 7.8),
        "depts": ["Computer Science", "Information Technology", "Electronics & Comm", "Mechanical Engg", "Civil Engg"]
    }
]

FIRST_NAMES = [
    "Aarav", "Aditi", "Rohan", "Sneha", "Vikram", "Pooja", "Rahul", "Ananya",
    "Kavya", "Siddharth", "Meera", "Arjun", "Neha", "Karthik", "Riya", "Varun",
    "Isha", "Naveen", "Tanvi", "Deepak", "Shreya", "Amit", "Divya", "Suresh",
    "Priya", "Manish", "Swati", "Harish", "Kiran", "Nikhil", "Bhavna", "Abhishek",
    "Tarun", "Payal", "Pranav", "Lavanya", "Kunal", "Mehak", "Gaurav", "Simran",
    "Rajat", "Pallavi", "Gautam", "Aishwarya", "Vishal", "Shruti", "Akash", "Komal"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Iyer", "Nair", "Gupta", "Singh",
    "Choudhury", "Das", "Rao", "Joshi", "Kulkarni", "Mehta", "Bhat", "Mishra",
    "Pandey", "Saxena", "Deshmukh", "Nambiar", "Pillai", "Chauhan", "Bhattacharya", "Menon"
]

DIPLOMA_COLLEGES = [
    "Government Polytechnic College, Hyderabad",
    "Government Institute of Electronics, Secunderabad",
    "State Technical Polytechnic Institute, Bangalore",
    "Dr. B.R. Ambedkar Polytechnic College, Pune",
    "Vivekananda Memorial Polytechnic, Chennai",
    "Central Polytechnic College, Thiruvananthapuram"
]


def seed_all_data(total_students: int = 200, grad_year: int = 2025):
    """Initializes tables and seeds 200 student records with placement data."""
    random.seed(42)  # For reproducible dataset
    default_hash = generate_password_hash("Student@123")
    init_database()
    conn = get_connection()
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM attendance")
    cursor.execute("DELETE FROM marks")
    cursor.execute("DELETE FROM placements")
    cursor.execute("DELETE FROM student_skills")
    cursor.execute("DELETE FROM skills")
    cursor.execute("DELETE FROM students")

    # 1. Insert Skills
    skill_ids = {}
    for skill_name in SKILLS_POOL:
        cursor.execute("INSERT INTO skills (skill_name) VALUES (?)", (skill_name,))
        skill_ids[skill_name] = cursor.lastrowid

    # 2. Insert 200 Students
    students = []
    # Weighted department distribution (realistic engineering college cohort)
    dept_choices = [
        "Computer Science", "Computer Science", "Computer Science",
        "Information Technology", "Information Technology",
        "Electronics & Comm", "Electronics & Comm",
        "Mechanical Engg", "Civil Engg"
    ]

    for i in range(1, total_students + 1):
        dept = random.choice(dept_choices)
        roll_no = f"{dept[:3].upper()}{grad_year}{i:03d}"
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}{i}@eduplace.ac.in"
        mobile = f"+91 {random.choice([98, 97, 99, 96, 94])}{random.randint(10000000, 99999999)}"
        gender = random.choice(["Male", "Female"] if i % 2 == 0 else ["Female", "Male"])
        section = random.choice(["A", "B", "C"])
        dob_year = random.randint(2002, 2004)
        dob_month = random.randint(1, 12)
        dob_day = random.randint(1, 28)
        dob = f"{dob_year}-{dob_month:02d}-{dob_day:02d}"

        # ~15% Lateral Entry students (e.g. 30 out of 200)
        is_lateral = (i % 7 == 0)
        if is_lateral:
            admission_type = "Lateral Entry"
            year_of_study = random.choice(["3rd Year", "4th Year"])
            admission_year = 2022
            diploma_dept = f"Diploma in {dept}"
            diploma_percentage = round(random.uniform(77.0, 94.5), 1)
            diploma_college = random.choice(DIPLOMA_COLLEGES)
        else:
            admission_type = "Regular"
            year_of_study = "4th Year"
            admission_year = 2021
            diploma_dept = None
            diploma_percentage = None
            diploma_college = None

        # CGPA & Eligibility
        cgpa = round(random.uniform(5.4, 9.85), 2)
        has_backlogs = 1 if (cgpa < 6.2 and random.random() < 0.45) else 0

        # Placement Eligibility: CGPA >= 6.0 and no active backlogs with 92% clearance
        is_eligible = 1 if (cgpa >= 6.0 and has_backlogs == 0 and random.random() < 0.92) else 0
        placement_eligibility = "Eligible" if is_eligible == 1 else "Not Eligible"

        cursor.execute("""
            INSERT INTO students (
                roll_no, name, admission_type, department, year_of_study, section,
                email, mobile, dob, gender, graduation_year, academic_year,
                cgpa, backlogs, is_eligible, placement_eligibility, placement_status,
                diploma_qualification, diploma_percentage, diploma_college, admission_year,
                password_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            roll_no, name, admission_type, dept, year_of_study, section,
            email, mobile, dob, gender, grad_year, "2024-2025",
            cgpa, has_backlogs, is_eligible, placement_eligibility, "Unplaced",
            diploma_dept, diploma_percentage, diploma_college, admission_year,
            default_hash
        ))
        student_id = cursor.lastrowid
        students.append({
            "student_id": student_id,
            "roll_no": roll_no,
            "name": name,
            "department": dept,
            "admission_type": admission_type,
            "cgpa": cgpa,
            "is_eligible": is_eligible
        })

    # 3. Assign Skills to Students
    for s in students:
        if s["department"] in ["Computer Science", "Information Technology"]:
            dept_skills = ["Python", "SQL", "Java", "Data Structures", "React", "AWS", "Machine Learning", "Docker", "Node.js", "Kubernetes"]
        elif s["department"] == "Electronics & Comm":
            dept_skills = ["C++", "Embedded Systems", "Python", "MATLAB", "SQL", "Data Structures", "IoT"]
        elif s["department"] == "Mechanical Engg":
            dept_skills = ["AutoCAD", "MATLAB", "Python", "Data Analytics", "IoT"]
        else:  # Civil Engg
            dept_skills = ["AutoCAD", "Data Analytics", "Python", "SQL"]

        assigned = random.sample(dept_skills, k=random.randint(3, min(6, len(dept_skills))))
        for sk in assigned:
            cursor.execute("""
                INSERT OR IGNORE INTO student_skills (student_id, skill_id)
                VALUES (?, ?)
            """, (s["student_id"], skill_ids[sk]))

    # 4. Insert Placement Offers
    eligible_students = [s for s in students if s["is_eligible"] == 1]
    base_date = datetime(grad_year - 1, 8, 1)

    for s in eligible_students:
        # Placement probability: tech departments get higher placement rate
        bias = 0.88 if s["department"] in ["Computer Science", "Information Technology"] else 0.72
        if s["cgpa"] >= 8.0:
            bias += 0.09

        is_placed = random.random() < bias
        if is_placed:
            # 1 offer (72%), 2 offers (23%), 3 offers (5%)
            num_offers = random.choices([1, 2, 3], weights=[0.72, 0.23, 0.05])[0]

            # Filter companies recruiting from this department
            matched_companies = [c for c in COMPANY_PARTNERS if s["department"] in c["depts"]]
            if not matched_companies:
                matched_companies = COMPANY_PARTNERS

            chosen_companies = random.sample(matched_companies, k=min(num_offers, len(matched_companies)))

            for idx, c_info in enumerate(chosen_companies):
                comp_name = c_info["company"]
                role_name = c_info["role"]
                min_p, max_p = c_info["salary_range"]

                cgpa_factor = max(0.0, min(1.0, (s["cgpa"] - 6.0) / 4.0))
                package = round(min_p + (max_p - min_p) * (cgpa_factor * 0.65 + random.random() * 0.35), 2)
                placement_date = (base_date + timedelta(days=random.randint(15, 210))).strftime("%Y-%m-%d")
                status = "Accepted" if idx == 0 else "Offered"

                cursor.execute("""
                    INSERT INTO placements (student_id, company, role, package, placement_date, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (s["student_id"], comp_name, role_name, package, placement_date, status))

            # Update student placement status to 'Placed'
            cursor.execute("UPDATE students SET placement_status = 'Placed' WHERE student_id = ?", (s["student_id"],))

    # 5. Populate Attendance & Marks for All 200 Students
    att_rows = []
    mark_rows = []
    for s in students:
        s_id = s["student_id"]
        dept = s["department"]
        cgpa = s["cgpa"]
        elig = s["is_eligible"]
        subjs = SUBJECTS_BY_DEPARTMENT.get(dept, SUBJECTS_BY_DEPARTMENT["Computer Science"])
        total_classes = 48

        for subj in subjs:
            if elig == 1:
                pct = round(random.uniform(78.5, 96.0), 1)
            else:
                pct = round(random.uniform(54.0, 72.0), 1)
            attended = int(round((pct / 100.0) * total_classes))
            att_rows.append((s_id, subj, total_classes, attended, pct))

            # Marks
            base = min(98, max(46, int(cgpa * 9.4 + random.uniform(-4, 4))))
            internal = round(min(30, max(14, base * 0.3)), 1)
            external = round(min(70, max(28, base * 0.7)), 1)
            tot = round(internal + external, 1)
            grade = "O" if tot >= 90 else "A+" if tot >= 80 else "A" if tot >= 70 else "B+" if tot >= 60 else "B" if tot >= 50 else "RA"
            mark_rows.append((s_id, "Semester 7", subj, internal, external, tot, grade, 4))

    cursor.executemany("INSERT INTO attendance (student_id, subject, total_classes, attended_classes, percentage) VALUES (?, ?, ?, ?, ?)", att_rows)
    cursor.executemany("INSERT INTO marks (student_id, semester, subject, internal_marks, external_marks, total_marks, grade, credits) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", mark_rows)

    conn.commit()
    conn.close()

    log_audit_event(
        action="SEED_DATABASE",
        student_id=None,
        roll_no=None,
        details=f"Successfully seeded {len(students)} students with 16 hiring partners, attendance, and marks.",
        performed_by="System Administrator"
    )
    print(f"[OK] Successfully seeded {len(students)} students and their placement outcomes.")


if __name__ == "__main__":
    seed_all_data(200)
