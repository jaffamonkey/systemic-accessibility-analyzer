# Systemic Accessibility Analyzer

> Status: early alpha. Suitable for local analysis and static dashboard generation. Public server deployment is not yet hardened.

A FastAPI-based platform for identifying **systemic accessibility issues
across large web estates** by aggregating and analyzing results from
multiple accessibility testing engines.

Instead of treating accessibility violations as isolated page-level
bugs, this system detects patterns and shared root causes, helping teams
prioritize fixes that resolve issues across many pages or components
simultaneously.


# Summary WCAG Support Table

| Tool Framework 	| WCAG 2.0 (A/AA/AAA) |	WCAG 2.1 (A/AA/AAA)	| WCAG 2.2 (A/AA/AAA) | 
| ------------------------ | ------------------- |----------- | ------------------- |
| Playwright/Axe-core	| A / AA (Partial AAA)	| A / AA (Partial AAA)	| A / AA | 
| Axe-scan	| A / AA (Partial AAA)|	A / AA (Partial AAA)| 	A / AA | 
| UUV	| A / AA	| A / AA	| A / AA | 
| Lighthouse	| A / AA	| A / AA	| A / AA | 
| IBM Accessibility Checker	| A / AA	| A / AA	| A / AA | 
| Oobee	| A / AA / AAA	| A / AA / AAA	| Limited | 
| Pa11y-CI	| A / AA / AAA	| A / AA / AAA	| A / AA (via axe) | 
| Html-sniffer	| A / AA / AAA	| A / AA / AAA	| No | 

------------------------------------------------------------------------

# Why This Exists

Most accessibility scanners report issues **per page**, which often
leads to hundreds or thousands of repeated violations.

Example:

  Page           Issue
  -------------- -------------------------
  Homepage       Button contrast failure
  Product page   Button contrast failure
  Checkout       Button contrast failure
  Account page   Button contrast failure

Traditional reports treat these as separate issues.

In reality:

> The design system button component has a contrast issue.

This platform identifies that pattern and reports it as **one systemic
issue affecting many pages**.

------------------------------------------------------------------------

# Key Capabilities

## Multi‑Tool Support

Supports accessibility reports from:

- IBM Accessibility Checker
- axe-core
- pa11y-ci
- Lighthouse
- HTML CodeSniffer
- uuv
- Oobee

Reports are normalized into a **canonical violation model**.

------------------------------------------------------------------------

## Automatic Format Detection

The system automatically detects report formats.

  Tool       Detection Logic
  ---------- -----------------
  IBM        report.results
  axe-core   violations
  pa11y      issues

------------------------------------------------------------------------

## Systemic Issue Clustering

Violations are grouped using a fingerprint built from:

ruleId + message

Example fingerprint:

color-contrast + Elements must have sufficient color contrast

All matching violations across reports are grouped together.

------------------------------------------------------------------------

## Severity‑Weighted Prioritization

score = occurrences × severity_weight

  Severity   Weight
  ---------- --------
  critical   5
  serious    4
  moderate   3
  minor      2
  unknown    1

------------------------------------------------------------------------

## WCAG 2.2 Mapping

Violations are mapped to WCAG Success Criteria where possible.

  Field   Description
  ------- ----------------------
  WCAG    Success criterion ID
  Level   A / AA / AAA
  Title   Official criterion
  URL     Documentation link

Example:

  Rule             WCAG    Level   Title
  ---------------- ------- ------- --------------------
  color-contrast   1.4.3   AA      Contrast (Minimum)
  image-alt        1.1.1   A       Non-text Content

------------------------------------------------------------------------

## Component‑Level Analysis

Violations grouped by detected UI components.

Examples:

  DOM                 Component
  ------------------- ------------
  /html/body/header   Header
  /html/body/footer   Footer
  /dialog             Modal
  /nav                Navigation

------------------------------------------------------------------------

## Professional Excel Audit Reports

Generated sheets:

  Sheet          Description
  -------------- -------------------------
  Summary        Systemic issue clusters
  Detail         Raw violations
  Components     Component groupings
  Rules          Rule frequency
  WCAG Summary   WCAG totals

