# Student Placement Data Analysis System

**Difficulty Level**: Intermediate  
**Project Category**: Data Engineering & Analytics  
**Status**: Ready to Run (Dual Database: SQLite & MySQL 8.0)

---

## 1. Tech Stack Overview

| Layer | Technology | Purpose & Details |
|---|---|---|
| **Core Language** | Python 3.14 | Procedural, clean, modular Python codebase (beginner-friendly and readable) |
| **Database** | Dual Mode: SQLite & MySQL 8.0 | Out-of-the-box SQLite local database (`placement_system.db`) + full `schema.sql` and `mysql-connector-python` integration |
| **Data Manipulation** | Pandas | Data cleaning, department aggregation, placement rate calculations, cross-tabulations |
| **Statistical Analysis** | NumPy | Package distribution metrics (Mean, Median, Std Dev, Min, Max, 25th/75th Percentiles, IQR) |
| **Data Visualization** | Matplotlib | High-resolution charts saved to `charts/` (Bar, Histogram, Boxplot, Horizontal Bar, Donut) |
| **Web Server & APIs** | Flask 3.1 | REST API endpoints for metrics, departments, packages, skills, students, and seeding |
| **Frontend Framework** | HTML5 & Vanilla CSS | Modern Slate Glassmorphism theme, fully responsive, zero heavy external frameworks |
| **Interactive Charts** | Chart.js | Dynamic, interactive charts with custom tooltips, responsive rendering, and smooth animations |
| **Console Interface** | Python CLI | Interactive menu-driven interface with tabulate formatting and instant `--run-all` automation |

---

## 2. Key Acceptance Criteria & Business Definitions

### A. Documented Package Units
* All compensation values are strictly stored and reported in **LPA (Lakhs Per Annum in INR)**.
* Example: `12.50 LPA` = ₹12,50,000 per year.

### B. Documented Placement Rate & Denominator Formula
* **Denominator**: Only **Eligible Students** in the graduating cohort (`is_eligible = 1`, criteria: CGPA $\ge$ 6.0 and no active backlogs/disciplinary restrictions).
* **Numerator**: Count of **Unique Eligible Students Placed** (regardless of how many offers each student holds).
$$\text{Placement Rate (\%)} = \left(\frac{\text{Unique Placed Eligible Students}}{\text{Total Eligible Students in Cohort}}\right) \times 100$$

### C. Handling Duplicate Placements
* **Offers vs. Placed Students**: Top candidates often receive multiple offers (e.g. from Google and Infosys).
* The system counts duplicate offers separately (`Total Offers` vs `Unique Placed Students`).
* Placement rate counts each placed candidate exactly once (`COUNT(DISTINCT student_id)`).
* For package analytics, both **All Offers Received** and **Highest/Accepted Package per Student** are computed to avoid skewed statistics.

### D. Sensitive Student Data Protection
* In compliance with student privacy norms, individual names, roll numbers, and contact details are excluded from all aggregate reports and charts.
* Reports output department-level, skill-level, and cohort-level summaries.

---

## 3. Database Entities & Schema

The schema matches the specified requirements:

1. **`students`**:
   - `student_id` (PK, AUTO_INCREMENT)
   - `roll_no` (VARCHAR, UNIQUE)
   - `name` (VARCHAR)
   - `department` (VARCHAR: Computer Science, Information Technology, Electronics & Comm, Mechanical Engg, Civil Engg)
   - `graduation_year` (INT)
   - `cgpa` (DECIMAL/REAL)
   - `is_eligible` (TINYINT/INTEGER: 1 for Eligible, 0 for Ineligible)

2. **`skills`**:
   - `skill_id` (PK, AUTO_INCREMENT)
   - `skill_name` (VARCHAR, UNIQUE: Python, SQL, Java, React, AWS, etc.)

