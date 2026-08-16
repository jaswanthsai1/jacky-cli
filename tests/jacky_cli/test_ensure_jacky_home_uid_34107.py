"""Regression tests for #34107 — Docker UID/GID handling in ensure_jacky_home.

When Jacky runs in Docker with ``JACKY_UID=1000`` / ``JACKY_GID=911``,
the entrypoint chowns the top-level ``JACKY_HOME`` once at startup. But
subdirectories created at runtime by ``ensure_jacky_home()`` — especially
for profile namespaces under ``profiles/<name>/`` spawned by kanban
workers — were landing as ``root:root`` and blocking subsequent
uid-mapped worker invocations with ``PermissionError [Errno 13]``.

The fix is a ``_chown_to_jacky_uid`` helper that reads the env vars and
applies chown after ``mkdir``, invoked from ``_secure_dir`` (which already
runs after every directory creation in the home-init path).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# _resolve_jacky_uid_gid
# ---------------------------------------------------------------------------


class TestResolveJackyUidGid:
    def test_returns_parsed_values_when_both_set(self, monkeypatch):
        monkeypatch.setenv("JACKY_UID", "1000")
        monkeypatch.setenv("JACKY_GID", "911")
        from jacky_cli.config import _resolve_jacky_uid_gid
        uid, gid = _resolve_jacky_uid_gid()
        assert uid == 1000
        assert gid == 911

    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("JACKY_UID", raising=False)
        monkeypatch.delenv("JACKY_GID", raising=False)
        from jacky_cli.config import _resolve_jacky_uid_gid
        uid, gid = _resolve_jacky_uid_gid()
        assert uid is None
        assert gid is None

    def test_uid_only_returns_gid_none(self, monkeypatch):
        monkeypatch.setenv("JACKY_UID", "1000")
        monkeypatch.delenv("JACKY_GID", raising=False)
        from jacky_cli.config import _resolve_jacky_uid_gid
        uid, gid = _resolve_jacky_uid_gid()
        assert uid == 1000
        assert gid is None

    def test_invalid_uid_returns_none_for_that_field(self, monkeypatch):
        monkeypatch.setenv("JACKY_UID", "not-a-number")
        monkeypatch.setenv("JACKY_GID", "911")
        from jacky_cli.config import _resolve_jacky_uid_gid
        uid, gid = _resolve_jacky_uid_gid()
        assert uid is None
        assert gid == 911

    def test_empty_string_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv("JACKY_UID", "")
        monkeypatch.setenv("JACKY_GID", "")
        from jacky_cli.config import _resolve_jacky_uid_gid
        uid, gid = _resolve_jacky_uid_gid()
        assert uid is None
        assert gid is None

    def test_whitespace_padded_values(self, monkeypatch):
        monkeypatch.setenv("JACKY_UID", " 1000 ")
        monkeypatch.setenv("JACKY_GID", "  911")
        from jacky_cli.config import _resolve_jacky_uid_gid
        uid, gid = _resolve_jacky_uid_gid()
        assert uid == 1000
        assert gid == 911

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific")
    def test_windows_returns_none_none(self, monkeypatch):
        monkeypatch.setenv("JACKY_UID", "1000")
        monkeypatch.setenv("JACKY_GID", "911")
        from jacky_cli.config import _resolve_jacky_uid_gid
        uid, gid = _resolve_jacky_uid_gid()
        assert uid is None
        assert gid is None


# ---------------------------------------------------------------------------
# _chown_to_jacky_uid
# ---------------------------------------------------------------------------


class TestChownToJackyUid:
    def test_calls_os_chown_when_both_set(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JACKY_UID", "1000")
        monkeypatch.setenv("JACKY_GID", "911")
        from jacky_cli import config as cfg

        d = tmp_path / "subdir"
        d.mkdir()

        with patch.object(cfg.os, "chown") as mock_chown:
            cfg._chown_to_jacky_uid(d)
        mock_chown.assert_called_once_with(d, 1000, 911)

    def test_uses_minus_one_for_missing_field(self, tmp_path, monkeypatch):
        """When only one env var is set, the other field passes -1 to
        os.chown which means 'do not change' on POSIX."""
        monkeypatch.setenv("JACKY_UID", "1000")
        monkeypatch.delenv("JACKY_GID", raising=False)
        from jacky_cli import config as cfg

        d = tmp_path / "subdir"
        d.mkdir()

        with patch.object(cfg.os, "chown") as mock_chown:
            cfg._chown_to_jacky_uid(d)
        mock_chown.assert_called_once_with(d, 1000, -1)

    def test_no_op_when_neither_set(self, tmp_path, monkeypatch):
        monkeypatch.delenv("JACKY_UID", raising=False)
        monkeypatch.delenv("JACKY_GID", raising=False)
        from jacky_cli import config as cfg

        d = tmp_path / "subdir"
        d.mkdir()

        with patch.object(cfg.os, "chown") as mock_chown:
            cfg._chown_to_jacky_uid(d)
        mock_chown.assert_not_called()

    def test_eperm_is_silently_swallowed(self, tmp_path, monkeypatch):
        """When running as non-root, os.chown raises EPERM. That's fine —
        the entrypoint's startup chown -R will pick it up on restart, and
        in most cases the dir was already correctly-owned by the calling
        user anyway."""
        monkeypatch.setenv("JACKY_UID", "1000")
        monkeypatch.setenv("JACKY_GID", "911")
        from jacky_cli import config as cfg

        d = tmp_path / "subdir"
        d.mkdir()

        def _raises_eperm(*args, **kwargs):
            raise PermissionError("operation not permitted")

        with patch.object(cfg.os, "chown", side_effect=_raises_eperm):
            # Must not raise — the catch is non-fatal.
            cfg._chown_to_jacky_uid(d)

    def test_attributeerror_swallowed_for_windows_compat(self, tmp_path, monkeypatch):
        """os.chown doesn't exist on Windows. Catching AttributeError keeps
        the helper portable."""
        monkeypatch.setenv("JACKY_UID", "1000")
        monkeypatch.setenv("JACKY_GID", "911")
        from jacky_cli import config as cfg

        d = tmp_path / "subdir"
        d.mkdir()

        with patch.object(cfg.os, "chown", side_effect=AttributeError("no chown on this platform")):
            cfg._chown_to_jacky_uid(d)  # must not raise


# ---------------------------------------------------------------------------
# End-to-end: _secure_dir now also chowns
# ---------------------------------------------------------------------------


class TestSecureDirChown:
    @pytest.mark.skipif(sys.platform == "win32", reason="chown is no-op on Windows")
    def test_secure_dir_invokes_chown_when_env_set(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JACKY_UID", "1000")
        monkeypatch.setenv("JACKY_GID", "911")
        from jacky_cli import config as cfg

        d = tmp_path / "subdir"
        d.mkdir()

        with patch.object(cfg.os, "chown") as mock_chown:
            cfg._secure_dir(d)
        mock_chown.assert_called_once_with(d, 1000, 911)

    @pytest.mark.skipif(sys.platform == "win32", reason="chown is no-op on Windows")
    def test_secure_dir_no_chown_when_env_unset(self, tmp_path, monkeypatch):
        monkeypatch.delenv("JACKY_UID", raising=False)
        monkeypatch.delenv("JACKY_GID", raising=False)
        from jacky_cli import config as cfg

        d = tmp_path / "subdir"
        d.mkdir()

        with patch.object(cfg.os, "chown") as mock_chown:
            cfg._secure_dir(d)
        mock_chown.assert_not_called()
