# Systemic Accessibility Analyzer

> Status: early alpha. 

A FastAPI-based platform for identifying **systemic accessibility issues across large web estates** by aggregating, deduplicating, and clustering results from 11+ accessibility testing engines.

Instead of treating accessibility violations as isolated, repetitive page-level bugs, this system provides **Component Intelligence**—identifying shared root causes and "Fix Once, Benefit Many" patterns that resolve issues across entire design systems simultaneously.

# Why This Exists
Standard scanners report issues per URL node. If a button component in your design system is broken, a standard scanner flags that same issue hundreds of times.

**We turn thousands of raw findings into a lean list of systemic remediation targets.**

# Core Capabilities
- **Multi-Tool Consensus**: Aggregates data from 11 engines (Axe, IBM, Lighthouse, Alfa, etc.) and calculates tool agreement scores.
- **Component Intelligence**: Automatically maps findings to inferred UI components (Header, Nav, Forms, etc.) rather than just DOM nodes.
- **Systemic Clustering**: Fingerprints issues by `ruleId + message` to identify patterns.
- **Fix Once, Benefit Many**: Prioritizes issues by systemic impact, page spread, and cross-tool consensus.
- **Visual Explorer**: Integrated companion views for Virtual Screenreaders, Tab Maps, and Contrast Logs.

# Workflow: The Intelligence Pipeline
1. **Evidence Layer**: Normalize findings from 11+ scan engines into a canonical model.
2. **Component Learning**: Map raw code patterns to UI components and design-system root causes.
3. **Consensus Layer**: Deduplicate findings based on tool agreement and DOM fingerprinting.
4. **Action Layer**: Rank issues by systemic impact to build high-ROI remediation sprints.

# Roadmap: Phase 2 Focus
*   **Component Intelligence**: Mapping findings to inferred UI components (Forms, Nav, etc.) to target design-system repairs.
*   **Confidence Scoring**: Ranking findings based on tool agreement and WCAG criteria consistency.
*   **Root Cause Analysis**: Grouping recurring failures by their shared underlying repair.
*   **Visual Exploration**: Richer overlays for landmark hierarchies and form/image analysis.

# Installation & Running
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload