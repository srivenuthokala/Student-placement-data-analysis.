/**
 * EduPlace Analytics - Client JavaScript Logic
 * Handles interactive tabs, Chart.js visualizations, live REST API calls,
 * filtering/search, and placement record submissions.
 */

// Global Chart Instances
let chartDeptRateInstance = null;
let chartCohortStatusInstance = null;
let chartSalaryTiersInstance = null;
let chartTopSkillsInstance = null;
let chartPackageDistCurveInstance = null;

// Global Cache
let cachedStudents = [];
let cachedSkills = [];

document.addEventListener("DOMContentLoaded", () => {
    initNavigationTabs();
    initModals();
    initEventListeners();
    loadAllDashboardData();
});

/* ==========================================================================
   Navigation Tabs
   ========================================================================== */
function initNavigationTabs() {
    const tabLinks = document.querySelectorAll(".tab-link");
    const tabViews = document.querySelectorAll(".tab-view");

    tabLinks.forEach(link => {
        link.addEventListener("click", () => {
            const targetId = link.getAttribute("data-target");

            // Update Tab Link States
            tabLinks.forEach(tl => {
                tl.classList.remove("active");
                tl.setAttribute("aria-selected", "false");
            });
            link.classList.add("active");
            link.setAttribute("aria-selected", "true");

            // Update Tab View Visibility
            tabViews.forEach(view => {
                view.classList.remove("active");
                if (view.id === targetId) {
                    view.classList.add("active");
                }
            });

            // Trigger chart resize if needed
            window.dispatchEvent(new Event("resize"));
        });
    });
}

/* ==========================================================================
   Data Fetching Pipeline
   ========================================================================== */
async function loadAllDashboardData() {
    try {
        await Promise.all([
            fetchSummaryKPIs(),
            fetchDepartmentAnalytics(),
            fetchPackageAnalytics(),
            fetchSkillDemand(),
            fetchStudentsDirectory()
        ]);
    } catch (err) {
        console.error("Error loading dashboard data:", err);
        showToast("Error connecting to server. Please check backend.", "error");
    }
}

/* ==========================================================================
   1. KPI Summary & Overview Tab
   ========================================================================== */
async function fetchSummaryKPIs() {
    const res = await fetch("/api/summary");
    const data = await res.json();

    // Fill KPI Elements
    document.getElementById("kpiPlacementRate").textContent = `${data.placement_rate_pct}%`;
    document.getElementById("kpiEligibleDenominator").textContent = data.total_eligible_denominator;
    document.getElementById("kpiUniquePlaced").textContent = data.unique_students_placed;
    document.getElementById("kpiTotalOffers").textContent = data.total_offers_received;
    document.getElementById("kpiDuplicateOffers").textContent = data.duplicate_offers_count;

    const pkg = data.package_stats || {};
    document.getElementById("kpiAvgPackage").textContent = pkg.Mean ? `${pkg.Mean} LPA` : "-- LPA";
    document.getElementById("kpiMedianPackage").textContent = pkg.Median ? `${pkg.Median} LPA` : "-- LPA";
    document.getElementById("kpiMaxPackage").textContent = pkg.Max ? `${pkg.Max} LPA` : "-- LPA";

    document.getElementById("kpiEligibleCount").textContent = data.total_eligible_denominator;
    document.getElementById("kpiTotalEnrolled").textContent = data.total_enrolled;
    document.getElementById("kpiIneligibleCount").textContent = data.total_ineligible;

    // Render Cohort Status Donut Chart
    renderCohortStatusChart(data);
}

function renderCohortStatusChart(data) {
    const ctx = document.getElementById("chartCohortStatus");
    if (!ctx) return;

    if (chartCohortStatusInstance) chartCohortStatusInstance.destroy();

    chartCohortStatusInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: [
                `Placed Eligible (${data.unique_students_placed})`,
                `Unplaced Eligible (${data.unplaced_eligible})`,
                `Ineligible (${data.total_ineligible})`
            ],
            datasets: [{
                data: [
                    data.unique_students_placed,
                    data.unplaced_eligible,
                    data.total_ineligible
                ],
                backgroundColor: [
                    "rgba(16, 185, 129, 0.85)",
                    "rgba(245, 158, 11, 0.85)",
                    "rgba(244, 63, 94, 0.85)"
                ],
                borderColor: "#0f172a",
                borderWidth: 2,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: "#94a3b8", font: { family: "'Plus Jakarta Sans', sans-serif", size: 12 } }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const val = context.raw;
                            const total = data.total_enrolled;
                            const pct = ((val / total) * 100).toFixed(1);
                            return ` ${context.label}: ${val} students (${pct}%)`;
                        }
                    }
                }
            },
            cutout: "68%"
        }
    });
}

