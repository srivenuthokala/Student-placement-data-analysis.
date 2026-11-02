"""
Flask Web Application for Student Placement Data Analysis System.
Provides REST APIs, role-based authentication (Faculty vs Student),
and interactive analytics dashboards.
"""
import os
from datetime import timedelta
from functools import wraps
from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    send_from_directory,
    redirect,
    url_for,
    session,
    flash,
    Response
)
import json
import io
import pandas as pd
from werkzeug.security import check_password_hash, generate_password_hash

from database import fetch_dataframe, execute_non_query, init_database, log_audit_event, clean_records
from academic_data import SUBJECTS_BY_DEPARTMENT
from analysis import (
    calculate_placement_rate,
    compare_departments,
    analyze_package_distribution,
    analyze_skill_demand,
    get_clean_data
)
from seed_data import seed_all_data
from visualization import generate_all_charts
from config import CHARTS_DIR, REPORTS_DIR, PACKAGE_UNIT, TARGET_GRADUATION_YEAR

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "eduplace_student_placement_analytics_secret_2025_prod_key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Ensure required directories exist
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Ensure database tables and initial accounts exist on startup
init_database()

try:
    df_chk = fetch_dataframe("SELECT COUNT(*) as cnt FROM students")
    if df_chk.empty or df_chk.iloc[0]["cnt"] < 200:
        seed_all_data(200)
        generate_all_charts()
except Exception:
    seed_all_data(200)
    generate_all_charts()


