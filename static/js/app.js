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

/**
 * Universal HTML escape helper to prevent XSS and rendering breakages.
 */
function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

document.addEventListener("DOMContentLoaded", () => {
    initThemeToggle();
    initNavigationTabs();
    initModals();
    initEventListeners();
    loadAllDashboardData();
});

/* ==========================================================================
   Theme Switcher (Dark Mode / Light Mode)
   ========================================================================== */
function initThemeToggle() {
    const toggleBtn = document.getElementById("themeToggleBtn");
    if (!toggleBtn) return;

    function updateThemeUI(theme) {
        const icon = toggleBtn.querySelector("i");
        const label = toggleBtn.querySelector(".theme-toggle-text");
        if (theme === "dark") {
            if (icon) icon.className = "fa-solid fa-sun";
            if (label) label.textContent = "Light Mode";
            toggleBtn.setAttribute("title", "Switch to Light Mode");
        } else {
            if (icon) icon.className = "fa-solid fa-moon";
            if (label) label.textContent = "Dark Mode";
            toggleBtn.setAttribute("title", "Switch to Dark Mode");
        }
        if (window.Chart) {
            Chart.defaults.color = theme === "dark" ? "#94a3b8" : "#64748b";
            Chart.defaults.borderColor = theme === "dark" ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)";
        }
    }

    const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
    updateThemeUI(currentTheme);

    toggleBtn.addEventListener("click", () => {
        const active = document.documentElement.getAttribute("data-theme") || "light";
        const nextTheme = active === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", nextTheme);
        localStorage.setItem("eduplace_theme", nextTheme);
        updateThemeUI(nextTheme);
        window.dispatchEvent(new Event("resize"));
    });
}

/* ==========================================================================
   Navigation Tabs
   ========================================================================== */
