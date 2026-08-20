"""Tests for the evidence bundler / finding report generator tool."""

import json

import pytest

from tools.evidence_bundler_tool import (
    Artifact,
    EvidenceBundlerError,
    build_finding_report,
    evidence_bundler_tool,
)
from tools.registry import registry


class TestBuildFindingReportBasics:
    def test_minimal_report_has_core_sections(self):
        report = build_finding_report(
            title="IDOR in /api/users/{id}/orders",
            description="The endpoint does not verify ownership of the requested user_id.",
            generated_at="2026-08-20 00:00 UTC",
        )
        assert report.startswith("# IDOR in /api/users/{id}/orders")
        assert "## Summary" in report
        assert "The endpoint does not verify ownership" in report
        assert "## Steps to Reproduce" in report
        assert "## Impact" in report
        assert "evidence_bundler_tool at 2026-08-20 00:00 UTC" in report

    def test_missing_title_raises(self):
        with pytest.raises(EvidenceBundlerError):
            build_finding_report(title="", description="something")

    def test_missing_description_raises(self):
        with pytest.raises(EvidenceBundlerError):
            build_finding_report(title="Some Bug", description="   ")

    def test_no_impact_or_steps_shows_placeholders(self):
        report = build_finding_report(title="Bug", description="desc")
        assert "no explicit steps or request/response artifacts provided" in report
        assert "impact not yet quantified" in report
        # The "never claim could potentially" reminder from report-writing skill
        assert "could potentially" in report


class TestVulnerabilityDetails:
    def test_cvss_fields_rendered(self):
        report = build_finding_report(
            title="Bug",
            description="desc",
            vulnerability_type="IDOR / Broken Object Level Authorization",
            affected_endpoint="GET /api/users/{user_id}/orders",
            cvss_score="6.5 (Medium)",
            cvss_vector="AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N",
        )
        assert "## Vulnerability Details" in report
        assert "**Vulnerability Type:** IDOR / Broken Object Level Authorization" in report
        assert "**CVSS Score:** 6.5 (Medium) — AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N" in report
        assert "**Affected Endpoint:** GET /api/users/{user_id}/orders" in report

    def test_severity_used_when_no_cvss(self):
        report = build_finding_report(title="Bug", description="desc", severity="High")
        assert "**Severity:** High" in report
        assert "CVSS Score" not in report

    def test_no_details_section_when_nothing_given(self):
        report = build_finding_report(title="Bug", description="desc")
        assert "## Vulnerability Details" not in report


class TestArtifacts:
    def test_request_response_artifacts_land_in_steps(self):
        report = build_finding_report(
            title="Bug",
            description="desc",
            artifacts=[
                {"type": "request", "label": "Attacker request", "content": "GET /api/users/456/orders HTTP/1.1"},
                {"type": "response", "label": "Victim data", "content": '{"email": "victim@test.com"}'},
            ],
        )
        steps_section = report.split("## Steps to Reproduce", 1)[1].split("## Impact", 1)[0]
        assert "**Attacker request**" in steps_section
        assert "```http" in steps_section
        assert "GET /api/users/456/orders HTTP/1.1" in steps_section
        assert "**Victim data**" in steps_section
        assert "```json" in steps_section
        assert '"email": "victim@test.com"' in steps_section

    def test_code_artifact_lands_in_root_cause(self):
        report = build_finding_report(
            title="Bug",
            description="desc",
            artifacts=[
                {"type": "code", "label": "Vulnerable handler", "content": "if True: pass", "language": "python"},
            ],
        )
        assert "## Root Cause" in report
        root_cause_section = report.split("## Root Cause", 1)[1].split("## Steps to Reproduce", 1)[0]
        assert "**Vulnerable handler**" in root_cause_section
        assert "```python" in root_cause_section
        assert "if True: pass" in root_cause_section

    def test_screenshot_artifact_lands_in_supporting_materials(self):
        report = build_finding_report(
            title="Bug",
            description="desc",
            artifacts=[
                {"type": "screenshot", "label": "PoC screenshot", "path": "poc-step1.png"},
            ],
        )
        assert "## Supporting Materials" in report
        assert "PoC screenshot" in report
        assert "poc-step1.png" in report

    def test_explicit_section_override(self):
        report = build_finding_report(
            title="Bug",
            description="desc",
            artifacts=[
                {"type": "note", "label": "Scale note", "content": "Affects 100K users", "section": "impact"},
            ],
        )
        impact_section = report.split("## Impact", 1)[1].split("## Supporting Materials", 1)[0]
        assert "Scale note" in impact_section
        assert "Affects 100K users" in impact_section

    def test_hygiene_reminder_included_by_default(self):
        report = build_finding_report(title="Bug", description="desc")
        assert "evidence-hygiene skill" in report
        assert "redact session cookies" in report

    def test_evidence_log_table_lists_all_artifacts(self):
        report = build_finding_report(
            title="Bug",
            description="desc",
            artifacts=[
                {"type": "request", "label": "Req 1", "content": "GET / HTTP/1.1", "timestamp": "2026-08-20T00:00:00Z"},
                {"type": "code", "label": "Handler", "content": "pass"},
            ],
        )
        assert "## Evidence Log" in report
        log_section = report.split("## Evidence Log", 1)[1]
        assert "| 1 | request | Req 1 | steps | 2026-08-20T00:00:00Z |" in log_section
        assert "| 2 | code | Handler | root_cause |" in log_section

    def test_unknown_artifact_type_raises(self):
        with pytest.raises(EvidenceBundlerError, match="unknown type"):
            build_finding_report(
                title="Bug", description="desc",
                artifacts=[{"type": "carrier_pigeon", "content": "x"}],
            )

    def test_unknown_section_override_raises(self):
        with pytest.raises(EvidenceBundlerError, match="unknown section"):
            build_finding_report(
                title="Bug", description="desc",
                artifacts=[{"type": "note", "content": "x", "section": "nowhere"}],
            )

    def test_artifact_missing_content_and_path_raises(self):
        with pytest.raises(EvidenceBundlerError, match="content"):
            build_finding_report(
                title="Bug", description="desc",
                artifacts=[{"type": "note"}],
            )

    def test_artifact_not_a_dict_raises(self):
        with pytest.raises(EvidenceBundlerError):
            build_finding_report(title="Bug", description="desc", artifacts=["not a dict"])


