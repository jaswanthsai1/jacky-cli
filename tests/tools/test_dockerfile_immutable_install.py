"""Contract tests for the Docker image's immutable /opt/jacky install tree."""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = REPO_ROOT / "Dockerfile"


def _dockerfile_text() -> str:
    return DOCKERFILE.read_text()


def test_dockerfile_makes_opt_jacky_readonly_for_jacky_user() -> None:
    text = _dockerfile_text()

    # --chmod on the source COPY bakes read-only perms at copy time instead
    # of a separate chmod -R pass (which walked ~30k files — #49113).
    assert "COPY --link --chmod=a+rX,go-w . ." in text
    # The old tree-walking passes must not be present.
    assert "chown -R root:root /opt/jacky" not in text
    assert "chmod -R a+rX /opt/jacky" not in text
    assert "chmod -R a-w /opt/jacky" not in text


def test_dockerfile_keeps_mutable_state_under_opt_data() -> None:
    text = _dockerfile_text()

    assert "ENV JACKY_HOME=/opt/data" in text
    assert "ENV JACKY_WRITE_SAFE_ROOT=/opt/data" in text
    assert 'VOLUME [ "/opt/data" ]' in text


def test_dockerfile_disables_runtime_install_mutations() -> None:
    text = _dockerfile_text()

    assert "ENV PYTHONDONTWRITEBYTECODE=1" in text
    assert "ENV JACKY_DISABLE_LAZY_INSTALLS=1" in text
    assert "JACKY_TUI_DIR=/opt/jacky/ui-tui" in text


def test_dockerfile_does_not_chown_install_trees_to_jacky() -> None:
    text = _dockerfile_text()
    forbidden_patterns = (
        r"chown\s+-R\s+jacky:jacky\s+/opt/jacky/\.venv",
        r"chown\s+-R\s+jacky:jacky\s+/opt/jacky/ui-tui",
        r"chown\s+-R\s+jacky:jacky\s+/opt/jacky/gateway",
        r"chown\s+-R\s+jacky:jacky\s+/opt/jacky/node_modules",
    )
    for pattern in forbidden_patterns:
        assert not re.search(pattern, text), (
            "runtime install trees under /opt/jacky must stay immutable; "
            f"found forbidden pattern {pattern!r}"
        )


def test_dockerfile_bakes_code_scoped_install_method_stamp() -> None:
    """The 'docker' install-method stamp is baked next to the code.

    detect_install_method() reads the code-scoped stamp
    (/opt/jacky/.install_method) first; baking it at build time keeps the
    published image self-identifying as 'docker' WITHOUT writing into the
    shared $JACKY_HOME data volume (which a host install may also use).
    The stamp is created by root in the shim-wiring RUN block; the jacky
    user can't modify it (go-w from the --chmod on the source COPY).
    """
    text = _dockerfile_text()
    assert "printf 'docker\\n' > /opt/jacky/.install_method" in text

    # The stamp must be in the RUN block that wires the exec shim.
    shim_block = re.search(
        r"RUN mkdir -p /opt/jacky/bin && \\\n"
        r"(?:.*\\\n)+?"
        r"\s+printf 'docker\\n' > /opt/jacky/\.install_method",
        text,
    )
    assert shim_block, "install-method stamp must be in the shim-wiring RUN block"


def test_dockerfile_redirects_lazy_installs_to_durable_target() -> None:
    """Immutable image seals the venv but redirects lazy installs to the
    writable data volume, so opt-in backends still install at first use
    without being able to break the sealed core.

    Guards the contract between the Dockerfile env var, the stage2-hook
    seeding, and tools/lazy_deps.py — these three must agree on the path.
    """
    text = _dockerfile_text()
    target = "/opt/data/lazy-packages"

    # The redirect target must be set AND must live under the data volume,
    # never under the immutable /opt/jacky tree.
    assert f"ENV JACKY_LAZY_INSTALL_TARGET={target}" in text
    assert target.startswith("/opt/data/"), "target must be on the durable volume"
    assert "ENV JACKY_LAZY_INSTALL_TARGET=/opt/jacky" not in text

    # The seal flag must still be present — the redirect rides on top of it,
    # it does not replace it.
    assert "ENV JACKY_DISABLE_LAZY_INSTALLS=1" in text

    # stage2-hook must seed + chown the target dir so first-use installs
    # succeed as the unprivileged jacky runtime user.
    stage2 = (REPO_ROOT / "docker" / "stage2-hook.sh").read_text()
    assert '"$JACKY_HOME/lazy-packages"' in stage2, (
        "stage2-hook.sh must create the lazy-packages dir on the data volume"
    )
    assert "lazy-packages" in stage2.split("for sub in", 1)[1].split(";", 1)[0], (
        "lazy-packages must be in the per-boot chown subdir list so it stays "
        "jacky-owned"
    )
