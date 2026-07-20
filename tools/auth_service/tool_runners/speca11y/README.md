# SpecA11y URL Runner

A simple Node.js runner that performs accessibility audits against a list of URLs using **SpecA11y** and **Playwright**.

Unlike many accessibility tools, SpecA11y goes beyond static rule checking and includes browser-based testing for many modern accessibility issues including focus indicators, reflow, keyboard navigation, reduced motion and emerging WCAG 3 draft guidance.

---

## Features

- Audits multiple URLs
- Uses Playwright Chromium
- Automatically scrolls each page
- Saves JSON report
- Saves SARIF report
- Generates summary.json
- Headless execution
- Supports WCAG 2.0
- Supports WCAG 2.1
- Supports WCAG 2.2
- Includes SpecA11y's experimental WCAG 3 draft rules

---

## Installation

Clone the repository:

```bash
git clone <repo>
cd speca11y-runner
```

Install dependencies:

```bash
npm install
```

Install Chromium:

```bash
npm run install:browsers
```
---

## Input

Create a file named **urls.txt**

Example:

```text
https://example.com
https://example.com/about
https://example.com/contact
```

Blank lines are ignored.

Lines beginning with `#` are treated as comments.

---

## Running

Using the default files:

```bash
npm run audit
```

Or specify your own:

```bash
node run-speca11y.mjs urls.txt reports
```

Arguments:

```
run-speca11y.mjs <url-list> <output-directory>
```

Example:

```bash
node run-speca11y.mjs myurls.txt output
```

---

## Output

For each page the runner produces:

```
reports/

example_com.speca11y.json
example_com.speca11y.sarif

another_site.speca11y.json
another_site.speca11y.sarif

summary.json
```

---

## JSON Report

Contains the complete SpecA11y results including:

- violations
- warnings
- passes (optional)
- rule information
- element locations
- accessibility metadata

---

## SARIF Report

SARIF output can be imported into:

- GitHub Code Scanning
- Azure DevOps
- Visual Studio
- VS Code SARIF Viewer
- Other SARIF-compatible tools

---

## Summary

A `summary.json` file is also generated.

Example:

```json
[
  {
    "url": "https://example.com",
    "ok": true,
    "violations": 7,
    "warnings": 3
  },
  {
    "url": "https://example.com/about",
    "ok": true,
    "violations": 1,
    "warnings": 0
  }
]
```

---

## Browser Configuration

The runner uses Playwright Chromium in headless mode.

Default viewport:

```
1366 × 900
```

Reduced Motion:

```
enabled
```

Network idle wait:

```
enabled
```

Automatic page scrolling:

```
enabled
```

---

## Accessibility Coverage

SpecA11y includes checks covering areas such as:

- Keyboard navigation
- Focus indicators
- Focus visibility
- Focus traps
- Reduced motion
- Reflow
- Text spacing
- Target size
- Landmark usage
- Form accessibility
- Dialog behaviour
- Accessible names
- ARIA usage
- WCAG 2.0
- WCAG 2.1
- WCAG 2.2
- Experimental WCAG 3 draft checks

---

## Notes

SpecA11y is not intended to replace manual accessibility testing.

Results should be used alongside:

- Screen reader testing
- Keyboard-only testing
- Zoom testing
- Colour contrast analysis
- Human accessibility review

---

## Requirements

- Node.js 20+
- Chromium (installed via Playwright)

---

## License

MIT