class TestStepsAndImpactAndFix:
    def test_explicit_steps_numbered(self):
        report = build_finding_report(
            title="Bug",
            description="desc",
            steps=["Log in as attacker", "Send the request", "Observe response"],
        )
        assert "1. Log in as attacker" in report
        assert "2. Send the request" in report
        assert "3. Observe response" in report

    def test_accounts_rendered_as_environment(self):
        report = build_finding_report(
            title="Bug",
            description="desc",
            attacker_account="attacker@test.com (ID 123)",
            victim_account="victim@test.com (ID 456)",
        )
        assert "**Environment:**" in report
        assert "- Attacker account: attacker@test.com (ID 123)" in report
        assert "- Victim account: victim@test.com (ID 456)" in report

    def test_recommended_fix_only_shown_when_given(self):
        no_fix = build_finding_report(title="Bug", description="desc")
        assert "## Recommended Fix" not in no_fix

        with_fix = build_finding_report(
            title="Bug", description="desc", recommended_fix="Add ownership check."
        )
        assert "## Recommended Fix" in with_fix
        assert "Add ownership check." in with_fix


class TestArtifactDataclass:
    def test_resolved_section_defaults(self):
        assert Artifact(type="request").resolved_section() == "steps"
        assert Artifact(type="code").resolved_section() == "root_cause"
        assert Artifact(type="screenshot").resolved_section() == "supporting"

    def test_resolved_section_override_wins(self):
        assert Artifact(type="request", section="impact").resolved_section() == "impact"

    def test_resolved_language_defaults_and_override(self):
        assert Artifact(type="response").resolved_language() == "json"
        assert Artifact(type="response", language="xml").resolved_language() == "xml"


class TestEvidenceBundlerToolWrapper:
    def test_returns_markdown_text_directly(self):
        result = evidence_bundler_tool(title="Bug", description="desc")
        assert isinstance(result, str)
        assert result.startswith("# Bug")
        # Not JSON — a plain report, not wrapped in an error/result envelope
        with pytest.raises(json.JSONDecodeError):
            json.loads(result)

    def test_missing_required_fields_returns_tool_error_json(self):
        result = evidence_bundler_tool(title="", description="")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "title" in parsed["error"]

    def test_malformed_artifact_returns_tool_error_json(self):
        result = evidence_bundler_tool(
            title="Bug", description="desc", artifacts=[{"type": "nonsense", "content": "x"}]
        )
        parsed = json.loads(result)
        assert "error" in parsed

    def test_output_path_writes_file_and_returns_confirmation(self, tmp_path):
        out = tmp_path / "finding-001.md"
        result = evidence_bundler_tool(
            title="Bug",
            description="desc",
            output_path=str(out),
        )
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["path"] == str(out)
        assert parsed["bytes_written"] > 0
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert content.startswith("# Bug")

    def test_output_path_write_failure_returns_tool_error(self, tmp_path):
        bad_path = str(tmp_path / "nonexistent_dir" / "report.md")
        result = evidence_bundler_tool(title="Bug", description="desc", output_path=bad_path)
        parsed = json.loads(result)
        assert "error" in parsed


class TestRegistryRegistration:
    def test_tool_registered_with_expected_schema(self):
        entry = registry._tools.get("evidence_bundler")
        assert entry is not None
        assert entry.toolset == "evidence"
        assert entry.schema["name"] == "evidence_bundler"
        props = entry.schema["parameters"]["properties"]
        assert "title" in props
        assert "description" in props
        assert "artifacts" in props
        assert entry.schema["parameters"]["required"] == ["title", "description"]

    def test_handler_dispatches_through_registry(self):
        entry = registry._tools.get("evidence_bundler")
        result = entry.handler({"title": "Registry Bug", "description": "via handler"})
        assert result.startswith("# Registry Bug")

    def test_handler_passes_artifacts_and_output_path(self, tmp_path):
        entry = registry._tools.get("evidence_bundler")
        out = tmp_path / "r.md"
        result = entry.handler({
            "title": "T",
            "description": "D",
            "artifacts": [{"type": "note", "content": "n"}],
            "output_path": str(out),
        })
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert out.exists()
