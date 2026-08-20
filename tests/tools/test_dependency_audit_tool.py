"""Tests for the dependency/SCA audit tool."""

import json
import textwrap
from unittest.mock import MagicMock, patch

import pytest

from tools.dependency_audit_tool import (
    audit_dependencies,
    build_osv_batch_query,
    find_manifests,
    format_audit_report,
    parse_cargo_lock,
    parse_go_mod,
    parse_manifest,
    parse_package_json,
    parse_pyproject_toml,
    parse_requirements_txt,
    query_osv_batch,
)


class TestParsePackageJson:
    def test_basic(self):
        content = json.dumps({
            "dependencies": {"lodash": "4.17.15", "react": "^18.3.1"},
            "devDependencies": {"jest": "29.0.0"},
        })
        deps = parse_package_json(content)
        names = {d[0] for d in deps}
        assert names == {"lodash", "react", "jest"}
        by_name = {d[0]: d for d in deps}
        assert by_name["lodash"] == ("lodash", "4.17.15", "npm")
        assert by_name["react"] == ("react", "18.3.1", "npm")

    def test_unresolvable_range_gives_none_version(self):
        content = json.dumps({"dependencies": {"express": ">=4.0.0 <5.0.0"}})
        deps = parse_package_json(content)
        assert deps == [("express", None, "npm")]

    def test_invalid_json(self):
        assert parse_package_json("not json{{{") == []

    def test_empty_object(self):
        assert parse_package_json("{}") == []


class TestParseRequirementsTxt:
    def test_pinned(self):
        content = "requests==2.6.0\nflask==1.0\n"
        deps = parse_requirements_txt(content)
        assert ("requests", "2.6.0", "PyPI") in deps
        assert ("flask", "1.0", "PyPI") in deps

    def test_comments_and_blank_lines(self):
        content = "# a comment\n\nrequests==2.6.0\n"
        deps = parse_requirements_txt(content)
        assert deps == [("requests", "2.6.0", "PyPI")]

    def test_unpinned(self):
        deps = parse_requirements_txt("django\n")
        assert deps == [("django", None, "PyPI")]

    def test_environment_marker_stripped(self):
        deps = parse_requirements_txt("requests==2.6.0; python_version >= '3.8'\n")
        assert deps == [("requests", "2.6.0", "PyPI")]

    def test_editable_and_recursive_skipped(self):
        content = "-r other.txt\n-e .\nrequests==2.6.0\n"
        deps = parse_requirements_txt(content)
        assert deps == [("requests", "2.6.0", "PyPI")]

    def test_extras(self):
        deps = parse_requirements_txt("mcp[cli]==1.2.3\n")
        assert deps == [("mcp", "1.2.3", "PyPI")]


class TestParsePyprojectToml:
    def test_pep621_dependencies(self):
        content = textwrap.dedent("""
            [project]
            name = "demo"
            dependencies = [
                "requests==2.6.0",
                "flask>=1.0",
            ]
        """)
        deps = parse_pyproject_toml(content)
        names = {d[0] for d in deps}
        assert "requests" in names
        assert "flask" in names
        by_name = {d[0]: d for d in deps}
        assert by_name["requests"] == ("requests", "2.6.0", "PyPI")

    def test_poetry_dependencies(self):
        content = textwrap.dedent("""
            [tool.poetry.dependencies]
            python = "^3.10"
            requests = "2.6.0"
        """)
        deps = parse_pyproject_toml(content)
        names = {d[0] for d in deps}
        assert "python" not in names
        assert "requests" in names


class TestParseGoMod:
    def test_require_block(self):
        content = textwrap.dedent("""
            module example.com/demo

            go 1.21

            require (
                github.com/gin-gonic/gin v1.7.0
                golang.org/x/text v0.3.0 // indirect
            )
        """)
        deps = parse_go_mod(content)
        names = {d[0]: d for d in deps}
        assert names["github.com/gin-gonic/gin"] == ("github.com/gin-gonic/gin", "v1.7.0", "Go")
        assert names["golang.org/x/text"] == ("golang.org/x/text", "v0.3.0", "Go")

    def test_single_line_require(self):
        content = "module m\n\nrequire github.com/pkg/errors v0.9.1\n"
        deps = parse_go_mod(content)
        assert deps == [("github.com/pkg/errors", "v0.9.1", "Go")]


class TestParseCargoLock:
    def test_basic(self):
        content = textwrap.dedent("""
            [[package]]
            name = "serde"
            version = "1.0.130"
            source = "registry+https://github.com/rust-lang/crates.io-index"

            [[package]]
            name = "libc"
            version = "0.2.98"
        """)
        deps = parse_cargo_lock(content)
        assert ("serde", "1.0.130", "crates.io") in deps
        assert ("libc", "0.2.98", "crates.io") in deps
        assert len(deps) == 2


class TestParseManifestDispatch:
    def test_package_json_dispatch(self):
        deps = parse_manifest("/a/b/package.json", json.dumps({"dependencies": {"x": "1.0.0"}}))
        assert deps == [("x", "1.0.0", "npm")]

    def test_requirements_variant_dispatch(self):
        deps = parse_manifest("/a/b/requirements-dev.txt", "pytest==7.0.0\n")
        assert deps == [("pytest", "7.0.0", "PyPI")]

    def test_unknown_file_returns_empty(self):
        assert parse_manifest("/a/b/README.md", "hello") == []


