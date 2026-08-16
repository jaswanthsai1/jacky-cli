"""Regression tests for _apply_profile_override JACKY_HOME guard (issue #22502).

When JACKY_HOME is set to the jacky root (e.g. systemd hardcodes
JACKY_HOME=/root/.jacky), _apply_profile_override must still read
active_profile and update JACKY_HOME to the profile directory.

When JACKY_HOME is already a profile directory (.../profiles/<name>),
_apply_profile_override must trust it and return without re-reading
active_profile (child-process inheritance contract).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace



def _run_apply_profile_override(
    tmp_path, monkeypatch, *, jacky_home: str | None, active_profile: str | None,
    argv: list[str] | None = None,
):
    """Run _apply_profile_override in isolation.

    Returns the value of os.environ["JACKY_HOME"] after the call,
    or None if unset.
    """
    jacky_root = tmp_path / ".jacky"
    jacky_root.mkdir(parents=True, exist_ok=True)

    if active_profile is not None:
        (jacky_root / "active_profile").write_text(active_profile)

    if active_profile and active_profile != "default":
        (jacky_root / "profiles" / active_profile).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    if jacky_home is not None:
        monkeypatch.setenv("JACKY_HOME", jacky_home)
    else:
        monkeypatch.delenv("JACKY_HOME", raising=False)

    monkeypatch.setattr(sys, "argv", argv or ["jacky", "gateway", "start"])

    from jacky_cli.main import _apply_profile_override
    _apply_profile_override()

    return os.environ.get("JACKY_HOME")


class TestApplyProfileOverrideJackyHomeGuard:
    """Regression guard for issue #22502.

    Verifies that JACKY_HOME pointing to the jacky root does NOT suppress
    the active_profile check, while JACKY_HOME already pointing to a
    profile directory IS trusted as-is.
    """

    def test_jacky_home_at_root_with_active_profile_is_redirected(
        self, tmp_path, monkeypatch
    ):
        """JACKY_HOME=/root/.jacky + active_profile=coder must redirect
        JACKY_HOME to .../profiles/coder.

        Bug scenario from #22502: systemd sets JACKY_HOME to the jacky root
        and the user switches to a profile via `jacky profile use`.
        Before the fix, the guard returned early and active_profile was ignored.
        """
        jacky_root = tmp_path / ".jacky"
        jacky_root.mkdir(parents=True, exist_ok=True)

        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            jacky_home=str(jacky_root),
            active_profile="coder",
        )

        assert result is not None, "JACKY_HOME must be set after profile redirect"
        assert "profiles" in result, (
            f"Expected JACKY_HOME to point into profiles/ dir, got: {result!r}"
        )
        assert result.endswith("coder"), (
            f"Expected JACKY_HOME to end with 'coder', got: {result!r}"
        )

    def test_jacky_home_already_profile_dir_is_trusted(self, tmp_path, monkeypatch):
        """JACKY_HOME=.../profiles/coder must not be overridden even when
        active_profile says something different.

        Preserves the child-process inheritance contract: a subprocess spawned
        with JACKY_HOME already set to a specific profile must stay in that
        profile.
        """
        jacky_root = tmp_path / ".jacky"
        profile_dir = jacky_root / "profiles" / "coder"
        profile_dir.mkdir(parents=True, exist_ok=True)

        (jacky_root / "active_profile").write_text("other")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("JACKY_HOME", str(profile_dir))
        monkeypatch.setattr(sys, "argv", ["jacky", "gateway", "start"])

        from jacky_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("JACKY_HOME") == str(profile_dir), (
            "JACKY_HOME must remain unchanged when already pointing to a profile dir"
        )

    def test_jacky_home_unset_reads_active_profile(self, tmp_path, monkeypatch):
        """Classic case: JACKY_HOME unset + active_profile=coder must set
        JACKY_HOME to the profile directory (existing behaviour must not regress).
        """
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            jacky_home=None,
            active_profile="coder",
        )

        assert result is not None
        assert "coder" in result

    def test_sudo_explicit_profile_resolves_invoking_users_profile(self, tmp_path, monkeypatch):
        """sudo elias ... should resolve `-p elias` under SUDO_USER, not root."""
        root_home = tmp_path / "root"
        user_home = tmp_path / "home" / "jacky"
        profile_dir = user_home / ".jacky" / "profiles" / "elias"
        profile_dir.mkdir(parents=True, exist_ok=True)
        (root_home / ".jacky").mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(Path, "home", lambda: root_home)
        monkeypatch.setenv("SUDO_USER", "jacky")
        monkeypatch.delenv("JACKY_HOME", raising=False)
        monkeypatch.setattr(os, "geteuid", lambda: 0, raising=False)
        monkeypatch.setattr(sys, "argv", ["jacky", "-p", "elias", "gateway", "install", "--system"])

        import pwd

        monkeypatch.setattr(pwd, "getpwnam", lambda name: SimpleNamespace(pw_dir=str(user_home)))

        from jacky_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("JACKY_HOME") == str(profile_dir)
        assert sys.argv == ["jacky", "gateway", "install", "--system"]

    def test_jacky_home_unset_default_profile_no_redirect(self, tmp_path, monkeypatch):
        """active_profile=default must not redirect JACKY_HOME."""
        jacky_root = tmp_path / ".jacky"
        jacky_root.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("JACKY_HOME", raising=False)
        monkeypatch.setattr(sys, "argv", ["jacky", "gateway", "start"])
        (jacky_root / "active_profile").write_text("default")

        from jacky_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("JACKY_HOME") is None

    def test_subcommand_profile_flag_is_not_consumed(self, tmp_path, monkeypatch):
        """Command argv flags named --profile must stay with that command.

        Docker Desktop's MCP Toolkit uses `docker mcp gateway run --profile ...`.
        When that argv is passed through `jacky mcp add --args`, the early
        profile pre-parser must not interpret the Docker profile as a Jacky
        profile.
        """
        jacky_root = tmp_path / ".jacky"
        jacky_root.mkdir(parents=True, exist_ok=True)
        argv = [
            "jacky",
            "mcp",
            "add",
            "docker-research",
            "--command",
            "docker",
            "--args",
            "mcp",
            "gateway",
            "run",
            "--profile",
            "research",
        ]

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("JACKY_HOME", raising=False)
        monkeypatch.setattr(sys, "argv", list(argv))

        from jacky_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("JACKY_HOME") is None
        assert sys.argv == argv

    def test_profile_after_chat_subcommand_is_still_consumed(self, tmp_path, monkeypatch):
        """Profile flags historically work after normal Jacky subcommands."""
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            jacky_home=None,
            active_profile="coder",
            argv=["jacky", "chat", "-p", "coder", "-q", "hello"],
        )

        assert result is not None
        assert result.endswith("coder")
        assert sys.argv == ["jacky", "chat", "-q", "hello"]

    def test_top_level_profile_after_value_flag_is_consumed(self, tmp_path, monkeypatch):
        """Top-level --profile still works after other top-level value flags."""
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            jacky_home=None,
            active_profile="coder",
            argv=["jacky", "-m", "gpt-5", "--profile", "coder", "chat"],
        )

        assert result is not None
        assert result.endswith("coder")
        assert sys.argv == ["jacky", "-m", "gpt-5", "chat"]

    def test_top_level_profile_after_continue_flag_is_consumed(self, tmp_path, monkeypatch):
        """--continue has an optional value, so a following --profile is a flag."""
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            jacky_home=None,
            active_profile="coder",
            argv=["jacky", "--continue", "--profile", "coder"],
        )

        assert result is not None
        assert result.endswith("coder")
        assert sys.argv == ["jacky", "--continue"]


class TestSupervisedChildIgnoresStickyProfile:
    """The reserved default gateway s6 slot must not follow active_profile.

    Inside the Docker s6 image the ``gateway-default`` service slot runs a
    bare ``jacky gateway run`` (no ``-p``) to mean "the root JACKY_HOME
    profile". The run-script exports ``JACKY_S6_SUPERVISED_CHILD=1``.
    Without a guard, ``_apply_profile_override`` would read the sticky
    ``active_profile`` file (set by e.g. the dashboard profile switcher) and
    redirect the reserved default gateway into that profile — producing a
    duplicate gateway for the active profile and no real default gateway.
    """

    def test_supervised_child_does_not_follow_active_profile(
        self, tmp_path, monkeypatch
    ):
        """JACKY_S6_SUPERVISED_CHILD + active_profile=briefer must NOT redirect.

        Reproduces the Docker/profile scoping bug: the supervised default
        gateway is launched as bare ``jacky gateway run`` with
        JACKY_HOME=/opt/data (the container root, whose parent is NOT
        ``profiles``), and a sticky ``active_profile`` of another profile.
        The reserved default slot must stay on the root profile.
        """
        jacky_root = tmp_path / ".jacky"
        jacky_root.mkdir(parents=True, exist_ok=True)
        (jacky_root / "active_profile").write_text("briefer")
        (jacky_root / "profiles" / "briefer").mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # Container root JACKY_HOME: parent dir is NOT "profiles", so the
        # #22502 guard does not short-circuit — step 2 (active_profile) runs.
        monkeypatch.setenv("JACKY_HOME", str(jacky_root))
        monkeypatch.setenv("JACKY_S6_SUPERVISED_CHILD", "1")
        monkeypatch.setattr(sys, "argv", ["jacky", "gateway", "run"])

        from jacky_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("JACKY_HOME") == str(jacky_root), (
            "Supervised default gateway must stay on the root profile, not be "
            f"hijacked by active_profile; got {os.environ.get('JACKY_HOME')!r}"
        )

    def test_non_supervised_run_still_follows_active_profile(
        self, tmp_path, monkeypatch
    ):
        """Without the sentinel, a normal `jacky gateway run` still honors
        active_profile — the guard is scoped strictly to supervised children."""
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            jacky_home=None,
            active_profile="briefer",
            argv=["jacky", "gateway", "run"],
        )

        assert result is not None
        assert result.endswith("briefer")

    def test_supervised_named_profile_flag_still_wins(self, tmp_path, monkeypatch):
        """A supervised named-profile slot passes ``-p <name>`` explicitly;
        that must still resolve (the sentinel guard only skips the sticky
        active_profile fallback, never an explicit flag)."""
        jacky_root = tmp_path / ".jacky"
        jacky_root.mkdir(parents=True, exist_ok=True)
        (jacky_root / "active_profile").write_text("briefer")
        (jacky_root / "profiles" / "briefer").mkdir(parents=True, exist_ok=True)
        (jacky_root / "profiles" / "coder").mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("JACKY_HOME", raising=False)
        monkeypatch.setenv("JACKY_S6_SUPERVISED_CHILD", "1")
        monkeypatch.setattr(sys, "argv", ["jacky", "-p", "coder", "gateway", "run"])

        from jacky_cli.main import _apply_profile_override
        _apply_profile_override()

        result = os.environ.get("JACKY_HOME")
        assert result is not None
        assert result.endswith("coder")