/* ==========================================================================
   2. Department Analytics Tab
   ========================================================================== */
async function fetchDepartmentAnalytics() {
    const res = await fetch("/api/departments");
    const departments = await res.json();

    // Render Overview Dept Rate Bar Chart
    renderDepartmentRateChart(departments);

    // Populate Department Cards
    const cardsGrid = document.getElementById("deptCardsGrid");
    cardsGrid.innerHTML = departments.map(d => `
        <div class="dept-card">
            <div class="dept-card-header">
                <span class="dept-card-title">${d.Department}</span>
                <span class="dept-card-rate">${d["Placement Rate (%)"]}%</span>
            </div>
            <div class="dept-stat-row">
                <span>Eligible Denominator:</span>
                <strong>${d["Eligible (Denominator)"]} / ${d.Enrolled}</strong>
            </div>
            <div class="dept-stat-row">
                <span>Unique Placed:</span>
                <strong>${d["Placed Students"]}</strong>
            </div>
            <div class="dept-stat-row">
                <span>Total Offers:</span>
                <strong>${d["Total Offers"]}</strong>
            </div>
            <div class="dept-stat-row">
                <span>Avg Package:</span>
                <strong style="color: var(--accent-cyan)">${d["Avg Package (LPA (Lakhs Per Annum - INR))"]} LPA</strong>
            </div>
            <div class="dept-stat-row">
                <span>Highest Offer:</span>
                <strong style="color: var(--accent-emerald)">${d["Max Package (LPA (Lakhs Per Annum - INR))"]} LPA</strong>
            </div>
        </div>
    `).join("");

    // Populate Department Summary Table
    const tbody = document.getElementById("departmentTableBody");
    tbody.innerHTML = departments.map(d => `
        <tr>
            <td><strong>${d.Department}</strong></td>
            <td>${d.Enrolled}</td>
            <td><span class="status-pill status-eligible">${d["Eligible (Denominator)"]}</span></td>
            <td><span class="status-pill status-placed">${d["Placed Students"]}</span></td>
            <td><strong style="color: var(--accent-emerald)">${d["Placement Rate (%)"]}%</strong></td>
            <td>${d["Total Offers"]}</td>
            <td><strong>${d["Avg Package (LPA (Lakhs Per Annum - INR))"]} LPA</strong></td>
            <td>${d["Max Package (LPA (Lakhs Per Annum - INR))"]} LPA</td>
            <td>${d["Min Package (LPA (Lakhs Per Annum - INR))"]} LPA</td>
        </tr>
    `).join("");
}

function renderDepartmentRateChart(departments) {
    const ctx = document.getElementById("chartDeptRate");
    if (!ctx) return;

    if (chartDeptRateInstance) chartDeptRateInstance.destroy();

    const labels = departments.map(d => d.Department);
    const rates = departments.map(d => d["Placement Rate (%)"]);

    chartDeptRateInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Placement Rate (%)",
                data: rates,
                backgroundColor: [
                    "rgba(99, 102, 241, 0.8)",
                    "rgba(6, 182, 212, 0.8)",
                    "rgba(16, 185, 129, 0.8)",
                    "rgba(245, 158, 11, 0.8)",
                    "rgba(168, 85, 247, 0.8)"
                ],
                borderColor: [
                    "#6366f1",
                    "#06b6d4",
                    "#10b981",
                    "#f59e0b",
                    "#a855f7"
                ],
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#94a3b8", callback: val => `${val}%` }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: "#cbd5e1", font: { size: 11, weight: "bold" } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ` Placement Rate: ${ctx.raw}%`
                    }
                }
            }
        }
    });
}

/* ==========================================================================
   3. Package & Salary Analytics Tab
   ========================================================================== */
