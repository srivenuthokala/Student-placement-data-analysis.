"""
Data Analysis Module using Pandas and NumPy.
Calculates placement rates, department comparisons, package statistics, and skill demand.
Strictly adheres to documented acceptance criteria:
- Package units: LPA (Lakhs Per Annum)
- Placement denominator: Unique eligible students in the cohort (is_eligible = 1)
- Duplicate handling: Separates offer count from unique student placement count
- Sensitive data protection: Reports are aggregated and do not expose personal identifiers
"""
import numpy as np
import pandas as pd
from database import fetch_dataframe
from config import PACKAGE_UNIT, TARGET_GRADUATION_YEAR


def get_clean_data(grad_year: int = TARGET_GRADUATION_YEAR):
    """
    Fetches raw tables and returns clean, pre-processed DataFrames.
    """
    students_query = """
        SELECT student_id, roll_no, department, graduation_year, cgpa, is_eligible
        FROM students
        WHERE graduation_year = ?
    """
    placements_query = """
        SELECT placement_id, student_id, company, role, package, placement_date, status
        FROM placements
    """
    skills_query = """
        SELECT s.student_id, sk.skill_name
        FROM student_skills ss
        JOIN skills sk ON ss.skill_id = sk.skill_id
        JOIN students s ON ss.student_id = s.student_id
        WHERE s.graduation_year = ?
    """
    df_students = fetch_dataframe(students_query, params=(grad_year,))
    df_placements = fetch_dataframe(placements_query)
    df_skills = fetch_dataframe(skills_query, params=(grad_year,))

    # Filter placements to only students in the target cohort
    df_cohort_placements = df_placements.merge(
        df_students[["student_id", "department", "is_eligible"]],
        on="student_id",
        how="inner"
    )

    return df_students, df_cohort_placements, df_skills


def calculate_placement_rate(grad_year: int = TARGET_GRADUATION_YEAR) -> dict:
    """
    Calculates overall placement metrics using documented eligible denominator.
    Denominator: Total students where is_eligible == 1 in the graduating cohort.
    Duplicate handling: Count of DISTINCT placed students (not total offers).
    """
    df_students, df_placements, _ = get_clean_data(grad_year)

    total_students = len(df_students)
    df_eligible = df_students[df_students["is_eligible"] == 1]
    total_eligible = len(df_eligible)
    total_ineligible = total_students - total_eligible

    # Eligible students who received at least one placement
    placed_student_ids = df_placements["student_id"].unique()
    placed_eligible_ids = set(placed_student_ids).intersection(set(df_eligible["student_id"]))
    unique_placed = len(placed_eligible_ids)
    unplaced_eligible = total_eligible - unique_placed

    # Duplicate offer metrics
    total_offers = len(df_placements)
    duplicate_offers = total_offers - unique_placed

    placement_rate = (unique_placed / total_eligible * 100) if total_eligible > 0 else 0.0

    return {
        "graduation_year": grad_year,
        "total_enrolled": total_students,
        "total_eligible_denominator": total_eligible,
        "total_ineligible": total_ineligible,
        "unique_students_placed": unique_placed,
        "unplaced_eligible": unplaced_eligible,
        "total_offers_received": total_offers,
        "duplicate_offers_count": duplicate_offers,
        "placement_rate_pct": round(placement_rate, 2),
        "avg_offers_per_placed_student": round(total_offers / unique_placed, 2) if unique_placed > 0 else 0.0
    }


def compare_departments(grad_year: int = TARGET_GRADUATION_YEAR) -> pd.DataFrame:
    """
    Department-wise comparison of placement outcomes, rates, and package ranges.
    Adheres to sensitive data protection: output is aggregated by department.
    """
    df_students, df_placements, _ = get_clean_data(grad_year)

    dept_stats = []
    for dept, group in df_students.groupby("department"):
        total = len(group)
        eligible = len(group[group["is_eligible"] == 1])
        eligible_ids = set(group[group["is_eligible"] == 1]["student_id"])

        dept_placements = df_placements[df_placements["student_id"].isin(eligible_ids)]
        unique_placed = dept_placements["student_id"].nunique()
        total_offers = len(dept_placements)

        rate = (unique_placed / eligible * 100) if eligible > 0 else 0.0

        if not dept_placements.empty:
            avg_pkg = round(float(np.mean(dept_placements["package"])), 2)
            max_pkg = round(float(np.max(dept_placements["package"])), 2)
            min_pkg = round(float(np.min(dept_placements["package"])), 2)
        else:
            avg_pkg, max_pkg, min_pkg = 0.0, 0.0, 0.0

        dept_stats.append({
            "Department": dept,
            "Enrolled": total,
            "Eligible (Denominator)": eligible,
            "Placed Students": unique_placed,
            "Placement Rate (%)": round(rate, 2),
            "Total Offers": total_offers,
            f"Avg Package ({PACKAGE_UNIT})": avg_pkg,
            f"Max Package ({PACKAGE_UNIT})": max_pkg,
            f"Min Package ({PACKAGE_UNIT})": min_pkg
        })

    return pd.DataFrame(dept_stats).sort_values(by="Placement Rate (%)", ascending=False)