function initNavigationTabs() {
    const navButtons = document.querySelectorAll(".sidebar-tab-btn, .tab-link");
    const tabViews = document.querySelectorAll(".tab-view");
    const breadcrumb = document.getElementById("activeBreadcrumb");

    window.switchDashboardTab = function(targetId) {
        if (!targetId) return;

        let matchedBtn = null;
        navButtons.forEach(btn => {
            if (btn.getAttribute("data-target") === targetId) {
                btn.classList.add("active");
                btn.setAttribute("aria-selected", "true");
                matchedBtn = btn;
            } else {
                btn.classList.remove("active");
                btn.setAttribute("aria-selected", "false");
            }
        });

        tabViews.forEach(view => {
            if (view.id === targetId) {
                view.classList.add("active");
            } else {
                view.classList.remove("active");
            }
        });

        if (breadcrumb && matchedBtn) {
            const span = matchedBtn.querySelector("span");
            if (span) breadcrumb.textContent = span.textContent;
        }

        if (targetId === "view-students" && (!cachedStudents || cachedStudents.length === 0)) {
            fetchStudentsDirectory();
        }

        try {
            history.replaceState(null, "", `#${targetId}`);
        } catch (e) {}

        window.dispatchEvent(new Event("resize"));
    };

    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            if (targetId) window.switchDashboardTab(targetId);
        });
    });

    // Check if initial hash matches a view
    const initialHash = window.location.hash.replace("#", "");
    if (initialHash && document.getElementById(initialHash)) {
        window.switchDashboardTab(initialHash);
    }
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
            fetchStudentsDirectory(),
            fetchCompanyPartners(),
            fetchCompaniesList(),
            fetchPlacementDrives(),
            fetchApplications(),
            fetchEligibilityRules(),
            fetchUsersList(),
            fetchAuditLogs()
        ]);
    } catch (err) {
        console.error("Error loading dashboard data:", err);
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
    try {
        const res = await fetch("/api/departments");
        const departments = await res.json();

        // Render Overview Dept Rate Bar Chart
        renderDepartmentRateChart(departments);

        // Populate Department Cards
        const cardsGrid = document.getElementById("deptCardsGrid");
        if (cardsGrid) {
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
                        <strong style="color: var(--royal-600)">${d["Avg Package (LPA (Lakhs Per Annum - INR))"]} LPA</strong>
                    </div>
                    <div class="dept-stat-row">
                        <span>Highest Offer:</span>
                        <strong style="color: var(--emerald-600)">${d["Max Package (LPA (Lakhs Per Annum - INR))"]} LPA</strong>
                    </div>
                </div>
            `).join("");
        }

        // Populate Department Summary Table
        const tbody = document.getElementById("departmentTableBody");
        if (tbody) {
            tbody.innerHTML = departments.map(d => `
                <tr>
                    <td><strong>${d.Department}</strong></td>
                    <td>${d.Enrolled}</td>
                    <td><span class="status-pill status-eligible">${d["Eligible (Denominator)"]}</span></td>
                    <td><span class="status-pill status-placed">${d["Placed Students"]}</span></td>
                    <td><strong style="color: var(--emerald-600)">${d["Placement Rate (%)"]}%</strong></td>
                    <td>${d["Total Offers"]}</td>
                    <td><strong>${d["Avg Package (LPA (Lakhs Per Annum - INR))"]} LPA</strong></td>
                    <td>${d["Max Package (LPA (Lakhs Per Annum - INR))"]} LPA</td>
                    <td>${d["Min Package (LPA (Lakhs Per Annum - INR))"]} LPA</td>
                </tr>
            `).join("");
        }
    } catch (e) {
        console.error("Error in fetchDepartmentAnalytics:", e);
    }
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
    try {
        const res = await fetch("/api/packages");
        const data = await res.json();

        const stats = data.all_offers_summary || {};
        const tiers = data.salary_tiers || {};

        // Render Stat Boxes
        const statBoxes = document.getElementById("salaryStatBoxes");
        if (statBoxes) {
            statBoxes.innerHTML = `
                <div class="stat-box">
                    <div class="stat-box-title">Mean Package</div>
                    <div class="stat-box-value" style="color: var(--royal-600);">${stats.Mean || "--"} <span style="font-size: 0.8rem;">LPA</span></div>
                </div>
                <div class="stat-box">
                    <div class="stat-box-title">Median Package</div>
                    <div class="stat-box-value" style="color: var(--emerald-600);">${stats.Median || "--"} <span style="font-size: 0.8rem;">LPA</span></div>
                </div>
                <div class="stat-box">
                    <div class="stat-box-title">Std Deviation</div>
                    <div class="stat-box-value">${stats["Std Dev"] || "--"}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-box-title">Interquartile Range</div>
                    <div class="stat-box-value" style="color: #7c3aed;">${stats.IQR || "--"} <span style="font-size: 0.8rem;">LPA</span></div>
                </div>
                <div class="stat-box">
                    <div class="stat-box-title">25th Percentile (Q1)</div>
                    <div class="stat-box-value">${stats["25th Percentile (Q1)"] || "--"} <span style="font-size: 0.8rem;">LPA</span></div>
                </div>
                <div class="stat-box">
                    <div class="stat-box-title">75th Percentile (Q3)</div>
                    <div class="stat-box-value">${stats["75th Percentile (Q3)"] || "--"} <span style="font-size: 0.8rem;">LPA</span></div>
                </div>
                <div class="stat-box">
                    <div class="stat-box-title">Min - Max Range</div>
                    <div class="stat-box-value" style="font-size: 1.15rem;">${stats.Min || "--"} - ${stats.Max || "--"} <span style="font-size: 0.8rem;">LPA</span></div>
                </div>
            `;
        }

        // Render Salary Tiers Chart on Overview Tab
        renderSalaryTiersChart(tiers);

        // Render Salary Tiers Chart on Salary Tab
        renderSalaryTiersPackageTab(tiers);

        // Render Package Distribution Curve
        renderPackageDistCurve(data.raw_packages || []);

        // Render Recruiting Companies Table
        const compBody = document.getElementById("companiesTableBody");
        const companies = data.companies || [];
        if (compBody) {
            compBody.innerHTML = companies.map(c => `
                <tr>
                    <td>
                        <div style="display: flex; align-items: center; gap: 0.65rem;">
                            <div class="partner-icon-wrap" style="width: 32px; height: 32px; font-size: 1rem;">
                                <i class="${c.icon || 'fa-solid fa-building'}"></i>
                            </div>
                            <div>
                                <strong>${c.company}</strong>
                                <span style="display: block; font-size: 0.72rem; color: var(--slate-500);">${c.category || 'Recruiter'}</span>
                            </div>
                        </div>
                    </td>
                    <td><span class="partner-tier-badge ${c.badge_class || 'badge-secondary'}">${c.tier || 'Partner'}</span></td>
                    <td><strong style="color: var(--royal-600); font-size: 0.95rem;">${c.count} Offers</strong></td>
                    <td><strong>${Number(c.mean).toFixed(2)} LPA</strong></td>
                    <td><strong style="color: var(--emerald-600); font-size: 0.95rem;">${Number(c.max).toFixed(2)} LPA</strong></td>
                    <td><span class="status-pill status-placed"><i class="fa-solid fa-circle-check"></i> Active</span></td>
                </tr>
            `).join("");
        }
    } catch (e) {
        console.error("Error in fetchPackageAnalytics:", e);
    }
}

/* ==========================================================================
   Company Recruitment Partners Showcase
   ========================================================================== */
async function fetchCompanyPartners() {
    try {
        const res = await fetch("/api/company-partners");
        const data = await res.json();

        // 1. Company Partners Showcase Grid
        const grid = document.getElementById("companyPartnersGrid");
        if (grid && data.partners) {
            grid.innerHTML = data.partners.map(p => `
                <div class="partner-card">
                    <div class="partner-card-header">
                        <div class="partner-icon-wrap">
                            <i class="${p.icon}"></i>
                        </div>
                        <div>
                            <span class="partner-name">${p.company}</span>
                            <span class="partner-category">${p.category}</span>
                        </div>
                        <span class="partner-tier-badge ${p.badge_class}">${p.tier}</span>
                    </div>
                    <div class="partner-stats-grid">
                        <div class="p-stat">
                            <span class="p-stat-label">Offers</span>
                            <strong class="p-stat-val text-royal">${p.total_hires}</strong>
                        </div>
                        <div class="p-stat">
                            <span class="p-stat-label">Highest</span>
                            <strong class="p-stat-val text-emerald">${p.max_package} <span style="font-size: 0.65rem;">LPA</span></strong>
                        </div>
                        <div class="p-stat">
                            <span class="p-stat-label">Average</span>
                            <strong class="p-stat-val text-navy">${p.avg_package} <span style="font-size: 0.65rem;">LPA</span></strong>
                        </div>
                    </div>
                    <div class="partner-roles-list">
                        ${p.roles.slice(0, 2).map(r => `<span class="partner-role-tag">${r}</span>`).join("")}
                    </div>
                </div>
            `).join("");
        }

        // 2. Recent Placement Stream Table
        const recentBody = document.getElementById("recentPlacementsTableBody");
        if (recentBody && data.recent_placements) {
            recentBody.innerHTML = data.recent_placements.map(item => `
                <tr>
                    <td><code>${item.roll_no}</code></td>
                    <td><strong>${item.name}</strong></td>
                    <td><span style="font-size: 0.82rem; color: var(--slate-600);">${item.department}</span></td>
                    <td>
                        <strong class="student-name-text"><i class="fa-solid fa-briefcase" style="color: var(--royal-600); margin-right: 4px;"></i> ${item.company}</strong>
                    </td>
                    <td>${item.role}</td>
                    <td><strong style="color: var(--emerald-600); font-size: 0.92rem;">${item.package} LPA</strong></td>
                    <td>${item.placement_date || '--'}</td>
                    <td><span class="status-pill status-placed">${item.status || 'Accepted'}</span></td>
                </tr>
            `).join("");
        }
    } catch (e) {
        console.error("Error in fetchCompanyPartners:", e);
    }
}

let chartSalaryTiersPackageTabInstance = null;
function renderSalaryTiersPackageTab(tiers) {
    const ctx = document.getElementById("chartSalaryTiersPackageTab");
    if (!ctx) return;

    if (chartSalaryTiersPackageTabInstance) chartSalaryTiersPackageTabInstance.destroy();

    const labels = Object.keys(tiers);
    const counts = Object.values(tiers);

    chartSalaryTiersPackageTabInstance = new Chart(ctx, {
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
                    grid: { color: "rgba(15, 23, 42, 0.06)" },
                    ticks: { color: "#64748b" }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: "#334155", font: { weight: "bold" } }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
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
    try {
        const res = await fetch("/api/skills");
        cachedSkills = await res.json();

        // Render Overview Top Skills Chart
        renderTopSkillsChart(cachedSkills.slice(0, 8));

        // Render Skill Tags Cloud
        const tagsCloud = document.getElementById("skillTagsCloud");
        if (tagsCloud) {
            tagsCloud.innerHTML = cachedSkills.map(s => `
                <div class="skill-tag" onclick="filterSkillsByTag('${s.Skill}')">
                    <span>${s.Skill}</span>
                    <span class="skill-tag-count">${s["Placed Students"]} placed</span>
                </div>
            `).join("");
        }

        renderSkillsTable(cachedSkills);
    } catch (e) {
        console.error("Error in fetchSkillDemand:", e);
    }
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
    if (!tbody) return;
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
                <td><strong style="color: var(--royal-600); font-size: 0.95rem;">${s["Placed Students"]}</strong></td>
                <td><strong>${s["Placement Success Rate (%)"]}%</strong></td>
                <td><strong style="color: var(--emerald-600);">${s["Avg Package (LPA (Lakhs Per Annum - INR))"]} LPA</strong></td>
                <td>${tierBadge}</td>
            </tr>
        `;
    }).join("");
}

function filterSkillsByTag(skillName) {
    const searchInput = document.getElementById("skillSearchInput");
    if (searchInput) searchInput.value = skillName;
    const filtered = cachedSkills.filter(s => s.Skill.toLowerCase().includes(skillName.toLowerCase()));
    renderSkillsTable(filtered);
}

/* ==========================================================================
   5. Students Directory & Offers Tab
   ========================================================================== */
