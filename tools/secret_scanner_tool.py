#!/usr/bin/env python3
"""
Secret Scanner Tool

Scans a directory (and optionally its git history) for high-entropy
strings and known credential patterns: AWS access keys, GitHub tokens,
Google API keys, OpenAI/Anthropic keys, private key PEM blocks, and
generic ``api_key=`` / ``password=`` assignments.

Pattern reuse: this tool does NOT maintain its own copy of credential
regexes. It imports and reuses the maintained pattern list from
``agent.redact`` (``_PREFIX_PATTERNS``, ``_PRIVATE_KEY_RE``, the
``_SECRET_ENV_NAMES`` / ``_SECRET_CFG_NAMES`` assignment-name vocab) — the
same patterns exercised by ``tests/agent/test_redact.py`` — so a new
vendor prefix added there is picked up here automatically instead of
drifting out of sync with a second copy.

Findings are reported with file/line location and a redacted preview
(never the raw secret value) via ``agent.redact.redact_sensitive_text``.

Usage:
    from tools.secret_scanner_tool import scan_directory_for_secrets, scan_git_history_for_secrets
"""

import json
import logging
import math
import os
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from agent.redact import (
    _PREFIX_PATTERNS,
    _PRIVATE_KEY_RE,
    _SECRET_CFG_NAMES,
    redact_sensitive_text,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pattern set — reuses agent.redact's maintained vendor-prefix list plus a
# handful of scanner-specific detectors (entropy, generic assignments) that
# redact.py has no equivalent for (it redacts known shapes; it doesn't need
# to *discover* generic ones).
# ---------------------------------------------------------------------------

# Named, labeled compilation of the redaction module's prefix patterns so
# findings can report *which* vendor matched instead of a bare "credential".
_LABELED_PREFIX_PATTERNS: List[tuple] = []
_PREFIX_LABEL_RE = re.compile(r"^r?[\"']?([A-Za-z0-9_.\-]+[-_])")
for _pattern in _PREFIX_PATTERNS:
    _m = _PREFIX_LABEL_RE.match(_pattern)
    _label = _m.group(1) if _m else "credential"
    try:
        _LABELED_PREFIX_PATTERNS.append((_label, re.compile(_pattern)))
    except re.error:  # noqa: BLE001 — skip a pattern that doesn't compile standalone
        continue

# Generic ``key = value`` / ``key: value`` assignment for names that don't
# have a recognizable vendor prefix (e.g. an in-house "api_key=xyz123").
# Reuses agent.redact's _SECRET_CFG_NAMES vocabulary so "api key", "token",
# "secret", "password", "credential" etc. all count, matching what the
# redactor itself treats as a secret-shaped key.
_GENERIC_ASSIGNMENT_RE = re.compile(
    rf"\b([A-Za-z0-9_.\-]*{_SECRET_CFG_NAMES}[A-Za-z0-9_.\-]*)\s*[:=]\s*"
    r"""(['"]?)([A-Za-z0-9_\-+/=]{8,})\2""",
    re.IGNORECASE,
)

# Placeholder/test values that should never be flagged as a real credential.
_PLACEHOLDER_RE = re.compile(
    r"^(?:x{4,}|\*{4,}|0{4,}|1{4,}|changeme|change_me|your[-_]?api[-_]?key(?:[-_]?here)?|"
    r"example|placeholder|test|dummy|fixme|todo|redacted|none|null|xxx.*)$",
    re.IGNORECASE,
)

# Shannon entropy threshold above which a bare token (no known prefix, no
# recognizable key name) is flagged as "possible high-entropy secret".
DEFAULT_ENTROPY_THRESHOLD = 4.0
DEFAULT_ENTROPY_MIN_LENGTH = 20

# Generic long base64/hex-ish token candidates for entropy scanning.
_TOKEN_CANDIDATE_RE = re.compile(r"[A-Za-z0-9+/_=\-]{20,}")

# Binary/large-artifact extensions to skip outright.
_SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp3", ".mp4", ".mov", ".avi", ".webm",
    ".so", ".dll", ".dylib", ".class", ".pyc", ".o", ".a",
    ".lock",
}
_SKIP_DIR_NAMES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
    "build", ".tox", ".mypy_cache", ".pytest_cache", "vendor",
}

