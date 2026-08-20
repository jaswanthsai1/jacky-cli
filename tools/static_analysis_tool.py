#!/usr/bin/env python3
"""
Static Analysis / AST Vulnerability Scanner Tool

Semgrep-style source-code scanning for vulnerability patterns: SQL
injection, command injection, SSRF, hardcoded secrets, and unsafe
deserialization, across Python and JavaScript/TypeScript.

Two engines, selected automatically:

1. ``semgrep`` (preferred when the real ``semgrep`` binary is on PATH) —
   runs it against a small, bundled, offline rule pack
   (``tools/data/semgrep_security_rules.yml``) via ``--config``, so no
   network call to the Semgrep registry is made and results are
   deterministic. This is a real semgrep run, not a re-implementation.

2. ``heuristic`` (built-in fallback, always available) — a pure Python
   scanner: an ``ast``-based visitor for ``.py`` files (so it understands
   real syntax, not just regex — e.g. it won't fire on a string literal
   that merely *contains* the word ``os.system``) and a regex-based
   heuristic scanner for ``.js``/``.jsx``/``.ts``/``.tsx`` files, covering
   the same vulnerability classes as the bundled semgrep rules.

Distinct from ``tools/skills_ast_audit.py``, which is a separate, narrow,
opt-in diagnostic over skill Python files only (dynamic import / dynamic
attribute access patterns) — this tool is a general-purpose vulnerability
scanner over arbitrary project source and is not related to skill
auditing.

Degrades gracefully: engine='auto' (default) uses semgrep when available
and silently falls back to the heuristic engine otherwise. It never
raises for a missing semgrep binary — that's reported in the result's
``engine`` / ``warning`` fields, not an exception.

Usage:
    from tools.static_analysis_tool import static_analysis

    result = static_analysis("/path/to/project")
    print(result["findings"])
"""

import ast
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_BUNDLED_RULES_PATH = os.path.join(os.path.dirname(__file__), "data", "semgrep_security_rules.yml")
_SEMGREP_TIMEOUT = 120  # seconds

_PY_EXTENSIONS = {".py"}
_JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
_SUPPORTED_EXTENSIONS = _PY_EXTENSIONS | _JS_EXTENSIONS

_SKIP_DIR_NAMES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
    "build", ".tox", ".mypy_cache", ".pytest_cache", "vendor",
}

DEFAULT_MAX_FILES = 3_000
DEFAULT_MAX_FINDINGS = 300
DEFAULT_MAX_FILE_BYTES = 2_000_000

_SEVERITY_MAP = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}


# ---------------------------------------------------------------------------
# Semgrep engine
# ---------------------------------------------------------------------------


def check_semgrep_available() -> bool:
    """Return True when a ``semgrep`` binary is discoverable on PATH."""
    return shutil.which("semgrep") is not None


def run_semgrep(
    path: str,
    config: Optional[str] = None,
    timeout: int = _SEMGREP_TIMEOUT,
) -> Dict[str, Any]:
    """Run the real ``semgrep`` CLI against *path* and return its parsed JSON output.

    Raises ``RuntimeError`` (never a raw ``subprocess``/``json`` exception)
    on a missing binary, non-understood exit code, timeout, or unparsable
    output, so callers get one exception type to catch.
    """
    if not check_semgrep_available():
        raise RuntimeError("semgrep is not installed or not on PATH")

    cfg = config or _BUNDLED_RULES_PATH
    cmd = ["semgrep", "--config", cfg, "--json", "--quiet", "--no-git-ignore", path]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"semgrep timed out after {timeout}s") from exc
    except OSError as exc:
        raise RuntimeError(f"failed to execute semgrep: {exc}") from exc

    # 0 = clean run, no findings. 1 = clean run, findings present. Anything
    # else (2 = fatal error, etc.) means the JSON body can't be trusted.
    if proc.returncode not in (0, 1):
        stderr_tail = (proc.stderr or "").strip()[-500:]
        raise RuntimeError(f"semgrep exited {proc.returncode}: {stderr_tail}")

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"could not parse semgrep JSON output: {exc}") from exc