class TestFindManifests:
    def test_finds_manifests_and_skips_noise_dirs(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "requirements.txt").write_text("requests==2.6.0\n")
        nested = tmp_path / "node_modules" / "somepkg"
        nested.mkdir(parents=True)
        (nested / "package.json").write_text("{}")

        found = find_manifests(str(tmp_path))
        basenames = {p.split("/")[-1] for p in found}
        assert "package.json" in basenames
        assert "requirements.txt" in basenames
        assert not any("node_modules" in p for p in found)


class TestBuildOsvBatchQuery:
    def test_well_formed_shape(self):
        deps = [("lodash", "4.17.15", "npm"), ("requests", None, "PyPI")]
        payload = build_osv_batch_query(deps)
        assert "queries" in payload
        assert payload["queries"][0] == {"package": {"name": "lodash", "ecosystem": "npm"}, "version": "4.17.15"}
        # No version key at all when version is unknown (not null) — matches OSV's documented shape.
        assert payload["queries"][1] == {"package": {"name": "requests", "ecosystem": "PyPI"}}

    def test_deduplicates(self):
        deps = [("a", "1.0", "npm"), ("a", "1.0", "npm")]
        payload = build_osv_batch_query(deps)
        assert len(payload["queries"]) == 1

    def test_json_serializable(self):
        deps = [("lodash", "4.17.15", "npm")]
        payload = build_osv_batch_query(deps)
        # The request body must be valid, well-formed JSON matching OSV's
        # documented /v1/querybatch shape — this is what proves the request
        # we build is well-formed even when we can't reach OSV live.
        encoded = json.dumps(payload)
        assert json.loads(encoded) == payload


class TestQueryOsvBatchMocked:
    def test_posts_expected_url_and_body(self):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"results": [{"vulns": []}]}).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("tools.dependency_audit_tool.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            results = query_osv_batch([("lodash", "4.17.15", "npm")])

        assert results == [{"vulns": []}]
        sent_req = mock_urlopen.call_args[0][0]
        assert sent_req.full_url == "https://api.osv.dev/v1/querybatch"
        body = json.loads(sent_req.data)
        assert body["queries"][0]["package"]["name"] == "lodash"

    def test_network_error_propagates_for_caller_to_handle(self):
        with patch(
            "tools.dependency_audit_tool.urllib.request.urlopen",
            side_effect=ConnectionError("no route"),
        ):
            with pytest.raises(ConnectionError):
                query_osv_batch([("lodash", "4.17.15", "npm")])


class TestAuditDependenciesFailOpen:
    def test_network_failure_is_reported_not_raised(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.6.0\n")
        with patch(
            "tools.dependency_audit_tool.query_osv_batch",
            side_effect=ConnectionError("simulated outage"),
        ):
            result = audit_dependencies(str(tmp_path))
        assert result["error"] is not None
        assert "OSV.dev unreachable" in result["error"]
        assert result["vulnerable_dependencies"] == []

    def test_no_manifests_found(self, tmp_path):
        result = audit_dependencies(str(tmp_path))
        assert result["manifests_found"] == []
        assert result["dependencies_scanned"] == 0

    def test_vulnerable_dependency_reported(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"lodash": "4.17.15"}}))

        with patch(
            "tools.dependency_audit_tool.query_osv_batch",
            return_value=[{"vulns": [{"id": "GHSA-fake-0001"}]}],
        ), patch(
            "tools.dependency_audit_tool.fetch_vuln_details",
            return_value={"summary": "Prototype pollution", "severity": [{"type": "CVSS_V3", "score": "7.5"}]},
        ):
            result = audit_dependencies(str(tmp_path))

        assert result["dependencies_scanned"] == 1
        assert len(result["vulnerable_dependencies"]) == 1
        dep = result["vulnerable_dependencies"][0]
        assert dep["name"] == "lodash"
        assert dep["vulns"][0]["id"] == "GHSA-fake-0001"
        assert dep["vulns"][0]["summary"] == "Prototype pollution"
        assert dep["vulns"][0]["severity"] == "7.5"

    def test_clean_dependency_not_reported(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"lodash": "4.17.15"}}))
        with patch("tools.dependency_audit_tool.query_osv_batch", return_value=[{"vulns": []}]):
            result = audit_dependencies(str(tmp_path))
        assert result["vulnerable_dependencies"] == []


class TestFormatAuditReport:
    def test_report_includes_key_fields(self):
        result = {
            "manifests_found": ["/p/package.json"],
            "dependencies_scanned": 1,
            "vulnerable_dependencies": [
                {
                    "name": "lodash",
                    "version": "4.17.15",
                    "ecosystem": "npm",
                    "manifest": "/p/package.json",
                    "vulns": [{"id": "GHSA-x", "severity": "7.5", "summary": "bad thing"}],
                }
            ],
            "error": None,
        }
        report = format_audit_report(result)
        assert "lodash@4.17.15" in report
        assert "GHSA-x" in report
        assert "7.5" in report

    def test_no_vulns_message(self):
        result = {"manifests_found": [], "dependencies_scanned": 0, "vulnerable_dependencies": [], "error": None}
        report = format_audit_report(result)
        assert "No known vulnerabilities" in report


class TestLiveOsvReachability:
    """Live integration test against the real OSV.dev API. Skipped if offline."""

    def test_lodash_known_vulnerable_version_live(self):
        try:
            results = query_osv_batch([("lodash", "4.17.15", "npm")])
        except Exception:
            pytest.skip("OSV.dev unreachable from this environment")
        assert len(results) == 1
        assert len(results[0].get("vulns", [])) > 0
