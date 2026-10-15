"""
Student Placement Data Analysis System - Main Entry Point.
Provides a clear, interactive CLI and automated reporting pipeline.
"""
import sys
import os
from tabulate_shim import print_table
from config import PACKAGE_UNIT, TARGET_GRADUATION_YEAR, REPORTS_DIR
from seed_data import seed_all_data
from analysis import (
    calculate_placement_rate,
    compare_departments,
    analyze_package_distribution,
    analyze_skill_demand
)
from visualization import generate_all_charts
from database import execute_non_query, fetch_dataframe


def ensure_reports_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def display_placement_rate_report():
    print("\n" + "=" * 65)
    print("           PLACEMENT-RATE REPORT (COHORT: 2025)")
    print("=" * 65)
    data = calculate_placement_rate()

    print(f"Total Enrolled Students       : {data['total_enrolled']}")
    print(f"Eligible Students (Denominator): {data['total_eligible_denominator']} (Criteria: CGPA >= 6.0, no backlogs)")
    print(f"Ineligible Students           : {data['total_ineligible']}")
    print("-" * 65)
    print(f"Unique Placed Students (Num)  : {data['unique_students_placed']}")
    print(f"Unplaced Eligible Students    : {data['unplaced_eligible']}")
    print(f"Total Placement Offers Made   : {data['total_offers_received']}")
    print(f"Duplicate Offers Handled      : {data['duplicate_offers_count']} extra offers")
    print(f"Avg Offers per Placed Student : {data['avg_offers_per_placed_student']}")
    print("=" * 65)
    print(f"--> OFFICIAL PLACEMENT RATE   : {data['placement_rate_pct']}%")
    print("    [Formula: (Unique Placed / Eligible Students) * 100]")
    print("=" * 65 + "\n")


def display_department_comparison():
    print("\n" + "=" * 80)
    print("                  DEPARTMENT-WISE COMPARISON REPORT")
    print("=" * 80)
    df = compare_departments()
    print_table(df)
    print(f"* Note: Package figures are in {PACKAGE_UNIT}. Sensitive student details excluded.")
    print("=" * 80 + "\n")


def display_package_summary():
    print("\n" + "=" * 65)
    print("          PACKAGE DISTRIBUTION & SALARY METRICS")
    print("=" * 65)
    summary = analyze_package_distribution()

    print(f"\n[A] All Offers Distribution (Unit: {PACKAGE_UNIT}):")
    for k, v in summary["all_offers_summary"].items():
        print(f"  - {k:<22}: {v}")

    print(f"\n[B] Unique Students' Highest Offer Distribution:")
    for k, v in summary["highest_package_per_student_summary"].items():
        print(f"  - {k:<22}: {v}")

    print("\n[C] Salary Tier Breakdown (All Offers):")
    for tier, count in summary["salary_tiers"].items():
        print(f"  - {tier:<26}: {count} offers")
    print("=" * 65 + "\n")


def display_skill_demand_report():
    print("\n" + "=" * 75)
    print("                     SKILL-DEMAND REPORT")
    print("=" * 75)
    df = analyze_skill_demand()
    print_table(df)
    print("=" * 75 + "\n")


def add_placement_record():
    print("\n--- Record New Placement Offer ---")
    try:
        student_id = int(input("Enter Student ID: ").strip())
        company = input("Enter Company Name: ").strip()
        role = input("Enter Role: ").strip()
        package = float(input(f"Enter Package ({PACKAGE_UNIT}): ").strip())
        date_str = input("Enter Placement Date (YYYY-MM-DD) [Default: Today]: ").strip()
        if not date_str:
            from datetime import date
            date_str = date.today().isoformat()

        # Check student exists and is eligible
        df = fetch_dataframe("SELECT roll_no, name, is_eligible FROM students WHERE student_id = ?", (student_id,))
        if df.empty:
            print(f"[ERROR] Student with ID {student_id} not found.")
            return

        is_eligible = df.iloc[0]["is_eligible"]
        if is_eligible == 0:
            print(f"[WARNING] Student {df.iloc[0]['name']} is marked Ineligible for placements!")
            confirm = input("Proceed anyway? (y/n): ").strip().lower()
            if confirm != 'y':
                return

        execute_non_query("""
            INSERT INTO placements (student_id, company, role, package, placement_date, status)
            VALUES (?, ?, ?, ?, ?, 'Placed')
        """, (student_id, company, role, package, date_str))

        print(f"[OK] Successfully recorded placement offer of {package} {PACKAGE_UNIT} at {company}!")
    except ValueError as ve:
        print(f"[ERROR] Invalid input: {ve}")