DEFAULT_MAX_FILE_BYTES = 2_000_000
DEFAULT_MAX_FILES = 5_000
DEFAULT_MAX_FINDINGS = 500


def _shannon_entropy(s: str) -> float:
    """Return the Shannon entropy (bits/char) of *s*. 0.0 for empty input."""
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def _is_probably_binary(sample: bytes) -> bool:
    if b"\x00" in sample:
        return True
    text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
    nontext = sample.translate(None, bytes(text_chars))
    return bool(sample) and (len(nontext) / len(sample) > 0.30)


def _iter_candidate_files(
    root: Path, max_files: int, extra_skip_dirs: Optional[Iterable[str]] = None
) -> Iterable[Path]:
    skip_dirs = set(_SKIP_DIR_NAMES) | set(extra_skip_dirs or ())
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".git")]
        for fname in filenames:
            if count >= max_files:
                return
            path = Path(dirpath) / fname
            if path.suffix.lower() in _SKIP_EXTENSIONS:
                continue
            try:
                if path.stat().st_size > DEFAULT_MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            count += 1
            yield path


def _label_for_match(pattern_index_label: str, matched_text: str) -> str:
    return pattern_index_label.rstrip("-_") or "credential"


def _scan_text_for_secrets(
    text: str,
    *,
    source: str,
    entropy_threshold: float,
    entropy_min_length: int,
    include_entropy: bool,
) -> List[Dict[str, Any]]:
    """Scan a text blob (file content or a git diff hunk) for secrets.

    Returns a list of finding dicts: {source, line, rule, match_preview}.
    The raw matched value is never included — only a redacted preview.
    """
    findings: List[Dict[str, Any]] = []
    lines = text.splitlines()

    for lineno, line in enumerate(lines, start=1):
        # 1. Known vendor prefixes (reused from agent.redact)
        for label, compiled in _LABELED_PREFIX_PATTERNS:
            for m in compiled.finditer(line):
                findings.append(
                    {
                        "source": source,
                        "line": lineno,
                        "rule": f"vendor:{_label_for_match(label, m.group(0))}",
                        "match_preview": redact_sensitive_text(m.group(0), force=True, file_read=True),
                    }
                )

        # 2. Private key PEM blocks (single-line scan won't catch multi-line
        #    blocks — handled separately over the whole text below).

        # 3. Generic key=value / key: value assignments
        for m in _GENERIC_ASSIGNMENT_RE.finditer(line):
            key, _quote, value = m.group(1), m.group(2), m.group(3)
            if _PLACEHOLDER_RE.match(value):
                continue
            findings.append(
                {
                    "source": source,
                    "line": lineno,
                    "rule": f"generic-assignment:{key.strip().lower()}",
                    "match_preview": f"{key}={redact_sensitive_text(value, force=True, file_read=True)}",
                }
            )

        # 4. High-entropy bare tokens (opt-in — noisier than the above)
        if include_entropy:
            for m in _TOKEN_CANDIDATE_RE.finditer(line):
                token = m.group(0)
                if len(token) < entropy_min_length:
                    continue
                if _PLACEHOLDER_RE.match(token):
                    continue
                entropy = _shannon_entropy(token)
                if entropy >= entropy_threshold:
                    findings.append(
                        {
                            "source": source,
                            "line": lineno,
                            "rule": "high-entropy-string",
                            "entropy": round(entropy, 2),
                            "match_preview": redact_sensitive_text(token, force=True, file_read=True),
                        }
                    )

    # Private key PEM blocks span multiple lines — scan the whole blob.
    for m in _PRIVATE_KEY_RE.finditer(text):
        line_no = text.count("\n", 0, m.start()) + 1
        findings.append(
            {
                "source": source,
                "line": line_no,
                "rule": "private-key-pem-block",
                "match_preview": "-----BEGIN [REDACTED] PRIVATE KEY----- ... -----END [REDACTED] PRIVATE KEY-----",
            }
        )

    return findings


