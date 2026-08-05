from adapters.registry import register_adapter


def detect_uuv(data):
    if not isinstance(data, dict):
        return False
    return (
        isinstance(data.get("generatedBy"), str)
        and "@uuv/playwright" in data.get("generatedBy", "")
        and any(k in data for k in ("requestedUrl", "finalUrl", "findings", "axe", "pageErrors"))
    )


SUMMARY_CODE_RULE_MAP = {
    "blank-links": "link-name",
    "blank-buttons": "button-name",
    "images-missing-alt": "image-alt",
    "missing-label-inputs": "label",
}

DETAIL_LIST_MAP = {
    "linksWithoutText": ("link-name", "Links must have discernible text", "moderate"),
    "buttonsWithoutText": ("button-name", "Buttons must have discernible text", "moderate"),
    "imagesMissingAlt": ("image-alt", "Images must have alternative text", "serious"),
    "missingLabelInputs": ("label", "Form elements must have labels", "serious"),
}

RULE_WCAG_MAP = {
    "link-name": (["2.4.4", "4.1.2"], "A"),
    "button-name": (["4.1.2"], "A"),
    "image-alt": (["1.1.1"], "A"),
    "label": (["3.3.2", "4.1.2"], "A"),
    "landmark-one-main": (["1.3.1"], "A"),
    
    # Newly mapped rules to resolve blank WCAG reporting gaps
    "hidden-content": (["Best Practice"], None),
    "http-error-status": (["Best Practice"], None),
}

IGNORED_SUMMARY_CODES = {"failed-requests", "console-noise", "axe-violations"}

SEVERITY_MAP = {
    "minor": "minor",
    "low": "minor",
    "moderate": "moderate",
    "medium": "moderate",
    "serious": "serious",
    "high": "serious",
    "critical": "critical",
    "severe": "critical",
}


def _normalize_severity(value, default="moderate"):
    if value is None:
        return default
    key = str(value).strip().lower()
    return SEVERITY_MAP.get(key, default)


def _extract_wcag_criteria(tags):
    out = []
    for tag in tags or []:
        if not isinstance(tag, str):
            continue
        t = tag.strip().lower()
        if not t.startswith("wcag"):
            continue
        suffix = t[4:]
        if suffix.isdigit() and len(suffix) >= 3:
            out.append(".".join(suffix))
    seen = set()
    deduped = []
    for item in out:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _wcag_level_from_tags(tags):
    level = None
    for tag in tags or []:
        if not isinstance(tag, str):
            continue
        t = tag.strip().lower()
        if t.endswith("aaa"):
            return "AAA"
        if t.endswith("aa"):
            level = "AA"
        elif t.endswith("a") and level is None:
            level = "A"
    return level


def _detect_conformance_level(data):
    explicit_candidates = [
        data.get("conformanceLevel"),
        data.get("wcagLevel"),
        (data.get("config") or {}).get("conformanceLevel") if isinstance(data.get("config"), dict) else None,
        (data.get("axe") or {}).get("conformanceLevel") if isinstance(data.get("axe"), dict) else None,
    ]
    for value in explicit_candidates:
        if isinstance(value, str):
            level = value.strip().upper()
            if level in {"A", "AA", "AAA"}:
                return level

    axe = data.get("axe") or {}
    rule_ids = {str(v.get("id") or "").strip() for v in (axe.get("violations") or [])}
    rule_ids |= {str(v.get("id") or "").strip() for v in (axe.get("incomplete") or [])}

    aaa_rule_ids = {
        "identical-links-same-purpose",
        "meta-refresh-no-exceptions",
        "p-as-heading",
    }
    if rule_ids & aaa_rule_ids:
        return "AAA"

    return None


def _mapped_wcag(rule_id):
    return RULE_WCAG_MAP.get(rule_id, ([], None))


def _soften_audit_note(rule_id, result_type, severity, message):
    if str(rule_id or "").strip().lower() == "frame-tested":
        return {
            "result_type": "warning",
            "needs_review": True,
            "is_audit_note": True,
            "severity": "minor",
            "message": (
                "Frame content may require separate accessibility review. "
                "This is an audit coverage note rather than a confirmed defect."
            ),
        }

    return {
        "result_type": result_type,
        "needs_review": result_type in {"warning", "incomplete", "potentialviolation"},
        "is_audit_note": False,
        "severity": severity,
        "message": message,
    }


