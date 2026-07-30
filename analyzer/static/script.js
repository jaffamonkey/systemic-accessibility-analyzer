/**
 * Systemic Accessibility Analyzer - Dashboard Client
 * 
 * This file powers the interactive frontend of the analysis dashboard.
 * It is responsible for fetching the exported JSON data payload, 
 * rendering the Business Intelligence (BI) charts using Chart.js, 
 * and handling the dynamic drill-down tables when a user clicks 
 * on a specific chart segment.
 */

let fixChart, sourceChart, componentChart, designChart, riskChart, wcagRuleChart, pageChart, toolAgreementChart, problemTypeChart;
let GLOBAL_CLUSTERS = [];
let GLOBAL_ROWS = [];

const palette = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f"];

// -------------------------
// 🗺️ ROUTING & STATIC MODE
// -------------------------

function getJobBasePath() {
    const match = window.location.pathname.match(/^\/jobs\/([^/]+)/);
    return match ? `/jobs/${match[1]}` : "";
}

const JOB_BASE_PATH = getJobBasePath();
const STATIC_ANALYSIS_PATH = JOB_BASE_PATH ? `${JOB_BASE_PATH}/data/analysis.json` : "data/analysis.json";
const STATIC_XLSX_PATH = "accessibility_analysis.xlsx";
let STATIC_MODE = !!JOB_BASE_PATH;

// -------------------------
// 🛠️ TOOL METADATA MAPS
// -------------------------

const TOOL_LEVELS = {
    "alfa": "AAA",
    "axe-scan": "AAA",
    "html-sniffer": "AAA",
    "ibm": "AA",
    "lighthouse": "AA",
    "oobee": "AA",
    "pa11y-axe": "AAA",
    "pa11y-htmlcs": "AAA",
    "uuv": "AAA",
    "axe-core": "AAA",
    "speca11y": "AAA",
    "avalpdf": "AA"
};

const ENGINE_META = {
    "axe-core": { label: "Axe", badge: "🪓", className: "engine-axe" },
    "axe-scan": { label: "Axe", badge: "🪓", className: "engine-axe" },
    "pa11y-axe": { label: "Axe", badge: "🪓", className: "engine-axe" },
    "html-sniffer": { label: "HTMLCS", badge: "🔍", className: "engine-htmlcs" },
    "htmlcs": { label: "HTMLCS", badge: "🔍", className: "engine-htmlcs" },
    "pa11y-htmlcs": { label: "HTMLCS", badge: "🔍", className: "engine-htmlcs" },
    "html codesniffer": { label: "HTMLCS", badge: "🔍", className: "engine-htmlcs" },
    "ibm": { label: "IBM", badge: "🏢", className: "engine-ibm" },
    "ibm-equal-access": { label: "IBM", badge: "🏢", className: "engine-ibm" },
    "ibm accessibility checker": { label: "IBM", badge: "🏢", className: "engine-ibm" },
    "lighthouse": { label: "Browser", badge: "💡", className: "engine-browser" },
    "uuv": { label: "UUV", badge: "🧪", className: "engine-uuv" },
    "oobee": { label: "Oobee", badge: "🧩", className: "engine-oobee" },
    "speca11y": { label: "Validator", badge: "⚖️", className: "engine-speca11y" },
    "nu html checker": { label: "Validator", badge: "⚖️", className: "engine-validator" },
    "alfa": { label: "Alfa", badge: "🧩", className: "engine-alfa" },
    "siteimprove alfa": { label: "Alfa", badge: "🧩", className: "engine-alfa" },
    "nu-html-checker": { label: "Validator", badge: "⚖️", className: "engine-validator" },
    "contrast-checker": { label: "Visual", badge: "👁️", className: "engine-visual" },
    "tab-map": { label: "Keyboard", badge: "⌨️", className: "engine-keyboard" },
    "virtual-screenreader": { label: "AT", badge: "🗣️", className: "engine-at" },
    "avalpdf": { label: "PDF", badge: "📄", className: "engine-pdf" }
};

// -------------------------
// 🎨 UI HELPERS & FORMATTERS
// -------------------------

function normalizeToolKey(source) {
    return String(source || "")
        .trim()
        .toLowerCase()
        .replace(/_/g, "-");
}

function engineBadgeFor(source) {
    const key = normalizeToolKey(source);
    return ENGINE_META[key] || { label: "Other", badge: "•", className: "engine-other" };
}

function chartToolLabel(tool) {
    const meta = engineBadgeFor(tool);
    return `${meta.badge} ${tool}`;
}

function renderEnginePill(source) {
    const meta = engineBadgeFor(source);
    return `
        <span class="engine-pill ${escapeHtml(meta.className)}" title="Engine family: ${escapeHtml(meta.label)}">
            <span class="engine-icon" aria-hidden="true">${escapeHtml(meta.badge)}</span>
            <span>${escapeHtml(meta.label)}</span>
        </span>
    `;
}

