"""
Configuration Module for Student Placement Data Analysis System.
Supports dual-mode: 'sqlite' (zero-setup local file) or 'mysql' (MySQL 8.0 server).
"""
import os

# Database Engine Selection: 'sqlite' or 'mysql'
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite")

# SQLite Configuration (Default for out-of-the-box execution)
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "placement_system.db")

# MySQL Configuration (Update with your MySQL credentials when using DB_ENGINE='mysql')
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "placement_db"),
}

# Standard Business Definitions & Acceptance Criteria
PACKAGE_UNIT = "LPA (Lakhs Per Annum - INR)"
TARGET_GRADUATION_YEAR = 2025
CHARTS_DIR = os.path.join(os.path.dirname(__file__), "charts")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