def scan_directory_for_secrets(
    directory: str,
    include_entropy: bool = True,
    entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD,
    entropy_min_length: int = DEFAULT_ENTROPY_MIN_LENGTH,
    max_files: int = DEFAULT_MAX_FILES,
    max_findings: int = DEFAULT_MAX_FINDINGS,
) -> str:
    """Scan every text file under *directory* for secrets.

    Args:
        directory: Path to scan (recursively). Binary files, VCS/dependency
            directories (.git, node_modules, .venv, etc.), and files over
            2MB are skipped.
        include_entropy: Also flag bare high-entropy tokens that don't match
            a known vendor prefix or key-name pattern (noisier; default True).
        entropy_threshold: Shannon-entropy bits/char cutoff (default 4.0).
        entropy_min_length: Minimum token length considered for entropy scoring.
        max_files: Cap on number of files scanned (default 5000).
        max_findings: Cap on number of findings returned (default 500).

    Returns:
        JSON string: {"success": bool, "directory": str, "files_scanned": int,
        "findings_count": int, "truncated": bool, "findings": [...], "error": str|None}
    """
    if not directory or not isinstance(directory, str):
        return json.dumps({"success": False, "error": "directory is required"}, ensure_ascii=False)

    root = Path(directory).expanduser()
    if not root.exists():
        return json.dumps({"success": False, "error": f"Path does not exist: {directory}"}, ensure_ascii=False)
    if not root.is_dir():
        return json.dumps({"success": False, "error": f"Not a directory: {directory}"}, ensure_ascii=False)

    try:
        max_files_i = max(1, min(int(max_files) if max_files else DEFAULT_MAX_FILES, 50_000))
    except (TypeError, ValueError):
        max_files_i = DEFAULT_MAX_FILES
    try:
        max_findings_i = max(1, min(int(max_findings) if max_findings else DEFAULT_MAX_FINDINGS, 5_000))
    except (TypeError, ValueError):
        max_findings_i = DEFAULT_MAX_FINDINGS
    try:
        entropy_threshold_f = float(entropy_threshold) if entropy_threshold else DEFAULT_ENTROPY_THRESHOLD
    except (TypeError, ValueError):
        entropy_threshold_f = DEFAULT_ENTROPY_THRESHOLD
    try:
        entropy_min_length_i = max(8, int(entropy_min_length) if entropy_min_length else DEFAULT_ENTROPY_MIN_LENGTH)
    except (TypeError, ValueError):
        entropy_min_length_i = DEFAULT_ENTROPY_MIN_LENGTH

    findings: List[Dict[str, Any]] = []
    files_scanned = 0
    truncated = False

    for path in _iter_candidate_files(root, max_files_i):
        try:
            with open(path, "rb") as fh:
                sample = fh.read(4096)
                if _is_probably_binary(sample):
                    continue
                fh.seek(0)
                raw = fh.read()
        except (OSError, PermissionError) as exc:
            logger.debug("secret_scanner: skipping %s (%s)", path, exc)
            continue

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw.decode("latin-1")
            except Exception:  # noqa: BLE001
                continue

        files_scanned += 1
        rel_path = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        file_findings = _scan_text_for_secrets(
            text,
            source=rel_path,
            entropy_threshold=entropy_threshold_f,
            entropy_min_length=entropy_min_length_i,
            include_entropy=include_entropy,
        )
        findings.extend(file_findings)
        if len(findings) >= max_findings_i:
            findings = findings[:max_findings_i]
            truncated = True
            break

    result = {
        "success": True,
        "directory": str(root),
        "files_scanned": files_scanned,
        "findings_count": len(findings),
        "truncated": truncated,
        "findings": findings,
        "error": None,
    }
    return json.dumps(result, ensure_ascii=False)


