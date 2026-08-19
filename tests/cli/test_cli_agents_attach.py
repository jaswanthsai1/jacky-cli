"""``/agents`` — resume hints + ``/agents attach <delegation_id>`` live tail.

Background delegations (``delegate_task(background=true)``) now carry a real,
SessionDB-backed ``session_id`` (and, when a display channel exists, a
``subagent_id`` into ``tools.delegate_tool``'s live registry). ``/agents``
surfaces a resume hint for each running delegation and ``/agents attach``
polls the live registry so a user can watch a still-running subagent instead
of only seeing its result once the completion event lands.
"""

import jacky_cli.cli as cli
import jacky_cli.cli_commands_mixin as mixin
from jacky_cli.cli import JackyCLI


def _make_cli():
    cli_obj = JackyCLI.__new__(JackyCLI)
    cli_obj._pending_edit_snapshots = {}
    cli_obj._agent_running = False
    return cli_obj


def _capture(monkeypatch):
    printed: list[str] = []
    monkeypatch.setattr(cli, "_cprint", lambda text: printed.append(text))
    return printed


def test_agents_list_shows_resume_hint_for_single_session(monkeypatch):
    cli_obj = _make_cli()
    printed = _capture(monkeypatch)
    monkeypatch.setattr(
        "tools.async_delegation.list_async_delegations",
        lambda: [
            {
                "delegation_id": "deleg_abc123",
                "status": "running",
                "goal": "wait 3 seconds then say done",
                "session_ids": ["sess_xyz"],
            }
        ],
    )
    monkeypatch.setattr(
        "tools.process_registry.process_registry.list_sessions", lambda: []
    )

    cli_obj._handle_agents_command("/agents")

    joined = "\n".join(printed)
    assert "deleg_abc123" in joined
    assert "jacky --resume sess_xyz" in joined
    assert "/agents attach" in joined  # hint to watch it live


def test_agents_list_shows_batch_hint_for_multiple_sessions(monkeypatch):
    cli_obj = _make_cli()
    printed = _capture(monkeypatch)
    monkeypatch.setattr(
        "tools.async_delegation.list_async_delegations",
        lambda: [
            {
                "delegation_id": "deleg_batch1",
                "status": "running",
                "goal": "2 parallel subagents: a; b",
                "session_ids": ["sess_a", "sess_b"],
            }
        ],
    )
    monkeypatch.setattr(
        "tools.process_registry.process_registry.list_sessions", lambda: []
    )

    cli_obj._handle_agents_command("/agents")

    joined = "\n".join(printed)
    assert "2 subagent sessions" in joined
    assert "/agents attach deleg_batch1" in joined


def test_agents_attach_unknown_id_reports_not_found(monkeypatch):
    cli_obj = _make_cli()
    printed = _capture(monkeypatch)
    monkeypatch.setattr(
        "tools.async_delegation.get_async_delegation", lambda did: None
    )

    cli_obj._handle_agents_command("/agents attach deleg_missing")

    joined = "\n".join(printed)
    assert "No delegation found" in joined
    assert "deleg_missing" in joined


def test_agents_attach_finished_delegation_shows_resume_only(monkeypatch):
    cli_obj = _make_cli()
    printed = _capture(monkeypatch)
    monkeypatch.setattr(
        "tools.async_delegation.get_async_delegation",
        lambda did: {
            "delegation_id": did,
            "status": "completed",
            "goal": "done already",
            "session_ids": ["sess_finished"],
        },
    )

    cli_obj._handle_agents_command("/agents attach deleg_done")

    joined = "\n".join(printed)
    assert "already finished" in joined
    assert "jacky --resume sess_finished" in joined


def test_agents_attach_missing_argument_shows_usage(monkeypatch):
    cli_obj = _make_cli()
    printed = _capture(monkeypatch)

    cli_obj._handle_agents_command("/agents attach")

    joined = "\n".join(printed)
    assert "Usage: /agents attach" in joined


def test_agents_attach_polls_live_progress_then_stops_on_completion(monkeypatch):
    """The attach loop should print live tool-call progress from the shared
    subagent registry, then exit cleanly (no infinite loop / real sleep) the
    moment the delegation record flips away from "running"."""
    cli_obj = _make_cli()
    printed = _capture(monkeypatch)

    calls = {"n": 0}

    def _fake_get_async_delegation(did):
        calls["n"] += 1
        status = "running" if calls["n"] == 1 else "completed"
        return {
            "delegation_id": did,
            "status": status,
            "goal": "wait 3 seconds then say done",
            "session_ids": ["sess_live"],
            "subagent_ids": ["sub_1"],
        }

    def _fake_list_active_subagents():
        return [
            {
                "subagent_id": "sub_1",
                "goal": "wait 3 seconds then say done",
                "started_at": 0.0,
                "tool_count": 2,
                "last_tool": "bash",
            }
        ]

    monkeypatch.setattr(
        "tools.async_delegation.get_async_delegation", _fake_get_async_delegation
    )
    monkeypatch.setattr(
        "tools.delegate_tool.list_active_subagents", _fake_list_active_subagents
    )
    monkeypatch.setattr(mixin.time, "sleep", lambda *_a, **_kw: None)

    cli_obj._handle_agents_command("/agents attach deleg_live")

    joined = "\n".join(printed)
    assert "Attached to deleg_live" in joined
    assert "jacky --resume sess_live" in joined
    assert "tool_calls=2" in joined
    assert "current=bash" in joined
    assert "finished: completed" in joined
