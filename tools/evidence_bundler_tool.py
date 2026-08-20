#!/usr/bin/env python3
"""
Evidence Bundler Tool

Assembles raw finding artifacts (HTTP request/response text, code snippets,
notes, screenshot references, timestamps, a description) into a single
structured markdown finding report.

The report shape follows this repo's ``report-writing`` skill (the generic
HackerOne-style template: Summary -> Vulnerability Details -> Root Cause ->
Steps to Reproduce -> Impact -> Recommended Fix -> Supporting Materials) so
output produced here can be pasted directly into a platform submission, or
handed to a platform-specific overlay skill (bugcrowd-reporting, etc.)
without restructuring. It also appends an Evidence Log (chain-of-custody:
artifact label / type / timestamp) and an evidence-hygiene redaction
reminder, per the ``evidence-hygiene`` skill's redact-before-attach
discipline.

This module does not decide WHETHER to report (that's triage-validation's
job) or WHAT tone/severity language to use beyond structure (that's
report-writing's job in full) — it is purely a formatting/assembly tool
that turns scattered artifacts into one clean document.

Available tools:
- evidence_bundler_tool: Build a markdown finding report from artifacts

Usage:
    from tools.evidence_bundler_tool import build_finding_report, evidence_bundler_tool

    report = build_finding_report(
        title="IDOR in /api/users/{id}/orders allows reading any user's orders",
        description="The endpoint does not verify object ownership...",
        artifacts=[
            {"type": "request", "label": "Attacker request", "content": "GET /api/users/456/orders ..."},
            {"type": "response", "label": "Victim data returned", "content": '{"email": "victim@test.com"}'},
        ],
    )
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Artifact "type" -> default report section and default code-fence language.
_TYPE_DEFAULTS = {
    "request": {"section": "steps", "language": "http"},
    "response": {"section": "steps", "language": "json"},
    "code": {"section": "root_cause", "language": "text"},
    "note": {"section": "steps", "language": None},
    "screenshot": {"section": "supporting", "language": None},
    "log": {"section": "supporting", "language": "text"},
}

_VALID_TYPES = set(_TYPE_DEFAULTS.keys())
_VALID_SECTIONS = {"root_cause", "steps", "impact", "supporting"}

_SECTION_TITLES = {
    "root_cause": "Root Cause",
    "steps": "Steps to Reproduce",
    "impact": "Impact",
    "supporting": "Supporting Materials",
}


@dataclass
class Artifact:
    """A single normalized evidence artifact."""
    type: str
    content: str = ""
    label: Optional[str] = None
    timestamp: Optional[str] = None
    language: Optional[str] = None
    section: Optional[str] = None
    path: Optional[str] = None  # for screenshot/file references with no inline content

    def resolved_section(self) -> str:
        if self.section and self.section in _VALID_SECTIONS:
            return self.section
        return _TYPE_DEFAULTS.get(self.type, {}).get("section", "supporting")

    def resolved_language(self) -> Optional[str]:
        if self.language:
            return self.language
        return _TYPE_DEFAULTS.get(self.type, {}).get("language")


class EvidenceBundlerError(ValueError):
    """Raised when required report inputs are missing or malformed."""


def _normalize_artifact(raw: Dict[str, Any], index: int) -> Artifact:
    if not isinstance(raw, dict):
        raise EvidenceBundlerError(f"artifacts[{index}] must be an object, got {type(raw).__name__}")

    a_type = str(raw.get("type", "note")).strip().lower()
    if a_type not in _VALID_TYPES:
        raise EvidenceBundlerError(
            f"artifacts[{index}]: unknown type {a_type!r} — expected one of "
            f"{sorted(_VALID_TYPES)}"
        )

    content = raw.get("content", "") or ""
    path = raw.get("path")
    if not content and not path:
        raise EvidenceBundlerError(
            f"artifacts[{index}]: must have non-empty 'content' or a 'path' reference"
        )

    section = raw.get("section")
    if section is not None:
        section = str(section).strip().lower()
        if section not in _VALID_SECTIONS:
            raise EvidenceBundlerError(
                f"artifacts[{index}]: unknown section {section!r} — expected one of "
                f"{sorted(_VALID_SECTIONS)}"
            )

    return Artifact(
        type=a_type,
        content=str(content),
        label=raw.get("label"),
        timestamp=raw.get("timestamp"),
        language=raw.get("language"),
        section=section,
        path=path,
    )


def _render_artifact(a: Artifact, number: int) -> str:
    """Render one artifact as a labeled markdown block."""
    header_bits = [a.label or f"{a.type.replace('_', ' ').title()} {number}"]
    if a.timestamp:
        header_bits.append(f"— {a.timestamp}")
    header = " ".join(header_bits)

    lines = [f"**{header}**"]
    if a.content:
        lang = a.resolved_language() or ""
        lines.append(f"```{lang}".rstrip())
        lines.append(a.content.rstrip("\n"))
        lines.append("```")
    elif a.path:
        lines.append(f"*(see attachment: `{a.path}`)*")
    return "\n".join(lines)


def build_finding_report(
    title: str,
    description: str,
    artifacts: Optional[List[Dict[str, Any]]] = None,
    vulnerability_type: str = "",
    affected_endpoint: str = "",
    cvss_score: Optional[str] = None,
    cvss_vector: Optional[str] = None,
    severity: Optional[str] = None,
    impact: str = "",
    recommended_fix: str = "",
    steps: Optional[List[str]] = None,
    attacker_account: str = "",
    victim_account: str = "",
    include_hygiene_reminder: bool = True,
    generated_at: Optional[str] = None,
) -> str:
    """Assemble a structured markdown finding report from raw artifacts.

    Args:
        title: Finding title. Should follow the report-writing skill's title
            formula: "[Bug Class] in [Endpoint/Feature] allows [actor] to [impact]".
        description: Impact-first summary paragraph — what the bug is, where
            it lives, what an attacker can do. Required, non-empty.
        artifacts: List of evidence items. Each is a dict with:
            - type: one of "request", "response", "code", "note", "screenshot", "log"
            - content: the raw text (required unless "path" is given)
            - label: optional human label (defaults to "{Type} {n}")
            - timestamp: optional ISO-ish timestamp string
            - language: optional code-fence language override
            - section: optional explicit placement override, one of
              "root_cause", "steps", "impact", "supporting" (defaults per type)
            - path: optional file/attachment reference when there's no inline
              content (e.g. a screenshot file)
        vulnerability_type: e.g. "IDOR / Broken Object Level Authorization"
        affected_endpoint: e.g. "GET /api/users/{user_id}/orders"
        cvss_score: e.g. "6.5 (Medium)"
        cvss_vector: e.g. "AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N"
        severity: e.g. "High" — used when a CVSS vector isn't available
        impact: Quantified impact paragraph (appended before artifact-derived
            impact evidence, if any)
        recommended_fix: 1-3 sentence concrete fix, optionally with a code snippet
        steps: Optional explicit numbered reproduction steps (plain text,
            rendered before any "steps"-section artifacts)
        attacker_account: e.g. "attacker@test.com (ID 123)"
        victim_account: e.g. "victim@test.com (ID 456)"
        include_hygiene_reminder: append the evidence-hygiene redaction
            reminder under Supporting Materials (default True)
        generated_at: override the report generation timestamp (defaults to
            current UTC time); primarily for deterministic tests

    Returns:
        A markdown string with sections: Summary, Vulnerability Details,
        Root Cause (if any), Steps to Reproduce, Impact, Recommended Fix,
        Supporting Materials, Evidence Log.

    Raises:
        EvidenceBundlerError: if title/description are empty or an artifact
            is malformed.
    """
    title = (title or "").strip()
    description = (description or "").strip()
    if not title:
        raise EvidenceBundlerError("title is required")
    if not description:
        raise EvidenceBundlerError("description is required")

    raw_artifacts = artifacts or []
    normalized = [_normalize_artifact(a, i) for i, a in enumerate(raw_artifacts)]

    by_section: Dict[str, List[Artifact]] = {k: [] for k in _VALID_SECTIONS}
    for a in normalized:
        by_section[a.resolved_section()].append(a)

    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(description)
    lines.append("")

    # --- Vulnerability Details ---
    detail_rows = []
    if vulnerability_type:
        detail_rows.append(f"**Vulnerability Type:** {vulnerability_type}")
    if cvss_score or cvss_vector:
        cvss_line = "**CVSS Score:**"
        if cvss_score:
            cvss_line += f" {cvss_score}"
        if cvss_vector:
            cvss_line += f" — {cvss_vector}"
        detail_rows.append(cvss_line)
    elif severity:
        detail_rows.append(f"**Severity:** {severity}")
    if affected_endpoint:
        detail_rows.append(f"**Affected Endpoint:** {affected_endpoint}")
    if detail_rows:
        lines.append("## Vulnerability Details")
        lines.append("")
        lines.extend(detail_rows)
        lines.append("")

    # --- Root Cause (code artifacts) ---
    if by_section["root_cause"]:
        lines.append(f"## {_SECTION_TITLES['root_cause']}")
        lines.append("")
        for i, a in enumerate(by_section["root_cause"], 1):
            lines.append(_render_artifact(a, i))
            lines.append("")

    # --- Steps to Reproduce ---
    lines.append(f"## {_SECTION_TITLES['steps']}")
    lines.append("")
    if attacker_account or victim_account:
        lines.append("**Environment:**")
        if attacker_account:
            lines.append(f"- Attacker account: {attacker_account}")
        if victim_account:
            lines.append(f"- Victim account: {victim_account}")
        lines.append("")
    if steps:
        lines.append("**Steps:**")
        lines.append("")
        for i, step in enumerate(steps, 1):
            lines.append(f"{i}. {step}")
        lines.append("")
    if by_section["steps"]:
        for i, a in enumerate(by_section["steps"], 1):
            lines.append(_render_artifact(a, i))
            lines.append("")
    if not steps and not by_section["steps"]:
        lines.append("*(no explicit steps or request/response artifacts provided)*")
        lines.append("")

    # --- Impact ---
    lines.append(f"## {_SECTION_TITLES['impact']}")
    lines.append("")
    if impact:
        lines.append(impact)
        lines.append("")
    if by_section["impact"]:
        for i, a in enumerate(by_section["impact"], 1):
            lines.append(_render_artifact(a, i))
            lines.append("")
    if not impact and not by_section["impact"]:
        lines.append("*(impact not yet quantified — do not submit until this is filled in; "
                      "see report-writing skill: never claim \"could potentially\")*")
        lines.append("")

    # --- Recommended Fix ---
    if recommended_fix:
        lines.append("## Recommended Fix")
        lines.append("")
        lines.append(recommended_fix)
        lines.append("")

    # --- Supporting Materials ---
    if by_section["supporting"] or include_hygiene_reminder:
        lines.append(f"## {_SECTION_TITLES['supporting']}")
        lines.append("")
        for i, a in enumerate(by_section["supporting"], 1):
            lines.append(_render_artifact(a, i))
            lines.append("")
        if include_hygiene_reminder:
            lines.append(
                "> Before attaching: redact session cookies/Authorization headers and "
                "other-users' PII per the evidence-hygiene skill (cookie redaction, PII "
                "black-bar, HAR sanitization). Confirm the pre-screenshot checklist passed."
            )
            lines.append("")

    # --- Evidence Log (chain-of-custody) ---
    if normalized:
        lines.append("## Evidence Log")
        lines.append("")
        lines.append("| # | Type | Label | Section | Timestamp |")
        lines.append("|---|---|---|---|---|")
        for i, a in enumerate(normalized, 1):
            label = a.label or f"{a.type} {i}"
            lines.append(f"| {i} | {a.type} | {label} | {a.resolved_section()} | {a.timestamp or '—'} |")
        lines.append("")

    gen_time = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"*Report generated by evidence_bundler_tool at {gen_time}.*")

    return "\n".join(lines).rstrip() + "\n"


def evidence_bundler_tool(
    title: str = "",
    description: str = "",
    artifacts: Optional[List[Dict[str, Any]]] = None,
    vulnerability_type: str = "",
    affected_endpoint: str = "",
    cvss_score: Optional[str] = None,
    cvss_vector: Optional[str] = None,
    severity: Optional[str] = None,
    impact: str = "",
    recommended_fix: str = "",
    steps: Optional[List[str]] = None,
    attacker_account: str = "",
    victim_account: str = "",
    output_path: Optional[str] = None,
) -> str:
    """Build a markdown finding report and optionally write it to disk.

    Thin wrapper around :func:`build_finding_report` for tool-call use: on
    success returns the markdown report as plain text (so it can be read or
    pasted directly); on failure returns a ``tool_error`` JSON string. When
    ``output_path`` is given the report is additionally written to that file
    and a short JSON confirmation (with a report preview) is returned
    instead of the raw markdown, so callers can tell where it landed.

    Returns:
        str: markdown report text, or JSON (error, or write confirmation).
    """
    from tools.registry import tool_error, tool_result

    try:
        report = build_finding_report(
            title=title,
            description=description,
            artifacts=artifacts,
            vulnerability_type=vulnerability_type,
            affected_endpoint=affected_endpoint,
            cvss_score=cvss_score,
            cvss_vector=cvss_vector,
            severity=severity,
            impact=impact,
            recommended_fix=recommended_fix,
            steps=steps,
            attacker_account=attacker_account,
            victim_account=victim_account,
        )
    except EvidenceBundlerError as e:
        return tool_error(str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("evidence_bundler_tool failed")
        return tool_error(f"Failed to build report: {e}")

    if not output_path:
        return report

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
    except OSError as e:
        return tool_error(f"Failed to write report to {output_path}: {e}")

    preview = report[:400] + ("…" if len(report) > 400 else "")
    return tool_result(
        success=True,
        path=output_path,
        bytes_written=len(report.encode("utf-8")),
        preview=preview,
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
from tools.registry import registry

EVIDENCE_BUNDLER_SCHEMA = {
    "name": "evidence_bundler",
    "description": (
        "Assemble raw finding evidence (a description, HTTP request/response text, "
        "code snippets, notes, screenshot references, timestamps) into one structured "
        "markdown finding report (Summary / Vulnerability Details / Root Cause / Steps "
        "to Reproduce / Impact / Recommended Fix / Supporting Materials / Evidence Log). "
        "Follows this repo's report-writing skill template and appends an evidence-hygiene "
        "redaction reminder. Returns the markdown report text directly, or writes it to "
        "output_path and returns a JSON confirmation. Use this once a finding is validated "
        "and you have concrete evidence to write up — not for deciding whether to report."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Finding title, e.g. '[Bug Class] in [Endpoint] allows [actor] to [impact]'."
            },
            "description": {
                "type": "string",
                "description": "Impact-first summary paragraph: what the bug is, where, what an attacker can do."
            },
            "artifacts": {
                "type": "array",
                "description": "Evidence items to embed in the report, in the order they should appear within their section.",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["request", "response", "code", "note", "screenshot", "log"],
                            "description": "Artifact kind. Determines default section/language."
                        },
                        "content": {"type": "string", "description": "Raw text content (required unless 'path' is given)."},
                        "label": {"type": "string", "description": "Human label shown above the block."},
                        "timestamp": {"type": "string", "description": "When this evidence was captured."},
                        "language": {"type": "string", "description": "Code-fence language override, e.g. 'json', 'python', 'http'."},
                        "section": {
                            "type": "string",
                            "enum": ["root_cause", "steps", "impact", "supporting"],
                            "description": "Explicit section override; defaults based on 'type'."
                        },
                        "path": {"type": "string", "description": "Attachment/file reference when there's no inline content (e.g. a screenshot file)."},
                    },
                },
            },
            "vulnerability_type": {"type": "string", "description": "e.g. 'IDOR / Broken Object Level Authorization'."},
            "affected_endpoint": {"type": "string", "description": "e.g. 'GET /api/users/{user_id}/orders'."},
            "cvss_score": {"type": "string", "description": "e.g. '6.5 (Medium)'."},
            "cvss_vector": {"type": "string", "description": "e.g. 'AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N'."},
            "severity": {"type": "string", "description": "Used instead of CVSS when no vector is available, e.g. 'High'."},
            "impact": {"type": "string", "description": "Quantified impact paragraph."},
            "recommended_fix": {"type": "string", "description": "1-3 sentence concrete fix, optionally with a code snippet."},
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Explicit plain-text reproduction steps, rendered before any request/response artifacts."
            },
            "attacker_account": {"type": "string", "description": "e.g. 'attacker@test.com (ID 123)'."},
            "victim_account": {"type": "string", "description": "e.g. 'victim@test.com (ID 456)'."},
            "output_path": {"type": "string", "description": "If given, write the report to this path and return a JSON confirmation instead of the raw markdown."},
        },
        "required": ["title", "description"],
    },
}

registry.register(
    name="evidence_bundler",
    toolset="evidence",
    schema=EVIDENCE_BUNDLER_SCHEMA,
    handler=lambda args, **kw: evidence_bundler_tool(
        title=args.get("title", ""),
        description=args.get("description", ""),
        artifacts=args.get("artifacts"),
        vulnerability_type=args.get("vulnerability_type", ""),
        affected_endpoint=args.get("affected_endpoint", ""),
        cvss_score=args.get("cvss_score"),
        cvss_vector=args.get("cvss_vector"),
        severity=args.get("severity"),
        impact=args.get("impact", ""),
        recommended_fix=args.get("recommended_fix", ""),
        steps=args.get("steps"),
        attacker_account=args.get("attacker_account", ""),
        victim_account=args.get("victim_account", ""),
        output_path=args.get("output_path"),
    ),
    emoji="🗂️",
    max_result_size_chars=200_000,
)