def add_student_record():
    print("\n--- Register New Student to Cohort ---")
    try:
        name = input("Enter Full Name: ").strip()
        roll_no = input("Enter Roll Number (e.g. CSE2025101): ").strip().upper()
        if not (name and roll_no):
            print("[ERROR] Name and Roll Number cannot be empty.")
            return

        print("Select Department:")
        print("  1. Computer Science")
        print("  2. Information Technology")
        print("  3. Electronics & Comm")
        print("  4. Mechanical Engg")
        print("  5. Civil Engg")
        dept_choice = input("Choice (1-5): ").strip()
        dept_map = {
            "1": "Computer Science",
            "2": "Information Technology",
            "3": "Electronics & Comm",
            "4": "Mechanical Engg",
            "5": "Civil Engg"
        }
        department = dept_map.get(dept_choice, "Computer Science")

        grad_year_str = input(f"Enter Graduation Year [Default: {TARGET_GRADUATION_YEAR}]: ").strip()
        grad_year = int(grad_year_str) if grad_year_str else TARGET_GRADUATION_YEAR

        cgpa = float(input("Enter CGPA (0.0 - 10.0): ").strip())

        elig_default = "1" if cgpa >= 6.0 else "0"
        elig_prompt = f"Eligible for Placements? (1: Eligible, 0: Ineligible) [Default: {elig_default}]: "
        elig_str = input(elig_prompt).strip()
        is_eligible = int(elig_str) if elig_str in ["0", "1"] else int(elig_default)

        skills_str = input("Enter Key Skills (comma-separated, e.g. Python, SQL, AWS): ").strip()
        skills = [s.strip() for s in skills_str.split(",") if s.strip()]

        # Check existing roll_no
        df_chk = fetch_dataframe("SELECT student_id FROM students WHERE roll_no = ?", (roll_no,))
        if not df_chk.empty:
            print(f"[ERROR] Student with Roll No '{roll_no}' already exists.")
            return

        student_id = execute_non_query("""
            INSERT INTO students (roll_no, name, department, graduation_year, cgpa, is_eligible)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (roll_no, name, department, grad_year, cgpa, is_eligible))

        for sk in skills:
            df_sk = fetch_dataframe("SELECT skill_id FROM skills WHERE skill_name = ?", (sk,))
            if df_sk.empty:
                sk_id = execute_non_query("INSERT INTO skills (skill_name) VALUES (?)", (sk,))
            else:
                sk_id = int(df_sk.iloc[0]["skill_id"])

            execute_non_query("INSERT OR IGNORE INTO student_skills (student_id, skill_id) VALUES (?, ?)", (student_id, sk_id))

        status_label = "ELIGIBLE" if is_eligible == 1 else "INELIGIBLE"
        print(f"[OK] Successfully registered student #{student_id} '{name}' ({roll_no}) in {department} as {status_label}!")
    except ValueError as ve:
        print(f"[ERROR] Invalid input: {ve}")


def export_full_text_report():
    ensure_reports_dir()
    filepath = os.path.join(REPORTS_DIR, "placement_summary_report.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        # Redirect stdout to file
        original_stdout = sys.stdout
        sys.stdout = f
        try:
            print("================================================================================")
            print("            STUDENT PLACEMENT DATA ANALYSIS SYSTEM - SUMMARY REPORT             ")
            print("================================================================================")
            display_placement_rate_report()
            display_department_comparison()
            display_package_summary()
            display_skill_demand_report()
        finally:
            sys.stdout = original_stdout

    print(f"[OK] Full summary report exported to: {filepath}")
    return filepath


def run_all():
    """Runs data seeding (if DB is empty), prints all reports, and generates charts."""
    # Check if students exist
    try:
        df_chk = fetch_dataframe("SELECT COUNT(*) as cnt FROM students")
        if df_chk.iloc[0]["cnt"] == 0:
            print("[INFO] Database empty. Seeding initial fictional dataset...")
            seed_all_data()
    except Exception:
        seed_all_data()

    display_placement_rate_report()
    display_department_comparison()
    display_package_summary()
    display_skill_demand_report()
    generate_all_charts()
    export_full_text_report()
    print("\n[SUCCESS] All reports and visualizations have been generated successfully!")


def main_menu():
    while True:
        print("\n" + "=" * 55)
        print("    STUDENT PLACEMENT DATA ANALYSIS SYSTEM")
        print("=" * 55)
        print("1. Run Full Analysis & Generate All Visualizations")
        print("2. View Placement-Rate Report")
        print("3. View Department-Wise Comparison")
        print("4. View Package Distribution & Statistics")
        print("5. View Skill-Demand Report")
        print("6. Generate Matplotlib Charts")
        print("7. Add New Student to Cohort")
        print("8. Record Placement Offer for Student")
        print("9. Seed / Reset Database with Fictional Records")
        print("10. Export Text Summary Report")
        print("0. Exit")
        print("=" * 55)

        choice = input("Enter your choice (0-10): ").strip()
        if choice == "1":
            run_all()
        elif choice == "2":
            display_placement_rate_report()
        elif choice == "3":
            display_department_comparison()
        elif choice == "4":
            display_package_summary()
        elif choice == "5":
            display_skill_demand_report()
        elif choice == "6":
            generate_all_charts()
        elif choice == "7":
            add_student_record()
        elif choice == "8":
            add_placement_record()
        elif choice == "9":
            seed_all_data()
        elif choice == "10":
            export_full_text_report()
        elif choice == "0":
            print("Exiting system. Goodbye!")
            break
        else:
            print("Invalid option. Please choose between 0 and 9.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--run-all", "-a", "all"]:
        run_all()
    else:
        main_menu()