def _normalize_semgrep_results(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map raw semgrep ``results`` entries onto this tool's finding shape."""
    findings: List[Dict[str, Any]] = []
    for item in data.get("results", []) or []:
        extra = item.get("extra", {}) or {}
        metadata = extra.get("metadata", {}) or {}
        start = item.get("start", {}) or {}
        end = item.get("end", {}) or {}
        raw_severity = str(extra.get("severity", "WARNING")).upper()
        findings.append(
            {
                "rule_id": item.get("check_id", "unknown"),
                "category": metadata.get("category", "other"),
                "severity": _SEVERITY_MAP.get(raw_severity, "medium"),
                "file": item.get("path", ""),
                "line": start.get("line"),
                "end_line": end.get("line"),
                "message": extra.get("message", "").strip(),
                "snippet": (extra.get("lines") or "").strip()[:300],
                "cwe": metadata.get("cwe"),
                "engine": "semgrep",
            }
        )
    return findings


# ---------------------------------------------------------------------------
# Heuristic engine — Python (ast-based)
# ---------------------------------------------------------------------------

_SECRET_NAME_RE = re.compile(
    r"(?i)(password|passwd|secret|api[_-]?key|access[_-]?key|auth[_-]?token|private[_-]?key)"
)
_PLACEHOLDER_VALUE_RE = re.compile(
    r"^(?:x{4,}|\*{4,}|0{4,}|changeme|change_me|your[-_]?.*here|example|placeholder|test|dummy|"
    r"fixme|todo|redacted|none|null)$",
    re.IGNORECASE,
)

_PY_COMMAND_INJECTION_CALLS = {("os", "system"), ("os", "popen")}
_PY_SUBPROCESS_FUNCS = {"run", "call", "check_output", "check_call", "Popen"}
_PY_DESERIALIZATION_CALLS = {
    ("pickle", "load"), ("pickle", "loads"),
    ("marshal", "load"), ("marshal", "loads"),
}
_PY_SSRF_CALLS = {
    ("requests", "get"), ("requests", "post"), ("requests", "put"),
    ("requests", "delete"), ("requests", "head"), ("requests", "patch"),
    ("urllib.request", "urlopen"), ("httpx", "get"), ("httpx", "post"),
}


def _dotted_call_name(node: ast.Call) -> Optional[str]:
    """Best-effort dotted name for a Call's func, e.g. 'os.system' or 'eval'."""
    func = node.func
    parts: List[str] = []
    while isinstance(func, ast.Attribute):
        parts.append(func.attr)
        func = func.value
    if isinstance(func, ast.Name):
        parts.append(func.id)
        return ".".join(reversed(parts))
    return None


def _line_snippet(source_lines: List[str], lineno: int) -> str:
    if 1 <= lineno <= len(source_lines):
        return source_lines[lineno - 1].strip()[:300]
    return ""


def _has_kwarg_true(node: ast.Call, name: str) -> bool:
    for kw in node.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant) and kw.value.value is True:
            return True
    return False


def _has_safe_loader_kwarg(node: ast.Call) -> bool:
    for kw in node.keywords:
        if kw.arg == "Loader":
            val = kw.value
            name = getattr(val, "attr", None) or getattr(val, "id", None)
            if name and "Safe" in str(name):
                return True
    return False


