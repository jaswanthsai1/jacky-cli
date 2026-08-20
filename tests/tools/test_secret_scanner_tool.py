"""Tests for tools/secret_scanner_tool.py."""

import json
import subprocess

import pytest

from tools.secret_scanner_tool import (
    _secret_scan_dispatch,
    _shannon_entropy,
    scan_directory_for_secrets,
    scan_git_history_for_secrets,
)


def _write(tmp_path, relpath, content):
    p = tmp_path / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class TestShannonEntropy:
    def test_empty_string(self):
        assert _shannon_entropy("") == 0.0

    def test_repeated_char_has_low_entropy(self):
        assert _shannon_entropy("aaaaaaaaaa") == 0.0

    def test_random_looking_string_has_higher_entropy(self):
        assert _shannon_entropy("aB3xQ9zK7mP2") > _shannon_entropy("aaaaaaaaaaaa")


class TestScanDirectoryVendorPrefixes:
    def test_finds_aws_key(self, tmp_path):
        _write(tmp_path, "config.py", 'AWS_KEY = "AKIAABCDEFGHIJKLMNOP"\n')
        result = json.loads(scan_directory_for_secrets(str(tmp_path), include_entropy=False))
        assert result["success"] is True
        rules = [f["rule"] for f in result["findings"]]
        assert any("vendor:AKIA" in r or "vendor" in r for r in rules)
        # never leak the raw key
        assert "AKIAABCDEFGHIJKLMNOP" not in json.dumps(result)

    def test_finds_github_token(self, tmp_path):
        _write(tmp_path, ".env", "GITHUB_TOKEN=ghp_" + "a" * 36 + "\n")
        result = json.loads(scan_directory_for_secrets(str(tmp_path), include_entropy=False))
        assert result["findings_count"] >= 1
        assert "ghp_" + "a" * 36 not in json.dumps(result)

    def test_finds_openai_style_key(self, tmp_path):
        _write(tmp_path, "notes.txt", "here is my key sk-" + "a" * 20 + " do not share\n")
        result = json.loads(scan_directory_for_secrets(str(tmp_path), include_entropy=False))
        assert result["findings_count"] >= 1

    def test_finds_private_key_block(self, tmp_path):
        pem = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIBOgIBAAJBAK...redacted...fakekeycontent\n"
            "-----END RSA PRIVATE KEY-----\n"
        )
        _write(tmp_path, "id_rsa", pem)
        result = json.loads(scan_directory_for_secrets(str(tmp_path), include_entropy=False))
        rules = [f["rule"] for f in result["findings"]]
        assert "private-key-pem-block" in rules

    def test_finds_generic_assignment(self, tmp_path):
        _write(tmp_path, "settings.ini", "db_password=SuperSecretValue123\n")
        result = json.loads(scan_directory_for_secrets(str(tmp_path), include_entropy=False))
        rules = [f["rule"] for f in result["findings"]]
        assert any(r.startswith("generic-assignment") for r in rules)

    def test_ignores_placeholder_values(self, tmp_path):
        _write(tmp_path, "settings.ini", "api_key=YOUR_API_KEY_HERE\napi_key=changeme\n")
        result = json.loads(scan_directory_for_secrets(str(tmp_path), include_entropy=False))
        assert result["findings_count"] == 0

    def test_clean_directory_no_findings(self, tmp_path):
        _write(tmp_path, "app.py", "def add(a, b):\n    return a + b\n")
        result = json.loads(scan_directory_for_secrets(str(tmp_path), include_entropy=False))
        assert result["success"] is True
        assert result["findings_count"] == 0

    def test_finding_has_file_and_line_location(self, tmp_path):
        _write(tmp_path, "sub/config.py", '\n\nAWS_KEY = "AKIAABCDEFGHIJKLMNOP"\n')
        result = json.loads(scan_directory_for_secrets(str(tmp_path), include_entropy=False))
        finding = result["findings"][0]
        assert finding["source"] == "sub/config.py"
        assert finding["line"] == 3

    def test_missing_directory(self):
        result = json.loads(scan_directory_for_secrets("/nonexistent/path/xyz123"))
        assert result["success"] is False

    def test_directory_required(self):
        result = json.loads(scan_directory_for_secrets(""))
        assert result["success"] is False

    def test_skips_dot_git_and_node_modules(self, tmp_path):
        _write(tmp_path, ".git/config", 'AWS_KEY = "AKIAABCDEFGHIJKLMNOP"\n')
        _write(tmp_path, "node_modules/pkg/index.js", 'AWS_KEY = "AKIAABCDEFGHIJKLMNOP"\n')
        result = json.loads(scan_directory_for_secrets(str(tmp_path), include_entropy=False))
        assert result["findings_count"] == 0

    def test_binary_file_skipped(self, tmp_path):
        p = tmp_path / "blob.bin"
        p.write_bytes(b"\x00\x01\x02AKIAABCDEFGHIJKLMNOP\xff\xfe")
        result = json.loads(scan_directory_for_secrets(str(tmp_path), include_entropy=False))
        assert result["findings_count"] == 0