def scan_git_history_for_secrets(
    directory: str,
    max_commits: int = 200,
    include_entropy: bool = False,
    entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD,
    entropy_min_length: int = DEFAULT_ENTROPY_MIN_LENGTH,
    max_findings: int = DEFAULT_MAX_FINDINGS,
) -> str:
    """Scan ``git log -p`` output for secrets that were ever committed.

    Useful for catching a credential that was added then later removed —
    it's still recoverable from history. Only scans the *diff* text (added
    and removed lines), not the full blob at each revision, so this is a
    fast pass rather than an exhaustive one (a dedicated tool like
    trufflehog/gitleaks does a full-blob-graph walk; this is the built-in
    equivalent for a quick check without an extra dependency).

    Args:
        directory: Path to a git repository (or a subdirectory of one).
        max_commits: Cap on number of commits inspected via ``-n`` (default 200).
        include_entropy: Also run the high-entropy bare-token detector (default
            False for history scans — noisier over diff text, especially
            around lockfiles/minified diffs).
        entropy_threshold: Shannon-entropy bits/char cutoff (default 4.0).
        entropy_min_length: Minimum token length considered for entropy scoring.
        max_findings: Cap on number of findings returned (default 500).

    Returns:
        JSON string: {"success": bool, "directory": str, "commits_scanned": int,
        "findings_count": int, "truncated": bool, "findings": [...], "error": str|None}
    """
    if not directory or not isinstance(directory, str):
        return json.dumps({"success": False, "error": "directory is required"}, ensure_ascii=False)

    root = Path(directory).expanduser()
    if not root.exists() or not root.is_dir():
        return json.dumps({"success": False, "error": f"Not a directory: {directory}"}, ensure_ascii=False)

    try:
        max_commits_i = max(1, min(int(max_commits) if max_commits else 200, 5_000))
    except (TypeError, ValueError):
        max_commits_i = 200
    try:
        max_findings_i = max(1, min(int(max_findings) if max_findings else DEFAULT_MAX_FINDINGS, 5_000))
    except (TypeError, ValueError):
        max_findings_i = DEFAULT_MAX_FINDINGS
    try:
        entropy_threshold_f = float(entropy_threshold) if entropy_threshold else DEFAULT_ENTROPY_THRESHOLD
    except (TypeError, ValueError):
        entropy_threshold_f = DEFAULT_ENTROPY_THRESHOLD
    try:
        entropy_min_length_i = max(8, int(entropy_min_length) if entropy_min_length else DEFAULT_ENTROPY_MIN_LENGTH)
    except (TypeError, ValueError):
        entropy_min_length_i = DEFAULT_ENTROPY_MIN_LENGTH

    check = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if check.returncode != 0:
        return json.dumps(
            {"success": False, "error": f"Not a git repository: {directory}"},
            ensure_ascii=False,
        )

    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "log", "-p", f"-n{max_commits_i}", "--no-color", "--", "."],
            capture_output=True,
            text=True,
            timeout=120,
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return json.dumps(
            {"success": False, "error": "git log -p timed out after 120s (try a smaller max_commits)"},
            ensure_ascii=False,
        )
    if proc.returncode != 0:
        stderr = proc.stderr or ""
        if "does not have any commits yet" in stderr or "unknown revision" in stderr:
            # Freshly-initialized repo with no history — nothing to scan, not an error.
            return json.dumps(
                {
                    "success": True,
                    "directory": str(root),
                    "commits_scanned": 0,
                    "findings_count": 0,
                    "truncated": False,
                    "findings": [],
                    "error": None,
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {"success": False, "error": f"git log failed: {redact_sensitive_text(stderr.strip())}"},
            ensure_ascii=False,
        )

    log_text = proc.stdout
    commits_scanned = log_text.count("\ncommit ") + (1 if log_text.startswith("commit ") else 0)

    current_commit = None
    current_file = None
    findings: List[Dict[str, Any]] = []
    truncated = False

    for raw_line in log_text.splitlines():
        if raw_line.startswith("commit "):
            current_commit = raw_line.split()[1][:12]
            continue
        if raw_line.startswith("+++ b/") or raw_line.startswith("--- a/"):
            candidate = raw_line[6:]
            if candidate not in ("/dev/null",):
                current_file = candidate
            continue
        if not (raw_line.startswith("+") and not raw_line.startswith("+++")):
            continue  # only scan added lines — removed/context lines are noise duplication

        content = raw_line[1:]
        source = f"{current_file or '?'}@{current_commit or '?'}"
        line_findings = _scan_text_for_secrets(
            content,
            source=source,
            entropy_threshold=entropy_threshold_f,
            entropy_min_length=entropy_min_length_i,
            include_entropy=include_entropy,
        )
        findings.extend(line_findings)
        if len(findings) >= max_findings_i:
            findings = findings[:max_findings_i]
            truncated = True
            break

    result = {
        "success": True,
        "directory": str(root),
        "commits_scanned": commits_scanned,
        "findings_count": len(findings),
        "truncated": truncated,
        "findings": findings,
        "error": None,
    }
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
from tools.registry import registry, tool_error  # noqa: E402


def _secret_scan_dispatch(args: Dict[str, Any], **_kw) -> str:
    action = (args.get("action") or "directory").strip().lower()

    if action == "directory":
        return scan_directory_for_secrets(
            directory=args.get("directory", ""),
            include_entropy=args.get("include_entropy", True),
            entropy_threshold=args.get("entropy_threshold", DEFAULT_ENTROPY_THRESHOLD),
            entropy_min_length=args.get("entropy_min_length", DEFAULT_ENTROPY_MIN_LENGTH),
            max_files=args.get("max_files", DEFAULT_MAX_FILES),
            max_findings=args.get("max_findings", DEFAULT_MAX_FINDINGS),
        )
    if action == "git_history":
        return scan_git_history_for_secrets(
            directory=args.get("directory", ""),
            max_commits=args.get("max_commits", 200),
            include_entropy=args.get("include_entropy", False),
            entropy_threshold=args.get("entropy_threshold", DEFAULT_ENTROPY_THRESHOLD),
            entropy_min_length=args.get("entropy_min_length", DEFAULT_ENTROPY_MIN_LENGTH),
            max_findings=args.get("max_findings", DEFAULT_MAX_FINDINGS),
        )

    return tool_error(f"Unknown secret_scan action '{action}'. Use directory or git_history.")


SECRET_SCAN_SCHEMA = {
    "name": "secret_scan",
    "description": (
        "Scan a directory (or its git history) for leaked credentials: AWS access keys (AKIA...), "
        "GitHub tokens (ghp_/gho_/ghs_/ghu_/ghr_/github_pat_), Google API keys (AIza...), OpenAI/Anthropic-style "
        "keys (sk-...), Slack tokens, Stripe keys, private key PEM blocks, generic api_key=/password=/secret= "
        "assignments, and (optionally) bare high-entropy strings. "
        "action='directory' walks the filesystem tree (skips .git/node_modules/.venv/binaries). "
        "action='git_history' scans `git log -p` diffs so a credential that was committed then later removed "
        "is still caught. Findings never include the raw secret — only a redacted preview and file:line location."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["directory", "git_history"],
                "description": "directory (default): scan files on disk. git_history: scan `git log -p`.",
                "default": "directory",
            },
            "directory": {
                "type": "string",
                "description": "Path to scan. For git_history, must be inside a git repository.",
            },
            "include_entropy": {
                "type": "boolean",
                "description": "Also flag bare high-entropy tokens with no recognized prefix/key-name (noisier). Default true for directory scans, false for git_history.",
            },
            "entropy_threshold": {
                "type": "number",
                "description": "Shannon-entropy bits/char cutoff for the high-entropy detector (default 4.0).",
            },
            "entropy_min_length": {
                "type": "integer",
                "description": "Minimum token length considered for entropy scoring (default 20).",
            },
            "max_files": {
                "type": "integer",
                "description": "For action=directory: cap on number of files scanned (default 5000).",
            },
            "max_commits": {
                "type": "integer",
                "description": "For action=git_history: cap on number of commits scanned via `git log -n` (default 200).",
            },
            "max_findings": {
                "type": "integer",
                "description": "Cap on number of findings returned (default 500).",
            },
        },
        "required": ["directory"],
    },
}


def check_secret_scan_available() -> bool:
    """Always available — pure stdlib (os, re, math, subprocess for git)."""
    return True


registry.register(
    name="secret_scan",
    toolset="secret_scan",
    schema=SECRET_SCAN_SCHEMA,
    handler=_secret_scan_dispatch,
    check_fn=check_secret_scan_available,
    emoji="🔑",
    max_result_size_chars=150_000,
)