# ============================================================================
# Role-Based Access Control (RBAC) Decorators
# ============================================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "role" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def faculty_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "role" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401
            return redirect(url_for("login", role="faculty"))
        if session.get("role") != "faculty":
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Access denied. Faculty role required."}), 403
            flash("Access restricted. Faculty permissions required.", "error")
            return redirect(url_for("student_dashboard"))
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "role" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401
            return redirect(url_for("login", role="student"))
        if session.get("role") != "student":
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Access denied. Student role required."}), 403
            flash("Access restricted to student accounts.", "info")
            return redirect(url_for("faculty_dashboard"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# Authentication & Root Routes
# ============================================================================
@app.route("/")
def index():
    """Root entry point: renders the informational landing page with 'Login to Dashboard' CTA."""
    if "role" in session:
        if session["role"] == "faculty":
            return redirect(url_for("faculty_dashboard"))
        elif session["role"] == "student":
            return redirect(url_for("student_dashboard"))
    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Unified login gateway: renders login page on GET, auto-detects Faculty vs. Student on POST."""
    if request.method == "GET":
        if "role" in session:
            if session["role"] == "faculty":
                return redirect(url_for("faculty_dashboard"))
            elif session["role"] == "student":
                return redirect(url_for("student_dashboard"))
        return render_template("login.html")

    # POST: Unified Auto-detecting authentication
    data = request.get_json(silent=True) or request.form
    identifier = str(data.get("identifier", data.get("username", ""))).strip()
    password = str(data.get("password", "")).strip()

    if not (identifier and password):
        msg = "Please enter both Username / Roll Number and Password."
        if request.is_json:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "error")
        return redirect(url_for("login"))

    # 1. Try authenticating as Faculty (username: faculty / password: faculty123)
    df_fac = fetch_dataframe(
        "SELECT faculty_id, faculty_code, username, name, department, email, password_hash "
        "FROM faculty WHERE LOWER(username) = LOWER(?) OR LOWER(faculty_code) = LOWER(?)",
        (identifier, identifier)
    )
    if not df_fac.empty and check_password_hash(df_fac.iloc[0]["password_hash"], password):
        row = df_fac.iloc[0]
        session.clear()
        session["user_id"] = int(row["faculty_id"])
        session["role"] = "faculty"
        session["faculty_code"] = str(row["faculty_code"])
        session["username"] = str(row["username"])
        session["name"] = str(row["name"])
        session["department"] = str(row["department"])
        session.permanent = True

        if request.is_json:
            return jsonify({"success": True, "role": "faculty", "redirect": url_for("faculty_dashboard")})
        return redirect(url_for("faculty_dashboard"))

    # 2. Try authenticating as Student (username: student / password: student123 or roll_no)
    student_id_val = int(identifier) if identifier.isdigit() else -1
    df_stu = fetch_dataframe(
        "SELECT student_id, roll_no, name, department, graduation_year, cgpa, is_eligible, password_hash "
        "FROM students WHERE LOWER(roll_no) = LOWER(?) OR LOWER(username) = LOWER(?) OR student_id = ? "
        "OR (LOWER(?) = 'student' AND student_id = (SELECT MIN(student_id) FROM students))",
        (identifier, identifier, student_id_val, identifier)
    )
    if not df_stu.empty and check_password_hash(df_stu.iloc[0]["password_hash"], password):
        row = df_stu.iloc[0]
        session.clear()
        session["user_id"] = int(row["student_id"])
        session["role"] = "student"
        session["roll_no"] = str(row["roll_no"])
        session["name"] = str(row["name"])
        session["department"] = str(row["department"])
        session.permanent = True

        if request.is_json:
            return jsonify({"success": True, "role": "student", "redirect": url_for("student_dashboard")})
        return redirect(url_for("student_dashboard"))

    # Neither matched
    msg = "Invalid credentials. Please verify your username and password."
    if request.is_json:
        return jsonify({"success": False, "error": msg}), 401
    flash(msg, "error")
    return redirect(url_for("login"))


@app.route("/login/faculty", methods=["POST"])
def login_faculty():
    """Backward compatibility wrapper: delegates to unified login."""
    return login()


@app.route("/login/student", methods=["POST"])
def login_student():
    """Backward compatibility wrapper: delegates to unified login."""
    return login()


@app.route("/logout")
def logout():
    """Logs the user out, terminates session, and redirects to login portal."""
    session.clear()
    flash("You have been securely logged out.", "success")
    return redirect(url_for("login"))


from academic_data import get_faculty_academic_bundle, get_student_academic_bundle


# ============================================================================
# Dashboards
# ============================================================================
@app.route("/faculty/dashboard")
@faculty_required
def faculty_dashboard():
    """Faculty Dashboard: complete access to faculty & administrative placement analytics."""
    faculty_info = {
        "name": session.get("name", "Faculty Member"),
        "username": session.get("username", "faculty"),
        "faculty_code": session.get("faculty_code", "FAC"),
        "department": session.get("department", "Computer Science")
    }
    return render_template(
        "faculty_dashboard.html",
        package_unit=PACKAGE_UNIT,
        grad_year=TARGET_GRADUATION_YEAR,
        faculty=faculty_info
    )


@app.route("/student/dashboard")
@student_required
def student_dashboard():
    """Student Dashboard: dedicated view for personal offers, skills, and campus benchmarks."""
    student_id = session.get("user_id")
    student_df = fetch_dataframe(
        "SELECT student_id, roll_no, name, department, graduation_year, cgpa, is_eligible "
        "FROM students WHERE student_id = ?",
        (student_id,)
    )

    if student_df.empty:
        flash("Student record not found. Please log in again.", "error")
        return redirect(url_for("logout"))

    student = student_df.iloc[0].to_dict()

    # Fetch skills assigned to this student
    skills_df = fetch_dataframe("""
        SELECT s.skill_name FROM skills s
        JOIN student_skills ss ON s.skill_id = ss.skill_id
        WHERE ss.student_id = ?
        ORDER BY s.skill_name ASC
    """, (student_id,))
    skills = skills_df["skill_name"].tolist() if not skills_df.empty else []

    # Fetch placement offers for this student
    offers_df = fetch_dataframe("""
        SELECT placement_id, company, role, package, placement_date, status
        FROM placements WHERE student_id = ?
        ORDER BY package DESC, placement_date DESC
    """, (student_id,))
    offers = offers_df.to_dict(orient="records") if not offers_df.empty else []

    # Department-level comparative benchmarks
    dept_df = fetch_dataframe("""
        SELECT 
            COUNT(DISTINCT s.student_id) as total_students,
            COUNT(DISTINCT CASE WHEN s.is_eligible = 1 THEN s.student_id END) as eligible_students,
            COUNT(DISTINCT CASE WHEN s.is_eligible = 1 AND p.placement_id IS NOT NULL THEN s.student_id END) as placed_students,
            ROUND(AVG(p.package), 2) as avg_package,
            ROUND(MAX(p.package), 2) as max_package
        FROM students s
        LEFT JOIN placements p ON s.student_id = p.student_id
        WHERE s.department = ?
    """, (student["department"],))

    dept_stats = dept_df.iloc[0].to_dict() if not dept_df.empty else {}
    if dept_stats.get("eligible_students", 0) > 0:
        dept_stats["placement_rate"] = round(
            (dept_stats.get("placed_students", 0) / dept_stats["eligible_students"]) * 100, 1
        )
    else:
        dept_stats["placement_rate"] = 0.0

    return render_template(
        "student_dashboard.html",
        package_unit=PACKAGE_UNIT,
        student=student,
        skills=skills,
        offers=offers,
        dept_stats=dept_stats
    )


@app.route("/api/announcements", methods=["GET", "POST"])
@login_required
def api_announcements():
    """Fetches or posts announcements."""
    if request.method == "POST":
        if session.get("role") != "faculty":
            return jsonify({"success": False, "error": "Faculty permissions required."}), 403
        data = request.get_json() or {}
        title = str(data.get("title", "")).strip()
        content = str(data.get("content", "")).strip()
        category = str(data.get("category", "General")).strip()
        priority = str(data.get("priority", "Normal")).strip()
        author = session.get("name", "Faculty Administration")
        from datetime import date
        date_posted = date.today().isoformat()

        if not (title and content):
            return jsonify({"success": False, "error": "Title and content are required."}), 400

        execute_non_query(
            "INSERT INTO announcements (title, content, author, category, date_posted, priority) VALUES (?, ?, ?, ?, ?, ?)",
            (title, content, author, category, date_posted, priority)
        )
        return jsonify({"success": True, "message": "Announcement posted successfully."})

    df = fetch_dataframe("SELECT * FROM announcements ORDER BY date_posted DESC")
    return jsonify(df.to_dict(orient="records"))


# ============================================================================
# REST APIs
# ============================================================================
@app.route("/api/student/me")
@student_required
def api_student_me():
    """Returns the authenticated student's full profile, offers, and skills."""
    student_id = session.get("user_id")
    df = fetch_dataframe(
        "SELECT student_id, roll_no, name, department, graduation_year, cgpa, is_eligible "
        "FROM students WHERE student_id = ?",
        (student_id,)
    )
    if df.empty:
        return jsonify({"success": False, "error": "Student record not found"}), 404

    student = df.iloc[0].to_dict()

    skills_df = fetch_dataframe("""
        SELECT s.skill_name FROM skills s
        JOIN student_skills ss ON s.skill_id = ss.skill_id
        WHERE ss.student_id = ?
        ORDER BY s.skill_name ASC
    """, (student_id,))
    student["skills"] = skills_df["skill_name"].tolist() if not skills_df.empty else []

    offers_df = fetch_dataframe("""
        SELECT placement_id, company, role, package, placement_date, status
        FROM placements WHERE student_id = ?
        ORDER BY package DESC
    """, (student_id,))
    student["offers"] = offers_df.to_dict(orient="records") if not offers_df.empty else []
    student["total_offers"] = len(student["offers"])
    student["highest_package"] = max([o["package"] for o in student["offers"]], default=0.0)

    return jsonify({"success": True, "student": clean_records(student)})


@app.route("/api/summary")
@login_required
def api_summary():
    """Returns top-level KPI metrics."""
    grad_year = request.args.get("year", default=TARGET_GRADUATION_YEAR, type=int)
    data = calculate_placement_rate(grad_year)
    pkg_stats = analyze_package_distribution(grad_year)
    data["package_stats"] = pkg_stats.get("all_offers_summary", {})
    data["highest_package_stats"] = pkg_stats.get("highest_package_per_student_summary", {})
    data["package_unit"] = PACKAGE_UNIT
    return jsonify(data)


@app.route("/api/departments")
@login_required
def api_departments():
    """Returns department-wise comparative metrics."""
    grad_year = request.args.get("year", default=TARGET_GRADUATION_YEAR, type=int)
    df = compare_departments(grad_year)
    return jsonify(df.to_dict(orient="records"))


COMPANY_META = {
    "Google": {"tier": "Super Dream", "category": "Tier 1 Product", "icon": "fa-brands fa-google", "badge_class": "badge-super-dream"},
    "Microsoft": {"tier": "Super Dream", "category": "Cloud & OS Systems", "icon": "fa-brands fa-microsoft", "badge_class": "badge-super-dream"},
    "Amazon": {"tier": "Super Dream", "category": "E-Commerce & AWS", "icon": "fa-brands fa-amazon", "badge_class": "badge-super-dream"},
    "Qualcomm": {"tier": "Super Dream", "category": "Semiconductors & 5G", "icon": "fa-solid fa-microchip", "badge_class": "badge-super-dream"},
    "Adobe": {"tier": "Super Dream", "category": "Creative Cloud", "icon": "fa-solid fa-shapes", "badge_class": "badge-super-dream"},
    "Cisco Systems": {"tier": "Dream", "category": "Networking & Security", "icon": "fa-solid fa-network-wired", "badge_class": "badge-dream"},
    "Samsung R&D": {"tier": "Dream", "category": "Consumer Electronics", "icon": "fa-solid fa-mobile-screen", "badge_class": "badge-dream"},
    "Oracle": {"tier": "Dream", "category": "Enterprise Database", "icon": "fa-solid fa-database", "badge_class": "badge-dream"},
    "Deloitte": {"tier": "Dream", "category": "Tech Strategy & Advisory", "icon": "fa-solid fa-chart-line", "badge_class": "badge-dream"},
    "Texas Instruments": {"tier": "Dream", "category": "Hardware & Embedded", "icon": "fa-solid fa-bolt", "badge_class": "badge-dream"},
    "Tata Motors": {"tier": "Core Engineering", "category": "Automotive R&D", "icon": "fa-solid fa-car-side", "badge_class": "badge-core"},
    "L&T (Larsen & Toubro)": {"tier": "Core Engineering", "category": "Infrastructure & Design", "icon": "fa-solid fa-building", "badge_class": "badge-core"},
    "Bosch": {"tier": "Core Engineering", "category": "Automotive & Industrial IoT", "icon": "fa-solid fa-gears", "badge_class": "badge-core"},
    "TCS": {"tier": "IT Solutions", "category": "Global Enterprise IT", "icon": "fa-solid fa-laptop-code", "badge_class": "badge-it"},
    "Infosys": {"tier": "IT Solutions", "category": "Digital Services", "icon": "fa-solid fa-code-branch", "badge_class": "badge-it"},
    "Cognizant": {"tier": "IT Solutions", "category": "Digital Transformation", "icon": "fa-solid fa-cubes", "badge_class": "badge-it"},
    "Wipro": {"tier": "IT Solutions", "category": "Enterprise Solutions", "icon": "fa-solid fa-server", "badge_class": "badge-it"},
    "Accenture": {"tier": "IT Solutions", "category": "Cloud & Consulting", "icon": "fa-solid fa-briefcase", "badge_class": "badge-it"}
}


@app.route("/api/packages")
@login_required
def api_packages():
    """Returns detailed package distribution statistics and corporate recruiters."""
    grad_year = request.args.get("year", default=TARGET_GRADUATION_YEAR, type=int)
    dist = analyze_package_distribution(grad_year)
    _, df_placements, _ = get_clean_data(grad_year)
    dist["raw_packages"] = sorted(df_placements["package"].tolist())
    
    comp_list = []
    if not df_placements.empty:
        comp_grouped = df_placements.groupby("company")["package"].agg(["count", "mean", "max", "min"]).reset_index()
        for _, r in comp_grouped.iterrows():
            c_name = str(r["company"])
            meta = COMPANY_META.get(c_name, {
                "tier": "Recruitment Partner",
                "category": "Corporate Recruiter",
                "icon": "fa-solid fa-building",
                "badge_class": "badge-secondary"
            })
            comp_list.append({
                "company": c_name,
                "tier": meta["tier"],
                "category": meta["category"],
                "icon": meta["icon"],
                "badge_class": meta["badge_class"],
                "count": int(r["count"]),
                "mean": round(float(r["mean"]), 2),
                "max": round(float(r["max"]), 2),
                "min": round(float(r["min"]), 2)
            })
        comp_list.sort(key=lambda x: (x["max"], x["count"]), reverse=True)
    dist["companies"] = comp_list
    return jsonify(dist)


@app.route("/api/company-partners")
@login_required
def api_company_partners():
    """Returns active corporate recruitment partners with hiring statistics and recent stream."""
    df_offers = fetch_dataframe("""
        SELECT company, COUNT(*) as offer_count,
               AVG(package) as avg_pkg, MAX(package) as max_pkg, MIN(package) as min_pkg
        FROM placements
        GROUP BY company
        ORDER BY max_pkg DESC, offer_count DESC
    """)
    partners = []
    for _, row in df_offers.iterrows():
        c_name = str(row["company"])
        meta = COMPANY_META.get(c_name, {
            "tier": "Recruitment Partner",
            "category": "Corporate Recruiter",
            "icon": "fa-solid fa-building",
            "badge_class": "badge-secondary"
        })
        roles_df = fetch_dataframe("SELECT DISTINCT role FROM placements WHERE company = ?", (c_name,))
        roles_list = roles_df["role"].tolist() if not roles_df.empty else []
        partners.append({
            "company": c_name,
            "tier": meta["tier"],
            "category": meta["category"],
            "icon": meta["icon"],
            "badge_class": meta["badge_class"],
            "total_hires": int(row["offer_count"]),
            "avg_package": round(float(row["avg_pkg"]), 2),
            "max_package": round(float(row["max_pkg"]), 2),
            "min_package": round(float(row["min_pkg"]), 2),
            "roles": roles_list,
            "status": "Active Recruiter"
        })

    # Recent placement offers stream (latest 35 records)
    stream_df = fetch_dataframe("""
        SELECT p.placement_id, p.company, p.role, p.package, p.placement_date, p.status,
               s.student_id, s.roll_no, s.name, s.department
        FROM placements p
        JOIN students s ON p.student_id = s.student_id
        ORDER BY p.placement_id DESC
        LIMIT 35
    """)
    return jsonify({
        "partners": partners,
        "recent_placements": stream_df.to_dict(orient="records")
    })


@app.route("/api/skills")
@login_required
def api_skills():
    """Returns skill-demand analysis."""
    grad_year = request.args.get("year", default=TARGET_GRADUATION_YEAR, type=int)
    df = analyze_skill_demand(grad_year)
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/students")
@login_required
def api_students():
    """Returns student list with full profile fields, skills, and placement status."""
    grad_year = request.args.get("year", default=TARGET_GRADUATION_YEAR, type=int)
    admission_type_filter = request.args.get("admission_type", default="ALL").strip()

    query = """
        SELECT s.student_id, s.roll_no, s.name, s.admission_type, s.department,
               s.year_of_study, s.section, s.email, s.mobile, s.dob, s.gender,
               s.cgpa, s.backlogs, s.academic_year, s.is_eligible,
               s.placement_eligibility, s.placement_status,
               s.diploma_qualification, s.diploma_percentage, s.diploma_college,
               s.admission_year, s.graduation_year,
               (
                   SELECT GROUP_CONCAT(sk.skill_name, ', ')
                   FROM student_skills ss
                   JOIN skills sk ON ss.skill_id = sk.skill_id
                   WHERE ss.student_id = s.student_id
               ) AS skills,
               (
                   SELECT COUNT(p.placement_id)
                   FROM placements p
                   WHERE p.student_id = s.student_id
               ) AS total_offers,
               (
                   SELECT MAX(p.package)
                   FROM placements p
                   WHERE p.student_id = s.student_id
               ) AS highest_package,
               (
                   SELECT GROUP_CONCAT(DISTINCT p.company)
                   FROM placements p
                   WHERE p.student_id = s.student_id
               ) AS companies
        FROM students s
        WHERE s.graduation_year = ?
        ORDER BY s.student_id ASC
    """
    df = fetch_dataframe(query, params=(grad_year,))
    if not df.empty:
        df["skills"] = df["skills"].fillna("None")
        df["highest_package"] = df["highest_package"].fillna(0.0)
        df["companies"] = df["companies"].fillna("None")
        df["admission_type"] = df["admission_type"].fillna("Regular")
        df["year_of_study"] = df["year_of_study"].fillna("4th Year")
        df["section"] = df["section"].fillna("A")
        df["placement_eligibility"] = df["placement_eligibility"].fillna("Eligible")

        def determine_status(row):
            if row["total_offers"] > 0:
                return "Placed"
            st = str(row["placement_status"]).strip()
            return st if st in ["Placed", "Unplaced", "Pending"] else "Unplaced"

        df["placement_status"] = df.apply(determine_status, axis=1)

        if admission_type_filter != "ALL":
            df = df[df["admission_type"].str.lower() == admission_type_filter.lower()]

    return jsonify(clean_records(df))


@app.route("/api/student/<int:student_id>", methods=["GET"])
@login_required
def api_get_student_profile(student_id):
    """Fetches comprehensive student profile, diploma details, offers, and academics."""
    df = fetch_dataframe("SELECT * FROM students WHERE student_id = ?", (student_id,))
    if df.empty:
        return jsonify({"success": False, "error": "Student record not found."}), 404

    student = df.iloc[0].to_dict()
    student.pop("password_hash", None)

    # Fetch assigned skills
    skills_df = fetch_dataframe("""
        SELECT s.skill_name FROM skills s
        JOIN student_skills ss ON s.skill_id = ss.skill_id
        WHERE ss.student_id = ?
        ORDER BY s.skill_name ASC
    """, (student_id,))
    student["skills"] = skills_df["skill_name"].tolist() if not skills_df.empty else []

    # Fetch placement offers
    offers_df = fetch_dataframe("""
        SELECT placement_id, company, role, package, placement_date, status
        FROM placements WHERE student_id = ?
        ORDER BY package DESC, placement_date DESC
    """, (student_id,))
    student["offers"] = offers_df.to_dict(orient="records") if not offers_df.empty else []
    student["total_offers"] = len(student["offers"])
    student["highest_package"] = max([o["package"] for o in student["offers"]], default=0.0)

    # Attendance records
    att_df = fetch_dataframe("SELECT subject, total_classes, attended_classes, percentage FROM attendance WHERE student_id = ?", (student_id,))
    student["attendance_records"] = att_df.to_dict(orient="records") if not att_df.empty else []

    # Marks records
    marks_df = fetch_dataframe("SELECT subject, semester, internal_marks, external_marks, total_marks, grade, credits FROM marks WHERE student_id = ?", (student_id,))
    student["marks_records"] = marks_df.to_dict(orient="records") if not marks_df.empty else []

    return jsonify({"success": True, "student": clean_records(student)})


@app.route("/api/student/<int:student_id>", methods=["PUT"])
@faculty_required
def api_update_student(student_id):
    """Updates student record, academics, placement eligibility & status (Faculty only)."""
    data = request.get_json() or {}
    df_s = fetch_dataframe("SELECT student_id, roll_no FROM students WHERE student_id = ?", (student_id,))
    if df_s.empty:
        return jsonify({"success": False, "error": "Student record not found."}), 404

    name = str(data.get("name", "")).strip()
    roll_no = str(data.get("roll_no", "")).strip().upper()
    admission_type = str(data.get("admission_type", "Regular")).strip()
    department = str(data.get("department", "")).strip()
    year_of_study = str(data.get("year_of_study", "4th Year")).strip()
    section = str(data.get("section", "A")).strip().upper()[:2]
    email = str(data.get("email", "")).strip()
    mobile = str(data.get("mobile", "")).strip()
    dob = str(data.get("dob", "")).strip()
    gender = str(data.get("gender", "Male")).strip()
    academic_year = str(data.get("academic_year", "2024-2025")).strip()
    graduation_year = int(data.get("graduation_year", TARGET_GRADUATION_YEAR))
    cgpa = float(data.get("cgpa", 0.0))
    backlogs = int(data.get("backlogs", 0))
    placement_eligibility = str(data.get("placement_eligibility", "Eligible")).strip()
    placement_status = str(data.get("placement_status", "Unplaced")).strip()

    # Lateral Entry fields
    diploma_qualification = str(data.get("diploma_qualification", "")).strip() or None
    diploma_pct_raw = data.get("diploma_percentage")
    diploma_percentage = float(diploma_pct_raw) if diploma_pct_raw not in (None, "") else None
    diploma_college = str(data.get("diploma_college", "")).strip() or None
    admission_year = int(data.get("admission_year", 2021 if admission_type == "Regular" else 2022))

    if not (name and roll_no and department):
        return jsonify({"success": False, "error": "Name, Roll Number, and Department are required."}), 400

    if not (0.0 <= cgpa <= 10.0):
        return jsonify({"success": False, "error": "CGPA must be between 0.0 and 10.0."}), 400

    # Ensure unique roll number across other students
    df_chk = fetch_dataframe("SELECT student_id FROM students WHERE roll_no = ? AND student_id != ?", (roll_no, student_id))
    if not df_chk.empty:
        return jsonify({"success": False, "error": f"Roll number '{roll_no}' is already used by another student."}), 400

    is_eligible = 1 if placement_eligibility == "Eligible" else 0

    execute_non_query("""
        UPDATE students SET
            roll_no = ?, name = ?, admission_type = ?, department = ?,
            year_of_study = ?, section = ?, email = ?, mobile = ?,
            dob = ?, gender = ?, graduation_year = ?, academic_year = ?,
            cgpa = ?, backlogs = ?, is_eligible = ?, placement_eligibility = ?,
            placement_status = ?, diploma_qualification = ?, diploma_percentage = ?,
            diploma_college = ?, admission_year = ?
        WHERE student_id = ?
    """, (
        roll_no, name, admission_type, department,
        year_of_study, section, email, mobile,
        dob, gender, graduation_year, academic_year,
        cgpa, backlogs, is_eligible, placement_eligibility,
        placement_status, diploma_qualification, diploma_percentage,
        diploma_college, admission_year, student_id
    ))

    # Update skills if provided
    if "skills" in data:
        skills = data.get("skills", [])
        execute_non_query("DELETE FROM student_skills WHERE student_id = ?", (student_id,))
        for skill_name in skills:
            skill_name = str(skill_name).strip()
            if not skill_name:
                continue
            df_sk = fetch_dataframe("SELECT skill_id FROM skills WHERE LOWER(skill_name) = LOWER(?)", (skill_name,))
            if df_sk.empty:
                sk_id = execute_non_query("INSERT INTO skills (skill_name) VALUES (?)", (skill_name,))
            else:
                sk_id = int(df_sk.iloc[0]["skill_id"])
            execute_non_query("INSERT OR IGNORE INTO student_skills (student_id, skill_id) VALUES (?, ?)", (student_id, sk_id))

    log_audit_event(
        action="EDIT_STUDENT",
        student_id=student_id,
        roll_no=roll_no,
        details=json.dumps({
            "name": name, "department": department, "admission_type": admission_type,
            "cgpa": cgpa, "eligibility": placement_eligibility, "status": placement_status
        }),
        performed_by=session.get("name", "Faculty Administration")
    )

    try:
        generate_all_charts()
    except Exception:
        pass

    return jsonify({"success": True, "message": f"Student '{name}' ({roll_no}) updated successfully."})


@app.route("/api/student/<int:student_id>", methods=["DELETE"])
@faculty_required
def api_delete_student(student_id):
    """Preserves placement history and complete dossier in audit log before deleting student (Faculty only)."""
    df_s = fetch_dataframe("SELECT * FROM students WHERE student_id = ?", (student_id,))
    if df_s.empty:
        return jsonify({"success": False, "error": "Student record not found."}), 404

    student_dict = df_s.iloc[0].to_dict()
    student_dict.pop("password_hash", None)
    roll_no = str(student_dict.get("roll_no", ""))
    name = str(student_dict.get("name", ""))

    # Fetch and preserve all placement history
    df_p = fetch_dataframe("SELECT * FROM placements WHERE student_id = ?", (student_id,))
    offers = df_p.to_dict(orient="records") if not df_p.empty else []

    archive_payload = {
        "student_record": student_dict,
        "placement_offers_archived": offers,
        "total_offers": len(offers)
    }

    log_audit_event(
        action="DELETE_STUDENT_PRESERVED",
        student_id=student_id,
        roll_no=roll_no,
        details=json.dumps(archive_payload, default=str),
        performed_by=session.get("name", "Faculty Administration")
    )

    execute_non_query("DELETE FROM students WHERE student_id = ?", (student_id,))

    try:
        generate_all_charts()
    except Exception:
        pass

    return jsonify({
        "success": True,
        "message": f"Student '{name}' ({roll_no}) successfully removed. Placement history ({len(offers)} offers) securely preserved in audit archives."
    })


@app.route("/api/available-skills")
@login_required
def api_available_skills():
    """Returns catalog of all available skills for selection."""
    df = fetch_dataframe("SELECT skill_id, skill_name FROM skills ORDER BY skill_name ASC")
    return jsonify(df["skill_name"].tolist())


# ============================================================================
# Faculty Mutation APIs (Role-Gated)
# ============================================================================
@app.route("/api/record-placement", methods=["POST"])
@faculty_required
def api_record_placement():
    """Records a new placement offer (Faculty only)."""
    data = request.get_json() or {}
    try:
        student_id = int(data.get("student_id"))
        company = str(data.get("company", "")).strip()
        role = str(data.get("role", "")).strip()
        package = float(data.get("package"))
        placement_date = str(data.get("placement_date", "")).strip()
        status = str(data.get("status", "Placed")).strip()

        if not (company and role and package > 0):
            return jsonify({"success": False, "error": "Company, role, and positive package are required."}), 400

        df = fetch_dataframe("SELECT roll_no, name, is_eligible FROM students WHERE student_id = ?", (student_id,))
        if df.empty:
            return jsonify({"success": False, "error": f"Student ID {student_id} not found."}), 404

        execute_non_query("""
            INSERT INTO placements (student_id, company, role, package, placement_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (student_id, company, role, package, placement_date, status))

        execute_non_query("UPDATE students SET placement_status = 'Placed' WHERE student_id = ?", (student_id,))

        log_audit_event(
            action="ADD_PLACEMENT_OFFER",
            student_id=student_id,
            roll_no=str(df.iloc[0]["roll_no"]),
            details=json.dumps({"company": company, "role": role, "package": package, "status": status}),
            performed_by=session.get("name", "Faculty Administration")
        )

        try:
            generate_all_charts()
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": f"Placement offer of {package} {PACKAGE_UNIT} at {company} recorded successfully."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/add-student", methods=["POST"])
@faculty_required
def api_add_student():
    """Adds a new student (Regular or Lateral Entry) with complete placement & academic tracking (Faculty only)."""
    data = request.get_json() or {}
    try:
        name = str(data.get("name", "")).strip()
        roll_no = str(data.get("roll_no", "")).strip().upper()
        admission_type = str(data.get("admission_type", "Regular")).strip().title()
        if admission_type not in ["Regular", "Lateral Entry"]:
            admission_type = "Lateral Entry" if "lateral" in admission_type.lower() else "Regular"

        department = str(data.get("department", "")).strip()
        year_of_study = str(data.get("year_of_study", "4th Year" if admission_type == "Regular" else "2nd Year")).strip()
        section = str(data.get("section", "A")).strip().upper()[:2] or "A"
        email = str(data.get("email", "")).strip() or f"{roll_no.lower()}@eduplace.ac.in"
        mobile = str(data.get("mobile", "")).strip()
        dob = str(data.get("dob", "")).strip() or "2003-01-01"
        gender = str(data.get("gender", "Male")).strip().title()
        academic_year = str(data.get("academic_year", "2024-2025")).strip()
        graduation_year = int(data.get("graduation_year", TARGET_GRADUATION_YEAR))
        cgpa = float(data.get("cgpa", 0.0))
        backlogs = int(data.get("backlogs", 0))

        # Eligibility: Eligible, Not Eligible, Pending
        placement_eligibility = str(data.get("placement_eligibility", "Eligible")).strip()
        if placement_eligibility not in ["Eligible", "Not Eligible", "Pending"]:
            placement_eligibility = "Eligible" if (cgpa >= 6.0 and backlogs == 0) else "Not Eligible"

        # Initially set placement status to Pending / Not Placed (Unplaced)
        placement_status = str(data.get("placement_status", "Unplaced")).strip()
        if placement_status not in ["Placed", "Unplaced", "Pending"]:
            placement_status = "Unplaced"

        # Lateral Entry Specific Fields
        diploma_qualification = str(data.get("diploma_qualification", "")).strip() or None
        diploma_pct_raw = data.get("diploma_percentage")
        diploma_percentage = float(diploma_pct_raw) if diploma_pct_raw not in (None, "") else None
        diploma_college = str(data.get("diploma_college", "")).strip() or None
        admission_year = int(data.get("admission_year", 2021 if admission_type == "Regular" else 2022))

        skills = data.get("skills", [])

        if not (name and roll_no and department):
            return jsonify({"success": False, "error": "Student Name, Roll Number, and Department are required."}), 400

        if not (0.0 <= cgpa <= 10.0):
            return jsonify({"success": False, "error": "CGPA must be between 0.0 and 10.0."}), 400

        df_chk = fetch_dataframe("SELECT student_id FROM students WHERE roll_no = ?", (roll_no,))
        if not df_chk.empty:
            return jsonify({"success": False, "error": f"Student with Roll No '{roll_no}' already exists in database."}), 400

        is_eligible = 1 if placement_eligibility == "Eligible" else 0

        # Assign default password hash (Student@123)
        pwd_hash = generate_password_hash("Student@123")
        student_id = execute_non_query("""
            INSERT INTO students (
                roll_no, name, admission_type, department, year_of_study, section,
                email, mobile, dob, gender, graduation_year, academic_year,
                cgpa, backlogs, is_eligible, placement_eligibility, placement_status,
                diploma_qualification, diploma_percentage, diploma_college, admission_year,
                password_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            roll_no, name, admission_type, department, year_of_study, section,
            email, mobile, dob, gender, graduation_year, academic_year,
            cgpa, backlogs, is_eligible, placement_eligibility, placement_status,
            diploma_qualification, diploma_percentage, diploma_college, admission_year,
            pwd_hash
        ))

        # Assign Skills
        for skill_name in skills:
            skill_name = str(skill_name).strip()
            if not skill_name:
                continue

            df_sk = fetch_dataframe("SELECT skill_id FROM skills WHERE LOWER(skill_name) = LOWER(?)", (skill_name,))
            if df_sk.empty:
                skill_id = execute_non_query("INSERT INTO skills (skill_name) VALUES (?)", (skill_name,))
            else:
                skill_id = int(df_sk.iloc[0]["skill_id"])

            execute_non_query("""
                INSERT OR IGNORE INTO student_skills (student_id, skill_id)
                VALUES (?, ?)
            """, (student_id, skill_id))

        # Initialize academic records for seamless portal integration
        dept_subjects = SUBJECTS_BY_DEPARTMENT.get(department, ["Engineering Core I", "Engineering Core II", "Technical Lab"])
        for sub in dept_subjects:
            execute_non_query("""
                INSERT INTO attendance (student_id, subject, total_classes, attended_classes, percentage)
                VALUES (?, ?, 40, 35, 87.5)
            """, (student_id, sub))
            execute_non_query("""
                INSERT INTO marks (student_id, semester, subject, internal_marks, external_marks, total_marks, grade, credits)
                VALUES (?, 'Semester 7', ?, 25, 62, 87, 'A', 4)
            """, (student_id, sub))

        # Log audit entry
        log_audit_event(
            action="ADD_STUDENT",
            student_id=student_id,
            roll_no=roll_no,
            details=json.dumps({
                "name": name, "department": department, "admission_type": admission_type,
                "cgpa": cgpa, "eligibility": placement_eligibility, "status": placement_status
            }),
            performed_by=session.get("name", "Faculty Administration")
        )

        try:
            generate_all_charts()
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": f"Student '{name}' ({roll_no}) successfully registered as {admission_type} ({placement_eligibility}).",
            "student_id": student_id,
            "is_eligible": is_eligible,
            "placement_eligibility": placement_eligibility
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/students/sample-template", methods=["GET"])
@faculty_required
def api_download_sample_template():
    """Generates a downloadable sample CSV template with Regular and Lateral Entry rows."""
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Roll Number", "Full Name", "Admission Type", "Department",
        "Year of Study", "Section", "Email Address", "Mobile Number",
        "Date of Birth", "Gender", "CGPA", "Backlogs",
        "Academic Year", "Placement Eligibility", "Diploma Qualification",
        "Diploma Percentage", "Diploma College", "Admission Year", "Skills"
    ])
    writer.writerow([
        "CSE2025201", "Aditi Sharma", "Regular", "Computer Science",
        "4th Year", "A", "aditi.sharma@eduplace.ac.in", "9876543210",
        "2003-05-14", "Female", "8.85", "0",
        "2024-2025", "Eligible", "", "", "", "2021", "Python, Cloud Computing, SQL"
    ])
    writer.writerow([
        "INF2025202", "Rohan Deshmukh", "Lateral Entry", "Information Technology",
        "4th Year", "B", "rohan.deshmukh@eduplace.ac.in", "9876543211",
        "2002-10-22", "Male", "8.40", "0",
        "2024-2025", "Eligible", "Diploma in Information Tech", "87.5", "Govt Polytechnic Pune", "2022", "React, Node.js, MongoDB"
    ])
    writer.writerow([
        "ELE2025203", "Kavita Nair", "Regular", "Electronics & Comm",
        "4th Year", "A", "kavita.nair@eduplace.ac.in", "9876543212",
        "2003-08-19", "Female", "7.60", "0",
        "2024-2025", "Eligible", "", "", "", "2021", "Embedded C, MATLAB, IoT"
    ])
    writer.writerow([
        "MEC2025204", "Siddharth Verma", "Lateral Entry", "Mechanical Engg",
        "4th Year", "A", "siddharth.verma@eduplace.ac.in", "9876543213",
        "2002-03-11", "Male", "8.15", "0",
        "2024-2025", "Eligible", "Diploma in Mechanical", "84.0", "State Technical Institute", "2022", "AutoCAD, SolidWorks, FEA"
    ])
    writer.writerow([
        "CIV2025205", "Manoj Kumar", "Regular", "Civil Engg",
        "4th Year", "B", "manoj.kumar@eduplace.ac.in", "9876543214",
        "2003-12-05", "Male", "5.90", "1",
        "2024-2025", "Not Eligible", "", "", "", "2021", "STAAD Pro, AutoCAD"
    ])

    csv_bytes = output.getvalue().encode("utf-8")
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sample_student_placement_template.csv"}
    )


