"""
Seed script to populate database with realistic, fictional student placement data.
Generates:
- Students with department, CGPA, and eligibility status
- Skills catalog
- Student skill mappings
- Placement offers (including students with multiple offers to test duplicate handling)
"""
import random
from datetime import datetime, timedelta
from database import init_database, get_connection

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
    "Data Analytics", "Kubernetes"
]

COMPANIES_AND_ROLES = [
    ("Google", "Associate Software Engineer", (22.0, 32.0)),
    ("Microsoft", "Software Engineer", (18.0, 28.0)),
    ("Amazon", "Cloud Support Associate", (14.0, 20.0)),
    ("Qualcomm", "Embedded Software Engineer", (12.0, 18.0)),
    ("Cisco", "Network Engineer", (10.0, 15.0)),
    ("Deloitte", "Technology Analyst", (7.0, 10.5)),
    ("TCS", "Systems Engineer", (3.6, 7.2)),
    ("Infosys", "Specialist Programmer", (4.0, 8.0)),
    ("Wipro", "Project Engineer", (3.5, 6.5)),
    ("Tata Motors", "Graduate Engineer Trainee", (5.5, 8.5)),
    ("L&T", "Design & Planning Engineer", (4.5, 7.5)),
    ("Cognizant", "Programmer Analyst", (4.0, 6.8)),
    ("Accenture", "Associate Software Engineer", (4.5, 7.0))
]

FIRST_NAMES = [
    "Aarav", "Aditi", "Rohan", "Sneha", "Vikram", "Pooja", "Rahul", "Ananya",
    "Kavya", "Siddharth", "Meera", "Arjun", "Neha", "Karthik", "Riya", "Varun",
    "Isha", "Naveen", "Tanvi", "Deepak", "Shreya", "Amit", "Divya", "Suresh",
    "Priya", "Manish", "Swati", "Harish", "Kiran", "Nikhil", "Bhavna", "Abhishek"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Iyer", "Nair", "Gupta", "Singh",
    "Choudhury", "Das", "Rao", "Joshi", "Kulkarni", "Mehta", "Bhat", "Mishra"
]


def seed_all_data(total_students: int = 100, grad_year: int = 2025):
    """Initializes tables and seeds fictional student placement records."""
    random.seed(42)  # For reproducible dataset
    init_database()
    conn = get_connection()
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM placements")
    cursor.execute("DELETE FROM student_skills")
    cursor.execute("DELETE FROM skills")
    cursor.execute("DELETE FROM students")

    # 1. Insert Skills
    skill_ids = {}
    for skill_name in SKILLS_POOL:
        cursor.execute("INSERT INTO skills (skill_name) VALUES (?)", (skill_name,))
        skill_ids[skill_name] = cursor.lastrowid

    # 2. Insert Students
    students = []
    for i in range(1, total_students + 1):
        dept = random.choice(DEPARTMENTS)
        roll_no = f"{dept[:3].upper()}{grad_year}{i:03d}"
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        cgpa = round(random.uniform(5.5, 9.8), 2)
        # Eligibility criteria: CGPA >= 6.0 and 90% random clearance (no disciplinary/backlogs)
        is_eligible = 1 if (cgpa >= 6.0 and random.random() < 0.92) else 0

        cursor.execute("""
            INSERT INTO students (roll_no, name, department, graduation_year, cgpa, is_eligible)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (roll_no, name, dept, grad_year, cgpa, is_eligible))
        student_id = cursor.lastrowid
        students.append({
            "student_id": student_id,
            "roll_no": roll_no,
            "department": dept,
            "cgpa": cgpa,
            "is_eligible": is_eligible
        })

    # 3. Assign Skills to Students
    for s in students:
        # Tech students get more programming skills; core students get mixed
        if s["department"] in ["Computer Science", "Information Technology"]:
            dept_skills = ["Python", "SQL", "Java", "Data Structures", "React", "AWS", "Machine Learning", "Docker"]
        elif s["department"] == "Electronics & Comm":
            dept_skills = ["C++", "Embedded Systems", "Python", "MATLAB", "SQL", "Data Structures"]
        elif s["department"] == "Mechanical Engg":
            dept_skills = ["AutoCAD", "MATLAB", "Python", "Data Analytics"]
        else:  # Civil Engg
            dept_skills = ["AutoCAD", "Data Analytics", "Python", "SQL"]

        assigned = random.sample(dept_skills, k=random.randint(2, min(5, len(dept_skills))))
        for sk in assigned:
            cursor.execute("""
                INSERT OR IGNORE INTO student_skills (student_id, skill_id)
                VALUES (?, ?)
            """, (s["student_id"], skill_ids[sk]))

    # 4. Insert Placements
    # Only eligible students can participate in placements
    eligible_students = [s for s in students if s["is_eligible"] == 1]
    base_date = datetime(grad_year - 1, 8, 1)

    for s in eligible_students:
        # Placement probability depends on CGPA and department
        bias = 0.85 if s["department"] in ["Computer Science", "Information Technology"] else 0.65
        if s["cgpa"] > 8.0:
            bias += 0.10

        is_placed = random.random() < bias
        if is_placed:
            # Determine number of offers (1, 2, or rarely 3 offers to test duplicate handling)
            num_offers = random.choices([1, 2, 3], weights=[0.70, 0.25, 0.05])[0]

            # Filter appropriate company types
            if s["department"] in ["Mechanical Engg", "Civil Engg"]:
                available_comp = [c for c in COMPANIES_AND_ROLES if c[0] in ["Tata Motors", "L&T", "TCS", "Infosys", "Wipro", "Cognizant", "Accenture"]]
            else:
                available_comp = COMPANIES_AND_ROLES

            offers = random.sample(available_comp, k=min(num_offers, len(available_comp)))

            for idx, (company, role, (min_p, max_p)) in enumerate(offers):
                # Higher CGPA skews towards higher packages
                cgpa_factor = (s["cgpa"] - 6.0) / 4.0
                package = round(min_p + (max_p - min_p) * (cgpa_factor * 0.6 + random.random() * 0.4), 2)
                placement_date = (base_date + timedelta(days=random.randint(15, 180))).strftime("%Y-%m-%d")
                status = "Placed" if idx == 0 else "Offered"

                cursor.execute("""
                    INSERT INTO placements (student_id, company, role, package, placement_date, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (s["student_id"], company, role, package, placement_date, status))

    conn.commit()
    conn.close()
    print(f"[OK] Successfully seeded {len(students)} students and their placement outcomes.")


if __name__ == "__main__":
    seed_all_data()