class _PythonSecurityVisitor(ast.NodeVisitor):
    def __init__(self, filepath: str, source_lines: List[str]):
        self.filepath = filepath
        self.source_lines = source_lines
        self.findings: List[Dict[str, Any]] = []

    def _add(self, node: ast.AST, category: str, severity: str, message: str, rule_id: str) -> None:
        lineno = getattr(node, "lineno", 0)
        self.findings.append(
            {
                "rule_id": rule_id,
                "category": category,
                "severity": severity,
                "file": self.filepath,
                "line": lineno,
                "end_line": getattr(node, "end_lineno", lineno),
                "message": message,
                "snippet": _line_snippet(self.source_lines, lineno),
                "cwe": None,
                "engine": "heuristic",
            }
        )

    def visit_Call(self, node: ast.Call) -> None:
        dotted = _dotted_call_name(node)
        func_tail = dotted.split(".")[-1] if dotted else None
        module_prefix = dotted.rsplit(".", 1)[0] if dotted and "." in dotted else None

        # Command injection: os.system / os.popen
        if module_prefix and func_tail and (module_prefix, func_tail) in _PY_COMMAND_INJECTION_CALLS:
            self._add(
                node, "command-injection", "high",
                f"{dotted}() executes a shell command — verify no attacker-controlled input reaches this call.",
                "heuristic-command-injection-os",
            )
        # Command injection: subprocess.* with shell=True
        elif module_prefix == "subprocess" and func_tail in _PY_SUBPROCESS_FUNCS and _has_kwarg_true(node, "shell"):
            self._add(
                node, "command-injection", "high",
                f"{dotted}() called with shell=True — shell metacharacters in the command can lead to injection.",
                "heuristic-command-injection-subprocess",
            )
        # Direct eval/exec
        elif dotted in ("eval", "exec") and node.args:
            first = node.args[0]
            if not isinstance(first, ast.Constant):
                self._add(
                    node, "command-injection", "high",
                    f"{dotted}() on a non-literal expression — arbitrary code execution if the input is attacker-controlled.",
                    "heuristic-eval-exec",
                )
        # Unsafe deserialization
        elif module_prefix and func_tail and (module_prefix, func_tail) in _PY_DESERIALIZATION_CALLS:
            self._add(
                node, "unsafe-deserialization", "high",
                f"{dotted}() on untrusted data allows arbitrary code execution during deserialization.",
                "heuristic-unsafe-deserialization",
            )
        elif dotted == "yaml.load" and not _has_safe_loader_kwarg(node):
            self._add(
                node, "unsafe-deserialization", "medium",
                "yaml.load() without Loader=yaml.SafeLoader can execute arbitrary Python objects embedded in the YAML.",
                "heuristic-unsafe-yaml-load",
            )
        # SQL injection: <cursor>.execute(<non-constant-or-formatted string>)
        elif func_tail == "execute" and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) or isinstance(arg, ast.JoinedStr):
                self._add(
                    node, "sql-injection", "high",
                    "SQL query built via string concatenation/f-string instead of a parameterized query.",
                    "heuristic-sql-injection",
                )
            elif (
                isinstance(arg, ast.Call)
                and isinstance(arg.func, ast.Attribute)
                and arg.func.attr == "format"
            ):
                self._add(
                    node, "sql-injection", "high",
                    "SQL query built via str.format() instead of a parameterized query.",
                    "heuristic-sql-injection",
                )
        # SSRF: HTTP client call with a non-literal URL
        elif module_prefix and func_tail and (module_prefix, func_tail) in _PY_SSRF_CALLS and node.args:
            arg = node.args[0]
            if not isinstance(arg, ast.Constant):
                self._add(
                    node, "ssrf", "medium",
                    f"{dotted}() called with a non-literal URL — verify the destination is validated/allow-listed to prevent SSRF.",
                    "heuristic-ssrf",
                )

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            value = node.value.value
            for target in node.targets:
                name = getattr(target, "id", None)
                if not name or not _SECRET_NAME_RE.search(name):
                    continue
                if len(value) < 8 or _PLACEHOLDER_VALUE_RE.match(value):
                    continue
                self._add(
                    node, "hardcoded-secret", "medium",
                    f"Hardcoded credential-shaped string literal assigned to '{name}'.",
                    "heuristic-hardcoded-secret",
                )
        self.generic_visit(node)