def _push(
    out,
    file,
    url,
    rule_id,
    message,
    severity,
    html="",
    selector="",
    source_detail=None,
    result_type="violation",
    wcag=None,
    wcag_criteria=None,
    wcag_level=None,
    is_audit_note=False,
    needs_review=None,
    **extra,
):
    softened = _soften_audit_note(rule_id, result_type, severity, message)

    row = {
        "file": file,
        "page_url": url,
        "url": url,
        "ruleId": rule_id,
        "rule_name": extra.get("rule_name") or rule_id,
        "message": softened["message"],
        "dom": selector or html or softened["message"],
        "selector": selector,
        "html": html,
        "severity": _normalize_severity(softened["severity"]),
        "source": "uuv",
        "result_type": softened["result_type"],
        "needs_review": softened["needs_review"] if needs_review is None else needs_review,
        "is_audit_note": softened["is_audit_note"] or is_audit_note,
        "wcag": wcag or ((wcag_criteria or [None])[0]),
        "wcag_criteria": wcag_criteria or ([wcag] if wcag else []),
        "wcag_level": wcag_level,
    }
    if source_detail:
        row["source_detail"] = source_detail
    row.update({k: v for k, v in extra.items() if v is not None})
    out.append(row)


def adapt_uuv(file, data):
    out = []
    page_url = data.get("finalUrl") or data.get("requestedUrl")
    run_status = data.get("status")
    scenario_name = data.get("scenarioName")
    generated_by = data.get("generatedBy")
    conformance_level = _detect_conformance_level(data)

    common_meta = {
        "scan_status": run_status,
        "scenario_name": scenario_name,
        "generated_by": generated_by,
        "conformance_level": conformance_level,
    }

    details = data.get("details") or {}
    seen_detail_groups = set()
    for key, mapping in DETAIL_LIST_MAP.items():
        items = details.get(key) or []
        if not items:
            continue
        rule_id, rule_name, default_severity = mapping
        wcag_criteria, wcag_level = _mapped_wcag(rule_id)
        seen_detail_groups.add(key)
        for item in items:
            html = item.get("outerHTML") or item.get("html") or ""
            selector = item.get("xpath") or item.get("selector") or item.get("href") or ""
            message = item.get("message") or rule_name
            _push(
                out,
                file,
                page_url,
                rule_id,
                message,
                default_severity,
                html=html,
                selector=selector,
                source_detail=key,
                result_type="violation",
                wcag_criteria=wcag_criteria,
                wcag_level=wcag_level,
                rule_name=rule_name,
                **common_meta,
            )

    for finding in data.get("findings") or []:
        code = str(finding.get("code") or "").strip()
        if not code or code in IGNORED_SUMMARY_CODES:
            continue
        if code == "blank-links" and "linksWithoutText" in seen_detail_groups:
            continue
        if code == "blank-buttons" and "buttonsWithoutText" in seen_detail_groups:
            continue
        if code == "images-missing-alt" and "imagesMissingAlt" in seen_detail_groups:
            continue
        if code == "missing-label-inputs" and "missingLabelInputs" in seen_detail_groups:
            continue
        rule_id = SUMMARY_CODE_RULE_MAP.get(code, code)
        wcag_criteria, wcag_level = _mapped_wcag(rule_id)
        _push(
            out,
            file,
            page_url,
            rule_id,
            finding.get("message") or code,
            finding.get("severity") or "moderate",
            source_detail="summary",
            result_type="violation",
            wcag_criteria=wcag_criteria,
            wcag_level=wcag_level,
            rule_name=code.replace("-", " ").title(),
            **common_meta,
        )

    axe = data.get("axe") or {}

    for violation in axe.get("violations") or []:
        rule_id = violation.get("id") or "axe-violation"
        rule_name = violation.get("help") or violation.get("description") or rule_id
        wcag_criteria = _extract_wcag_criteria(violation.get("tags"))
        wcag_level = _wcag_level_from_tags(violation.get("tags")) or conformance_level

        nodes = violation.get("nodes") or []
        if not nodes:
            parts = [part for part in [violation.get("help"), violation.get("description")] if part]
            node_count = violation.get("nodeCount")
            if node_count is not None:
                parts.append(f"Affected nodes: {node_count}")

            _push(
                out,
                file,
                page_url,
                rule_id,
                " | ".join(parts) or rule_id,
                violation.get("impact") or "moderate",
                source_detail="axe",
                result_type="violation",
                wcag_criteria=wcag_criteria,
                wcag_level=wcag_level,
                rule_name=rule_name,
                helpUrl=violation.get("helpUrl"),
                nodeCount=violation.get("nodeCount"),
                **common_meta,
            )
            continue

        for node in nodes:
            target = node.get("target") or []
            selector = target[0] if isinstance(target, list) and target else ""
            html = node.get("html") or ""
            message = node.get("failureSummary") or violation.get("help") or violation.get("description") or rule_id

            _push(
                out,
                file,
                page_url,
                rule_id,
                message,
                node.get("impact") or violation.get("impact") or "moderate",
                html=html,
                selector=selector,
                source_detail="axe",
                result_type="violation",
                wcag_criteria=wcag_criteria,
                wcag_level=wcag_level,
                rule_name=rule_name,
                helpUrl=violation.get("helpUrl"),
                nodeCount=violation.get("nodeCount"),
                **common_meta,
            )

    for incomplete in axe.get("incomplete") or []:
        rule_id = incomplete.get("id") or "axe-incomplete"
        rule_name = incomplete.get("help") or incomplete.get("description") or rule_id
        wcag_criteria = _extract_wcag_criteria(incomplete.get("tags"))
        wcag_level = _wcag_level_from_tags(incomplete.get("tags")) or conformance_level

        nodes = incomplete.get("nodes") or []
        if not nodes:
            parts = [part for part in [incomplete.get("help"), incomplete.get("description")] if part]
            node_count = incomplete.get("nodeCount")
            if node_count is not None:
                parts.append(f"Affected nodes: {node_count}")

            _push(
                out,
                file,
                page_url,
                rule_id,
                " | ".join(parts) or rule_id,
                incomplete.get("impact") or "moderate",
                source_detail="axe-incomplete",
                result_type="incomplete",
                wcag_criteria=wcag_criteria,
                wcag_level=wcag_level,
                rule_name=rule_name,
                helpUrl=incomplete.get("helpUrl"),
                nodeCount=incomplete.get("nodeCount"),
                axe_status="incomplete",
                **common_meta,
            )
            continue

        for node in nodes:
            target = node.get("target") or []
            selector = target[0] if isinstance(target, list) and target else ""
            html = node.get("html") or ""
            message = node.get("failureSummary") or incomplete.get("help") or incomplete.get("description") or rule_id

            _push(
                out,
                file,
                page_url,
                rule_id,
                message,
                node.get("impact") or incomplete.get("impact") or "moderate",
                html=html,
                selector=selector,
                source_detail="axe-incomplete",
                result_type="incomplete",
                wcag_criteria=wcag_criteria,
                wcag_level=wcag_level,
                rule_name=rule_name,
                helpUrl=incomplete.get("helpUrl"),
                nodeCount=incomplete.get("nodeCount"),
                axe_status="incomplete",
                **common_meta,
            )
            
    landmarks = data.get("landmarks") or {}
    existing_rules = {str(r.get("ruleId") or "") for r in out}
    if landmarks.get("hasMain") is False and not ({"region", "landmark-one-main"} & existing_rules):
        wcag_criteria, wcag_level = _mapped_wcag("landmark-one-main")
        _push(
            out,
            file,
            page_url,
            "landmark-one-main",
            "Document does not have a main landmark",
            "moderate",
            source_detail="landmarks",
            result_type="violation",
            wcag_criteria=wcag_criteria,
            wcag_level=wcag_level,
            rule_name="Document should have one main landmark",
            **common_meta,
        )

    if not out and run_status and str(run_status).lower() == "failed":
        _push(
            out,
            file,
            page_url,
            "uuv-run-failed",
            data.get("errorMessage") or "UUV run failed before normalized findings were produced",
            "moderate",
            source_detail="run-status",
            result_type="warning",
            is_audit_note=True,
            needs_review=True,
            rule_name="UUV run failed",
            **common_meta,
        )

    return out


register_adapter(detect_uuv, adapt_uuv)