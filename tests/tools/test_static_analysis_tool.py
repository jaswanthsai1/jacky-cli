"""Tests for tools/static_analysis_tool.py."""

import json
import subprocess
import textwrap
from unittest.mock import MagicMock, patch

import pytest

from tools.static_analysis_tool import (
    _static_analysis_handler,
    check_semgrep_available,
    check_static_analysis_available,
    find_source_files,
    run_heuristic_scan,
    run_semgrep,
    scan_js_source,
    scan_python_source,
    scan_source_file,
    static_analysis,
)


def _write(tmp_path, relpath, content):
    p = tmp_path / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Python heuristic (AST) scanner
# ---------------------------------------------------------------------------


class TestScanPythonSourceCommandInjection:
    def test_os_system_flagged(self):
        findings = scan_python_source("import os\nos.system(cmd)\n", "f.py")
        assert any(f["category"] == "command-injection" for f in findings)

    def test_os_popen_flagged(self):
        findings = scan_python_source("import os\nos.popen(cmd)\n", "f.py")
        assert any(f["category"] == "command-injection" for f in findings)

    def test_subprocess_shell_true_flagged(self):
        code = "import subprocess\nsubprocess.run(cmd, shell=True)\n"
        findings = scan_python_source(code, "f.py")
        assert any(f["rule_id"] == "heuristic-command-injection-subprocess" for f in findings)

    def test_subprocess_without_shell_true_not_flagged(self):
        code = "import subprocess\nsubprocess.run(['ls', '-la'])\n"
        findings = scan_python_source(code, "f.py")
        assert not any(f["category"] == "command-injection" for f in findings)

    def test_eval_on_variable_flagged(self):
        findings = scan_python_source("eval(user_input)\n", "f.py")
        assert any(f["rule_id"] == "heuristic-eval-exec" for f in findings)

    def test_eval_on_literal_not_flagged(self):
        findings = scan_python_source("eval('1 + 1')\n", "f.py")
        assert not any(f["rule_id"] == "heuristic-eval-exec" for f in findings)


class TestScanPythonSourceDeserialization:
    def test_pickle_loads_flagged(self):
        findings = scan_python_source("import pickle\npickle.loads(data)\n", "f.py")
        assert any(f["category"] == "unsafe-deserialization" for f in findings)

    def test_pickle_load_flagged(self):
        findings = scan_python_source("import pickle\npickle.load(fh)\n", "f.py")
        assert any(f["category"] == "unsafe-deserialization" for f in findings)

    def test_yaml_load_without_safe_loader_flagged(self):
        findings = scan_python_source("import yaml\nyaml.load(data)\n", "f.py")
        assert any(f["rule_id"] == "heuristic-unsafe-yaml-load" for f in findings)

    def test_yaml_load_with_safe_loader_not_flagged(self):
        code = "import yaml\nyaml.load(data, Loader=yaml.SafeLoader)\n"
        findings = scan_python_source(code, "f.py")
        assert not any(f["rule_id"] == "heuristic-unsafe-yaml-load" for f in findings)


class TestScanPythonSourceSqlInjection:
    def test_string_concat_execute_flagged(self):
        code = "cursor.execute('SELECT * FROM t WHERE x=' + val)\n"
        findings = scan_python_source(code, "f.py")
        assert any(f["category"] == "sql-injection" for f in findings)

    def test_fstring_execute_flagged(self):
        code = 'cursor.execute(f"SELECT * FROM t WHERE x={val}")\n'
        findings = scan_python_source(code, "f.py")
        assert any(f["category"] == "sql-injection" for f in findings)

    def test_format_execute_flagged(self):
        code = 'cursor.execute("SELECT * FROM t WHERE x={}".format(val))\n'
        findings = scan_python_source(code, "f.py")
        assert any(f["category"] == "sql-injection" for f in findings)

    def test_parameterized_query_not_flagged(self):
        code = 'cursor.execute("SELECT * FROM t WHERE x=%s", (val,))\n'
        findings = scan_python_source(code, "f.py")
        assert not any(f["category"] == "sql-injection" for f in findings)


class TestScanPythonSourceSsrf:
    def test_requests_get_with_variable_url_flagged(self):
        code = "import requests\nrequests.get(user_url)\n"
        findings = scan_python_source(code, "f.py")
        assert any(f["category"] == "ssrf" for f in findings)

    def test_requests_get_with_literal_url_not_flagged(self):
        code = "import requests\nrequests.get('https://example.com')\n"
        findings = scan_python_source(code, "f.py")
        assert not any(f["category"] == "ssrf" for f in findings)