function renderToolNameWithEngine(toolName, sourceKey = toolName) {
    return `
        <span class="tool-label-with-engine">
            ${renderEnginePill(sourceKey)}
            <strong>${escapeHtml(toolName)}</strong>
        </span>
    `;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function severityBadgeClass(severity) {
    const key = String(severity || "unknown").toLowerCase();
    if (["critical", "serious", "moderate", "minor"].includes(key)) {
        return `badge-${key}`;
    }
    return "badge-unknown";
}

// -------------------------
// 🔗 NAVIGATION UPDATERS
// -------------------------

function updateSitePreviewLink(jobId) {
    const link = document.getElementById("sitePreviewLink");
    if (!link) return;
    link.href = jobId
        ? `http://127.0.0.1:8000/jobs/${encodeURIComponent(jobId)}/tab_map.html`
        : "#";
}

function updateVirtualScreenreaderLink(jobId) {
    const link = document.getElementById("virtualScreenreaderLink");
    if (!link) return;
    link.href = jobId
        ? `http://127.0.0.1:8000/jobs/${encodeURIComponent(jobId)}/virtual_screenreader.html`
        : "#";
}

function updateContrastReportLink(jobId) {
    const link = document.getElementById("contrastReportLink");
    if (!link) return;
    link.href = jobId
        ? `http://127.0.0.1:8000/jobs/${encodeURIComponent(jobId)}/contrast_report.html`
        : "#";
}

function updateTabbingOrderLink(jobId) {
    const link = document.getElementById("tabbingOrderLink");
    if (!link) return;
    link.href = jobId
        ? `http://127.0.0.1:8000/jobs/${encodeURIComponent(jobId)}/tab_map.html`
        : "#";
}

// -------------------------
// 🚀 INITIALIZATION & DATA LOADING
// -------------------------

function setStaticMode(enabled) {
    STATIC_MODE = !!enabled;
    const folderInput = document.getElementById("folder");
    const analyzeButton = document.getElementById("analyzeButton");
    const exportButton = document.getElementById("exportButton");
    const modeHint = document.getElementById("modeHint");

    if (folderInput) {
        folderInput.value = enabled ? "Prebuilt job dataset" : folderInput.value;
        folderInput.disabled = enabled;
        folderInput.style.display = enabled ? "none" : "";
    }
    if (analyzeButton) {
        analyzeButton.innerText = enabled ? "Reload Dashboard Data" : "Run Analysis";
        analyzeButton.style.display = enabled ? "none" : "";
    }
    if (exportButton) {
        exportButton.innerText = enabled ? "Download XLSX" : "Export XLSX";
    }
    if (modeHint) {
        modeHint.innerText = enabled
            ? "Static mode: this dashboard is reading prebuilt analysis data and workbook files."
            : "Enter a reports folder and run a live analysis.";
    }
}

async function loadStaticAnalysis() {
    const res = await fetch(STATIC_ANALYSIS_PATH, { cache: "no-store" });
    if (!res.ok) throw new Error(`Static analysis load failed: ${res.status}`);
    const data = await res.json();
    applyAnalysisData(data);
    updateSitePreviewLink(data.job_id);
    updateVirtualScreenreaderLink(data.job_id);
    updateTabbingOrderLink(data.job_id);
    updateContrastReportLink(data.job_id);
}

async function runAnalysis() {
    if (STATIC_MODE) {
        await loadStaticAnalysis();
        return;
    }

    const folder = document.getElementById("folder").value;

    const res = await fetch("/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder })
    });

    const data = await res.json();
    applyAnalysisData(data);
    updateSitePreviewLink(data.job_id);
    updateVirtualScreenreaderLink(data.job_id);
    updateTabbingOrderLink(data.job_id);
    updateContrastReportLink(data.job_id);
}

function applyAnalysisData(data) {
    GLOBAL_CLUSTERS = data.clusters || [];
    GLOBAL_ROWS = data.rows || [];

    updateCards(data);
    renderComponentChart(data.component_heatmap);
    renderWcagSupportPanel();
    renderDesignChart(data.design_heatmap);
    renderWCAGRuleChart(GLOBAL_CLUSTERS);
    renderPageChart(data.issuesperpage);
    renderProblemTypeChart(data.problem_types);
    renderToolAgreementChart(
        data.tool_family_agreement_profile ||
        data.tool_agreement_profile ||
        {}
    );
    renderNextBestFixes(data.next_best_fixes || [], data.next_best_fixes_summary || {});
    renderPageInventoryCheck(data.page_inventory_check || {});
    updateWCAGLevels(data.wcag_levels || {});

    // Hook up interactivity for the charts that support drill-down
    markChartInteractive("problemTypeChart", true, "Click a bar to inspect matching findings");
    markChartInteractive("componentChart", true, "Click a bar to inspect matching findings");
    markChartInteractive("wcagRuleChart", true, "Click a bar to inspect matching findings");
    markChartInteractive("pageChart", true, "Click a bar to inspect matching findings");
    markChartInteractive("toolAgreementChart", false);
    markChartInteractive("designChart", false);
}

// -------------------------
// 📊 CHART FACTORY
// -------------------------