async function fetchPackageAnalytics() {
    const res = await fetch("/api/packages");
    const data = await res.json();

    const stats = data.all_offers_summary || {};
    const tiers = data.salary_tiers || {};

    // Render Stat Boxes
    const statBoxes = document.getElementById("salaryStatBoxes");
    statBoxes.innerHTML = `
        <div class="stat-box">
            <div class="stat-box-title">Mean Package</div>
            <div class="stat-box-value" style="color: var(--accent-cyan);">${stats.Mean || "--"} <span style="font-size: 0.85rem;">LPA</span></div>
        </div>
        <div class="stat-box">
            <div class="stat-box-title">Median Package</div>
            <div class="stat-box-value" style="color: var(--accent-emerald);">${stats.Median || "--"} <span style="font-size: 0.85rem;">LPA</span></div>
        </div>
        <div class="stat-box">
            <div class="stat-box-title">Std Deviation</div>
            <div class="stat-box-value">${stats["Std Dev"] || "--"}</div>
        </div>
        <div class="stat-box">
            <div class="stat-box-title">Interquartile Range (IQR)</div>
            <div class="stat-box-value">${stats.IQR || "--"} <span style="font-size: 0.85rem;">LPA</span></div>
        </div>
        <div class="stat-box">
            <div class="stat-box-title">25th Percentile (Q1)</div>
            <div class="stat-box-value">${stats["25th Percentile (Q1)"] || "--"} <span style="font-size: 0.85rem;">LPA</span></div>
        </div>
        <div class="stat-box">
            <div class="stat-box-title">75th Percentile (Q3)</div>
            <div class="stat-box-value">${stats["75th Percentile (Q3)"] || "--"} <span style="font-size: 0.85rem;">LPA</span></div>
        </div>
        <div class="stat-box">
            <div class="stat-box-title">Min - Max Range</div>
            <div class="stat-box-value">${stats.Min || "--"} - ${stats.Max || "--"} <span style="font-size: 0.85rem;">LPA</span></div>
        </div>
    `;

    // Render Salary Tiers Chart on Overview Tab
    renderSalaryTiersChart(tiers);

    // Render Package Distribution Curve
    renderPackageDistCurve(data.raw_packages || []);

    // Render Recruiting Companies Table
    const compBody = document.getElementById("companiesTableBody");
    const companies = data.companies || [];
    compBody.innerHTML = companies.map(c => `
        <tr>
            <td><strong>${c.company}</strong></td>
            <td><span class="status-pill status-eligible">${c.count}</span></td>
            <td><strong>${Number(c.mean).toFixed(2)} LPA</strong></td>
            <td><strong style="color: var(--accent-emerald)">${Number(c.max).toFixed(2)} LPA</strong></td>
        </tr>
    `).join("");
}

