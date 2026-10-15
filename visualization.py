"""
Visualization Module using Matplotlib.
Generates clear, informative charts for placement statistics and package distributions.
Saves all charts as high-resolution PNGs to the 'charts/' folder.
"""
import os
import matplotlib
matplotlib.use("Agg")  # Safe headless backend for Windows/CLI
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from analysis import (
    calculate_placement_rate,
    compare_departments,
    analyze_package_distribution,
    analyze_skill_demand,
    get_clean_data
)
from config import CHARTS_DIR, PACKAGE_UNIT


def ensure_charts_dir():
    """Creates the charts directory if it does not exist."""
    os.makedirs(CHARTS_DIR, exist_ok=True)


def plot_department_placement_rate(save_path=None):
    """Generates a bar chart comparing placement rate (%) by department."""
    ensure_charts_dir()
    df_dept = compare_departments()

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(
        df_dept["Department"],
        df_dept["Placement Rate (%)"],
        color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
        edgecolor="black",
        alpha=0.85
    )

    ax.set_title("Department-Wise Placement Rate (%)", fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel("Placement Rate (%)", fontsize=11)
    ax.set_ylim(0, 105)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # Annotate bars with values
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{height:.1f}%",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4),
                    textcoords="offset points",
                    ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.xticks(rotation=15, ha="right", fontsize=10)
    plt.tight_layout()

    out_file = save_path or os.path.join(CHARTS_DIR, "department_placement_rate.png")
    plt.savefig(out_file, dpi=200)
    plt.close()
    print(f"[OK] Saved chart: {out_file}")
    return out_file


def plot_package_distribution(save_path=None):
    """
    Generates a combined Histogram & Boxplot showing package distributions in LPA.
    Highlights NumPy Mean and Median lines clearly.
    """
    ensure_charts_dir()
    _, df_placements, _ = get_clean_data()
    packages = df_placements["package"].to_numpy()

    mean_pkg = np.mean(packages)
    median_pkg = np.median(packages)

    fig, (ax_box, ax_hist) = plt.subplots(
        2, 1,
        figsize=(9, 7),
        sharex=True,
        gridspec_kw={"height_ratios": [0.25, 0.75]}
    )

    # Boxplot
    ax_box.boxplot(packages, vert=False, patch_artist=True,
                   boxprops=dict(facecolor="#86b7fe", color="#0d6efd"),
                   medianprops=dict(color="#d62728", linewidth=2))
    ax_box.set_title(f"Package Distribution Analysis ({PACKAGE_UNIT})", fontsize=13, fontweight="bold")
    ax_box.set_yticks([])
    ax_box.grid(axis="x", linestyle="--", alpha=0.5)

    # Histogram
    counts, bins, patches = ax_hist.hist(packages, bins=12, color="#4c72b0", edgecolor="black", alpha=0.8)
    ax_hist.axvline(mean_pkg, color="red", linestyle="--", linewidth=2, label=f"Mean: {mean_pkg:.2f} LPA")
    ax_hist.axvline(median_pkg, color="green", linestyle="-.", linewidth=2, label=f"Median: {median_pkg:.2f} LPA")

    ax_hist.set_xlabel(f"Package ({PACKAGE_UNIT})", fontsize=11)
    ax_hist.set_ylabel("Number of Offers", fontsize=11)
    ax_hist.legend(fontsize=10, loc="upper right")
    ax_hist.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    out_file = save_path or os.path.join(CHARTS_DIR, "package_distribution.png")
    plt.savefig(out_file, dpi=200)
    plt.close()
    print(f"[OK] Saved chart: {out_file}")
    return out_file


def plot_top_skills_demand(top_n=10, save_path=None):
    """Generates a horizontal bar chart displaying top skills among placed students."""
    ensure_charts_dir()
    df_skills = analyze_skill_demand().head(top_n)
    df_skills = df_skills.sort_values(by="Placed Students", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 6))
    bars = ax.barh(
        df_skills["Skill"],
        df_skills["Placed Students"],
        color="#2b8cbe",
        edgecolor="black",
        alpha=0.85
    )

    ax.set_title(f"Top {top_n} In-Demand Skills (Placed Candidates)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Count of Placed Students Possessing Skill", fontsize=11)
    ax.grid(axis="x", linestyle="--", alpha=0.5)

    for bar in bars:
        width = bar.get_width()
        ax.annotate(f"{int(width)}",
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(5, 0),
                    textcoords="offset points",
                    ha="left", va="center", fontsize=9, fontweight="bold")

    plt.tight_layout()
    out_file = save_path or os.path.join(CHARTS_DIR, "top_skills_demand.png")
    plt.savefig(out_file, dpi=200)
    plt.close()
    print(f"[OK] Saved chart: {out_file}")
    return out_file


def plot_placement_status_overview(save_path=None):
    """Generates a Donut chart showing overall cohort breakdown."""
    ensure_charts_dir()
    rate_info = calculate_placement_rate()

    labels = ["Placed (Eligible)", "Unplaced (Eligible)", "Ineligible"]
    sizes = [
        rate_info["unique_students_placed"],
        rate_info["unplaced_eligible"],
        rate_info["total_ineligible"]
    ]
    colors = ["#2ca02c", "#ffbb78", "#d62728"]

    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.75,
        textprops=dict(fontsize=10)
    )

    # Style center to create donut
    centre_circle = plt.Circle((0, 0), 0.55, fc="white")
    ax.add_artist(centre_circle)

    for autotext in autotexts:
        autotext.set_color("black")
        autotext.set_fontweight("bold")

    ax.set_title("Student Cohort Placement Status Overview", fontsize=13, fontweight="bold")
    plt.tight_layout()

    out_file = save_path or os.path.join(CHARTS_DIR, "placement_status_overview.png")
    plt.savefig(out_file, dpi=200)
    plt.close()
    print(f"[OK] Saved chart: {out_file}")
    return out_file


def generate_all_charts():
    """Generates and saves all charts."""
    print("\n--- Generating Matplotlib Visualizations ---")
    plot_department_placement_rate()
    plot_package_distribution()
    plot_top_skills_demand()
    plot_placement_status_overview()
    print("[OK] All charts successfully generated in 'charts/' directory.")


if __name__ == "__main__":
    generate_all_charts()