@app.route("/api/students/bulk-upload", methods=["POST"])
@faculty_required
def api_bulk_upload():
    """Uploads multiple students from an Excel or CSV file with rigorous validation."""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded. Please select an Excel or CSV file."}), 400

    file = request.files["file"]
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in [".csv", ".xlsx", ".xls"]:
        return jsonify({"success": False, "error": "Invalid format. Supported file formats are .csv, .xlsx, .xls."}), 400

    try:
        if ext == ".csv":
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to parse file: {str(e)}"}), 400

    if df.empty:
        return jsonify({"success": False, "error": "Uploaded file contains no data."}), 400

    # Build canonical map for column headers
    col_map = {}
    for col in df.columns:
        norm = "".join(c if c.isalnum() else "_" for c in str(col).lower()).strip("_")
        while "__" in norm:
            norm = norm.replace("__", "_")
        col_map[norm] = col

    def get_val(row, *aliases, default=""):
        for a in aliases:
            if a in col_map:
                val = row[col_map[a]]
                if pd.notna(val):
                    return str(val).strip()
        return default

    # Pre-fetch existing roll numbers from database for instant lookup
    existing_rolls_df = fetch_dataframe("SELECT LOWER(roll_no) as roll_lower FROM students")
    db_roll_set = set(existing_rolls_df["roll_lower"].tolist()) if not existing_rolls_df.empty else set()

    file_roll_set = set()
    successful_records = []
    failed_records = []

    default_pwd_hash = generate_password_hash("Student@123")

    for idx, row in df.iterrows():
        row_num = idx + 2  # Account for 1-indexed header

        roll_no = get_val(row, "roll_number", "roll_no", "rollno", "student_roll_no").upper()
        name = get_val(row, "full_name", "student_full_name", "name", "student_name")
        admission_type = get_val(row, "admission_type", "type", default="Regular").title()
        if admission_type not in ["Regular", "Lateral Entry"]:
            admission_type = "Lateral Entry" if "lateral" in admission_type.lower() else "Regular"

        department = get_val(row, "department", "branch", "dept", default="Computer Science")
        known_depts = ["Computer Science", "Information Technology", "Electronics & Comm", "Mechanical Engg", "Civil Engg"]
        matched_dept = department
        for kd in known_depts:
            if kd.lower() in department.lower() or department.lower() in kd.lower():
                matched_dept = kd
                break
        department = matched_dept

        year_of_study = get_val(row, "year_of_study", "year", default="4th Year" if admission_type == "Regular" else "2nd Year")
        section = get_val(row, "section", default="A").upper()[:2] or "A"
        email = get_val(row, "email_address", "email", default=f"{roll_no.lower()}@eduplace.ac.in" if roll_no else "")
        mobile = get_val(row, "mobile_number", "mobile", "phone", default="")
        dob = get_val(row, "date_of_birth", "dob", default="2003-01-01")
        gender = get_val(row, "gender", default="Male").title()
        academic_year = get_val(row, "academic_year", default="2024-2025")

        cgpa_str = get_val(row, "cgpa", default="0.0")
        backlogs_str = get_val(row, "backlogs", "active_backlogs", default="0")
        eligibility = get_val(row, "placement_eligibility", "eligibility", default="")

        diploma_qual = get_val(row, "diploma_qualification", "diploma_branch", default="")
        diploma_pct_str = get_val(row, "diploma_percentage", "diploma_cgpa", default="")
        diploma_college = get_val(row, "diploma_college", "diploma_institute", default="")
        admission_yr_str = get_val(row, "admission_year", default="2022" if admission_type == "Lateral Entry" else "2021")
        skills_str = get_val(row, "skills", default="")

        # Validation Checks
        if not roll_no:
            failed_records.append({"row": row_num, "roll_no": "--", "name": name or "--", "error": "Missing Student Roll Number."})
            continue

        if not name:
            failed_records.append({"row": row_num, "roll_no": roll_no, "name": "--", "error": "Missing Student Full Name."})
            continue

        roll_lower = roll_no.lower()
        if roll_lower in file_roll_set:
            failed_records.append({"row": row_num, "roll_no": roll_no, "name": name, "error": f"Duplicate Roll Number '{roll_no}' repeated within file."})
            continue

        if roll_lower in db_roll_set:
            failed_records.append({"row": row_num, "roll_no": roll_no, "name": name, "error": f"Roll Number '{roll_no}' already exists in database."})
            continue

        try:
            cgpa = float(cgpa_str)
            if not (0.0 <= cgpa <= 10.0):
                failed_records.append({"row": row_num, "roll_no": roll_no, "name": name, "error": f"Invalid CGPA '{cgpa_str}'. Must be between 0.0 and 10.0."})
                continue
        except ValueError:
            failed_records.append({"row": row_num, "roll_no": roll_no, "name": name, "error": f"CGPA '{cgpa_str}' is not a valid number."})
            continue

        try:
            backlogs = int(float(backlogs_str)) if backlogs_str else 0
            if backlogs < 0:
                backlogs = 0
        except ValueError:
            backlogs = 0

        if eligibility in ["Eligible", "Not Eligible", "Pending"]:
            placement_eligibility = eligibility
        else:
            placement_eligibility = "Eligible" if (cgpa >= 6.0 and backlogs == 0) else "Not Eligible"

        is_eligible = 1 if placement_eligibility == "Eligible" else 0

        diploma_pct = None
        if diploma_pct_str:
            try:
                diploma_pct = float(diploma_pct_str)
            except ValueError:
                diploma_pct = None

        try:
            adm_year = int(float(admission_yr_str))
        except ValueError:
            adm_year = 2022 if admission_type == "Lateral Entry" else 2021

        try:
            student_id = execute_non_query("""
                INSERT INTO students (
                    roll_no, name, admission_type, department, year_of_study, section,
                    email, mobile, dob, gender, graduation_year, academic_year,
                    cgpa, backlogs, is_eligible, placement_eligibility, placement_status,
                    diploma_qualification, diploma_percentage, diploma_college, admission_year,
                    password_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                roll_no, name, admission_type, department, year_of_study, section,
                email, mobile, dob, gender, TARGET_GRADUATION_YEAR, academic_year,
                cgpa, backlogs, is_eligible, placement_eligibility, "Unplaced",
                diploma_qual or None, diploma_pct, diploma_college or None, adm_year,
                default_pwd_hash
            ))

            if skills_str:
                for s_item in skills_str.split(","):
                    s_name = s_item.strip()
                    if s_name:
                        df_sk = fetch_dataframe("SELECT skill_id FROM skills WHERE LOWER(skill_name) = LOWER(?)", (s_name,))
                        if df_sk.empty:
                            sk_id = execute_non_query("INSERT INTO skills (skill_name) VALUES (?)", (s_name,))
                        else:
                            sk_id = int(df_sk.iloc[0]["skill_id"])
                        execute_non_query("INSERT OR IGNORE INTO student_skills (student_id, skill_id) VALUES (?, ?)", (student_id, sk_id))

            dept_subjects = SUBJECTS_BY_DEPARTMENT.get(department, ["Engineering Core I", "Engineering Core II", "Technical Lab"])
            for sub in dept_subjects:
                execute_non_query("""
                    INSERT INTO attendance (student_id, subject, total_classes, attended_classes, percentage)
                    VALUES (?, ?, 40, 34, 85.0)
                """, (student_id, sub))
                execute_non_query("""
                    INSERT INTO marks (student_id, semester, subject, internal_marks, external_marks, total_marks, grade, credits)
                    VALUES (?, 'Semester 7', ?, 24, 60, 84, 'A', 4)
                """, (student_id, sub))

            file_roll_set.add(roll_lower)
            db_roll_set.add(roll_lower)
            successful_records.append({
                "row": row_num,
                "roll_no": roll_no,
                "name": name,
                "department": department,
                "admission_type": admission_type,
                "cgpa": cgpa,
                "eligibility": placement_eligibility
            })

        except Exception as insert_err:
            failed_records.append({
                "row": row_num,
                "roll_no": roll_no,
                "name": name,
                "error": f"Database insertion error: {str(insert_err)}"
            })

    if successful_records:
        log_audit_event(
            action="BULK_STUDENT_UPLOAD",
            student_id=None,
            roll_no=None,
            details=f"Bulk imported {len(successful_records)} students ({len(failed_records)} failed) from file '{filename}'",
            performed_by=session.get("name", "Faculty Administration")
        )
        try:
            generate_all_charts()
        except Exception:
            pass

    return jsonify({
        "success": True,
        "filename": filename,
        "total_records": len(df),
        "success_count": len(successful_records),
        "failed_count": len(failed_records),
        "successful_records": successful_records,
        "failed_records": failed_records
    })


@app.route("/api/audit-logs", methods=["GET"])
@faculty_required
def api_audit_logs():
    """Returns recent audit logs of student placement mutations."""
    df = fetch_dataframe("""
        SELECT log_id, action, student_id, roll_no, details, performed_by, created_at
        FROM placement_audit_logs
        ORDER BY log_id DESC
        LIMIT 50
    """)
    return jsonify(clean_records(df))



@app.route("/api/companies", methods=["GET", "POST"])
@login_required
def api_companies():
    """Returns partner companies with statistics or adds a new company."""
    if request.method == "POST":
        if session.get("role") != "faculty":
            return jsonify({"success": False, "error": "Faculty permissions required."}), 403
        data = request.get_json(silent=True) or request.form
        name = str(data.get("name", "")).strip()
        industry = str(data.get("industry", "Technology & Software")).strip()
        tier = str(data.get("tier", "Tier 2 (Dream)")).strip()
        website = str(data.get("website", "")).strip()
        email = str(data.get("contact_email", "")).strip()
        location = str(data.get("location", "Pan India")).strip()
        if not name:
            return jsonify({"success": False, "error": "Company name is required."}), 400
        try:
            execute_non_query("""
                INSERT INTO companies (name, industry, tier, website, contact_email, location)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, industry, tier, website, email, location))
            log_audit_event("COMPANY_ADDED", 0, "SYSTEM", json.dumps({"company": name, "tier": tier}), session.get("username", "faculty"))
            return jsonify({"success": True, "message": f"Company '{name}' registered successfully."})
        except Exception as e:
            return jsonify({"success": False, "error": f"Error saving company: {e}"}), 400

    df = fetch_dataframe("""
        SELECT c.company_id, c.name, c.industry, c.tier, c.website, c.contact_email, c.location,
               COUNT(p.placement_id) as total_offers,
               ROUND(AVG(p.package), 2) as avg_package,
               ROUND(MAX(p.package), 2) as max_package
        FROM companies c
        LEFT JOIN placements p ON LOWER(p.company) = LOWER(c.name)
        GROUP BY c.company_id, c.name
        ORDER BY total_offers DESC, c.name ASC
    """)
    return jsonify(clean_records(df))