function buildChart(id, labels, values, existing, title = "", onClickHandler = null) {
    const canvas = document.getElementById(id);
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (existing) {
        existing.data.labels = labels;
        existing.data.datasets[0].data = values;
        existing.data.datasets[0].backgroundColor =
            labels.map((_, i) => palette[i % palette.length]);

        existing.options.plugins.title.text = title;

        existing.options.onClick = (evt, elements) => {
            if (!onClickHandler || !elements.length) return;
            const index = elements[0].index;
            const label = existing.data.labels[index];
            onClickHandler(label);
        };

        existing.update();
        return existing;
    }

    return new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: labels.map((_, i) => palette[i % palette.length])
            }]
        },
        options: {
            responsive: true,
            animation: {
                duration: 600
            },
            plugins: {
                legend: { display: false },
                title: {
                    display: !!title,
                    text: title
                }
            },
            scales: {
                y: { beginAtZero: true }
            },
            onClick: (evt, elements) => {
                if (!onClickHandler || !elements.length) return;
                const index = elements[0].index;
                const label = labels[index];
                onClickHandler(label);
            }
        }
    });
}

function markChartInteractive(id, interactive, hintText = "") {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    canvas.style.cursor = interactive ? "pointer" : "default";
    canvas.title = interactive ? (hintText || "Click to inspect findings") : "";
}

// -------------------------
// 📈 DASHBOARD CARD UPDATERS
// -------------------------

function setInnerTextSafe(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerText = value;
}

function updateCards(data) {
    setInnerTextSafe("violations", data.violations || 0);
    setInnerTextSafe("pages", data.pages || 0);
    setInnerTextSafe("wcag_criteria_affected", data.distinct_wcag_criteria || 0);

    const impactVal = data.shared_pattern_impact !== undefined ? data.shared_pattern_impact : (data.design_system_impact || 0);
    setInnerTextSafe("impact", impactVal + "%");

    setInnerTextSafe("adi", data.accessibility_debt_index || 0);
    setInnerTextSafe("opportunity", (data.accessibility_opportunity_score || 0) + "%");

    setInnerTextSafe("frame_issues", (data.frame_issues || 0) + " frames");
    setInnerTextSafe("frame_pages", (data.frame_pages || 0) + " affected pages");
    setInnerTextSafe("frame_pages_list", data.frame_pages_list || "-");

    setInnerTextSafe("shared_source_rate", (data.shared_source_rate || 0) + "%");
    setInnerTextSafe("top5_page_concentration", (data.top5_page_concentration || 0) + "%");

    const top5 = (data.top5_pages_list && data.top5_pages_list.length)
        ? data.top5_pages_list.join(", ")
        : "-";
    setInnerTextSafe("top5_pages_list", top5);

    const conf = data.confidence_counts || {};
    setInnerTextSafe("conf_high", conf.high || 0);
    setInnerTextSafe("conf_medium", conf.medium || 0);
    setInnerTextSafe("conf_low", conf.low || 0);

    const cons = data.consensus_counts || {};
    setInnerTextSafe("cons_verified", cons.verified || 0);
    setInnerTextSafe("cons_likely", cons.likely || 0);
    setInnerTextSafe("cons_single", cons.single || 0);
}

function updateWCAGLevels(levels) {
    document.getElementById("wcag_a").innerText = levels.A ?? 0;
    document.getElementById("wcag_aa").innerText = levels.AA ?? 0;
    document.getElementById("wcag_aaa").innerText = levels.AAA ?? 0;
}

// -------------------------
// 📊 CHART RENDERERS
// -------------------------

function renderWcagSupportPanel() {
    const container = document.getElementById("wcagSupportPanel");
    if (!container) return;

    const rows = [
        ["Axe-core", "A/AA/some AAA", "A/AA/some AAA", "A/AA", "—", "axe-core"],
        ["Axe-scan", "A/AA/some AAA", "A/AA/some AAA", "A/AA", "—", "axe-scan"],
        ["UUV", "A/AA", "A/AA", "A/AA", "—", "uuv"],
        ["Lighthouse", "A/AA", "A/AA", "A/AA", "—", "lighthouse"],
        ["IBM Accessibility Checker", "A/AA", "A/AA", "A/AA", "—", "ibm"],
        ["Oobee", "A/AA/some AAA", "A/AA/some AAA", "Limited", "—", "oobee"],
        ["Pa11y Axe", "A/AA/AAA", "A/AA/AAA", "A/AA", "—", "pa11y-axe"],
        ["Pa11y HTMLCS", "A/AA/AAA", "A/AA/AAA", "A/AA", "—", "pa11y-htmlcs"],
        ["HTML CodeSniffer", "A/AA/AAA", "A/AA/AAA", "No", "—", "html-sniffer"],
        ["Siteimprove Alfa", "A/AA/AAA*", "A/AA/AAA*", "No", "—", "alfa"],
        ["Nu HTML Checker", "Markup / ARIA", "Markup / ARIA", "No", "—", "nu-html-checker"],
        ["SpecA11y", "A/AA/AAA", "A/AA/AAA", "A/AA/AAA", "🧪 Draft outcomes", "speca11y"]
    ];

    const html = `
        <div class="fix-table-wrap">
            <table class="fix-table">
                <thead>
                    <tr>
                        <th>Tool Framework</th>
                        <th>WCAG 2.0</th>
                        <th>WCAG 2.1</th>
                        <th>WCAG 2.2</th>
                        <th>WCAG 3 Draft</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(row => `
                        <tr>
                            <td>${renderToolNameWithEngine(row[0], row[5])}</td>
                            <td>${escapeHtml(row[1])}</td>
                            <td>${escapeHtml(row[2])}</td>
                            <td>${escapeHtml(row[3])}</td>
                            <td>${escapeHtml(row[4])}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;

    container.innerHTML = html;
}