def scan_python_source(content: str, filepath: str) -> List[Dict[str, Any]]:
    """AST-scan a single Python source blob for the vulnerability classes above.

    Returns [] on a syntax error rather than raising — a file that doesn't
    parse (wrong Python version, partial/generated code) is skipped, not
    fatal to the overall scan.
    """
    try:
        tree = ast.parse(content, filename=filepath)
    except (SyntaxError, ValueError, RecursionError):
        return []
    visitor = _PythonSecurityVisitor(filepath, content.splitlines())
    visitor.visit(tree)
    return visitor.findings


# ---------------------------------------------------------------------------
# Heuristic engine — JavaScript/TypeScript (regex-based)
# ---------------------------------------------------------------------------

_JS_RULES = [
    (
        "heuristic-eval-injection",
        "command-injection",
        "high",
        re.compile(r"\beval\s*\(|new\s+Function\s*\("),
        "eval()/Function() executes a dynamically-built string as code.",
    ),
    (
        "heuristic-command-injection-child-process",
        "command-injection",
        "high",
        re.compile(r"\b(?:exec|execSync)\s*\(\s*(?!['\"])"),
        "child_process exec()/execSync() with a non-literal command string can lead to shell command injection.",
    ),
    (
        "heuristic-xss-dom-innerhtml",
        "xss",
        "medium",
        re.compile(r"\.(?:innerHTML|outerHTML)\s*=\s*(?!['\"`][^$]*['\"`]\s*;?\s*$)"),
        "Assignment to innerHTML/outerHTML with dynamic content — potential DOM-based XSS.",
    ),
    (
        "heuristic-sql-injection-template-literal",
        "sql-injection",
        "high",
        re.compile(r"\.query\s*\(\s*`[^`]*\$\{"),
        "SQL query built from a template literal with interpolation instead of a parameterized query.",
    ),
    (
        "heuristic-ssrf-dynamic-url",
        "ssrf",
        "medium",
        re.compile(r"\b(?:fetch|axios\.(?:get|post|put|delete))\s*\(\s*(?!['\"`])"),
        "HTTP request with a non-literal URL — verify the destination is validated/allow-listed to prevent SSRF.",
    ),
]

_JS_SECRET_ASSIGN_RE = re.compile(
    r"(?i)\b(?:const|let|var)\s+([A-Za-z0-9_$]*(?:password|passwd|secret|api[_-]?key|access[_-]?key|"
    r"auth[_-]?token|private[_-]?key)[A-Za-z0-9_$]*)\s*=\s*(['\"])([^'\"]{8,})\2"
)


def scan_js_source(content: str, filepath: str) -> List[Dict[str, Any]]:
    """Regex-heuristic scan of a JS/TS source blob for the vulnerability classes above.

    Deliberately conservative (no JS AST parser bundled in this repo's
    toolchain): patterns look for the call/assignment shape, and generally
    only fire when the argument is NOT a plain string literal (so
    ``exec("ls -la")`` is quiet but ``exec(userCmd)`` fires).
    """
    findings: List[Dict[str, Any]] = []
    lines = content.splitlines()

    for lineno, line in enumerate(lines, start=1):
        for rule_id, category, severity, pattern, message in _JS_RULES:
            if pattern.search(line):
                findings.append(
                    {
                        "rule_id": rule_id,
                        "category": category,
                        "severity": severity,
                        "file": filepath,
                        "line": lineno,
                        "end_line": lineno,
                        "message": message,
                        "snippet": line.strip()[:300],
                        "cwe": None,
                        "engine": "heuristic",
                    }
                )
        for m in _JS_SECRET_ASSIGN_RE.finditer(line):
            value = m.group(3)
            if _PLACEHOLDER_VALUE_RE.match(value):
                continue
            findings.append(
                {
                    "rule_id": "heuristic-hardcoded-secret",
                    "category": "hardcoded-secret",
                    "severity": "medium",
                    "file": filepath,
                    "line": lineno,
                    "end_line": lineno,
                    "message": f"Hardcoded credential-shaped string literal assigned to '{m.group(1)}'.",
                    "snippet": line.strip()[:300],
                    "cwe": None,
                    "engine": "heuristic",
                }
            )
    return findings