class TestScanPythonSourceHardcodedSecret:
    def test_password_literal_flagged(self):
        findings = scan_python_source('PASSWORD = "hunter2hunter2"\n', "f.py")
        assert any(f["category"] == "hardcoded-secret" for f in findings)

    def test_api_key_literal_flagged(self):
        findings = scan_python_source('API_KEY = "sk_live_abcdefghijklmnop"\n', "f.py")
        assert any(f["category"] == "hardcoded-secret" for f in findings)

    def test_placeholder_value_not_flagged(self):
        findings = scan_python_source('PASSWORD = "changeme"\n', "f.py")
        assert not any(f["category"] == "hardcoded-secret" for f in findings)

    def test_short_value_not_flagged(self):
        findings = scan_python_source('PASSWORD = "abc"\n', "f.py")
        assert not any(f["category"] == "hardcoded-secret" for f in findings)

    def test_unrelated_variable_not_flagged(self):
        findings = scan_python_source('GREETING = "hello world 123"\n', "f.py")
        assert not any(f["category"] == "hardcoded-secret" for f in findings)


class TestScanPythonSourceRobustness:
    def test_syntax_error_returns_empty_not_raises(self):
        assert scan_python_source("def broken(:\n", "f.py") == []

    def test_clean_file_no_findings(self):
        code = "def add(a, b):\n    return a + b\n"
        assert scan_python_source(code, "f.py") == []

    def test_findings_include_file_and_line(self):
        findings = scan_python_source("import os\nos.system(cmd)\n", "myfile.py")
        assert findings[0]["file"] == "myfile.py"
        assert findings[0]["line"] == 2
        assert findings[0]["engine"] == "heuristic"


# ---------------------------------------------------------------------------
# JS/TS heuristic (regex) scanner
# ---------------------------------------------------------------------------


class TestScanJsSource:
    def test_eval_flagged(self):
        findings = scan_js_source("eval(userInput);\n", "f.js")
        assert any(f["rule_id"] == "heuristic-eval-injection" for f in findings)

    def test_exec_with_variable_flagged(self):
        findings = scan_js_source("exec(cmd);\n", "f.js")
        assert any(f["category"] == "command-injection" for f in findings)

    def test_exec_with_literal_not_flagged(self):
        findings = scan_js_source("exec('ls -la');\n", "f.js")
        assert not any(f["category"] == "command-injection" for f in findings)

    def test_innerhtml_dynamic_flagged(self):
        findings = scan_js_source("el.innerHTML = userValue;\n", "f.js")
        assert any(f["category"] == "xss" for f in findings)

    def test_sql_template_literal_flagged(self):
        code = "db.query(`SELECT * FROM t WHERE x=${val}`);\n"
        findings = scan_js_source(code, "f.js")
        assert any(f["category"] == "sql-injection" for f in findings)

    def test_fetch_with_variable_url_flagged(self):
        findings = scan_js_source("fetch(userUrl);\n", "f.js")
        assert any(f["category"] == "ssrf" for f in findings)

    def test_fetch_with_literal_url_not_flagged(self):
        findings = scan_js_source("fetch('https://example.com');\n", "f.js")
        assert not any(f["category"] == "ssrf" for f in findings)

    def test_hardcoded_secret_flagged(self):
        code = 'const apiKey = "sk_live_abcdefghijklmnop";\n'
        findings = scan_js_source(code, "f.js")
        assert any(f["category"] == "hardcoded-secret" for f in findings)

    def test_clean_file_no_findings(self):
        assert scan_js_source("function add(a, b) { return a + b; }\n", "f.js") == []


# ---------------------------------------------------------------------------
# File discovery + dispatch
# ---------------------------------------------------------------------------


class TestFindSourceFiles:
    def test_finds_supported_extensions_and_skips_noise_dirs(self, tmp_path):
        _write(tmp_path, "app.py", "x = 1\n")
        _write(tmp_path, "app.ts", "const x = 1;\n")
        _write(tmp_path, "README.md", "hello\n")
        _write(tmp_path, "node_modules/pkg/index.js", "x = 1;\n")

        found = find_source_files(str(tmp_path))
        basenames = {p.split("/")[-1] for p in found}
        assert "app.py" in basenames
        assert "app.ts" in basenames
        assert "README.md" not in basenames
        assert not any("node_modules" in p for p in found)

    def test_single_file_path_returns_that_file(self, tmp_path):
        f = _write(tmp_path, "app.py", "x = 1\n")
        assert find_source_files(str(f)) == [str(f)]

    def test_language_filter_python_only(self, tmp_path):
        _write(tmp_path, "app.py", "x = 1\n")
        _write(tmp_path, "app.js", "x = 1;\n")
        found = find_source_files(str(tmp_path), languages=["python"])
        assert all(p.endswith(".py") for p in found)

    def test_language_filter_javascript_only(self, tmp_path):
        _write(tmp_path, "app.py", "x = 1\n")
        _write(tmp_path, "app.js", "x = 1;\n")
        found = find_source_files(str(tmp_path), languages=["javascript"])
        assert all(p.endswith(".js") for p in found)