function renderComponentChart(data) {
    const rawLabels = Object.keys(data || {});
    const displayLabels = rawLabels.map(label =>
        String(label || "")
            .replace(/_/g, " ")
            .replace(/\b\w/g, ch => ch.toUpperCase())
    );
    const values = Object.values(data || {});

    componentChart = buildChart(
        "componentChart",
        displayLabels,
        values,
        componentChart,
        "Component Heatmap",
        (label) => {
            const index = displayLabels.indexOf(label);
            const rawLabel = index >= 0 ? rawLabels[index] : label;

            const matches = GLOBAL_ROWS.filter(
                r => (r.component || "other") === rawLabel
            );
            showDrilldown("Component: " + label, matches);
        }
    );
}

function renderProblemTypeChart(data) {
    const labels = Object.keys(data || {});
    const values = Object.values(data || {});

    problemTypeChart = buildChart(
        "problemTypeChart",
        labels,
        values,
        problemTypeChart,
        "Top Problem Types",
        (label) => {
            const map = {
                "Forms": ["form", "form_field", "file_upload"],
                "Interactive": ["button", "modal", "dialog", "accordion"],
                "Navigation": ["navigation", "tabs", "breadcrumb", "link"],
                "Content": ["heading", "text", "list", "card"],
                "Media": ["image", "icon"],
                "Structure": ["layout", "table", "frame"]
            };

            const matches = GLOBAL_ROWS.filter(r => {
                const comp = (r.component || "other").toLowerCase();
                return (map[label] || []).includes(comp);
            });

            showDrilldown("Problem Type: " + label, matches);
        }
    );
}

function renderToolAgreementChart(data) {
    const profile = data || {};
    const entries = Object.entries(profile);

    const labels = entries.map(([key]) => key);
    const displayLabels = labels.map(chartToolLabel);
    const crossFamily = entries.map(([, stats]) => stats.multi_family || 0);
    const sameFamily = entries.map(([, stats]) => stats.same_family_only || 0);
    const unique = entries.map(([, stats]) => stats.unique || 0);

    const canvas = document.getElementById("toolAgreementChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    const chartData = {
        labels: displayLabels,
        datasets: [
            {
                label: "Cross-family agreement",
                data: crossFamily,
                backgroundColor: palette[0]
            },
            {
                label: "Same-family only",
                data: sameFamily,
                backgroundColor: palette[1]
            },
            {
                label: "Unique",
                data: unique,
                backgroundColor: palette[2]
            }
        ]
    };

    const chartOptions = {
        responsive: true,
        indexAxis: "y",
        plugins: {
            title: {
                display: true,
                text: "Tool Agreement Profile"
            },
            tooltip: {
                callbacks: {
                    title: (items) => {
                        const index = items?.[0]?.dataIndex ?? 0;
                        return labels[index] || items?.[0]?.label || "";
                    }
                }
            }
        },
        scales: {
            x: {
                stacked: true,
                beginAtZero: true,
                title: {
                    display: true,
                    text: "Finding count"
                }
            },
            y: {
                stacked: true
            }
        }
    };

    if (toolAgreementChart) {
        toolAgreementChart.data = chartData;
        toolAgreementChart.options = chartOptions;
        toolAgreementChart.update();
        return;
    }

    toolAgreementChart = new Chart(ctx, {
        type: "bar",
        data: chartData,
        options: chartOptions
    });
}

function renderPageChart(data) {
    const labels = Object.keys(data || {});
    const values = Object.values(data || {});

    pageChart = buildChart(
        "pageChart",
        labels,
        values,
        pageChart,
        "Issues per page",
        (label) => {
            const matches = GLOBAL_ROWS.filter(r => {
                const pageFiles = Array.isArray(r.files) ? r.files : [r.page];
                return pageFiles.includes(label);
            });
            showDrilldown(`Page: ${label}`, matches);
        }
    );
}

function renderDesignChart(data) {
    designChart = buildChart(
        "designChart",
        Object.keys(data || {}),
        Object.values(data || {}),
        designChart,
        "Shared Source Issues"
    );
}

function isValidWcagCode(value) {
    if (value === null || value === undefined) return false;
    return /^\d+\.\d+\.\d+$/.test(String(value).trim());
}

function normalizeWcagCode(value) {
    if (!value && value !== 0) return null;
    const raw = String(value).trim();
    if (isValidWcagCode(raw)) return raw;
    const match = raw.match(/\b\d+\.\d+\.\d+\b/);
    return match ? match[0] : null;
}

function renderWCAGRuleChart(clusters) {
    const counts = {};

    clusters.forEach(c => {
        const wcag = normalizeWcagCode(c.wcag);
        if (!wcag) return;
        counts[wcag] = (counts[wcag] || 0) + (c.count || 0);
    });

    const labels = Object.keys(counts);
    const values = Object.values(counts);

    wcagRuleChart = buildChart(
        "wcagRuleChart",
        labels,
        values,
        wcagRuleChart,
        "WCAG Rule Breakdown",
        (label) => {
            const targetLabel = String(label).trim();
            const matches = GLOBAL_ROWS.filter(r => {
                const rowCode = normalizeWcagCode(r.wcag || r.ruleId);
                return rowCode === label;
            });
            showDrilldown("WCAG: " + targetLabel, matches);
        }
    );
}