function renderSalaryTiersChart(tiers) {
    const ctx = document.getElementById("chartSalaryTiers");
    if (!ctx) return;

    if (chartSalaryTiersInstance) chartSalaryTiersInstance.destroy();

    const labels = Object.keys(tiers);
    const counts = Object.values(tiers);

    chartSalaryTiersInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Number of Offers",
                data: counts,
                backgroundColor: [
                    "rgba(168, 85, 247, 0.85)", // Super Dream
                    "rgba(6, 182, 212, 0.85)",  // Dream
                    "rgba(59, 130, 246, 0.85)", // Standard
                    "rgba(148, 163, 184, 0.6)"  // Entry
                ],
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#94a3b8" }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: "#cbd5e1" }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function renderPackageDistCurve(packages) {
    const ctx = document.getElementById("chartPackageDistCurve");
    if (!ctx || packages.length === 0) return;

    if (chartPackageDistCurveInstance) chartPackageDistCurveInstance.destroy();

    // Group into histogram bins (e.g. 3-6, 6-9, 9-12, etc.)
    const binSize = 3;
    const maxPkg = Math.ceil(Math.max(...packages) / binSize) * binSize;
    const bins = {};

    for (let b = 3; b <= maxPkg; b += binSize) {
        bins[`${b}-${b + binSize} LPA`] = 0;
    }

    packages.forEach(p => {
        const binStart = Math.floor(p / binSize) * binSize;
        const key = `${binStart}-${binStart + binSize} LPA`;
        if (bins[key] !== undefined) {
            bins[key]++;
        } else {
            bins[`${binStart}-${binStart + binSize} LPA`] = 1;
        }
    });

    chartPackageDistCurveInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels: Object.keys(bins),
            datasets: [{
                label: "Offers Frequency Density",
                data: Object.values(bins),
                fill: true,
                backgroundColor: "rgba(99, 102, 241, 0.2)",
                borderColor: "#6366f1",
                tension: 0.35,
                pointBackgroundColor: "#06b6d4",
                pointRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#94a3b8" }
                },
                x: {
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#cbd5e1" }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

/* ==========================================================================
   4. Skill Demand Hub Tab
   ========================================================================== */
async function fetchSkillDemand() {
    const res = await fetch("/api/skills");
    cachedSkills = await res.json();

    // Render Overview Top Skills Chart
    renderTopSkillsChart(cachedSkills.slice(0, 8));

    // Render Skill Tags Cloud
    const tagsCloud = document.getElementById("skillTagsCloud");
    tagsCloud.innerHTML = cachedSkills.map(s => `
        <div class="skill-tag" onclick="filterSkillsByTag('${s.Skill}')">
            <span>${s.Skill}</span>
            <span class="skill-tag-count">${s["Placed Students"]} placed</span>
        </div>
    `).join("");

    renderSkillsTable(cachedSkills);
}

function renderTopSkillsChart(topSkills) {
    const ctx = document.getElementById("chartTopSkills");
    if (!ctx) return;

    if (chartTopSkillsInstance) chartTopSkillsInstance.destroy();

    const labels = topSkills.map(s => s.Skill);
    const placedCounts = topSkills.map(s => s["Placed Students"]);

    chartTopSkillsInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Placed Students Possessing Skill",
                data: placedCounts,
                backgroundColor: "rgba(6, 182, 212, 0.8)",
                borderColor: "#06b6d4",
                borderRadius: 5
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#94a3b8" }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: "#cbd5e1", font: { weight: "bold" } }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function renderSkillsTable(skills) {
    const tbody = document.getElementById("skillsTableBody");
    tbody.innerHTML = skills.map(s => {
        let tierBadge = `<span class="status-pill status-eligible">High Demand</span>`;
        if (s["Placed Students"] >= 20) {
            tierBadge = `<span class="status-pill status-placed">Critical Core</span>`;
        } else if (s["Placed Students"] < 10) {
            tierBadge = `<span class="status-pill status-unplaced">Niche / Specialized</span>`;
        }

        return `
            <tr>
                <td><strong>${s.Skill}</strong></td>
                <td>${s["Students with Skill"]}</td>
                <td><strong style="color: var(--accent-cyan);">${s["Placed Students"]}</strong></td>
                <td>${s["Placement Success Rate (%)"]}%</td>
                <td><strong>${s["Avg Package (LPA (Lakhs Per Annum - INR))"]} LPA</strong></td>
                <td>${tierBadge}</td>
            </tr>
        `;
    }).join("");
}

function filterSkillsByTag(skillName) {
    const searchInput = document.getElementById("skillSearchInput");
    searchInput.value = skillName;
    const filtered = cachedSkills.filter(s => s.Skill.toLowerCase().includes(skillName.toLowerCase()));
    renderSkillsTable(filtered);
}

/* ==========================================================================
   5. Students Directory & Offers Tab
   ========================================================================== */
async function fetchStudentsDirectory() {
    const res = await fetch("/api/students");
    cachedStudents = await res.json();

    // Populate student modal select dropdown
    const selectStudent = document.getElementById("selectStudent");
    selectStudent.innerHTML = `<option value="">-- Choose Eligible Student --</option>` +
        cachedStudents
            .filter(s => s.is_eligible === 1)
            .map(s => `<option value="${s.student_id}">${s.roll_no} - ${s.name} (${s.department}, CGPA: ${s.cgpa})</option>`)
            .join("");

    renderStudentsTable(cachedStudents);
}

function renderStudentsTable(students) {
    const tbody = document.getElementById("studentsTableBody");
    const countSpan = document.getElementById("filteredStudentCount");
    countSpan.textContent = students.length;

    if (students.length === 0) {
        tbody.innerHTML = `<tr><td colspan="11" class="text-center" style="padding: 2rem; color: var(--text-muted);">No matching student records found.</td></tr>`;
        return;
    }

    tbody.innerHTML = students.map(s => {
        const eligPill = s.is_eligible === 1
            ? `<span class="status-pill status-eligible">Eligible</span>`
            : `<span class="status-pill status-ineligible">Ineligible</span>`;

        const statusPill = s.placement_status === "Placed"
            ? `<span class="status-pill status-placed">Placed</span>`
            : `<span class="status-pill status-unplaced">Unplaced</span>`;

        const highestPkg = s.highest_package > 0 ? `${s.highest_package} LPA` : "--";
        const offersCount = s.total_offers > 1
            ? `<strong style="color: var(--accent-purple)">${s.total_offers} (Multi)</strong>`
            : s.total_offers;

        return `
            <tr>
                <td>#${s.student_id}</td>
                <td><code>${s.roll_no}</code></td>
                <td><strong>${s.name}</strong></td>
                <td>${s.department}</td>
                <td><strong>${s.cgpa}</strong></td>
                <td>${eligPill}</td>
                <td>${statusPill}</td>
                <td>${offersCount}</td>
                <td><strong style="color: var(--accent-emerald);">${highestPkg}</strong></td>
                <td><span style="font-size: 0.8rem; color: var(--text-secondary);">${s.companies}</span></td>
                <td><span style="font-size: 0.78rem; color: var(--text-muted);">${s.skills}</span></td>
            </tr>
        `;
    }).join("");
}

/* ==========================================================================
   Filtering & Event Listeners
   ========================================================================== */
function initEventListeners() {
    // Student Filters
    const deptSelect = document.getElementById("filterDepartment");
    const statusSelect = document.getElementById("filterStatus");
    const studentSearch = document.getElementById("studentSearchInput");

    function applyStudentFilters() {
        const dept = deptSelect.value;
        const status = statusSelect.value;
        const query = studentSearch.value.trim().toLowerCase();

        const filtered = cachedStudents.filter(s => {
            const matchesDept = (dept === "ALL" || s.department === dept);
            let matchesStatus = true;
            if (status === "Placed") matchesStatus = (s.placement_status === "Placed");
            else if (status === "Unplaced") matchesStatus = (s.placement_status === "Unplaced");
            else if (status === "Eligible") matchesStatus = (s.is_eligible === 1);
            else if (status === "Ineligible") matchesStatus = (s.is_eligible === 0);

            const matchesQuery = !query ||
                s.name.toLowerCase().includes(query) ||
                s.roll_no.toLowerCase().includes(query) ||
                (s.companies && s.companies.toLowerCase().includes(query)) ||
                (s.skills && s.skills.toLowerCase().includes(query));

            return matchesDept && matchesStatus && matchesQuery;
        });

        renderStudentsTable(filtered);
    }

    deptSelect.addEventListener("change", applyStudentFilters);
    statusSelect.addEventListener("change", applyStudentFilters);
    studentSearch.addEventListener("input", applyStudentFilters);

    // Skill Filter
    const skillSearch = document.getElementById("skillSearchInput");
    skillSearch.addEventListener("input", () => {
        const query = skillSearch.value.trim().toLowerCase();
        const filtered = cachedSkills.filter(s => s.Skill.toLowerCase().includes(query));
        renderSkillsTable(filtered);
    });

    // Re-Seed Data Button
    const btnSeed = document.getElementById("btnSeedData");
    btnSeed.addEventListener("click", async () => {
        if (!confirm("Reset database with fresh realistic fictional records? This will update all placement data.")) return;
        btnSeed.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Seeding...`;
        btnSeed.disabled = true;

        try {
            const res = await fetch("/api/seed", { method: "POST" });
            const data = await res.json();
            if (data.success) {
                showToast("Database successfully re-seeded with fresh records!", "success");
                await loadAllDashboardData();
                refreshMatplotlibImages();
            } else {
                showToast(data.error || "Failed to seed data.", "error");
            }
        } catch (e) {
            showToast("Server error during re-seeding.", "error");
        } finally {
            btnSeed.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> <span>Re-Seed Data</span>`;
            btnSeed.disabled = false;
        }
    });

    // Refresh Matplotlib Charts Gallery Button
    const btnRefreshCharts = document.getElementById("btnRefreshMatplotlibCharts");
    if (btnRefreshCharts) {
        btnRefreshCharts.addEventListener("click", () => {
            refreshMatplotlibImages();
            showToast("Matplotlib figures reloaded.", "success");
        });
    }
}

function refreshMatplotlibImages() {
    const timestamp = new Date().getTime();
    const imgs = ["imgDeptChart", "imgPkgChart", "imgSkillChart", "imgStatusChart"];
    imgs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            const src = el.src.split("?")[0];
            el.src = `${src}?t=${timestamp}`;
        }
    });
}