class TestScanSourceFile:
    def test_dispatches_python(self, tmp_path):
        f = _write(tmp_path, "app.py", "import os\nos.system(cmd)\n")
        findings = scan_source_file(str(f))
        assert any(fnd["category"] == "command-injection" for fnd in findings)

    def test_dispatches_js(self, tmp_path):
        f = _write(tmp_path, "app.js", "eval(x);\n")
        findings = scan_source_file(str(f))
        assert any(fnd["rule_id"] == "heuristic-eval-injection" for fnd in findings)

    def test_unsupported_extension_returns_empty(self, tmp_path):
        f = _write(tmp_path, "notes.txt", "os.system(cmd)\n")
        assert scan_source_file(str(f)) == []


class TestRunHeuristicScan:
    def test_scans_directory_and_caps_findings(self, tmp_path):
        for i in range(3):
            _write(tmp_path, f"f{i}.py", "import os\nos.system(cmd)\n")
        out = run_heuristic_scan(str(tmp_path), max_findings=2)
        assert out["files_scanned"] == 3
        assert len(out["findings"]) == 2
        assert out["truncated"] is True


# ---------------------------------------------------------------------------
# semgrep engine — mocked subprocess, no real network/binary dependency
# ---------------------------------------------------------------------------


class TestCheckSemgrepAvailable:
    def test_true_when_on_path(self):
        with patch("tools.static_analysis_tool.shutil.which", return_value="/usr/bin/semgrep"):
            assert check_semgrep_available() is True

    def test_false_when_not_on_path(self):
        with patch("tools.static_analysis_tool.shutil.which", return_value=None):
            assert check_semgrep_available() is False


class TestRunSemgrepMocked:
    def test_raises_when_unavailable(self):
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=False):
            with pytest.raises(RuntimeError, match="not installed"):
                run_semgrep("/some/path")

    def test_parses_json_output(self):
        payload = {"results": [{"check_id": "x", "path": "f.py", "start": {"line": 1}, "end": {"line": 1},
                                 "extra": {"message": "m", "severity": "ERROR", "lines": "code", "metadata": {}}}]}
        mock_proc = MagicMock(returncode=1, stdout=json.dumps(payload), stderr="")
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=True), \
             patch("tools.static_analysis_tool.subprocess.run", return_value=mock_proc) as mock_run:
            result = run_semgrep("/some/path")
        assert result == payload
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "semgrep"
        assert "/some/path" in cmd

    def test_returncode_zero_is_clean_no_findings(self):
        mock_proc = MagicMock(returncode=0, stdout=json.dumps({"results": []}), stderr="")
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=True), \
             patch("tools.static_analysis_tool.subprocess.run", return_value=mock_proc):
            result = run_semgrep("/some/path")
        assert result == {"results": []}

    def test_fatal_exit_code_raises(self):
        mock_proc = MagicMock(returncode=2, stdout="", stderr="fatal: bad config")
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=True), \
             patch("tools.static_analysis_tool.subprocess.run", return_value=mock_proc):
            with pytest.raises(RuntimeError, match="exited 2"):
                run_semgrep("/some/path")

    def test_timeout_raises_runtime_error(self):
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=True), \
             patch("tools.static_analysis_tool.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="semgrep", timeout=120)):
            with pytest.raises(RuntimeError, match="timed out"):
                run_semgrep("/some/path")

    def test_unparsable_output_raises_runtime_error(self):
        mock_proc = MagicMock(returncode=0, stdout="not json{{{", stderr="")
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=True), \
             patch("tools.static_analysis_tool.subprocess.run", return_value=mock_proc):
            with pytest.raises(RuntimeError, match="could not parse"):
                run_semgrep("/some/path")

    def test_missing_binary_oserror_raises_runtime_error(self):
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=True), \
             patch("tools.static_analysis_tool.subprocess.run", side_effect=OSError("no such file")):
            with pytest.raises(RuntimeError, match="failed to execute semgrep"):
                run_semgrep("/some/path")


# ---------------------------------------------------------------------------
# static_analysis() top-level dispatch + graceful degradation
# ---------------------------------------------------------------------------