// -------------------------
// 🔎 DRILL-DOWN TABLES
// -------------------------

let DRILLDOWN_ITEMS = [];
let DRILLDOWN_FILTERED_ITEMS = [];
let DRILLDOWN_TITLE = "";
let DRILLDOWN_PAGE = 1;
let DRILLDOWN_PAGE_SIZE = 25;
let searchTimeout;

function showDrilldown(title, items) {
    DRILLDOWN_TITLE = title || "Details";
    DRILLDOWN_ITEMS = Array.isArray(items) ? items : [];
    DRILLDOWN_PAGE = 1;

    const searchInput = document.getElementById("drilldown-search");
    const pageSizeSelect = document.getElementById("drilldown-page-size");

    if (searchInput) searchInput.value = "";
    if (pageSizeSelect && pageSizeSelect.value) {
        DRILLDOWN_PAGE_SIZE = parseInt(pageSizeSelect.value, 10) || 25;
    }

    applyDrilldownFilters();
}

function getDrilldownSearchValue() {
    const input = document.getElementById("drilldown-search");
    return input ? String(input.value || "").trim().toLowerCase() : "";
}

// Debounce the search input to prevent UI freezing on massive audits
function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(applyDrilldownFilters, 250);
}

function applyDrilldownFilters() {
    const query = getDrilldownSearchValue();

    if (!query) {
        DRILLDOWN_FILTERED_ITEMS = [...DRILLDOWN_ITEMS];
    } else {
        DRILLDOWN_FILTERED_ITEMS = DRILLDOWN_ITEMS.filter(i => {
            const haystack = [
                i.rule_label, i.rule_name, i.ruleId, i.rule_id,
                i.wcag_title, i.wcag, i.component_display, i.component,
                i.issue_scope, i.display_pattern, i.pattern,
                i.page_display, i.page, i.page_name, i.source,
                Array.isArray(i.sources) ? i.sources.join(" ") : i.sources,
                i.message, i.description, i.dom_path, i.selector,
                i.xpath, i.path, i.dom, i.fingerprint
            ].filter(Boolean).join(" ").toLowerCase();

            return haystack.includes(query);
        });
    }

    DRILLDOWN_PAGE = 1;
    renderDrilldownPage();
}

function updateDrilldownPageSize(value) {
    DRILLDOWN_PAGE_SIZE = parseInt(value, 10) || 25;
    DRILLDOWN_PAGE = 1;
    renderDrilldownPage();
}

function changeDrilldownPage(delta) {
    const totalPages = Math.max(1, Math.ceil(DRILLDOWN_FILTERED_ITEMS.length / DRILLDOWN_PAGE_SIZE));
    DRILLDOWN_PAGE = Math.min(totalPages, Math.max(1, DRILLDOWN_PAGE + delta));
    renderDrilldownPage();
}