/* ==========================================================================
   Modals & Form Submissions
   ========================================================================== */
function initModals() {
    const placementModal = document.getElementById("placementModal");
    const btnOpenPlacement = document.getElementById("btnOpenPlacementModal");
    const btnClosePlacement = document.getElementById("btnClosePlacementModal");
    const btnCancelPlacement = document.getElementById("btnCancelPlacementModal");
    const formRecordPlacement = document.getElementById("recordPlacementForm");

    // Default today date
    const dateInput = document.getElementById("inputPlacementDate");
    if (dateInput) dateInput.value = new Date().toISOString().split("T")[0];

    btnOpenPlacement.addEventListener("click", () => {
        placementModal.classList.add("open");
        placementModal.setAttribute("aria-hidden", "false");
    });

    function closePlacementModal() {
        placementModal.classList.remove("open");
        placementModal.setAttribute("aria-hidden", "true");
        formRecordPlacement.reset();
        if (dateInput) dateInput.value = new Date().toISOString().split("T")[0];
    }

    btnClosePlacement.addEventListener("click", closePlacementModal);
    btnCancelPlacement.addEventListener("click", closePlacementModal);

    // Form Submit
    formRecordPlacement.addEventListener("submit", async (e) => {
        e.preventDefault();
        const studentId = document.getElementById("selectStudent").value;
        const company = document.getElementById("inputCompany").value.trim();
        const role = document.getElementById("inputRole").value.trim();
        const pkgVal = parseFloat(document.getElementById("inputPackage").value);
        const placementDate = document.getElementById("inputPlacementDate").value;
        const status = document.getElementById("selectOfferStatus").value;

        if (!studentId || !company || !role || isNaN(pkgVal) || pkgVal <= 0) {
            showToast("Please fill all required fields correctly.", "error");
            return;
        }

        const submitBtn = document.getElementById("btnSubmitPlacement");
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Saving...`;

        try {
            const res = await fetch("/api/record-placement", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    student_id: studentId,
                    company: company,
                    role: role,
                    package: pkgVal,
                    placement_date: placementDate,
                    status: status
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast(data.message, "success");
                closePlacementModal();
                await loadAllDashboardData();
                refreshMatplotlibImages();
            } else {
                showToast(data.error || "Failed to record placement.", "error");
            }
        } catch (err) {
            showToast("Network error submitting placement.", "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="fa-solid fa-check"></i> Save Placement Record`;
        }
    });

    // Image Modal
    const imgModal = document.getElementById("imageModal");
    const btnCloseImg = document.getElementById("btnCloseImageModal");
    btnCloseImg.addEventListener("click", () => {
        imgModal.classList.remove("open");
    });

    /* ==========================================================================
       Student Registration Modal Logic
       ========================================================================== */
    const studentModal = document.getElementById("studentModal");
    const btnOpenStudent = document.getElementById("btnOpenStudentModal");
    const btnCloseStudent = document.getElementById("btnCloseStudentModal");
    const btnCancelStudent = document.getElementById("btnCancelStudentModal");
    const formAddStudent = document.getElementById("addStudentForm");
    const skillsGrid = document.getElementById("modalSkillsCheckboxGrid");
    const btnAddCustomSkill = document.getElementById("btnAddCustomSkill");
    const inputCustomSkill = document.getElementById("inputCustomSkill");

    async function populateSkillsGrid() {
        if (!skillsGrid) return;
        try {
            const res = await fetch("/api/available-skills");
            const skillsList = await res.json();
            skillsGrid.innerHTML = skillsList.map(skill => `
                <label class="skill-checkbox-label">
                    <input type="checkbox" name="studentSkill" value="${skill}">
                    <span>${skill}</span>
                </label>
            `).join("");
        } catch (err) {
            console.error("Error fetching skills catalog:", err);
        }
    }

    if (btnOpenStudent) {
        btnOpenStudent.addEventListener("click", () => {
            studentModal.classList.add("open");
            studentModal.setAttribute("aria-hidden", "false");
            populateSkillsGrid();
        });
    }

    function closeStudentModal() {
        if (studentModal) {
            studentModal.classList.remove("open");
            studentModal.setAttribute("aria-hidden", "true");
            formAddStudent.reset();
        }
    }

    if (btnCloseStudent) btnCloseStudent.addEventListener("click", closeStudentModal);
    if (btnCancelStudent) btnCancelStudent.addEventListener("click", closeStudentModal);

    if (btnAddCustomSkill && inputCustomSkill) {
        btnAddCustomSkill.addEventListener("click", () => {
            const newSkill = inputCustomSkill.value.trim();
            if (!newSkill) return;

            // Check if already in grid
            const existing = Array.from(skillsGrid.querySelectorAll("input")).map(cb => cb.value.toLowerCase());
            if (existing.includes(newSkill.toLowerCase())) {
                showToast(`Skill '${newSkill}' is already in list.`, "error");
                return;
            }

            const label = document.createElement("label");
            label.className = "skill-checkbox-label";
            label.innerHTML = `
                <input type="checkbox" name="studentSkill" value="${newSkill}" checked>
                <span>${newSkill}</span>
            `;
            skillsGrid.prepend(label);
            inputCustomSkill.value = "";
        });
    }

    // Auto-adjust eligibility dropdown based on CGPA input
    const inputCGPA = document.getElementById("inputStudentCGPA");
    const selectElig = document.getElementById("selectStudentEligibility");
    if (inputCGPA && selectElig) {
        inputCGPA.addEventListener("input", () => {
            const val = parseFloat(inputCGPA.value);
            if (!isNaN(val)) {
                if (val < 6.0) {
                    selectElig.value = "0"; // Ineligible
                } else {
                    selectElig.value = "1"; // Eligible
                }
            }
        });
    }

    // Add Student Form Submission
    if (formAddStudent) {
        formAddStudent.addEventListener("submit", async (e) => {
            e.preventDefault();
            const name = document.getElementById("inputStudentName").value.trim();
            const rollNo = document.getElementById("inputStudentRollNo").value.trim();
            const department = document.getElementById("selectStudentDept").value;
            const gradYear = parseInt(document.getElementById("inputGradYear").value, 10);
            const cgpa = parseFloat(document.getElementById("inputStudentCGPA").value);
            const isEligible = parseInt(document.getElementById("selectStudentEligibility").value, 10);

            // Collect checked skills
            const checkedSkills = Array.from(skillsGrid.querySelectorAll("input[name='studentSkill']:checked"))
                .map(cb => cb.value);

            if (!name || !rollNo || !department || isNaN(cgpa)) {
                showToast("Please fill all required student fields correctly.", "error");
                return;
            }

            const submitBtn = document.getElementById("btnSubmitStudent");
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Registering...`;

            try {
                const res = await fetch("/api/add-student", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        name: name,
                        roll_no: rollNo,
                        department: department,
                        graduation_year: gradYear,
                        cgpa: cgpa,
                        is_eligible: isEligible,
                        skills: checkedSkills
                    })
                });

                const data = await res.json();
                if (data.success) {
                    showToast(data.message, "success");
                    closeStudentModal();
                    await loadAllDashboardData();
                    refreshMatplotlibImages();
                } else {
                    showToast(data.error || "Failed to add student.", "error");
                }
            } catch (err) {
                showToast("Network error registering student.", "error");
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<i class="fa-solid fa-check"></i> Register Student`;
            }
        });
    }

    // Close on outside click
    window.addEventListener("click", (e) => {
        if (e.target === studentModal) closeStudentModal();
        if (e.target === placementModal) closePlacementModal();
        if (e.target === imgModal) imgModal.classList.remove("open");
    });
}

function openImageModal(imgSrc, title) {
    const imgModal = document.getElementById("imageModal");
    const fullImg = document.getElementById("fullPreviewImage");
    const modalTitle = document.getElementById("imageModalTitle");

    modalTitle.textContent = title;
    fullImg.src = imgSrc;
    imgModal.classList.add("open");
}

/* ==========================================================================
   Toast Notification Helper
   ========================================================================== */
function showToast(message, type = "success") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    const icon = type === "success" ? "fa-circle-check" : "fa-circle-exclamation";
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
