-- ============================================================================
-- Student Placement Data Analysis System - Database Schema (MySQL 8.0)
-- 
-- Definitions & Acceptance Criteria:
-- 1. Package Unit: LPA (Lakhs Per Annum in INR, e.g., 8.50 = 8.5 Lakhs/year)
-- 2. Placement Denominator: Total eligible students in cohort (is_eligible = 1)
-- 3. Duplicate Handling: Multiple offers per student allowed; placement rate
--    uses COUNT(DISTINCT student_id) among eligible students.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS placement_db;
USE placement_db;

-- 1. Students Table
DROP TABLE IF EXISTS placements;
DROP TABLE IF EXISTS student_skills;
DROP TABLE IF EXISTS skills;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    roll_no VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    graduation_year INT NOT NULL,
    cgpa DECIMAL(3, 2) NOT NULL,
    is_eligible TINYINT(1) DEFAULT 1, -- 1: Eligible for placements, 0: Ineligible
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Skills Catalog Table
CREATE TABLE skills (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(50) NOT NULL UNIQUE
);

-- 3. Student Skills Mapping Table (Many-to-Many)
CREATE TABLE student_skills (
    student_id INT NOT NULL,
    skill_id INT NOT NULL,
    PRIMARY KEY (student_id, skill_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);

-- 4. Placements Records Table (Allows multiple offers per student)
CREATE TABLE placements (
    placement_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    company VARCHAR(100) NOT NULL,
    role VARCHAR(100) NOT NULL,
    package DECIMAL(5, 2) NOT NULL, -- Stored in LPA
    placement_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Placed', -- 'Placed', 'Accepted', 'Offered'
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_student_dept ON students(department);
CREATE INDEX idx_student_grad_year ON students(graduation_year);
CREATE INDEX idx_placement_package ON placements(package);