function renderDrilldownPage() {
    const container = document.getElementById("drilldown");
    const content = document.getElementById("drilldown-content");
    const titleEl = document.getElementById("drilldown-title");

    if (!container || !content || !titleEl) return;

    titleEl.innerText = DRILLDOWN_TITLE;

    const totalItems = DRILLDOWN_FILTERED_ITEMS.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / DRILLDOWN_PAGE_SIZE));
    const start = totalItems === 0 ? 0 : (DRILLDOWN_PAGE - 1) * DRILLDOWN_PAGE_SIZE;
    const end = start + DRILLDOWN_PAGE_SIZE;
    const pageItems = DRILLDOWN_FILTERED_ITEMS.slice(start, end);

    let html = `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:10px 0 14px 0;border-bottom:1px solid #eee;">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <label for="drilldown-search"><strong>Search</strong></label>
                <input
                    id="drilldown-search"
                    type="text"
                    placeholder="Filter current results"
                    value="${escapeHtml(getDrilldownSearchValue())}"
                    oninput="debounceSearch()"
                    style="padding:8px 10px;min-width:260px;border:1px solid #d0d7de;border-radius:8px;"
                >
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <label for="drilldown-page-size"><strong>Page size</strong></label>
                <select
                    id="drilldown-page-size"
                    onchange="updateDrilldownPageSize(this.value)"
                    style="padding:8px 10px;border:1px solid #d0d7de;border-radius:8px;"
                >
                    <option value="10" ${DRILLDOWN_PAGE_SIZE === 10 ? "selected" : ""}>10</option>
                    <option value="25" ${DRILLDOWN_PAGE_SIZE === 25 ? "selected" : ""}>25</option>
                    <option value="50" ${DRILLDOWN_PAGE_SIZE === 50 ? "selected" : ""}>50</option>
                    <option value="100" ${DRILLDOWN_PAGE_SIZE === 100 ? "selected" : ""}>100</option>
                </select>
            </div>
        </div>
    `;

    pageItems.forEach(i => {
        const ruleLabel = escapeHtml(i.rule_label || i.ruleId || "Unknown");
        const componentLabel = escapeHtml(i.component || "Other");
        const sourceRaw = i.source || "-";
        const pageLabel = escapeHtml(
            i.page_display ||
            (i.page !== "Unknown" ? i.page : null) ||
            (Array.isArray(i.files) && i.files.length > 0 ? i.files[0] : "Unknown page")
        );

        const patternLabel = escapeHtml(i.display_pattern || i.pattern || "");
        const rawHtmlLabel = i.dom ? escapeHtml(i.dom) : "";
        const sourceLabel = escapeHtml(sourceRaw);
        
        const sourceHtml = sourceRaw && sourceRaw !== "-"
            ? `${renderEnginePill(sourceRaw)} ${sourceLabel}`
            : sourceLabel;

        const messageLabel = escapeHtml(i.message || i.description || "");
        const fingerprintLabel = escapeHtml(i.fingerprint || "");
        const frameWarning = i.component === "frame"
            ? "<br><span style='color:#e15759'>⚠️ Frame-based layout</span>"
            : "";

        html += `
            <div style="padding:10px;border-bottom:1px solid #eee;">
                <b>${ruleLabel}</b><br>
                <strong>Page:</strong> ${pageLabel}<br>
                <strong>Component:</strong> ${componentLabel}<br>
                ${patternLabel ? `<strong>Pattern:</strong> <span style="font-family:monospace; font-size:12px;">${patternLabel}</span><br>` : ""}
                <strong>Source:</strong> ${sourceHtml}<br>
                ${fingerprintLabel ? `<strong>Fingerprint:</strong> <span style="font-family:monospace; font-size:12px;">${fingerprintLabel}</span>` : ""}
                ${frameWarning}
                ${messageLabel ? `<div style="margin-top:6px;color:#666;font-size:12px; white-space: pre-wrap;">${messageLabel}</div>` : ""}
                
                ${rawHtmlLabel ? `
                <div style="margin-top:8px;">
                    <strong>Failing HTML:</strong>
                    <pre style="background:#f1f5f9; padding:8px; border-radius:6px; font-size:11px; overflow-x:auto;"><code>${rawHtmlLabel}</code></pre>
                </div>` : ""}
            </div>
        `;
    });

    const showingFrom = totalItems === 0 ? 0 : start + 1;
    const showingTo = Math.min(end, totalItems);

    html += `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0 0 0;gap:12px;flex-wrap:wrap;">
            <button onclick="changeDrilldownPage(-1)" ${DRILLDOWN_PAGE <= 1 ? "disabled" : ""}>Previous</button>
            <div>
                Showing ${showingFrom}-${showingTo} of ${totalItems}
                (Page ${Math.min(DRILLDOWN_PAGE, totalPages)} of ${totalPages})
            </div>
            <button onclick="changeDrilldownPage(1)" ${DRILLDOWN_PAGE >= totalPages ? "disabled" : ""}>Next</button>
        </div>
    `;

    content.innerHTML = html || "<p>No data</p>";
    container.style.display = "block";
}

// -------------------------
// 🚀 NEXT BEST FIXES (PRIORITIZATION)
// -------------------------

function renderNextBestFixes(items, summary) {
    const container = document.getElementById("nextBestFixes");
    if (!container) return;

    document.getElementById("systemicFixes").innerText = summary.systemic_fixes ?? 0;
    document.getElementById("top5Pages").innerText = summary.pages_impacted_top5 ?? 0;
    document.getElementById("topOwnerTeam").innerText = summary.top_owner_team || "-";

    if (!items || !items.length) {
        container.innerHTML = "<p>No prioritized fixes yet.</p>";
        return;
    }

    const maxPriority = Math.max(...items.map(i => i.priority_score || 0), 1);

    const rowsHtml = items.map((item) => {
        const priorityPct = Math.max(8, Math.round(((item.priority_score || 0) / maxPriority) * 100));
        const pagesLabel = item.affected_pages_count === 1 ? "page" : "pages";
        const findingsLabel = item.findings_count === 1 ? "finding" : "findings";
        
        return `
            <tr onclick="showNextBestFixDrilldown('${encodeURIComponent(item.pattern || '')}', '${encodeURIComponent(item.display_pattern || item.pattern || 'Unknown pattern')}')">
                <td><span class="rank-pill">#${item.top_fix_rank || ''}</span></td>
                <td>
                    <div><strong>${escapeHtml(item.display_pattern || item.pattern || "Unknown pattern")}</strong></div>
                    <div class="muted-text">${escapeHtml(item.root_cause || "Cross-page remediation candidate")}</div>
                </td>
                <td>${escapeHtml(item.component_display || item.component || "Other")}</td>
                <td>${escapeHtml(item.issue_scope || "Unknown")}</td>
                <td><span class="badge ${severityBadgeClass(item.severity)}">${escapeHtml(item.severity_display || item.severity || "Unknown")}</span></td>
                <td>${item.findings_count || 0} <span class="muted-text">${findingsLabel}</span></td>
                <td>${item.affected_pages_count || 0} <span class="muted-text">${pagesLabel}</span></td>
                <td><span class="badge ${item.is_systemic ? "badge-systemic" : "badge-local"}">${item.is_systemic ? "Yes" : "No"}</span></td>
                <td>${escapeHtml(item.owner_team || "-")}</td>
                <td class="priority-cell">
                    <strong>${item.priority_score || 0}</strong>
                    <div class="priority-bar"><div class="priority-fill" style="width:${priorityPct}%"></div></div>
                </td>
            </tr>
        `;
    }).join("");

    container.innerHTML = `
        <div class="fix-table-wrap">
            <table class="fix-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Issue Pattern</th>
                        <th>Affected Component</th>
                        <th>Shared Source</th>
                        <th>Severity</th>
                        <th>Findings</th>
                        <th>Pages Impacted</th>
                        <th>Systemic</th>
                        <th>Owner</th>
                        <th>Priority</th>
                    </tr>
                </thead>
                <tbody>${rowsHtml}</tbody>
            </table>
        </div>
    `;
}