def analyze_package_distribution(grad_year: int = TARGET_GRADUATION_YEAR) -> dict:
    """
    Calculates detailed statistical metrics for packages using NumPy and Pandas.
    Handles duplicates by computing stats for both:
    1. All offers received
    2. Highest package per unique placed student
    """
    _, df_placements, _ = get_clean_data(grad_year)

    if df_placements.empty:
        return {"error": "No placement records found."}

    all_packages = df_placements["package"].to_numpy()
    # Unique placed student's highest package
    highest_per_student = df_placements.groupby("student_id")["package"].max().to_numpy()

    def get_stats(arr):
        return {
            "Count": int(len(arr)),
            "Mean": round(float(np.mean(arr)), 2),
            "Median": round(float(np.median(arr)), 2),
            "Std Dev": round(float(np.std(arr, ddof=1)), 2) if len(arr) > 1 else 0.0,
            "Min": round(float(np.min(arr)), 2),
            "Max": round(float(np.max(arr)), 2),
            "25th Percentile (Q1)": round(float(np.percentile(arr, 25)), 2),
            "75th Percentile (Q3)": round(float(np.percentile(arr, 75)), 2),
            "IQR": round(float(np.percentile(arr, 75) - np.percentile(arr, 25)), 2),
            "Unit": PACKAGE_UNIT
        }

    return {
        "all_offers_summary": get_stats(all_packages),
        "highest_package_per_student_summary": get_stats(highest_per_student),
        "salary_tiers": {
            "Super Dream (> 15 LPA)": int(np.sum(all_packages >= 15.0)),
            "Dream (8 - 15 LPA)": int(np.sum((all_packages >= 8.0) & (all_packages < 15.0))),
            "Standard (4 - 8 LPA)": int(np.sum((all_packages >= 4.0) & (all_packages < 8.0))),
            "Entry (< 4 LPA)": int(np.sum(all_packages < 4.0))
        }
    }


def analyze_skill_demand(grad_year: int = TARGET_GRADUATION_YEAR) -> pd.DataFrame:
    """
    Analyzes which skills are in highest demand among placed students.
    Computes:
    - Skill frequency among placed students
    - Placement rate of students possessing each skill
    - Average package offered to students with the skill
    """
    df_students, df_placements, df_skills = get_clean_data(grad_year)

    placed_ids = set(df_placements["student_id"].unique())
    # Map student to max package
    student_pkg_map = df_placements.groupby("student_id")["package"].max().to_dict()

    skill_rows = []
    for skill_name, group in df_skills.groupby("skill_name"):
        student_ids_with_skill = set(group["student_id"].unique())
        total_students_with_skill = len(student_ids_with_skill)

        placed_with_skill = student_ids_with_skill.intersection(placed_ids)
        placed_count = len(placed_with_skill)

        packages_for_skill = [student_pkg_map[sid] for sid in placed_with_skill if sid in student_pkg_map]

        skill_placement_rate = (placed_count / total_students_with_skill * 100) if total_students_with_skill > 0 else 0.0
        avg_pkg = round(float(np.mean(packages_for_skill)), 2) if packages_for_skill else 0.0

        skill_rows.append({
            "Skill": skill_name,
            "Students with Skill": total_students_with_skill,
            "Placed Students": placed_count,
            "Placement Success Rate (%)": round(skill_placement_rate, 2),
            f"Avg Package ({PACKAGE_UNIT})": avg_pkg
        })

    df_result = pd.DataFrame(skill_rows).sort_values(by="Placed Students", ascending=False)
    return df_result