class TestStaticAnalysisTopLevel:
    def test_missing_path_error(self):
        result = static_analysis("")
        assert result["success"] is False
        assert "required" in result["error"]

    def test_nonexistent_path_error(self, tmp_path):
        result = static_analysis(str(tmp_path / "does_not_exist.py"))
        assert result["success"] is False
        assert "does not exist" in result["error"]

    def test_unknown_engine_error(self, tmp_path):
        f = _write(tmp_path, "app.py", "x = 1\n")
        result = static_analysis(str(f), engine="nonsense")
        assert result["success"] is False
        assert "Unknown engine" in result["error"]

    def test_forced_heuristic_engine_ignores_semgrep(self, tmp_path):
        f = _write(tmp_path, "app.py", "import os\nos.system(cmd)\n")
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=True):
            result = static_analysis(str(f), engine="heuristic")
        assert result["success"] is True
        assert result["engine"] == "heuristic"

    def test_auto_falls_back_when_semgrep_not_installed(self, tmp_path):
        f = _write(tmp_path, "app.py", "import os\nos.system(cmd)\n")
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=False):
            result = static_analysis(str(f), engine="auto")
        assert result["success"] is True
        assert result["engine"] == "heuristic"
        assert result["warning"] is not None
        assert result["findings_count"] >= 1

    def test_forced_semgrep_engine_reports_error_when_unavailable_not_raise(self, tmp_path):
        f = _write(tmp_path, "app.py", "x = 1\n")
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=False):
            result = static_analysis(str(f), engine="semgrep")
        assert result["success"] is False
        assert "semgrep" in result["error"].lower()

    def test_auto_falls_back_when_semgrep_raises_at_runtime(self, tmp_path):
        f = _write(tmp_path, "app.py", "import os\nos.system(cmd)\n")
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=True), \
             patch("tools.static_analysis_tool.run_semgrep", side_effect=RuntimeError("semgrep crashed")):
            result = static_analysis(str(f), engine="auto")
        assert result["success"] is True
        assert result["engine"] == "heuristic"
        assert "semgrep crashed" in result["warning"]

    def test_semgrep_engine_success_path_mocked(self, tmp_path):
        f = _write(tmp_path, "app.py", "x = 1\n")
        payload = {
            "results": [
                {
                    "check_id": "python-hardcoded-secret-assignment",
                    "path": str(f),
                    "start": {"line": 1},
                    "end": {"line": 1},
                    "extra": {
                        "message": "hardcoded secret",
                        "severity": "WARNING",
                        "lines": "PASSWORD = 'x'",
                        "metadata": {"category": "hardcoded-secret", "cwe": "CWE-798"},
                    },
                }
            ],
            "paths": {"scanned": [str(f)]},
        }
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=True), \
             patch("tools.static_analysis_tool.run_semgrep", return_value=payload):
            result = static_analysis(str(f), engine="semgrep")
        assert result["success"] is True
        assert result["engine"] == "semgrep"
        assert result["files_scanned"] == 1
        assert result["findings_count"] == 1
        finding = result["findings"][0]
        assert finding["category"] == "hardcoded-secret"
        assert finding["severity"] == "medium"
        assert finding["cwe"] == "CWE-798"

    def test_max_findings_truncates(self, tmp_path):
        for i in range(4):
            _write(tmp_path, f"f{i}.py", "import os\nos.system(cmd)\n")
        with patch("tools.static_analysis_tool.check_semgrep_available", return_value=False):
            result = static_analysis(str(tmp_path), engine="auto", max_findings=2)
        assert result["findings_count"] == 2
        assert result["truncated"] is True


# ---------------------------------------------------------------------------
# Registry handler + availability
# ---------------------------------------------------------------------------


class TestStaticAnalysisHandler:
    def test_missing_path_returns_error(self):
        response = _static_analysis_handler({})
        assert "error" in json.loads(response)

    def test_valid_path_returns_json_result(self, tmp_path):
        f = _write(tmp_path, "app.py", "import os\nos.system(cmd)\n")
        response = _static_analysis_handler({"path": str(f), "engine": "heuristic"})
        data = json.loads(response)
        assert data["success"] is True
        assert data["findings_count"] >= 1

    def test_invalid_max_findings_falls_back_to_default(self, tmp_path):
        f = _write(tmp_path, "app.py", "x = 1\n")
        response = _static_analysis_handler({"path": str(f), "engine": "heuristic", "max_findings": "not-a-number"})
        data = json.loads(response)
        assert data["success"] is True


class TestCheckStaticAnalysisAvailable:
    def test_always_true(self):
        assert check_static_analysis_available() is True


class TestToolRegistration:
    def test_registered_in_registry(self):
        from tools.registry import registry
        assert registry.get_entry("static_analysis") is not None
        assert registry.get_entry("static_analysis").toolset == "static_analysis"
