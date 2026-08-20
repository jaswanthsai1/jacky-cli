"""GET /api/agents/delegations — dashboard surfacing for background
delegate_task(background=true) delegations.

Mirrors the CLI's /agents listing so a web dashboard "Agents" panel can show
running/recent delegations, including the child's real session_id(s) for a
"resume/watch" link.
"""

import pytest

from jacky_cli import web_server

pytest.importorskip("starlette.testclient")
from starlette.testclient import TestClient


@pytest.fixture
def client():
    previous = getattr(web_server.app.state, "auth_required", None)
    web_server.app.state.auth_required = False
    test_client = TestClient(web_server.app)
    test_client.headers[web_server._SESSION_HEADER_NAME] = web_server._SESSION_TOKEN
    try:
        yield test_client
    finally:
        if previous is None:
            try:
                delattr(web_server.app.state, "auth_required")
            except AttributeError:
                pass
        else:
            web_server.app.state.auth_required = previous


def test_lists_running_and_finished_delegations(client, monkeypatch):
    fake = [
        {
            "delegation_id": "deleg_1",
            "status": "running",
            "goal": "watch me",
            "session_id": "sess_a",
            "session_ids": ["sess_a"],
        },
        {
            "delegation_id": "deleg_2",
            "status": "completed",
            "goal": "already done",
            "session_id": "sess_b",
            "session_ids": ["sess_b"],
        },
    ]
    monkeypatch.setattr(
        "tools.async_delegation.list_async_delegations", lambda: fake
    )

    resp = client.get("/api/agents/delegations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["running_count"] == 1
    ids = {d["delegation_id"] for d in body["delegations"]}
    assert ids == {"deleg_1", "deleg_2"}
    running = next(d for d in body["delegations"] if d["delegation_id"] == "deleg_1")
    assert running["session_id"] == "sess_a"


def test_import_failure_degrades_to_empty_list(client, monkeypatch):
    def _boom():
        raise RuntimeError("module unavailable")

    monkeypatch.setattr("tools.async_delegation.list_async_delegations", _boom)

    resp = client.get("/api/agents/delegations")
    assert resp.status_code == 200
    assert resp.json() == {"delegations": [], "running_count": 0}
