from __future__ import annotations

from unittest.mock import MagicMock

import agent.file_safety as fs

from plugins.memory.retaindb import RetainDBMemoryProvider


def test_upload_file_rejects_jacky_credential_store(tmp_path, monkeypatch):
    jacky_home = tmp_path / "jacky_home"
    jacky_home.mkdir()
    auth_json = jacky_home / "auth.json"
    auth_json.write_text('{"OPENAI_API_KEY":"sk-test-secret"}', encoding="utf-8")
    monkeypatch.setattr(fs, "_jacky_home_path", lambda: jacky_home)

    provider = RetainDBMemoryProvider()
    provider._client = MagicMock()

    result = provider._dispatch("retaindb_upload_file", {"local_path": str(auth_json)})

    assert "error" in result
    assert "credential store" in result["error"]
    provider._client.upload_file.assert_not_called()


def test_upload_file_allows_regular_file(tmp_path):
    note = tmp_path / "note.md"
    note.write_text("# Note\n", encoding="utf-8")
    provider = RetainDBMemoryProvider()
    provider._client = MagicMock()
    provider._client.upload_file.return_value = {
        "file": {"id": "file-1", "name": "note.md"},
    }

    result = provider._dispatch("retaindb_upload_file", {"local_path": str(note)})

    provider._client.upload_file.assert_called_once()
    assert provider._client.upload_file.call_args.args[0] == note.read_bytes()
    assert result["file"]["id"] == "file-1"