3. **`student_skills`** (Many-to-Many):
   - `student_id` (FK -> `students.student_id`)
   - `skill_id` (FK -> `skills.skill_id`)
   - PRIMARY KEY (`student_id`, `skill_id`)

4. **`placements`**:
   - `placement_id` (PK, AUTO_INCREMENT)
   - `student_id` (FK -> `students.student_id`)
   - `company` (VARCHAR)
   - `role` (VARCHAR)
   - `package` (DECIMAL/REAL, in LPA)
   - `placement_date` (DATE)
   - `status` (VARCHAR: 'Placed', 'Offered', 'Accepted')

---

## 4. Project File Structure

```
c:\python project\
├── app.py                     # Flask web server and REST API endpoints
├── config.py                 # Configuration settings (DB engine switch, paths, constants)
├── database.py               # Database connector abstraction (SQLite & MySQL)
├── schema.sql                # Pure MySQL 8.0 DDL & DML script
├── seed_data.py              # Realistic fictional dataset generator (100 students)
├── analysis.py               # Statistical calculations using Pandas and NumPy
├── visualization.py          # Matplotlib chart generators
├── tabulate_shim.py          # Clean CLI table printing utility
├── main.py                   # Main CLI application (interactive menu & automated runner)
├── requirements.txt          # Python dependencies
├── templates/
│   └── index.html            # Semantic HTML5 single-page application dashboard
├── static/
│   ├── css/
│   │   └── style.css         # Modern vanilla CSS design system & glassmorphism theme
│   └── js/
│       └── app.js            # Client logic: API data fetching, Chart.js instances, modal & filters
├── charts/                   # Auto-generated Matplotlib visualization images
│   ├── department_placement_rate.png
│   ├── package_distribution.png
│   ├── top_skills_demand.png
│   └── placement_status_overview.png
└── reports/                  # Exported summary text reports
    └── placement_summary_report.txt
```

---

## 5. How to Run the Project

### Method 1: Interactive Web Dashboard (Recommended)
Launch the modern web application:
```powershell
python app.py
```
Then open your web browser at:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

**Web Dashboard Features & Tabs**:
1. **📊 Overview**: Real-time KPI counter cards, interactive Chart.js bar and donut charts, salary tiers, and formula tooltips.
2. **🏛️ Department Analysis**: Visual cards and comparison matrix for all academic branches.
3. **💰 Package & Salary**: Full statistical metrics breakdown (Mean, Median, Std Dev, Q1, Q3, IQR) and recruiting company averages.
4. **💡 Skill Demand**: Interactive skill cloud, ranking matrix, and real-time skill search filter.
5. **🎓 Students & Placements**: Interactive searchable directory, department/eligibility filters, **Add New Student Modal** (to register students into the cohort with custom eligibility and skills), and **Record Placement Offer Modal** (to record placements for eligible students).
6. **📈 Matplotlib Visuals**: Built-in gallery viewing original high-res Python-generated figures.
7. **🔄 Re-Seed Data**: One-click action to reset and generate fresh fictional data.
8. **📥 Download Report**: Instantly download the formatted text summary report.

### Method 2: Instant Automated Run (CLI)
Runs data seeding, outputs all 4 reports, generates charts, and exports summary files:
```powershell
python main.py --run-all
```

### Method 3: Interactive CLI Menu Mode
Launch the interactive CLI menu:
```powershell
python main.py
```

---

## 6. Switching from SQLite to MySQL 8.0

To run directly against a live MySQL 8.0 server:
1. Open `config.py` and set:
   ```python
   DB_ENGINE = "mysql"
   MYSQL_CONFIG = {
       "host": "localhost",
       "port": 3306,
       "user": "root",
       "password": "YOUR_MYSQL_PASSWORD",
       "database": "placement_db",
   }
   ```
2. In MySQL Workbench or MySQL CLI, create the database:
   ```sql
   SOURCE schema.sql;
   ```
3. Run data seeding into MySQL:
   ```powershell
   python seed_data.py
   ```