function showNextBestFixDrilldown(patternEncoded, labelEncoded) {
    const pattern = decodeURIComponent(patternEncoded || "");
    const label = decodeURIComponent(labelEncoded || "") || pattern;

    let matches = GLOBAL_ROWS.filter(r => r.pattern === pattern);

    if (matches.length === 0) {
        const cluster = GLOBAL_CLUSTERS.find(c => c.pattern === pattern);
        if (cluster) {
            matches = GLOBAL_ROWS.filter(r => r.fingerprint === cluster.fingerprint);
        }
    }

    if (matches.length === 0) {
        const cluster = GLOBAL_CLUSTERS.find(c => c.pattern === pattern);
        if (cluster && cluster.instances) {
            matches = cluster.instances;
        }
    }

    const healedMatches = matches.map(item => ({
        ...item,
        sources: Array.isArray(item.sources) ? item.sources : [item.source || "Unknown"],
        page_display: (item.page && item.page !== "Unknown") ? item.page :
            (Array.isArray(item.files) && item.files.length > 0 ? item.files[0] : "Unknown page")
    }));

    showDrilldown(`Fix Candidate: ${label}`, healedMatches);
}

// -------------------------
// 🩺 INVENTORY & DIAGNOSTICS
// -------------------------

function renderInventoryStatusBadge(status) {
    const raw = String(status || "").trim();
    const lower = raw.toLowerCase();

    let label = raw || "Unknown";
    let cls = "badge-local";

    if (
        lower === "partial" ||
        lower === "warning" ||
        lower.includes("review") ||
        lower.includes("mismatch") ||
        lower.includes("missing") ||
        lower.includes("extra")
    ) {
        label = "Needs review";
        cls = "badge-serious";
    } else if (lower === "complete" || lower === "ok") {
        label = "Complete";
        cls = "badge-systemic";
    }

    return `<span class="badge ${cls}">${escapeHtml(label)}</span>`;
}