@app.route("/api/placement-drives", methods=["GET", "POST"])
@login_required
def api_placement_drives():
    """Lists scheduled placement drives or creates a new drive."""
    if request.method == "POST":
        if session.get("role") != "faculty":
            return jsonify({"success": False, "error": "Faculty permissions required."}), 403
        data = request.get_json(silent=True) or request.form
        company = str(data.get("company_name", "")).strip()
        role = str(data.get("role", "")).strip()
        package_lpa = float(data.get("package_lpa", 0))
        drive_date = str(data.get("drive_date", "")).strip()
        min_cgpa = float(data.get("min_cgpa", 6.0))
        eligible_depts = str(data.get("eligible_departments", "All Departments")).strip()
        max_backlogs = int(data.get("max_backlogs", 0))
        status = str(data.get("status", "Upcoming")).strip()

        if not (company and role and package_lpa > 0 and drive_date):
            return jsonify({"success": False, "error": "Company, role, positive package, and drive date are required."}), 400

        try:
            execute_non_query("""
                INSERT INTO placement_drives (company_name, role, package_lpa, drive_date, min_cgpa, eligible_departments, max_backlogs, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (company, role, package_lpa, drive_date, min_cgpa, eligible_depts, max_backlogs, status))
            log_audit_event("DRIVE_SCHEDULED", 0, "SYSTEM", json.dumps({"company": company, "role": role, "package": package_lpa}), session.get("username", "faculty"))
            return jsonify({"success": True, "message": f"Placement drive for '{company}' scheduled successfully."})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    df = fetch_dataframe("""
        SELECT drive_id, company_name, role, package_lpa, drive_date, min_cgpa,
               eligible_departments, max_backlogs, status, registered_count
        FROM placement_drives
        ORDER BY drive_date ASC
    """)
    return jsonify(clean_records(df))


@app.route("/api/applications", methods=["GET", "POST"])
@login_required
def api_applications():
    """Returns candidate applications or updates interview stage."""
    if request.method == "POST":
        if session.get("role") != "faculty":
            return jsonify({"success": False, "error": "Faculty permissions required."}), 403
        data = request.get_json(silent=True) or request.form
        app_id = int(data.get("application_id", 0))
        new_round = str(data.get("current_round", "")).strip()
        new_status = str(data.get("status", "")).strip()

        if not app_id:
            return jsonify({"success": False, "error": "Application ID is required."}), 400

        try:
            execute_non_query("""
                UPDATE applications
                SET current_round = ?, status = ?
                WHERE application_id = ?
            """, (new_round, new_status, app_id))
            return jsonify({"success": True, "message": "Candidate interview status updated."})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    df = fetch_dataframe("""
        SELECT application_id, student_id, roll_no, student_name, department, company,
               role, applied_date, current_round, status, package_lpa
        FROM applications
        ORDER BY application_id DESC
    """)
    return jsonify(clean_records(df))


@app.route("/api/eligibility-rules", methods=["GET", "POST"])
@faculty_required
def api_eligibility_rules():
    """Manages placement cutoff rules and recalculates cohort eligibility."""
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        min_cgpa = float(data.get("min_cgpa", 6.0))
        max_backlogs = int(data.get("max_backlogs", 0))

        # Update settings
        execute_non_query("REPLACE INTO system_settings (setting_key, setting_val) VALUES ('min_cgpa_cutoff', ?)", (str(min_cgpa),))
        execute_non_query("REPLACE INTO system_settings (setting_key, setting_val) VALUES ('max_backlogs_allowed', ?)", (str(max_backlogs),))

        # Re-evaluate all students in cohort
        execute_non_query("""
            UPDATE students
            SET is_eligible = CASE
                WHEN cgpa >= ? AND COALESCE(backlogs, 0) <= ? THEN 1
                ELSE 0
            END,
            placement_eligibility = CASE
                WHEN cgpa >= ? AND COALESCE(backlogs, 0) <= ? THEN 'Eligible'
                ELSE 'Not Eligible'
            END
        """, (min_cgpa, max_backlogs, min_cgpa, max_backlogs))

        log_audit_event("ELIGIBILITY_RULES_UPDATED", 0, "SYSTEM", json.dumps({"min_cgpa": min_cgpa, "max_backlogs": max_backlogs}), session.get("username", "faculty"))

        # Fetch new summary
        eligible_cnt = fetch_dataframe("SELECT COUNT(*) as cnt FROM students WHERE is_eligible = 1").iloc[0]["cnt"]
        total_cnt = fetch_dataframe("SELECT COUNT(*) as cnt FROM students").iloc[0]["cnt"]

        return jsonify({
            "success": True,
            "message": f"Eligibility rules updated. {eligible_cnt} of {total_cnt} students are now marked eligible.",
            "eligible_count": int(eligible_cnt),
            "total_count": int(total_cnt)
        })

    # GET: return current rules & breakdown
    settings_df = fetch_dataframe("SELECT setting_key, setting_val FROM system_settings")
    settings_dict = dict(zip(settings_df["setting_key"], settings_df["setting_val"])) if not settings_df.empty else {}

    min_cgpa = float(settings_dict.get("min_cgpa_cutoff", 6.0))
    max_backlogs = int(settings_dict.get("max_backlogs_allowed", 0))

    cohort_stats = fetch_dataframe("""
        SELECT 
            COUNT(*) as total_students,
            SUM(CASE WHEN is_eligible = 1 THEN 1 ELSE 0 END) as eligible_count,
            SUM(CASE WHEN is_eligible = 0 THEN 1 ELSE 0 END) as ineligible_count,
            SUM(CASE WHEN cgpa < ? THEN 1 ELSE 0 END) as low_cgpa_count,
            SUM(CASE WHEN COALESCE(backlogs, 0) > ? THEN 1 ELSE 0 END) as backlog_count
        FROM students
    """, (min_cgpa, max_backlogs)).iloc[0].to_dict()

    return jsonify({
        "min_cgpa": min_cgpa,
        "max_backlogs": max_backlogs,
        "policy_one_dream": settings_dict.get("policy_one_dream_offer", "Enabled"),
        "stats": cohort_stats
    })


@app.route("/api/system-settings", methods=["GET", "POST"])
@faculty_required
def api_system_settings():
    """Fetches or updates system configurations."""
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        for k, v in data.items():
            execute_non_query("REPLACE INTO system_settings (setting_key, setting_val) VALUES (?, ?)", (str(k), str(v)))
        return jsonify({"success": True, "message": "System settings saved successfully."})

    df = fetch_dataframe("SELECT setting_key, setting_val FROM system_settings")
    return jsonify(dict(zip(df["setting_key"], df["setting_val"])))


@app.route("/api/users", methods=["GET", "POST"])
@faculty_required
def api_users():
    """Lists authorized faculty and administrative accounts or creates a new account."""
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        code = str(data.get("faculty_code", "")).strip().upper()
        username = str(data.get("username", "")).strip().lower()
        name = str(data.get("name", "")).strip()
        dept = str(data.get("department", "Training & Placement Cell")).strip()
        email = str(data.get("email", "")).strip()
        password = str(data.get("password", "Faculty@123")).strip()

        if not (code and username and name):
            return jsonify({"success": False, "error": "Faculty code, username, and full name are required."}), 400

        try:
            execute_non_query("""
                INSERT INTO faculty (faculty_code, username, name, department, email, password_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (code, username, name, dept, email, generate_password_hash(password)))
            log_audit_event("USER_CREATED", 0, code, json.dumps({"username": username, "name": name, "department": dept}), session.get("username", "faculty"))
            return jsonify({"success": True, "message": f"User account '{username}' created successfully."})
        except Exception as e:
            return jsonify({"success": False, "error": f"Failed to create user: {e}"}), 400

    df = fetch_dataframe("""
        SELECT faculty_id, faculty_code, username, name, department, email, created_at
        FROM faculty
        ORDER BY faculty_id ASC
    """)
    return jsonify(clean_records(df))


@app.route("/api/export/<dataset>", methods=["GET"])
@faculty_required
def api_export_dataset(dataset):
    """Exports dataset (students, placements, companies, drives) as CSV."""
    if dataset == "students":
        df = fetch_dataframe("""
            SELECT roll_no, name, department, graduation_year, cgpa, is_eligible, placement_status,
                   placement_eligibility, email, mobile, backlogs
            FROM students ORDER BY roll_no ASC
        """)
        filename = "students_cohort_export.csv"
    elif dataset == "placements":
        df = fetch_dataframe("""
            SELECT p.placement_id, s.roll_no, s.name as student_name, s.department, p.company,
                   p.role, p.package as package_lpa, p.placement_date, p.status
            FROM placements p
            JOIN students s ON p.student_id = s.student_id
            ORDER BY p.placement_date DESC
        """)
        filename = "placements_export.csv"
    elif dataset == "companies":
        df = fetch_dataframe("SELECT name, industry, tier, website, contact_email, location FROM companies ORDER BY name ASC")
        filename = "recruiting_companies_export.csv"
    elif dataset == "drives":
        df = fetch_dataframe("SELECT company_name, role, package_lpa, drive_date, min_cgpa, eligible_departments, max_backlogs, status FROM placement_drives ORDER BY drive_date ASC")
        filename = "placement_drives_schedule.csv"
    else:
        return jsonify({"success": False, "error": "Invalid export dataset."}), 400

    csv_data = df.to_csv(index=False)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/api/seed", methods=["POST"])
@faculty_required
def api_seed():
    """Resets and re-seeds database with fictional data (Faculty only)."""
    try:
        seed_all_data(200)
        generate_all_charts()
        return jsonify({"success": True, "message": "Database re-seeded with 200 students and 16 corporate recruiters."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# Static Visuals & Reports (Protected)
# ============================================================================
@app.route("/charts/<path:filename>")
@login_required
def serve_chart(filename):
    """Serves generated Matplotlib charts."""
    return send_from_directory(CHARTS_DIR, filename)


@app.route("/reports/download")
@login_required
def download_report():
    """Serves the generated text summary report."""
    report_file = os.path.join(REPORTS_DIR, "placement_summary_report.txt")
    if not os.path.exists(report_file):
        from main import export_full_text_report
        export_full_text_report()
    return send_from_directory(REPORTS_DIR, "placement_summary_report.txt", as_attachment=True)


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    print(f"[INFO] Starting Student Placement Data Analysis Web Server on http://{host}:{port} ...")
    app.run(host=host, port=port, debug=False)