def scan_source_file(path: str) -> List[Dict[str, Any]]:
    """Dispatch a single file to the Python or JS/TS heuristic scanner by extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError as exc:
        logger.debug("static_analysis: could not read %s (%s)", path, exc)
        return []
    if ext in _PY_EXTENSIONS:
        return scan_python_source(content, path)
    return scan_js_source(content, path)


def find_source_files(
    root: str,
    languages: Optional[List[str]] = None,
    max_files: int = DEFAULT_MAX_FILES,
) -> List[str]:
    """Walk *root* (bounded) collecting supported source files, or return [*root*] if it's a file."""
    if os.path.isfile(root):
        return [root]

    ext_filter = _SUPPORTED_EXTENSIONS
    if languages:
        wanted = set()
        for lang in languages:
            lang_lower = lang.strip().lower()
            if lang_lower == "python":
                wanted |= _PY_EXTENSIONS
            elif lang_lower in ("javascript", "js"):
                wanted |= {".js", ".jsx", ".mjs", ".cjs"}
            elif lang_lower in ("typescript", "ts"):
                wanted |= {".ts", ".tsx"}
        if wanted:
            ext_filter = wanted

    found: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES and not d.startswith(".git")]
        for fname in filenames:
            if len(found) >= max_files:
                return found
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ext_filter:
                continue
            full = os.path.join(dirpath, fname)
            try:
                if os.path.getsize(full) > DEFAULT_MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            found.append(full)
    return found


def run_heuristic_scan(
    path: str,
    languages: Optional[List[str]] = None,
    max_files: int = DEFAULT_MAX_FILES,
    max_findings: int = DEFAULT_MAX_FINDINGS,
) -> Dict[str, Any]:
    """Run the built-in (semgrep-free) AST/regex scanner over *path*."""
    files = find_source_files(path, languages=languages, max_files=max_files)
    findings: List[Dict[str, Any]] = []
    truncated = False
    for f in files:
        findings.extend(scan_source_file(f))
        if len(findings) >= max_findings:
            findings = findings[:max_findings]
            truncated = True
            break
    return {"findings": findings, "files_scanned": len(files), "truncated": truncated}


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def static_analysis(
    path: str,
    engine: str = "auto",
    languages: Optional[List[str]] = None,
    max_findings: int = DEFAULT_MAX_FINDINGS,
) -> Dict[str, Any]:
    """Scan *path* (file or directory) for vulnerability patterns.

    Args:
        path: File or directory to scan.
        engine: 'auto' (default, prefers semgrep and falls back to the
            built-in heuristic scanner), 'semgrep' (force semgrep; reports
            an error rather than raising if it's unavailable/fails), or
            'heuristic' (force the built-in scanner regardless of whether
            semgrep is installed).
        languages: Optional filter, e.g. ['python'] or ['javascript', 'typescript'].
            Only honored by the heuristic engine — semgrep's bundled rule
            pack is language-scoped per rule and always runs all of them.
        max_findings: Cap on number of findings returned.

    Returns:
        {
            "success": bool,
            "path": str,
            "engine": "semgrep" | "heuristic",
            "files_scanned": int,
            "findings_count": int,
            "truncated": bool,
            "findings": [...],
            "warning": Optional[str],   # e.g. "semgrep unavailable, used heuristic engine"
            "error": Optional[str],
        }
    """
    result: Dict[str, Any] = {
        "success": False,
        "path": path,
        "engine": None,
        "files_scanned": 0,
        "findings_count": 0,
        "truncated": False,
        "findings": [],
        "warning": None,
        "error": None,
    }

    if not path or not isinstance(path, str):
        result["error"] = "path is required"
        return result
    if not os.path.exists(path):
        result["error"] = f"Path does not exist: {path}"
        return result

    engine = (engine or "auto").strip().lower()
    if engine not in ("auto", "semgrep", "heuristic"):
        result["error"] = f"Unknown engine {engine!r}. Use auto, semgrep, or heuristic."
        return result

    use_semgrep = engine in ("auto", "semgrep") and check_semgrep_available()

    if use_semgrep:
        try:
            raw = run_semgrep(path)
            findings = _normalize_semgrep_results(raw)
            if len(findings) > max_findings:
                findings = findings[:max_findings]
                result["truncated"] = True
            result.update(
                success=True,
                engine="semgrep",
                files_scanned=len((raw.get("paths", {}) or {}).get("scanned", []) or []),
                findings_count=len(findings),
                findings=findings,
            )
            return result
        except RuntimeError as exc:
            if engine == "semgrep":
                result["error"] = str(exc)
                return result
            # engine == 'auto': fall through to the heuristic engine below,
            # noting why.
            result["warning"] = f"semgrep failed ({exc}); used built-in heuristic engine instead."
            logger.debug("static_analysis: semgrep failed, falling back: %s", exc)

    if engine == "semgrep" and not check_semgrep_available():
        result["error"] = "semgrep is not installed or not on PATH"
        return result

    # Heuristic engine (engine == 'heuristic', or 'auto' with no/failed semgrep).
    if engine == "auto" and result["warning"] is None:
        result["warning"] = "semgrep not found on PATH; used built-in heuristic engine instead."

    heuristic_out = run_heuristic_scan(path, languages=languages, max_findings=max_findings)
    result.update(
        success=True,
        engine="heuristic",
        files_scanned=heuristic_out["files_scanned"],
        findings_count=len(heuristic_out["findings"]),
        truncated=heuristic_out["truncated"],
        findings=heuristic_out["findings"],
    )
    return result


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