------------------------------------------------------------------------

## Dashboard

http://localhost:8000/dashboard

Displays:

-   top systemic issues
-   rule distribution
-   WCAG coverage
-   violation counts

------------------------------------------------------------------------

# Architecture

Accessibility Tools → JSON Reports → Adapters → Canonical Violations →
Systemic Engine → Reports

------------------------------------------------------------------------

# Installation

Create environment:

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Activate:

Mac/Linux: source venv/bin/activate

Windows: venv`\Scripts`{=tex}`\activate`{=tex}

Install:

pip install -r requirements.txt

------------------------------------------------------------------------

# Running

uvicorn app.main:app --reload

Docs:

http://localhost:8000/docs

------------------------------------------------------------------------

# Workflow

1.  Run accessibility scanners
2.  Save JSON reports
3.  Run analyzer
4.  Export report
5.  Review systemic issues

------------------------------------------------------------------------

# API

Analyze:

POST /analyze

Request:

{ "folder": "./job-name/reports" }

Export:

POST /export?format=xlsx

------------------------------------------------------------------------

# CI/CD

Pipeline example:

tests → generate reports → analyzer → fail build if issues increase

------------------------------------------------------------------------

# Use Cases

-   enterprise sites
-   design systems
-   accessibility audits
-   remediation tracking

------------------------------------------------------------------------

# License

MIT

------------------------------------------------------------------------

# Acknowledgements

Tools used:

-   IBM Accessibility Checker
-   axe-core
-   pa11y


------------------------------------------------------------------------

# Power BI Ready Export

The XLSX export now includes dedicated sheets designed for BI ingestion:

- **Power BI Findings**: row-level dataset with sort columns and display labels
- **Power BI Patterns**: grouped recurring-issue dataset for prioritization visuals
- **Data Glossary**: quick reference for reporting fields

Additional export fields include:

- `severity_sort`
- `wcag_level_sort`
- `display_pattern`
- `affected_pages_count`
- `is_systemic`
- `design_system_issue`
- `issue_rank_score`
- `owner_team`
- `page_group`

These fields are intended to reduce Power BI modelling work and support
executive, page-level, and systemic remediation dashboards.


## Power BI star schema export

The XLSX export now includes a simple star-schema tab set for Power BI:

- `Fact Findings`
- `Dim Page`
- `Dim Rule`
- `Dim Component`
- `Dim Pattern`
- `Fix Once Benefit Many`
- `Model Notes`

Recommended relationships:

- `Fact Findings.page_key` -> `Dim Page.page_key`
- `Fact Findings.rule_key` -> `Dim Rule.rule_key`
- `Fact Findings.component_key` -> `Dim Component.component_key`
- `Fact Findings.pattern_key` -> `Dim Pattern.pattern_key`

Use `severity_sort` and `wcag_level_sort` as sort-by columns in Power BI.


The star-schema export also includes a pre-ranked `Fix Once Benefit Many` sheet for the final Power BI action panel. It exposes `top_fix_rank`, `top_fix_candidate`, `pattern_findings_count`, and pattern-level severity/owner columns so the dashboard can be built with minimal extra modeling.


------------------------------------------------------------------------

# Netlify Static Deployment

This project can be deployed to Netlify as a **prebuilt static dashboard**.
The Netlify build runs `python build_static_netlify.py`, which:

- loads the bundled `reports/` folder
- generates `dist/data/analysis.json`
- copies the dashboard assets into `dist/`
- generates `dist/accessibility_analysis.xlsx`

Files added for Netlify:

- `netlify.toml`
- `build_static_netlify.py`

## Local static build

```bash
python build_static_netlify.py
```

Then open `dist/index.html` locally or deploy the `dist/` folder.

## Netlify settings

These are already captured in `netlify.toml`:

- Build command: `python build_static_netlify.py`
- Publish directory: `dist`


## Supported tools

Current adapters include axe/axe-like JSON, Lighthouse, Pa11y, IBM, HTML CodeSniffer, Axis/axe scan, AvalPDF, and OOBEE.