function renderPageInventoryCheck(inventory) {
    const container = document.getElementById("pageInventoryCheck");
    if (!container) return;

    const rawRows = inventory?.rows ?? inventory?.pages ?? inventory?.items ?? inventory?.page_rows ?? inventory?.details ?? [];
    const allRows = Array.isArray(rawRows) ? rawRows : [];
    const rawTools = inventory?.tool_folders ?? inventory?.toolFolders ?? inventory?.tools ?? [];
    const toolList = Array.isArray(rawTools) ? rawTools : String(rawTools || "").split(",").map(s => s.trim()).filter(Boolean);
    const toolFolderCount = toolList.length || "—";

    const reviewRows = allRows.filter(row => {
        const status = String(row.status || "").trim().toLowerCase();
        return !["complete", "ok"].includes(status);
    });

    const completeRows = allRows.filter(row => {
        const status = String(row.status || "").trim().toLowerCase();
        return ["complete", "ok"].includes(status);
    });

    const computedMismatchPages = reviewRows.length;
    const computedCompletePages = completeRows.length;
    const computedMissingReports = reviewRows.reduce((sum, row) => {
        const missing = row.missing_from ?? row.missingFrom ?? row.tools_missing ?? [];
        return sum + (Array.isArray(missing) ? missing.length : 0);
    }, 0);

    const completePages = inventory?.pages_complete ?? inventory?.complete_pages ?? inventory?.completePages ?? inventory?.complete_count ?? inventory?.counts?.complete ?? computedCompletePages ?? "—";
    const mismatchPages = inventory?.pages_with_mismatch ?? inventory?.mismatch_pages ?? inventory?.mismatchPages ?? inventory?.needs_review ?? inventory?.review_count ?? inventory?.counts?.review ?? computedMismatchPages ?? "—";
    const missingReports = inventory?.missing_reports ?? inventory?.missingReports ?? inventory?.missing_count ?? inventory?.counts?.missing ?? computedMissingReports ?? "—";
    const rawStatus = inventory?.status ?? inventory?.inventory_status ?? "";

    let friendlyStatus = "—";
    const lowerStatus = String(rawStatus).trim().toLowerCase();

    if (lowerStatus === "warning" || lowerStatus === "partial" || lowerStatus.includes("review")) {
        friendlyStatus = "Needs review";
    } else if (lowerStatus === "ok" || lowerStatus === "complete" || lowerStatus === "good") {
        friendlyStatus = "Complete";
    } else if (reviewRows.length > 0) {
        friendlyStatus = "Needs review";
    } else if (allRows.length > 0) {
        friendlyStatus = "Complete";
    }

    document.getElementById("inventoryStatus").textContent = friendlyStatus;
    document.getElementById("inventoryTools").textContent = toolFolderCount;
    document.getElementById("inventoryCompletePages").textContent = completePages;
    document.getElementById("inventoryMismatchPages").textContent = mismatchPages;
    document.getElementById("inventoryMissingReports").textContent = missingReports;

    if (!allRows.length) {
        container.innerHTML = `
            <div class="inventory-summary-note inventory-warn">
                Inventory data unavailable.
            </div>
        `;
        return;
    }

    if (!reviewRows.length) {
        container.innerHTML = `
            <div class="inventory-summary-note inventory-ok">
                No pages need review. Cross-tool inventory looks complete.
            </div>
        `;
        return;
    }

    const summaryNote = inventory?.summary_note || inventory?.summaryNote || `${reviewRows.length} page${reviewRows.length === 1 ? "" : "s"} need review.`;

    const tableRows = reviewRows.map(row => {
        const presentIn = row.present_in ?? row.presentIn ?? row.tools_present ?? [];
        const missingFrom = row.missing_from ?? row.missingFrom ?? row.tools_missing ?? [];

        const presentList = Array.isArray(presentIn) ? presentIn : String(presentIn || "").split(",").map(s => s.trim()).filter(Boolean);
        const missingList = Array.isArray(missingFrom) ? missingFrom : String(missingFrom || "").split(",").map(s => s.trim()).filter(Boolean);

        const coverage = row.coverage ?? row.coverage_text ?? row.coverageText ?? `${presentList.length}/${toolList.length || "?"}`;

        return `
            <tr>
                <td>${escapeHtml(row.page || row.page_key || row.pageKey || "")}</td>
                <td>${renderInventoryStatusBadge(row.status)}</td>
                <td>${escapeHtml(String(coverage))}</td>
                <td>${escapeHtml(presentList.join(", "))}</td>
                <td>${escapeHtml(missingList.length ? missingList.join(", ") : "None")}</td>
            </tr>
        `;
    }).join("");

    container.innerHTML = `
        <div class="inventory-summary-note inventory-warn">
            ${escapeHtml(summaryNote)}
        </div>
        <div class="fix-table-wrap">
            <table class="fix-table">
                <thead>
                    <tr>
                        <th>Page</th>
                        <th>Status</th>
                        <th>Coverage</th>
                        <th>Present In</th>
                        <th>Missing From</th>
                    </tr>
                </thead>
                <tbody>
                    ${tableRows}
                </tbody>
            </table>
        </div>
    `;
}

// -------------------------
// 📤 EXPORTS & STYLING
// -------------------------

async function exportXlsx() {
    if (STATIC_MODE) {
        window.location.href = STATIC_XLSX_PATH;
        return;
    }

    const folder = document.getElementById("folder").value;

    const response = await fetch("/export-xlsx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder })
    });

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "accessibility_analysis.xlsx";
    a.click();
}

function ensureEngineBadgeStyles() {
    if (document.getElementById("engineBadgeStyles")) return;

    const style = document.createElement("style");
    style.id = "engineBadgeStyles";
    style.textContent = `
        .tool-label-with-engine {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            flex-wrap: wrap;
        }

        .engine-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            padding: 0.1rem 0.45rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            line-height: 1.4;
            background: #eef2f7;
            color: #1f2937;
            white-space: nowrap;
        }

        .engine-icon {
            font-size: 0.85rem;
            line-height: 1;
        }

        .engine-axe { background: #dbeafe; color: #1e3a8a; }
        .engine-htmlcs { background: #dcfce7; color: #166534; }
        .engine-ibm { background: #ede9fe; color: #5b21b6; }
        .engine-browser { background: #fef3c7; color: #92400e; }
        .engine-alfa { background: #fce7f3; color: #9d174d; }
        .engine-validator { background: #e0f2fe; color: #075985; }
        .engine-uuv { background: #ccfbf1; color: #115e59; }
        .engine-oobee { background: #f3e8ff; color: #6b21a8; }
        .engine-visual { background: #fee2e2; color: #991b1b; }
        .engine-keyboard { background: #f1f5f9; color: #334155; }
        .engine-at { background: #ecfccb; color: #3f6212; }
        .engine-pdf { background: #fce7f3; color: #be185d; }
        .engine-other { background: #e5e7eb; color: #374151; }

        .wcag-support-note {
            margin: 0.65rem 0 0;
            color: #526070;
            font-size: 0.85rem;
            line-height: 1.4;
        }
    `;
    document.head.appendChild(style);
}

// -------------------------
// 🚀 BOOTSTRAP
// -------------------------

document.addEventListener("DOMContentLoaded", async () => {
    ensureEngineBadgeStyles();

    if (JOB_BASE_PATH) {
        setStaticMode(true);
        await loadStaticAnalysis();
        return;
    }

    try {
        const res = await fetch(STATIC_ANALYSIS_PATH, { method: "HEAD", cache: "no-store" });
        if (res.ok) {
            setStaticMode(true);
            await loadStaticAnalysis();
        } else {
            setStaticMode(false);
        }
    } catch (error) {
        setStaticMode(false);
    }
});