from tools.registry import registry, tool_error, tool_result  # noqa: E402

STATIC_ANALYSIS_SCHEMA = {
    "name": "static_analysis",
    "description": (
        "Semgrep-style static analysis: scan a file or directory for "
        "code-level vulnerability patterns — SQL injection, command "
        "injection, SSRF, hardcoded secrets, and unsafe deserialization — "
        "across Python and JavaScript/TypeScript. Uses the real semgrep CLI "
        "against a bundled offline rule pack when semgrep is installed "
        "(engine='semgrep' result field), and degrades gracefully to a "
        "built-in Python-ast + regex heuristic scanner otherwise "
        "(engine='heuristic') — never fails just because semgrep is missing."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File or directory to scan.",
            },
            "engine": {
                "type": "string",
                "enum": ["auto", "semgrep", "heuristic"],
                "description": (
                    "'auto' (default): prefer semgrep, fall back to heuristic. "
                    "'semgrep': require semgrep (reports an error, doesn't crash, if unavailable). "
                    "'heuristic': force the built-in scanner."
                ),
                "default": "auto",
            },
            "languages": {
                "type": "array",
                "items": {"type": "string", "enum": ["python", "javascript", "typescript"]},
                "description": "Restrict the heuristic engine to specific languages. Default: all supported.",
            },
            "max_findings": {
                "type": "integer",
                "description": "Cap on number of findings returned (default 300).",
                "default": DEFAULT_MAX_FINDINGS,
            },
        },
        "required": ["path"],
    },
}


def _static_analysis_handler(args: Dict[str, Any], **_kw) -> str:
    path = args.get("path", "")
    if not path:
        return tool_error("'path' is required.")
    engine = args.get("engine", "auto")
    languages = args.get("languages")
    try:
        max_findings = int(args.get("max_findings") or DEFAULT_MAX_FINDINGS)
    except (TypeError, ValueError):
        max_findings = DEFAULT_MAX_FINDINGS

    result = static_analysis(path, engine=engine, languages=languages, max_findings=max_findings)
    return tool_result(result)


def check_static_analysis_available() -> bool:
    """Always available — the heuristic engine is pure stdlib and never requires semgrep."""
    return True


registry.register(
    name="static_analysis",
    toolset="static_analysis",
    schema=STATIC_ANALYSIS_SCHEMA,
    handler=_static_analysis_handler,
    check_fn=check_static_analysis_available,
    emoji="🔬",
    max_result_size_chars=100_000,
)