class TestScanDirectoryEntropy:
    def test_high_entropy_flagged_when_enabled(self, tmp_path):
        _write(tmp_path, "token.txt", "token_value = 4f8aQ2zPx9RbT7mK1cW6nJdL0sV3yHgE\n")
        result = json.loads(
            scan_directory_for_secrets(str(tmp_path), include_entropy=True, entropy_threshold=3.0)
        )
        assert result["findings_count"] >= 1

    def test_entropy_disabled_by_default_flag(self, tmp_path):
        _write(tmp_path, "token.txt", "some ordinary sentence with no secrets at all here\n")
        result = json.loads(scan_directory_for_secrets(str(tmp_path), include_entropy=False))
        assert result["findings_count"] == 0


class TestScanGitHistory:
    def _init_repo(self, tmp_path):
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
        return tmp_path

    def test_finds_secret_added_then_removed(self, tmp_path):
        self._init_repo(tmp_path)
        f = tmp_path / "config.py"
        f.write_text('AWS_KEY = "AKIAABCDEFGHIJKLMNOP"\n', encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "add key"], cwd=tmp_path, check=True)
        f.write_text('AWS_KEY = os.environ["AWS_KEY"]\n', encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "remove key"], cwd=tmp_path, check=True)

        result = json.loads(scan_git_history_for_secrets(str(tmp_path)))
        assert result["success"] is True
        assert result["findings_count"] >= 1
        assert "AKIAABCDEFGHIJKLMNOP" not in json.dumps(result)

    def test_not_a_git_repo(self, tmp_path):
        result = json.loads(scan_git_history_for_secrets(str(tmp_path)))
        assert result["success"] is False
        assert "git repository" in result["error"]

    def test_directory_required(self):
        result = json.loads(scan_git_history_for_secrets(""))
        assert result["success"] is False

    def test_missing_directory(self):
        result = json.loads(scan_git_history_for_secrets("/nonexistent/path/xyz123"))
        assert result["success"] is False


class TestDispatch:
    def test_default_action_is_directory(self, tmp_path):
        _write(tmp_path, "app.py", "print('hi')\n")
        result = json.loads(_secret_scan_dispatch({"directory": str(tmp_path)}))
        assert result["success"] is True
        assert "files_scanned" in result

    def test_unknown_action(self, tmp_path):
        result = json.loads(_secret_scan_dispatch({"action": "bogus", "directory": str(tmp_path)}))
        assert "error" in result

    def test_git_history_action(self, tmp_path):
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        result = json.loads(_secret_scan_dispatch({"action": "git_history", "directory": str(tmp_path)}))
        assert result["success"] is True

    def test_schema_registered(self):
        from tools.registry import registry

        entry = registry.get_entry("secret_scan")
        assert entry is not None
        assert entry.schema["name"] == "secret_scan"
        assert "directory" in entry.schema["parameters"]["required"]
