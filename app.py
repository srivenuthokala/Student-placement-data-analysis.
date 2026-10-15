"""
Flask Web Application for Student Placement Data Analysis System.
Provides REST APIs and serves a rich, interactive web dashboard.
"""
import os
from flask import Flask, render_template, jsonify, request, send_from_directory
from database import fetch_dataframe, execute_non_query
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

# Ensure required directories exist
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Ensure sample data exists on startup
try:
    df_chk = fetch_dataframe("SELECT COUNT(*) as cnt FROM students")
    if df_chk.iloc[0]["cnt"] == 0:
        seed_all_data()
        generate_all_charts()
except Exception:
    seed_all_data()
    generate_all_charts()


@app.route("/")
def index():
    """Main dashboard page."""
    return render_template("index.html", package_unit=PACKAGE_UNIT, grad_year=TARGET_GRADUATION_YEAR)


@app.route("/api/summary")
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
def api_departments():
    """Returns department-wise comparative metrics."""
    grad_year = request.args.get("year", default=TARGET_GRADUATION_YEAR, type=int)
    df = compare_departments(grad_year)
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/packages")
def api_packages():
    """Returns detailed package distribution statistics."""
    grad_year = request.args.get("year", default=TARGET_GRADUATION_YEAR, type=int)
    dist = analyze_package_distribution(grad_year)
    # Also fetch raw packages array for frontend dynamic charting
    _, df_placements, _ = get_clean_data(grad_year)
    dist["raw_packages"] = sorted(df_placements["package"].tolist())
    dist["companies"] = df_placements.groupby("company")["package"].agg(["count", "mean", "max"]).reset_index().to_dict(orient="records")
    return jsonify(dist)


@app.route("/api/skills")
def api_skills():
    """Returns skill-demand analysis."""
    grad_year = request.args.get("year", default=TARGET_GRADUATION_YEAR, type=int)
    df = analyze_skill_demand(grad_year)
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/students")
def api_students():
    """Returns student list with skills and placement status."""
    grad_year = request.args.get("year", default=TARGET_GRADUATION_YEAR, type=int)
    query = """
        SELECT s.student_id, s.roll_no, s.name, s.department, s.cgpa, s.is_eligible,
               GROUP_CONCAT(sk.skill_name, ', ') AS skills,
               COUNT(p.placement_id) AS total_offers,
               MAX(p.package) AS highest_package,
               GROUP_CONCAT(DISTINCT p.company) AS companies
        FROM students s
        LEFT JOIN student_skills ss ON s.student_id = ss.student_id
        LEFT JOIN skills sk ON ss.skill_id = sk.skill_id
        LEFT JOIN placements p ON s.student_id = p.student_id
        WHERE s.graduation_year = ?
        GROUP BY s.student_id
        ORDER BY s.student_id ASC
    """
    df = fetch_dataframe(query, params=(grad_year,))
    # Fill NAs
    df["skills"] = df["skills"].fillna("None")
    df["highest_package"] = df["highest_package"].fillna(0.0)
    df["companies"] = df["companies"].fillna("None")
    df["placement_status"] = df["total_offers"].apply(lambda x: "Placed" if x > 0 else "Unplaced")
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/record-placement", methods=["POST"])
def api_record_placement():
    """Records a new placement offer via web modal."""
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

        # Check student existence
        df = fetch_dataframe("SELECT roll_no, name, is_eligible FROM students WHERE student_id = ?", (student_id,))
        if df.empty:
            return jsonify({"success": False, "error": f"Student ID {student_id} not found."}), 404

        execute_non_query("""
            INSERT INTO placements (student_id, company, role, package, placement_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (student_id, company, role, package, placement_date, status))

        # Re-generate charts in background
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


@app.route("/api/available-skills")
def api_available_skills():
    """Returns catalog of all available skills for selection."""
    df = fetch_dataframe("SELECT skill_id, skill_name FROM skills ORDER BY skill_name ASC")
    return jsonify(df["skill_name"].tolist())


@app.route("/api/add-student", methods=["POST"])
def api_add_student():
    """Adds a new student to the cohort with eligibility status and skills."""
    data = request.get_json() or {}
    try:
        name = str(data.get("name", "")).strip()
        roll_no = str(data.get("roll_no", "")).strip().upper()
        department = str(data.get("department", "")).strip()
        graduation_year = int(data.get("graduation_year", TARGET_GRADUATION_YEAR))
        cgpa = float(data.get("cgpa", 0.0))
        is_eligible = int(data.get("is_eligible", 1 if cgpa >= 6.0 else 0))
        skills = data.get("skills", [])

        if not (name and roll_no and department):
            return jsonify({"success": False, "error": "Name, Roll Number, and Department are required."}), 400

        if not (0.0 <= cgpa <= 10.0):
            return jsonify({"success": False, "error": "CGPA must be between 0.0 and 10.0."}), 400

        # Check if roll_no already exists
        df_chk = fetch_dataframe("SELECT student_id FROM students WHERE roll_no = ?", (roll_no,))
        if not df_chk.empty:
            return jsonify({"success": False, "error": f"Student with Roll No '{roll_no}' already exists."}), 400

        # Insert student record
        student_id = execute_non_query("""
            INSERT INTO students (roll_no, name, department, graduation_year, cgpa, is_eligible)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (roll_no, name, department, graduation_year, cgpa, is_eligible))

        # Assign skills
        for skill_name in skills:
            skill_name = str(skill_name).strip()
            if not skill_name:
                continue

            # Check if skill exists in catalog, or insert it
            df_sk = fetch_dataframe("SELECT skill_id FROM skills WHERE skill_name = ?", (skill_name,))
            if df_sk.empty:
                skill_id = execute_non_query("INSERT INTO skills (skill_name) VALUES (?)", (skill_name,))
            else:
                skill_id = int(df_sk.iloc[0]["skill_id"])

            execute_non_query("""
                INSERT OR IGNORE INTO student_skills (student_id, skill_id)
                VALUES (?, ?)
            """, (student_id, skill_id))

        # Re-generate charts in background
        try:
            generate_all_charts()
        except Exception:
            pass

        status_text = "Eligible for Placements" if is_eligible == 1 else "Ineligible (Backlogs/Academic criteria)"
        return jsonify({
            "success": True,
            "message": f"Student '{name}' ({roll_no}) successfully added as {status_text}.",
            "student_id": student_id,
            "is_eligible": is_eligible
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/seed", methods=["POST"])
def api_seed():
    """Resets and re-seeds database with fictional data."""
    try:
        seed_all_data()
        generate_all_charts()
        return jsonify({"success": True, "message": "Database re-seeded and charts updated successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/charts/<path:filename>")
def serve_chart(filename):
    """Serves generated Matplotlib charts."""
    return send_from_directory(CHARTS_DIR, filename)


@app.route("/reports/download")
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