async function fetchStudentsDirectory() {
    try {
        const res = await fetch("/api/students");
        if (!res.ok) {
            throw new Error(`Server returned HTTP ${res.status}`);
        }
        cachedStudents = await res.json();

        // Populate student modal select dropdown
        const selectStudent = document.getElementById("selectStudent");
        if (selectStudent && Array.isArray(cachedStudents)) {
            selectStudent.innerHTML = `<option value="">-- Choose Eligible Student --</option>` +
                cachedStudents
                    .filter(s => s.is_eligible === 1)
                    .map(s => `<option value="${s.student_id}">${escapeHtml(s.roll_no)} - ${escapeHtml(s.name)} (${escapeHtml(s.department)}, CGPA: ${s.cgpa || '--'})</option>`)
                    .join("");
        }

        renderStudentsTable(cachedStudents);
    } catch (err) {
        console.error("Error loading students directory:", err);
        const tbody = document.getElementById("studentsTableBody");
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="12" class="text-center" style="padding: 2.5rem; color: var(--rose-600);"><i class="fa-solid fa-triangle-exclamation" style="font-size: 1.5rem; display: block; margin-bottom: 0.5rem;"></i>Failed to load students: ${escapeHtml(err.message || err)}</td></tr>`;
        }
    }
}

function renderStudentsTable(students) {
    const tbody = document.getElementById("studentsTableBody");
    const countSpan = document.getElementById("filteredStudentCount");
    if (countSpan) countSpan.textContent = Array.isArray(students) ? students.length : 0;

    if (!tbody) return;

    if (!Array.isArray(students) || students.length === 0) {
        tbody.innerHTML = `<tr><td colspan="12" class="text-center" style="padding: 2.5rem; color: var(--slate-500);"><i class="fa-solid fa-users-slash" style="font-size: 1.5rem; display: block; margin-bottom: 0.5rem; opacity: 0.5;"></i>No matching student records found.</td></tr>`;
        return;
    }

    tbody.innerHTML = students.map(s => {
        const isLateral = (s.admission_type && s.admission_type.toLowerCase() === "lateral entry");
        const typeBadge = isLateral
            ? `<span class="badge-lateral" title="Direct 2nd Year Entry"><i class="fa-solid fa-user-graduate"></i> Lateral Entry</span>`
            : `<span class="badge-regular" title="Regular 4-Year Admission"><i class="fa-solid fa-graduation-cap"></i> Regular</span>`;

        let eligBadge = `<span class="badge-pending">Pending</span>`;
        if (s.placement_eligibility === "Eligible" || s.is_eligible === 1) {
            eligBadge = `<span class="status-pill status-eligible">Eligible</span>`;
        } else if (s.placement_eligibility === "Not Eligible" || s.is_eligible === 0) {
            eligBadge = `<span class="status-pill status-ineligible">Ineligible</span>`;
        }

        let statusBadge = `<span class="status-pill status-unplaced">Unplaced</span>`;
        if (s.placement_status === "Placed" || (s.total_offers && s.total_offers > 0)) {
            statusBadge = `<span class="status-pill status-placed">Placed</span>`;
        } else if (s.placement_status === "Pending") {
            statusBadge = `<span class="badge-pending">Pending</span>`;
        }

        const highestPkg = (s.highest_package && Number(s.highest_package) > 0) ? `${Number(s.highest_package).toFixed(2)} LPA` : "--";
        const offersCount = (s.total_offers > 1)
            ? `<strong style="color: var(--royal-600);">${s.total_offers} (Multi)</strong>`
            : ((s.total_offers > 0) ? `<strong style="color: var(--emerald-600);">1 Offer</strong>` : "0");

        const yearSec = `${s.year_of_study || '4th Year'} (${s.section || 'A'})`;
        const backlogsBadge = (s.backlogs !== undefined && s.backlogs > 0)
            ? `<strong style="color: var(--rose-600);">${s.backlogs}</strong>`
            : `<span style="color: var(--emerald-600);">0</span>`;

        const cgpaFormatted = (s.cgpa !== null && s.cgpa !== undefined && !isNaN(Number(s.cgpa)))
            ? Number(s.cgpa).toFixed(2)
            : "--";

        return `
            <tr>
                <td><code>${escapeHtml(s.roll_no)}</code></td>
                <td>
                    <div class="student-name-text" style="font-weight: 700;">${escapeHtml(s.name)}</div>
                    <div style="font-size: 0.75rem; color: var(--slate-500); margin-top: 2px;">${escapeHtml(s.email || '')}</div>
                </td>
                <td>${typeBadge}</td>
                <td>${escapeHtml(s.department)}</td>
                <td><span style="font-size: 0.82rem; font-weight: 600;">${escapeHtml(yearSec)}</span></td>
                <td><strong>${cgpaFormatted}</strong></td>
                <td>${backlogsBadge}</td>
                <td>${eligBadge}</td>
                <td>${statusBadge}</td>
                <td>${offersCount}</td>
                <td><strong style="color: var(--emerald-600);">${highestPkg}</strong></td>
                <td style="text-align: center;">
                    <div class="table-actions-cell" style="justify-content: center;">
                        <button type="button" class="btn-table-action btn-view" onclick="openViewProfileModal(${s.student_id})" title="View Full Profile Dossier">
                            <i class="fa-solid fa-eye"></i>
                        </button>
                        <button type="button" class="btn-table-action btn-edit" onclick="openEditStudentModal(${s.student_id})" title="Edit Student Details">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                        <button type="button" class="btn-table-action btn-offer" onclick="openQuickPlacementModal(${s.student_id})" title="Add Corporate Offer">
                            <i class="fa-solid fa-plus"></i>
                        </button>
                        <button type="button" class="btn-table-action btn-delete" onclick="openDeleteStudentModal(${s.student_id})" title="Delete Student Record">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                </td>
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
    const typeSelect = document.getElementById("filterAdmissionType");
    const statusSelect = document.getElementById("filterStatus");
    const studentSearch = document.getElementById("studentSearchInput");

    function applyStudentFilters() {
        const dept = deptSelect ? deptSelect.value : "ALL";
        const admType = typeSelect ? typeSelect.value : "ALL";
        const status = statusSelect ? statusSelect.value : "ALL";
        const query = studentSearch ? studentSearch.value.trim().toLowerCase() : "";

        const filtered = (cachedStudents || []).filter(s => {
            const matchesDept = (dept === "ALL" || s.department === dept);

            let matchesType = true;
            if (admType !== "ALL") {
                const sType = (s.admission_type || "Regular").toLowerCase();
                matchesType = (sType === admType.toLowerCase());
            }

            let matchesStatus = true;
            if (status === "Placed") matchesStatus = (s.placement_status === "Placed" || (s.total_offers && s.total_offers > 0));
            else if (status === "Unplaced") matchesStatus = (s.placement_status === "Unplaced" && (!s.total_offers || s.total_offers === 0));
            else if (status === "Eligible") matchesStatus = (s.placement_eligibility === "Eligible" || s.is_eligible === 1);
            else if (status === "Ineligible") matchesStatus = (s.placement_eligibility === "Not Eligible" || s.is_eligible === 0);
            else if (status === "Pending") matchesStatus = (s.placement_eligibility === "Pending" || s.placement_status === "Pending");

            const matchesQuery = !query ||
                (s.name && s.name.toLowerCase().includes(query)) ||
                (s.roll_no && s.roll_no.toLowerCase().includes(query)) ||
                (s.department && s.department.toLowerCase().includes(query)) ||
                (s.diploma_college && s.diploma_college.toLowerCase().includes(query)) ||
                (s.diploma_qualification && s.diploma_qualification.toLowerCase().includes(query)) ||
                (s.companies && s.companies.toLowerCase().includes(query)) ||
                (s.skills && s.skills.toLowerCase().includes(query));

            return matchesDept && matchesType && matchesStatus && matchesQuery;
        });

        renderStudentsTable(filtered);
    }

    if (deptSelect) deptSelect.addEventListener("change", applyStudentFilters);
    if (typeSelect) typeSelect.addEventListener("change", applyStudentFilters);
    if (statusSelect) statusSelect.addEventListener("change", applyStudentFilters);
    if (studentSearch) studentSearch.addEventListener("input", applyStudentFilters);

    // Skill Filter
    const skillSearch = document.getElementById("skillSearchInput");
    if (skillSearch) {
        skillSearch.addEventListener("input", () => {
            const query = skillSearch.value.trim().toLowerCase();
            const filtered = cachedSkills.filter(s => s.Skill.toLowerCase().includes(query));
            renderSkillsTable(filtered);
        });
    }

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
       Student Registration & Lateral Entry Modal Logic
       ========================================================================== */
    const studentModal = document.getElementById("studentModal");
    const btnOpenStudent = document.getElementById("btnOpenStudentModal");
    const btnOpenLateral = document.getElementById("btnOpenLateralModal");
    const btnCloseStudent = document.getElementById("btnCloseStudentModal");
    const btnCancelStudent = document.getElementById("btnCancelStudentModal");
    const formAddStudent = document.getElementById("addStudentForm");
    const skillsGrid = document.getElementById("modalSkillsCheckboxGrid");
    const btnAddCustomSkill = document.getElementById("btnAddCustomSkill");
    const inputCustomSkill = document.getElementById("inputCustomSkill");

    const radioRegular = document.getElementById("radioTypeRegular");
    const radioLateral = document.getElementById("radioTypeLateral");
    const tabLabelRegular = document.getElementById("tabLabelRegular");
    const tabLabelLateral = document.getElementById("tabLabelLateral");
    const lateralFieldsBox = document.getElementById("lateralEntryFieldsBox");
    const inputAdmissionType = document.getElementById("inputAdmissionType");
    const selectYearOfStudy = document.getElementById("selectYearOfStudy");

    function setAdmissionTypeUI(type) {
        if (!inputAdmissionType) return;
        inputAdmissionType.value = type;
        if (type === "Lateral Entry") {
            if (radioLateral) radioLateral.checked = true;
            if (tabLabelLateral) {
                tabLabelLateral.style.background = "#7c3aed";
                tabLabelLateral.style.color = "#fff";
            }
            if (tabLabelRegular) {
                tabLabelRegular.style.background = "transparent";
                tabLabelRegular.style.color = "var(--slate-700)";
            }
            if (lateralFieldsBox) lateralFieldsBox.style.display = "block";
            if (selectYearOfStudy && selectYearOfStudy.value === "4th Year") {
                selectYearOfStudy.value = "2nd Year";
            }
        } else {
            if (radioRegular) radioRegular.checked = true;
            if (tabLabelRegular) {
                tabLabelRegular.style.background = "var(--royal-600)";
                tabLabelRegular.style.color = "#fff";
            }
            if (tabLabelLateral) {
                tabLabelLateral.style.background = "transparent";
                tabLabelLateral.style.color = "var(--slate-700)";
            }
            if (lateralFieldsBox) lateralFieldsBox.style.display = "none";
            if (selectYearOfStudy && selectYearOfStudy.value === "2nd Year") {
                selectYearOfStudy.value = "4th Year";
            }
        }
    }

    if (radioRegular && tabLabelRegular) {
        tabLabelRegular.addEventListener("click", () => setAdmissionTypeUI("Regular"));
    }
    if (radioLateral && tabLabelLateral) {
        tabLabelLateral.addEventListener("click", () => setAdmissionTypeUI("Lateral Entry"));
    }

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
            if (studentModal) {
                studentModal.classList.add("open");
                studentModal.setAttribute("aria-hidden", "false");
                setAdmissionTypeUI("Regular");
                populateSkillsGrid();
            }
        });
    }

    if (btnOpenLateral) {
        btnOpenLateral.addEventListener("click", () => {
            if (studentModal) {
                studentModal.classList.add("open");
                studentModal.setAttribute("aria-hidden", "false");
                setAdmissionTypeUI("Lateral Entry");
                populateSkillsGrid();
            }
        });
    }

    function closeStudentModal() {
        if (studentModal) {
            studentModal.classList.remove("open");
            studentModal.setAttribute("aria-hidden", "true");
            if (formAddStudent) formAddStudent.reset();
            setAdmissionTypeUI("Regular");
        }
    }

    if (btnCloseStudent) btnCloseStudent.addEventListener("click", closeStudentModal);
    if (btnCancelStudent) btnCancelStudent.addEventListener("click", closeStudentModal);

    if (btnAddCustomSkill && inputCustomSkill) {
        btnAddCustomSkill.addEventListener("click", () => {
            const newSkill = inputCustomSkill.value.trim();
            if (!newSkill) return;

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
                    selectElig.value = "Not Eligible";
                } else {
                    selectElig.value = "Eligible";
                }
            }
        });
    }

    // Add Student Form Submission
    if (formAddStudent) {
        formAddStudent.addEventListener("submit", async (e) => {
            e.preventDefault();
            const rollNo = document.getElementById("inputStudentRollNo").value.trim().toUpperCase();
            const name = document.getElementById("inputStudentName").value.trim();
            const admissionType = inputAdmissionType ? inputAdmissionType.value : "Regular";
            const department = document.getElementById("selectStudentDept").value;
            const yearOfStudy = document.getElementById("selectYearOfStudy").value;
            const section = document.getElementById("inputSection").value.trim() || "A";
            const academicYear = document.getElementById("inputAcademicYear").value.trim() || "2024-2025";
            const email = document.getElementById("inputStudentEmail").value.trim();
            const mobile = document.getElementById("inputStudentMobile").value.trim();
            const dob = document.getElementById("inputStudentDOB").value;
            const gender = document.getElementById("selectStudentGender").value;
            const cgpa = parseFloat(document.getElementById("inputStudentCGPA").value);
            const backlogs = parseInt(document.getElementById("inputBacklogs").value, 10) || 0;
            const eligibility = document.getElementById("selectStudentEligibility").value;
            const placementStatus = document.getElementById("selectInitialPlacementStatus").value;

            // Lateral Entry Details
            const diplomaQual = document.getElementById("inputDiplomaQual") ? document.getElementById("inputDiplomaQual").value.trim() : "";
            const diplomaPct = document.getElementById("inputDiplomaPct") ? document.getElementById("inputDiplomaPct").value.trim() : "";
            const diplomaCollege = document.getElementById("inputDiplomaCollege") ? document.getElementById("inputDiplomaCollege").value.trim() : "";
            const lateralAdmYear = document.getElementById("inputLateralAdmissionYear") ? document.getElementById("inputLateralAdmissionYear").value.trim() : "2022";

            const checkedSkills = skillsGrid
                ? Array.from(skillsGrid.querySelectorAll("input[name='studentSkill']:checked")).map(cb => cb.value)
                : [];

            if (!rollNo || !name || !department || isNaN(cgpa)) {
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
                        roll_no: rollNo,
                        name: name,
                        admission_type: admissionType,
                        department: department,
                        year_of_study: yearOfStudy,
                        section: section,
                        academic_year: academicYear,
                        email: email,
                        mobile: mobile,
                        dob: dob,
                        gender: gender,
                        cgpa: cgpa,
                        backlogs: backlogs,
                        placement_eligibility: eligibility,
                        placement_status: placementStatus,
                        diploma_qualification: diplomaQual,
                        diploma_percentage: diplomaPct ? parseFloat(diplomaPct) : null,
                        diploma_college: diplomaCollege,
                        admission_year: parseInt(lateralAdmYear, 10) || 2022,
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
                submitBtn.innerHTML = `<i class="fa-solid fa-check"></i> Save Student Record`;
            }
        });
    }

    /* ==========================================================================
       Edit Student Modal Logic
       ========================================================================== */
    const editModal = document.getElementById("editStudentModal");
    const btnCloseEdit = document.getElementById("btnCloseEditStudentModal");
    const btnCancelEdit = document.getElementById("btnCancelEditStudentModal");
    const formEditStudent = document.getElementById("editStudentForm");

    function closeEditModal() {
        if (editModal) {
            editModal.classList.remove("open");
            editModal.setAttribute("aria-hidden", "true");
            if (formEditStudent) formEditStudent.reset();
        }
    }

    if (btnCloseEdit) btnCloseEdit.addEventListener("click", closeEditModal);
    if (btnCancelEdit) btnCancelEdit.addEventListener("click", closeEditModal);

    if (formEditStudent) {
        formEditStudent.addEventListener("submit", async (e) => {
            e.preventDefault();
            const studentId = document.getElementById("editStudentId").value;
            const rollNo = document.getElementById("editStudentRollNo").value.trim().toUpperCase();
            const name = document.getElementById("editStudentName").value.trim();
            const admissionType = document.getElementById("editAdmissionType").value;
            const department = document.getElementById("editStudentDept").value;
            const yearOfStudy = document.getElementById("editYearOfStudy").value;
            const section = document.getElementById("editSection").value.trim() || "A";
            const email = document.getElementById("editEmail").value.trim();
            const mobile = document.getElementById("editMobile").value.trim();
            const dob = document.getElementById("editDOB").value;
            const gender = document.getElementById("editGender").value;
            const cgpa = parseFloat(document.getElementById("editCGPA").value);
            const backlogs = parseInt(document.getElementById("editBacklogs").value, 10) || 0;
            const eligibility = document.getElementById("editPlacementEligibility").value;
            const placementStatus = document.getElementById("editPlacementStatus").value;

            const diplomaQual = document.getElementById("editDiplomaQual") ? document.getElementById("editDiplomaQual").value.trim() : "";
            const diplomaPct = document.getElementById("editDiplomaPct") ? document.getElementById("editDiplomaPct").value.trim() : "";
            const diplomaCollege = document.getElementById("editDiplomaCollege") ? document.getElementById("editDiplomaCollege").value.trim() : "";
            const admYear = document.getElementById("editAdmissionYear") ? document.getElementById("editAdmissionYear").value.trim() : "";

            const submitBtn = document.getElementById("btnSubmitEditStudent");
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Saving...`;

            try {
                const res = await fetch(`/api/student/${studentId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        roll_no: rollNo,
                        name: name,
                        admission_type: admissionType,
                        department: department,
                        year_of_study: yearOfStudy,
                        section: section,
                        email: email,
                        mobile: mobile,
                        dob: dob,
                        gender: gender,
                        cgpa: cgpa,
                        backlogs: backlogs,
                        placement_eligibility: eligibility,
                        placement_status: placementStatus,
                        diploma_qualification: diplomaQual,
                        diploma_percentage: diplomaPct ? parseFloat(diplomaPct) : null,
                        diploma_college: diplomaCollege,
                        admission_year: admYear ? parseInt(admYear, 10) : 2021
                    })
                });

                const data = await res.json();
                if (data.success) {
                    showToast(data.message, "success");
                    closeEditModal();
                    await loadAllDashboardData();
                    refreshMatplotlibImages();
                } else {
                    showToast(data.error || "Failed to update student.", "error");
                }
            } catch (err) {
                showToast("Network error updating student.", "error");
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<i class="fa-solid fa-check"></i> Save Changes`;
            }
        });
    }

    /* ==========================================================================
       View Profile Dossier Modal Logic
       ========================================================================== */
    const viewProfileModal = document.getElementById("viewProfileModal");
    const btnCloseViewProfile = document.getElementById("btnCloseViewProfileModal");
    const btnDoneViewProfile = document.getElementById("btnDoneViewProfile");

    function closeViewProfileModal() {
        if (viewProfileModal) {
            viewProfileModal.classList.remove("open");
            viewProfileModal.setAttribute("aria-hidden", "true");
        }
    }

    if (btnCloseViewProfile) btnCloseViewProfile.addEventListener("click", closeViewProfileModal);
    if (btnDoneViewProfile) btnDoneViewProfile.addEventListener("click", closeViewProfileModal);

    /* ==========================================================================
       Delete Student Confirmation Modal Logic
       ========================================================================== */
    const deleteModal = document.getElementById("deleteStudentModal");
    const btnCloseDelete = document.getElementById("btnCloseDeleteStudentModal");
    const btnCancelDelete = document.getElementById("btnCancelDeleteModal");
    const btnConfirmDelete = document.getElementById("btnConfirmDeleteStudent");

    function closeDeleteModal() {
        if (deleteModal) {
            deleteModal.classList.remove("open");
            deleteModal.setAttribute("aria-hidden", "true");
        }
    }

    if (btnCloseDelete) btnCloseDelete.addEventListener("click", closeDeleteModal);
    if (btnCancelDelete) btnCancelDelete.addEventListener("click", closeDeleteModal);

    if (btnConfirmDelete) {
        btnConfirmDelete.addEventListener("click", async () => {
            const studentId = document.getElementById("deleteStudentId").value;
            if (!studentId) return;

            btnConfirmDelete.disabled = true;
            btnConfirmDelete.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Archiving &amp; Deleting...`;

            try {
                const res = await fetch(`/api/student/${studentId}`, { method: "DELETE" });
                const data = await res.json();
                if (data.success) {
                    showToast(data.message, "success");
                    closeDeleteModal();
                    await loadAllDashboardData();
                    refreshMatplotlibImages();
                } else {
                    showToast(data.error || "Failed to delete student.", "error");
                }
            } catch (err) {
                showToast("Network error deleting student.", "error");
            } finally {
                btnConfirmDelete.disabled = false;
                btnConfirmDelete.innerHTML = `<i class="fa-solid fa-trash-can"></i> Yes, Delete &amp; Archive Record`;
            }
        });
    }

    /* ==========================================================================
       Bulk Student Upload Modal Logic
       ========================================================================== */
    const bulkModal = document.getElementById("bulkUploadModal");
    const btnOpenBulk = document.getElementById("btnOpenBulkUploadModal");
    const btnCloseBulk = document.getElementById("btnCloseBulkUploadModal");
    const btnCancelBulk = document.getElementById("btnCancelBulkUpload");
    const btnDoneBulk = document.getElementById("btnDoneBulkUpload");
    const bulkForm = document.getElementById("bulkUploadForm");
    const bulkFileInput = document.getElementById("bulkFileInput");
    const bulkDropzone = document.getElementById("bulkDropzone");
    const selectedNotice = document.getElementById("selectedFileNotice");
    const btnSubmitBulk = document.getElementById("btnSubmitBulkUpload");
    const bulkResultsPanel = document.getElementById("bulkUploadResults");

    function closeBulkModal() {
        if (bulkModal) {
            bulkModal.classList.remove("open");
            bulkModal.setAttribute("aria-hidden", "true");
            if (bulkForm) bulkForm.reset();
            if (selectedNotice) { selectedNotice.style.display = "none"; selectedNotice.textContent = ""; }
            if (btnSubmitBulk) btnSubmitBulk.disabled = true;
            if (bulkResultsPanel) bulkResultsPanel.style.display = "none";
        }
    }

    if (btnOpenBulk) {
        btnOpenBulk.addEventListener("click", () => {
            if (bulkModal) {
                bulkModal.classList.add("open");
                bulkModal.setAttribute("aria-hidden", "false");
                if (bulkResultsPanel) bulkResultsPanel.style.display = "none";
            }
        });
    }

    if (btnCloseBulk) btnCloseBulk.addEventListener("click", closeBulkModal);
    if (btnCancelBulk) btnCancelBulk.addEventListener("click", closeBulkModal);
    if (btnDoneBulk) {
        btnDoneBulk.addEventListener("click", async () => {
            closeBulkModal();
            await loadAllDashboardData();
            refreshMatplotlibImages();
        });
    }

    if (bulkFileInput) {
        bulkFileInput.addEventListener("change", () => {
            if (bulkFileInput.files && bulkFileInput.files[0]) {
                const file = bulkFileInput.files[0];
                if (selectedNotice) {
                    selectedNotice.innerHTML = `<i class="fa-solid fa-file-csv"></i> Selected File: <strong>${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)`;
                    selectedNotice.style.display = "block";
                }
                if (btnSubmitBulk) btnSubmitBulk.disabled = false;
            }
        });
    }

    // Drag & Drop
    if (bulkDropzone) {
        ["dragenter", "dragover"].forEach(evt => {
            bulkDropzone.addEventListener(evt, (e) => {
                e.preventDefault();
                bulkDropzone.style.borderColor = "var(--royal-600)";
                bulkDropzone.style.background = "#e0e7ff";
            });
        });

        ["dragleave", "drop"].forEach(evt => {
            bulkDropzone.addEventListener(evt, (e) => {
                e.preventDefault();
                bulkDropzone.style.borderColor = "var(--royal-400)";
                bulkDropzone.style.background = "var(--royal-50)";
            });
        });

        bulkDropzone.addEventListener("drop", (e) => {
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
                bulkFileInput.files = e.dataTransfer.files;
                const file = e.dataTransfer.files[0];
                if (selectedNotice) {
                    selectedNotice.innerHTML = `<i class="fa-solid fa-file-csv"></i> Selected File: <strong>${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)`;
                    selectedNotice.style.display = "block";
                }
                if (btnSubmitBulk) btnSubmitBulk.disabled = false;
            }
        });
    }

    if (bulkForm) {
        bulkForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (!bulkFileInput.files || !bulkFileInput.files[0]) {
                showToast("Please choose a CSV or Excel file to upload.", "error");
                return;
            }

            const formData = new FormData();
            formData.append("file", bulkFileInput.files[0]);

            btnSubmitBulk.disabled = true;
            btnSubmitBulk.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing Spreadsheet...`;

            try {
                const res = await fetch("/api/students/bulk-upload", {
                    method: "POST",
                    body: formData
                });
                const data = await res.json();

                if (data.success) {
                    showToast(`Successfully processed: ${data.success_count} added, ${data.failed_count} failed.`, data.failed_count > 0 ? "error" : "success");

                    if (bulkResultsPanel) {
                        bulkResultsPanel.style.display = "block";
                        document.getElementById("bulkTotalParsed").textContent = data.total_records;
                        document.getElementById("bulkSuccessCount").textContent = data.success_count;
                        document.getElementById("bulkFailedCount").textContent = data.failed_count;

                        const failedContainer = document.getElementById("bulkFailedContainer");
                        const failedTbody = document.getElementById("bulkFailedTableBody");
                        if (data.failed_count > 0) {
                            failedContainer.style.display = "block";
                            failedTbody.innerHTML = data.failed_records.map(f => `
                                <tr>
                                    <td><strong>Row ${f.row}</strong></td>
                                    <td><code>${f.roll_no}</code></td>
                                    <td>${f.name}</td>
                                    <td><span style="color: var(--rose-600); font-weight: 600;">${f.error}</span></td>
                                </tr>
                            `).join("");
                        } else {
                            failedContainer.style.display = "none";
                        }
                    }
                } else {
                    showToast(data.error || "Failed to process bulk upload.", "error");
                }
            } catch (err) {
                showToast("Network error uploading spreadsheet.", "error");
            } finally {
                btnSubmitBulk.disabled = false;
                btnSubmitBulk.innerHTML = `<i class="fa-solid fa-upload"></i> Process &amp; Import Students`;
            }
        });
    }

    // Close on outside click
    window.addEventListener("click", (e) => {
        if (e.target === studentModal) closeStudentModal();
        if (e.target === placementModal) closePlacementModal();
        if (e.target === editModal) closeEditModal();
        if (e.target === viewProfileModal) closeViewProfileModal();
        if (e.target === deleteModal) closeDeleteModal();
        if (e.target === bulkModal) closeBulkModal();
        if (e.target === imgModal) imgModal.classList.remove("open");
    });
}

/* ==========================================================================
   Global Helper Functions for Table Actions (Called inline from rendered HTML)
   ========================================================================== */
window.openViewProfileModal = async function (studentId) {
    try {
        const res = await fetch(`/api/student/${studentId}`);
        const data = await res.json();
        if (!data.success) {
            showToast(data.error || "Could not fetch student dossier.", "error");
            return;
        }

        const s = data.student;
        document.getElementById("profileStudentName").textContent = s.name;
        document.getElementById("profileRollAndDept").textContent = `${s.roll_no} • ${s.department}`;
        document.getElementById("profileEmail").textContent = s.email || `${s.roll_no.toLowerCase()}@eduplace.ac.in`;
        document.getElementById("profileMobile").textContent = s.mobile || "--";
        document.getElementById("profileDOB").textContent = s.dob || "--";
        document.getElementById("profileGender").textContent = s.gender || "--";

        // Badges
        const isLateral = (s.admission_type && s.admission_type.toLowerCase() === "lateral entry");
        const admBadge = document.getElementById("profileAdmissionBadge");
        admBadge.className = isLateral ? "badge-lateral" : "badge-regular";
        admBadge.innerHTML = isLateral
            ? `<i class="fa-solid fa-user-graduate"></i> Lateral Entry`
            : `<i class="fa-solid fa-graduation-cap"></i> Regular`;

        const eligBadge = document.getElementById("profileEligibilityBadge");
        if (s.placement_eligibility === "Eligible" || s.is_eligible === 1) {
            eligBadge.className = "kpi-badge badge-success";
            eligBadge.textContent = "Eligible for Placements";
        } else if (s.placement_eligibility === "Not Eligible" || s.is_eligible === 0) {
            eligBadge.className = "kpi-badge badge-warning";
            eligBadge.style.background = "var(--rose-50)";
            eligBadge.style.color = "var(--rose-600)";
            eligBadge.textContent = "Ineligible (Academic Criteria)";
        } else {
            eligBadge.className = "kpi-badge badge-secondary";
            eligBadge.textContent = "Pending Eligibility";
        }

        const placeBadge = document.getElementById("profilePlacementBadge");
        const isPlaced = (s.total_offers > 0 || s.placement_status === "Placed");
        placeBadge.className = isPlaced ? "status-pill status-placed" : "status-pill status-unplaced";
        placeBadge.textContent = isPlaced ? "Placed" : (s.placement_status || "Unplaced");

        // Academic Stats
        document.getElementById("profileCGPA").textContent = Number(s.cgpa).toFixed(2);
        document.getElementById("profileBacklogs").textContent = s.backlogs !== undefined ? s.backlogs : 0;
        document.getElementById("profileYear").textContent = s.year_of_study || "4th Year";
        document.getElementById("profileSection").textContent = s.section || "A";
        document.getElementById("profileAcademicYear").textContent = s.academic_year || "2024-2025";
        document.getElementById("profileGradYear").textContent = s.graduation_year || 2025;

        // Lateral Entry Card
        const lateralCard = document.getElementById("profileLateralCard");
        if (isLateral) {
            lateralCard.style.display = "block";
            document.getElementById("profileDiplomaQual").textContent = s.diploma_qualification || "Diploma in " + s.department;
            document.getElementById("profileDiplomaPct").textContent = s.diploma_percentage ? `${s.diploma_percentage}%` : "--%";
            document.getElementById("profileDiplomaCollege").textContent = s.diploma_college || "Polytechnic Institute";
            document.getElementById("profileAdmYear").textContent = s.admission_year || 2022;
        } else {
            lateralCard.style.display = "none";
        }

        // Offers Table
        const offersCountBadge = document.getElementById("profileOffersCountBadge");
        offersCountBadge.textContent = `${s.total_offers} Offer(s) • Highest: ${s.highest_package > 0 ? s.highest_package + ' LPA' : '--'}`;

        const offersBody = document.getElementById("profileOffersTableBody");
        if (s.offers && s.offers.length > 0) {
            offersBody.innerHTML = s.offers.map(o => `
                <tr>
                    <td><strong>${o.company}</strong></td>
                    <td>${o.role}</td>
                    <td><strong style="color: var(--emerald-600);">${o.package} LPA</strong></td>
                    <td>${o.placement_date || '--'}</td>
                    <td><span class="status-pill status-placed">${o.status}</span></td>
                </tr>
            `).join("");
        } else {
            offersBody.innerHTML = `<tr><td colspan="5" class="text-center" style="padding: 1rem; color: var(--slate-500);">No placement offers recorded yet.</td></tr>`;
        }

        // Skills Tags
        const skillsContainer = document.getElementById("profileSkillsTags");
        if (s.skills && s.skills.length > 0) {
            skillsContainer.innerHTML = s.skills.map(sk => `<span class="kpi-badge badge-primary" style="font-size: 0.8rem; padding: 0.25rem 0.65rem;">${sk}</span>`).join("");
        } else {
            skillsContainer.innerHTML = `<span style="font-size: 0.8rem; color: var(--slate-500);">No specific technical skills recorded.</span>`;
        }

        document.getElementById("viewProfileModal").classList.add("open");
    } catch (e) {
        showToast("Error loading student dossier.", "error");
    }
};

window.openEditStudentModal = async function (studentId) {
    try {
        const res = await fetch(`/api/student/${studentId}`);
        const data = await res.json();
        if (!data.success) {
            showToast(data.error || "Could not fetch student details.", "error");
            return;
        }

        const s = data.student;
        document.getElementById("editStudentId").value = s.student_id;
        document.getElementById("editStudentRollNo").value = s.roll_no;
        document.getElementById("editStudentName").value = s.name;
        document.getElementById("editAdmissionType").value = s.admission_type || "Regular";
        document.getElementById("editStudentDept").value = s.department;
        document.getElementById("editYearOfStudy").value = s.year_of_study || "4th Year";
        document.getElementById("editSection").value = s.section || "A";
        document.getElementById("editEmail").value = s.email || "";
        document.getElementById("editMobile").value = s.mobile || "";
        document.getElementById("editDOB").value = s.dob || "2003-05-15";
        document.getElementById("editGender").value = s.gender || "Male";
        document.getElementById("editCGPA").value = s.cgpa;
        document.getElementById("editBacklogs").value = s.backlogs !== undefined ? s.backlogs : 0;
        document.getElementById("editPlacementEligibility").value = s.placement_eligibility || (s.is_eligible === 1 ? "Eligible" : "Not Eligible");
        document.getElementById("editPlacementStatus").value = s.placement_status || (s.total_offers > 0 ? "Placed" : "Unplaced");

        // Lateral entry
        document.getElementById("editDiplomaQual").value = s.diploma_qualification || "";
        document.getElementById("editDiplomaPct").value = s.diploma_percentage || "";
        document.getElementById("editDiplomaCollege").value = s.diploma_college || "";
        document.getElementById("editAdmissionYear").value = s.admission_year || (s.admission_type === "Lateral Entry" ? 2022 : 2021);

        document.getElementById("editStudentModal").classList.add("open");
    } catch (e) {
        showToast("Error opening edit form.", "error");
    }
};

window.openQuickPlacementModal = function (studentId) {
    const placementModal = document.getElementById("placementModal");
    const selectStudent = document.getElementById("selectStudent");
    if (selectStudent) {
        selectStudent.value = studentId;
    }
    if (placementModal) {
        placementModal.classList.add("open");
        placementModal.setAttribute("aria-hidden", "false");
    }
};

window.openDeleteStudentModal = function (studentId) {
    const s = cachedStudents.find(x => x.student_id === studentId);
    if (!s) return;

    document.getElementById("deleteStudentId").value = studentId;
    document.getElementById("deleteStudentRoll").textContent = s.roll_no;
    document.getElementById("deleteStudentName").textContent = s.name;
    document.getElementById("deleteStudentOffersCount").textContent = s.total_offers || 0;

    document.getElementById("deleteStudentModal").classList.add("open");
};

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

/* ==========================================================================
   Companies, Drives, Applications, Eligibility, Users & Audit Logs Handlers
   ========================================================================== */

async function fetchCompaniesList() {
    try {
        const res = await fetch("/api/companies");
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.getElementById("companiesTableBody");
        const kpiTotal = document.getElementById("kpiTotalCompanies");
        if (kpiTotal) kpiTotal.textContent = data.length || 10;
        if (tbody && data.length > 0) {
            tbody.innerHTML = data.map(c => `
                <tr>
                    <td><strong>${escapeHtml(c.name)}</strong></td>
                    <td>${escapeHtml(c.industry || "Technology")}</td>
                    <td><span class="kpi-badge ${c.tier && c.tier.includes('1') ? 'badge-success' : 'badge-primary'}">${escapeHtml(c.tier || "Tier 2")}</span></td>
                    <td>${escapeHtml(c.location || "Pan India")}</td>
                    <td><strong>${c.total_offers || 0}</strong></td>
                    <td><strong style="color: var(--royal-600);">${c.avg_package ? c.avg_package + " LPA" : "N/A"}</strong></td>
                    <td><code>${escapeHtml(c.contact_email || "-")}</code></td>
                </tr>
            `).join("");
        }
    } catch (e) {
        console.error("Error fetching companies:", e);
    }
}

async function fetchPlacementDrives() {
    try {
        const res = await fetch("/api/placement-drives");
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.getElementById("drivesTableBody");
        if (tbody && data.length > 0) {
            tbody.innerHTML = data.map(d => `
                <tr>
                    <td><strong>${escapeHtml(d.company_name)}</strong></td>
                    <td>${escapeHtml(d.role)}</td>
                    <td><strong style="color: var(--royal-600);">${d.package_lpa} LPA</strong></td>
                    <td>${escapeHtml(d.drive_date)}</td>
                    <td>${escapeHtml(d.eligible_departments || "All")}</td>
                    <td><strong>&ge; ${d.min_cgpa} CGPA</strong></td>
                    <td><span class="status-pill ${d.status === 'Active' ? 'status-eligible' : (d.status === 'Completed' ? 'status-placed' : 'badge-warning')}">${escapeHtml(d.status)}</span></td>
                    <td><strong>${d.registered_count || 0} Candidates</strong></td>
                </tr>
            `).join("");
        }
    } catch (e) {
        console.error("Error fetching drives:", e);
    }
}

async function fetchApplications() {
    try {
        const res = await fetch("/api/applications");
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.getElementById("applicationsTableBody");
        if (tbody && data.length > 0) {
            tbody.innerHTML = data.map(a => `
                <tr>
                    <td><code>${escapeHtml(a.roll_no)}</code></td>
                    <td><strong>${escapeHtml(a.student_name)}</strong></td>
                    <td>${escapeHtml(a.department)}</td>
                    <td><strong>${escapeHtml(a.company)}</strong></td>
                    <td>${escapeHtml(a.role)}</td>
                    <td><span class="badge ${a.current_round && (a.current_round.includes('HR') || a.current_round.includes('Offer')) ? 'badge-success' : 'badge-warning'}">${escapeHtml(a.current_round || "Round 1")}</span></td>
                    <td><span class="status-pill ${a.status === 'Placed' || a.status === 'Selected' ? 'status-placed' : 'status-eligible'}">${escapeHtml(a.status || "In Progress")}</span></td>
                    <td><strong>${a.package_lpa ? a.package_lpa + " LPA" : "-"}</strong></td>
                </tr>
            `).join("");
        }
    } catch (e) {
        console.error("Error fetching applications:", e);
    }
}

async function fetchEligibilityRules() {
    try {
        const res = await fetch("/api/eligibility-rules");
        if (!res.ok) return;
        const data = await res.json();
        const minCgpaInput = document.getElementById("ruleMinCgpa");
        const maxBacklogsInput = document.getElementById("ruleMaxBacklogs");
        const elEligible = document.getElementById("elCountEligible");
        const elIneligible = document.getElementById("elCountIneligible");

        if (minCgpaInput && data.min_cgpa) minCgpaInput.value = data.min_cgpa;
        if (maxBacklogsInput && data.max_backlogs !== undefined) maxBacklogsInput.value = data.max_backlogs;
        if (elEligible && data.stats) elEligible.textContent = data.stats.eligible_count;
        if (elIneligible && data.stats) elIneligible.textContent = data.stats.ineligible_count;
    } catch (e) {
        console.error("Error fetching eligibility rules:", e);
    }
}

async function handleSaveEligibility(e) {
    e.preventDefault();
    const btn = document.getElementById("btnApplyEligibility");
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Re-Calculating...';

    const minCgpa = parseFloat(document.getElementById("ruleMinCgpa").value);
    const maxBacklogs = parseInt(document.getElementById("ruleMaxBacklogs").value);

    try {
        const res = await fetch("/api/eligibility-rules", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ min_cgpa: minCgpa, max_backlogs: maxBacklogs })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            fetchEligibilityRules();
            fetchStudentsDirectory();
            fetchSummaryKPIs();
        } else {
            showToast(data.error || "Failed to update eligibility rules", "error");
        }
    } catch (err) {
        showToast("Error updating rules: " + err, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function handleSaveCompany(e) {
    e.preventDefault();
    const name = document.getElementById("compName").value;
    const industry = document.getElementById("compIndustry").value;
    const tier = document.getElementById("compTier").value;
    const email = document.getElementById("compEmail").value;
    const location = document.getElementById("compLocation").value;

    try {
        const res = await fetch("/api/companies", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, industry, tier, contact_email: email, location })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            document.getElementById("companyModal").classList.remove("open");
            document.getElementById("addCompanyForm").reset();
            fetchCompaniesList();
        } else {
            showToast(data.error || "Failed to save company", "error");
        }
    } catch (err) {
        showToast("Error: " + err, "error");
    }
}

async function handleSaveDrive(e) {
    e.preventDefault();
    const company = document.getElementById("drvCompany").value;
    const role = document.getElementById("drvRole").value;
    const pkg = parseFloat(document.getElementById("drvPackage").value);
    const date = document.getElementById("drvDate").value;
    const minCgpa = parseFloat(document.getElementById("drvMinCgpa").value);
    const depts = document.getElementById("drvDepartments").value;

    try {
        const res = await fetch("/api/placement-drives", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                company_name: company,
                role,
                package_lpa: pkg,
                drive_date: date,
                min_cgpa: minCgpa,
                eligible_departments: depts
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            document.getElementById("driveModal").classList.remove("open");
            document.getElementById("scheduleDriveForm").reset();
            fetchPlacementDrives();
        } else {
            showToast(data.error || "Failed to schedule drive", "error");
        }
    } catch (err) {
        showToast("Error: " + err, "error");
    }
}

async function handleSaveUser(e) {
    e.preventDefault();
    const code = document.getElementById("usrCode").value;
    const username = document.getElementById("usrUsername").value;
    const name = document.getElementById("usrName").value;
    const dept = document.getElementById("usrDept").value;
    const email = document.getElementById("usrEmail").value;
    const pass = document.getElementById("usrPass").value;

    try {
        const res = await fetch("/api/users", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ faculty_code: code, username, name, department: dept, email, password: pass })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            document.getElementById("userModal").classList.remove("open");
            document.getElementById("addUserForm").reset();
            fetchUsersList();
        } else {
            showToast(data.error || "Failed to create user", "error");
        }
    } catch (err) {
        showToast("Error: " + err, "error");
    }
}

async function handleSaveSettings(e) {
    e.preventDefault();
    const targetYear = document.getElementById("cfgTargetYear").value;
    const instName = document.getElementById("cfgInstName").value;
    const tpoEmail = document.getElementById("cfgTpoEmail").value;

    try {
        const res = await fetch("/api/system-settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ target_graduation_year: targetYear, institution_name: instName, contact_email: tpoEmail })
        });
        const data = await res.json();
        if (data.success) {
            showToast("System settings saved successfully.", "success");
        }
    } catch (err) {
        showToast("Error saving settings: " + err, "error");
    }
}

async function fetchUsersList() {
    try {
        const res = await fetch("/api/users");
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.getElementById("usersTableBody");
        if (tbody && data.length > 0) {
            tbody.innerHTML = data.map(u => `
                <tr>
                    <td><code>${escapeHtml(u.faculty_code)}</code></td>
                    <td><strong>${escapeHtml(u.name)}</strong></td>
                    <td><code>${escapeHtml(u.username)}</code></td>
                    <td>${escapeHtml(u.department || "-")}</td>
                    <td>${escapeHtml(u.email || "-")}</td>
                    <td><span class="role-pill role-faculty">${escapeHtml(u.username === 'faculty' ? 'Faculty Coordinator' : 'Placement Officer')}</span></td>
                    <td><span class="status-pill status-placed">Active</span></td>
                </tr>
            `).join("");
        }
    } catch (e) {
        console.error("Error fetching users:", e);
    }
}

async function fetchAuditLogs() {
    try {
        const res = await fetch("/api/audit-logs");
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.getElementById("auditLogsTableBody");
        if (tbody && data.length > 0) {
            tbody.innerHTML = data.map(l => `
                <tr>
                    <td><span style="font-family: var(--font-mono); font-size: 0.8rem;">${escapeHtml(l.created_at)}</span></td>
                    <td><span class="kpi-badge badge-primary">${escapeHtml(l.action)}</span></td>
                    <td><code>${escapeHtml(l.roll_no || '# ' + l.student_id)}</code></td>
                    <td><strong>${escapeHtml(l.performed_by)}</strong></td>
                    <td><div style="max-height: 48px; overflow-y: auto; font-family: var(--font-mono); font-size: 0.75rem; color: var(--slate-600);">${escapeHtml(l.details)}</div></td>
                </tr>
            `).join("");
        }
    } catch (e) {
        console.error("Error fetching audit logs:", e);
    }
}
